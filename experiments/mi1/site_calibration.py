"""Deterministic, pre-scored Appendix-C query-site calibration for MI1."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from experiments.mi1.native.bank import MemoryBank
from experiments.mi1.native.query_capture import QueryCapture
from experiments.mi1.native.selector import (
    appendix_c_sparse_selector,
    attention_mass,
    expand_kv_groups,
    gemma4_source_kv_mapping,
    grouped_alignment_margin,
)


@dataclass(frozen=True)
class SiteSelection:
    """Aggregate group scores and frozen sparse/broad query sites."""

    alignment: np.ndarray
    bank_mass: np.ndarray
    prompt_mass: np.ndarray
    sparse_groups: tuple[tuple[int, int], ...]
    sparse_query_sites: tuple[tuple[int, int], ...]
    broad_groups: tuple[tuple[int, int], ...]
    broad_query_sites: tuple[tuple[int, int], ...]
    source_kv_by_query_layer: tuple[tuple[int, int], ...]


def _source_layer_mapping(
    query_dims_by_layer: tuple[int, ...], bank_layer_ids: tuple[int, ...]
) -> tuple[tuple[int, int], ...]:
    """Resolve the pinned Gemma4 shared-KV source layer for every Q layer."""
    n_layers = len(query_dims_by_layer)
    if bank_layer_ids == tuple(range(n_layers)):
        return tuple((layer, layer) for layer in range(n_layers))
    n_kv_layers = len(bank_layer_ids)
    if bank_layer_ids != tuple(range(n_kv_layers)) or n_kv_layers >= n_layers:
        raise ValueError("MI1 bank layers do not match Gemma4 shared-KV source layout")
    full_attention_dim = max(query_dims_by_layer)
    if full_attention_dim <= 0 or any(dim <= 0 for dim in query_dims_by_layer):
        raise ValueError("query head dimensions must be positive")
    # This pinned Gemma4 E4B exposes 256-wide sliding-window and 512-wide full
    # attention Q heads. Shared K/V layers use the preceding SWA source or the
    # latest full-attention source, respectively.
    is_swa = tuple(dim != full_attention_dim for dim in query_dims_by_layer)
    return gemma4_source_kv_mapping(
        n_layers=n_layers, n_kv_layers_from_start=n_kv_layers, is_swa=is_swa
    )


def select_query_sites(
    captures: dict[str, QueryCapture],
    target_banks: dict[str, MemoryBank],
    reference_bank: MemoryBank,
    *,
    top_layers: int = 4,
) -> SiteSelection:
    """Score sites across held calibration prompts, never scored prompts.

    Each capture must be a prefill with its task target bank attached to every
    query head. The query representation comes from the last prompt token;
    target/reference alignment uses normalized pre-RoPE keys.
    """
    if not captures or set(captures) != set(target_banks):
        raise ValueError("every calibration capture requires its exact target bank")
    first_capture = next(iter(captures.values()))
    layer_ids = set(first_capture.layers)
    if layer_ids != set(range(42)):
        raise ValueError("site calibration requires all 42 Gemma4 query layers")
    alignment_rows: list[np.ndarray] = []
    bank_mass_rows: list[np.ndarray] = []
    prompt_mass_rows: list[np.ndarray] = []
    source_mapping: tuple[tuple[int, int], ...] | None = None

    for key in sorted(captures):
        capture = captures[key]
        target_bank = target_banks[key]
        if set(capture.layers) != layer_ids:
            raise ValueError("calibration captures have different query layer sets")
        mapping = _source_layer_mapping(
            tuple(capture.layers[layer].query.shape[-1] for layer in sorted(layer_ids)),
            target_bank.manifest.layer_ids,
        )
        if source_mapping is None:
            source_mapping = mapping
        elif source_mapping != mapping:
            raise ValueError("calibration tasks do not share one Gemma4 KV source mapping")
        source_by_query = dict(mapping)
        layer_alignment: list[np.ndarray] = []
        layer_bank_mass: list[np.ndarray] = []
        layer_prompt_mass: list[np.ndarray] = []
        for layer in sorted(layer_ids):
            q = capture.layers[layer].query[-1]
            source_layer = source_by_query[layer]
            target_keys = target_bank.keys[source_layer]
            reference_keys = reference_bank.keys[source_layer]
            margins = grouped_alignment_margin(q, target_keys, reference_keys)
            probabilities = capture.layers[layer].attention[-1].T
            # llama.cpp reserves a 256-token prompt cache even for short inputs;
            # the native graph appends bank slots after that capacity. The helper
            # verifies the unused capacity is masked, then measures actual tokens.
            prompt_mass, bank_mass = attention_mass(
                probabilities,
                prompt_slots=len(capture.token_ids),
                bank_slots=len(target_bank.token_ids),
            )
            kv_groups = target_keys.shape[1]
            q_per_group = q.shape[0] // kv_groups
            grouped_bank_mass = bank_mass.reshape(kv_groups, q_per_group).mean(axis=1)
            grouped_prompt_mass = prompt_mass.reshape(kv_groups, q_per_group).mean(axis=1)
            layer_alignment.append(margins)
            layer_bank_mass.append(grouped_bank_mass)
            layer_prompt_mass.append(grouped_prompt_mass)
        alignment_rows.append(np.stack(layer_alignment))
        bank_mass_rows.append(np.stack(layer_bank_mass))
        prompt_mass_rows.append(np.stack(layer_prompt_mass))

    alignment = np.mean(np.stack(alignment_rows), axis=0, dtype=np.float32)
    bank_mass = np.mean(np.stack(bank_mass_rows), axis=0, dtype=np.float32)
    prompt_mass = np.mean(np.stack(prompt_mass_rows), axis=0, dtype=np.float32)
    sparse_groups = appendix_c_sparse_selector(
        alignment, bank_mass, prompt_mass, groups_per_layer=1, top_layers=top_layers
    )
    broad_groups = tuple((layer, group) for layer in range(42) for group in range(2))
    return SiteSelection(
        alignment=alignment,
        bank_mass=bank_mass,
        prompt_mass=prompt_mass,
        sparse_groups=sparse_groups,
        sparse_query_sites=expand_kv_groups(
            sparse_groups, query_heads=8, kv_groups=2
        ),
        broad_groups=broad_groups,
        broad_query_sites=expand_kv_groups(
            broad_groups, query_heads=8, kv_groups=2
        ),
        source_kv_by_query_layer=source_mapping or (),
    )
