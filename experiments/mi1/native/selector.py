"""Appendix-C MI1 site calibration helpers for captured Gemma tensors."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]


def gemma4_source_kv_mapping(
    *, n_layers: int, n_kv_layers_from_start: int, is_swa: tuple[bool, ...]
) -> tuple[tuple[int, int], ...]:
    """Mirror the pinned Gemma4 shared-KV source-layer mapping."""
    if n_layers <= 0 or len(is_swa) != n_layers:
        raise ValueError("one SWA flag is required per Gemma4 query layer")
    if not 0 < n_kv_layers_from_start <= n_layers:
        raise ValueError("KV-producing layer count is outside the model")
    result: list[tuple[int, int]] = []
    for query_layer in range(n_layers):
        if query_layer < n_kv_layers_from_start:
            source_layer = query_layer
        else:
            source_layer = n_kv_layers_from_start - (2 if is_swa[query_layer] else 1)
        if not 0 <= source_layer < n_kv_layers_from_start:
            raise ValueError("Gemma4 shared-KV source mapping is invalid")
        result.append((query_layer, source_layer))
    return tuple(result)


def target_reference_alignment(
    queries: FloatArray,
    target_keys: FloatArray,
    reference_keys: FloatArray,
) -> FloatArray:
    """Compute Eq. 3 per-query-head target/reference alignment margins.

    Queries are normalized pre-RoPE rows ``[q_heads, head_dim]``. Target and
    reference keys are normalized pre-RoPE token banks ``[slots, kv_heads,
    head_dim]``. Query heads map contiguously to KV groups as in Gemma4 GQA.
    The returned score is max target alignment minus max reference alignment.
    """
    query = np.asarray(queries, dtype=np.float32)
    target = np.asarray(target_keys, dtype=np.float32)
    reference = np.asarray(reference_keys, dtype=np.float32)
    if query.ndim != 2 or target.ndim != 3 or reference.ndim != 3:
        raise ValueError("Q must be [heads,d] and target/reference K [slots,kv_heads,d]")
    if target.shape[1:] != reference.shape[1:] or query.shape[-1] != target.shape[-1]:
        raise ValueError("target/reference/query dimensions must match")
    if query.shape[0] % target.shape[1]:
        raise ValueError("query heads must evenly map to KV groups")
    if target.shape[0] == 0 or reference.shape[0] == 0:
        raise ValueError("target and reference banks must be nonempty")
    groups = query.shape[0] // target.shape[1]
    result = np.empty((query.shape[0],), dtype=np.float32)
    scale = np.float32(1.0 / np.sqrt(query.shape[-1]))
    for head in range(query.shape[0]):
        kv_head = head // groups
        target_score = target[:, kv_head, :] @ query[head] * scale
        reference_score = reference[:, kv_head, :] @ query[head] * scale
        result[head] = np.max(target_score) - np.max(reference_score)
    return result


def grouped_alignment_margin(
    queries: FloatArray,
    target_keys: FloatArray,
    reference_keys: FloatArray,
) -> FloatArray:
    """Average Eq. 3 Q-head margins by the KV group that supplies their K."""
    per_head = target_reference_alignment(queries, target_keys, reference_keys)
    n_groups = np.asarray(target_keys).shape[1]
    q_per_group = per_head.size // n_groups
    return per_head.reshape(n_groups, q_per_group).mean(axis=1, dtype=np.float32)


def attention_mass(
    probabilities: FloatArray,
    *,
    prompt_slots: int,
    bank_slots: int,
) -> tuple[FloatArray, FloatArray]:
    """Split captured attention probabilities into prompt and bank mass.

    Input uses llama.cpp ``kq_soft_max`` ordering normalized to
    ``[keys, q_heads]`` for one query. The returned arrays have one value per
    head. This deliberately does not infer cognition; it supports the frozen
    Appendix-C site-calibration statistic only.
    """
    values = np.asarray(probabilities, dtype=np.float32)
    if values.ndim != 2 or prompt_slots <= 0 or bank_slots <= 0:
        raise ValueError("probabilities must be [keys,heads] with positive slot counts")
    if values.shape[0] != prompt_slots + bank_slots:
        raise ValueError("prompt and bank slot counts do not cover captured keys")
    prompt = values[:prompt_slots].sum(axis=0)
    bank = values[prompt_slots:].sum(axis=0)
    return prompt, bank


def sparse_site_list(scores: FloatArray, *, keep_per_layer: int = 1) -> tuple[tuple[int, int], ...]:
    """Select deterministic top heads per layer from ``[layers,heads]`` scores."""
    values = np.asarray(scores, dtype=np.float32)
    if values.ndim != 2 or keep_per_layer < 1 or keep_per_layer > values.shape[1]:
        raise ValueError("scores must be [layers,heads] and keep_per_layer must fit")
    selected: list[tuple[int, int]] = []
    for layer, row in enumerate(values):
        # Stable tie handling uses ascending head index.
        order = np.lexsort((np.arange(row.size), -row))[:keep_per_layer]
        selected.extend((layer, int(head)) for head in order)
    return tuple(selected)


def appendix_c_sparse_selector(
    alignment: FloatArray,
    bank_mass: FloatArray,
    prompt_mass: FloatArray,
    *,
    groups_per_layer: int = 1,
    top_layers: int = 4,
) -> tuple[tuple[int, int], ...]:
    """Freeze group sites with per-layer top-k then global top-m selection.

    `alignment`, `bank_mass`, and `prompt_mass` are `[layers, kv_groups]`.
    Eq. 3 target/reference alignment is the primary rank. Bank mass breaks
    ties; prompt mass is retained as an audit diagnostic and not rewarded.
    The global layer score is the mean of selected group alignment scores.
    """
    scores = np.asarray(alignment, dtype=np.float32)
    masses = np.asarray(bank_mass, dtype=np.float32)
    prompt = np.asarray(prompt_mass, dtype=np.float32)
    if scores.ndim != 2 or masses.shape != scores.shape or prompt.shape != scores.shape:
        raise ValueError("alignment and mass matrices must share [layers,kv_groups] shape")
    if not 1 <= groups_per_layer <= scores.shape[1] or not 1 <= top_layers <= scores.shape[0]:
        raise ValueError("selector k/m exceed available KV groups/layers")
    per_layer: list[list[int]] = []
    layer_scores = np.full(scores.shape[0], -np.inf, dtype=np.float32)
    for layer, row in enumerate(scores):
        order = np.lexsort((np.arange(row.size), -masses[layer], -row))[:groups_per_layer]
        per_layer.append([int(group) for group in order])
        layer_scores[layer] = float(np.mean(row[order]))
    chosen_layers = np.lexsort((np.arange(layer_scores.size), -layer_scores))[:top_layers]
    return tuple((int(layer), group) for layer in chosen_layers for group in per_layer[int(layer)])


def expand_kv_groups(
    groups: tuple[tuple[int, int], ...],
    *,
    query_heads: int,
    kv_groups: int,
) -> tuple[tuple[int, int], ...]:
    """Expand frozen `(query_layer, kv_group)` sites to their Q-head masks."""
    if query_heads <= 0 or kv_groups <= 0 or query_heads % kv_groups:
        raise ValueError("query heads must be a positive multiple of KV groups")
    heads_per_group = query_heads // kv_groups
    expanded: list[tuple[int, int]] = []
    for layer, group in groups:
        if not 0 <= group < kv_groups:
            raise ValueError("selected KV group is out of range")
        expanded.extend(
            (layer, group * heads_per_group + offset) for offset in range(heads_per_group)
        )
    return tuple(expanded)
