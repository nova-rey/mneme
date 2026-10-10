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

    for key in sorted(captures):
        capture = captures[key]
        target_bank = target_banks[key]
        if set(capture.layers) != layer_ids:
            raise ValueError("calibration captures have different query layer sets")
        layer_alignment: list[np.ndarray] = []
        layer_bank_mass: list[np.ndarray] = []
        layer_prompt_mass: list[np.ndarray] = []
        for layer in sorted(layer_ids):
            q = capture.layers[layer].query[-1]
            target_keys = target_bank.keys[layer]
            reference_keys = reference_bank.keys[layer]
            margins = grouped_alignment_margin(q, target_keys, reference_keys)
            probabilities = capture.layers[layer].attention[-1].T
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
    )
