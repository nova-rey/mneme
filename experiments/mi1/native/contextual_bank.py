"""Paper-style contextualized descriptor slots for MI1 banks."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from experiments.mi1.native.bank import MemoryBank


def descriptor_positions_in_wrapped_tokens(
    descriptor_token_ids: tuple[int, ...], wrapped_token_ids: tuple[int, ...]
) -> tuple[int, ...]:
    """Find descriptor tokens inside the wrapper tokenization, excluding BOS.

    The raw and wrapped encodings both include the tokenizer's leading BOS.
    We match the remaining descriptor token sequence exactly and fail closed
    when tokenization is not compositional or the match is ambiguous.
    """
    if not descriptor_token_ids or not wrapped_token_ids:
        raise ValueError("descriptor and wrapped token sequences must be nonempty")
    needle = descriptor_token_ids[1:] if len(descriptor_token_ids) > 1 else descriptor_token_ids
    if not needle:
        raise ValueError("descriptor has no content tokens after its leading special token")
    starts = [
        start
        for start in range(len(wrapped_token_ids) - len(needle) + 1)
        if wrapped_token_ids[start : start + len(needle)] == needle
    ]
    if len(starts) != 1:
        raise ValueError(
            f"descriptor token sequence must occur exactly once in wrapper, found {len(starts)}"
        )
    return tuple(range(starts[0], starts[0] + len(needle)))


def contextualized_descriptor(
    wrapped_bank: MemoryBank,
    descriptor_token_ids: tuple[int, ...],
    *,
    wrapper_text: str,
) -> MemoryBank:
    """Keep descriptor positions whose hidden states were computed in a wrapper.

    This mirrors the MI paper's text-derived bank recipe: contextualize source
    text first, then retain positions aligned to the descriptor content.
    """
    positions = descriptor_positions_in_wrapped_tokens(
        descriptor_token_ids, wrapped_bank.token_ids
    )
    keys = {layer: tensor[list(positions)].copy() for layer, tensor in wrapped_bank.keys.items()}
    values = {
        layer: tensor[list(positions)].copy() for layer, tensor in wrapped_bank.values.items()
    }
    manifest = replace(wrapped_bank.manifest, slot_count=len(positions))
    result = MemoryBank(
        manifest=manifest,
        keys=keys,
        values=values,
        source_text=wrapper_text,
        token_ids=tuple(wrapped_bank.token_ids[index] for index in positions),
    )
    result.validate()
    return result


def concatenate_banks(left: MemoryBank, right: MemoryBank) -> MemoryBank:
    """Concatenate token slots from compatible banks without changing layers."""
    lm = left.manifest
    rm = right.manifest
    compatible = (
        lm.model_sha256 == rm.model_sha256
        and lm.llama_commit == rm.llama_commit
        and lm.architecture == rm.architecture
        and lm.layer_ids == rm.layer_ids
        and lm.kv_heads_by_layer == rm.kv_heads_by_layer
        and left._head_dims() == right._head_dims()
    )
    if not compatible:
        raise ValueError("cannot concatenate memory banks with different host dimensions")
    manifest = replace(lm, slot_count=lm.slot_count + rm.slot_count)
    keys = {
        layer: np.concatenate((left.keys[layer], right.keys[layer]), axis=0)
        for layer in lm.layer_ids
    }
    values = {
        layer: np.concatenate((left.values[layer], right.values[layer]), axis=0)
        for layer in lm.layer_ids
    }
    result = MemoryBank(
        manifest=manifest,
        keys=keys,
        values=values,
        source_text=f"{left.source_text}\n\n{right.source_text}",
        token_ids=left.token_ids + right.token_ids,
    )
    result.validate()
    return result
