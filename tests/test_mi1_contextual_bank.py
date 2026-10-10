from __future__ import annotations

import numpy as np
import pytest

from experiments.mi1.native.bank import BankManifest, MemoryBank
from experiments.mi1.native.contextual_bank import (
    concatenate_banks,
    contextualized_descriptor,
    descriptor_positions_in_wrapped_tokens,
)


def bank(token_ids: tuple[int, ...], offset: float = 0.0) -> MemoryBank:
    slots = len(token_ids)
    manifest = BankManifest(
        model_sha256="0" * 64,
        llama_commit="test-commit",
        architecture="gemma4-e4b",
        layer_ids=(0, 1),
        head_dim=2,
        kv_heads_by_layer=(1, 1),
        slot_count=slots,
    )
    keys = {
        layer: np.arange(slots * 2, dtype=np.float32).reshape(slots, 1, 2) + offset
        for layer in manifest.layer_ids
    }
    values = {layer: tensor + 10 for layer, tensor in keys.items()}
    result = MemoryBank(manifest, keys, values, "source", token_ids)
    result.validate()
    return result


def test_contextualized_descriptor_keeps_only_aligned_positions() -> None:
    wrapped = bank((1, 20, 10, 11, 21), offset=100)
    result = contextualized_descriptor(
        wrapped, (1, 10, 11), wrapper_text="prefix 10 11 suffix"
    )
    assert result.token_ids == (10, 11)
    assert result.manifest.slot_count == 2
    np.testing.assert_array_equal(result.keys[0], wrapped.keys[0][2:4])
    np.testing.assert_array_equal(result.values[1], wrapped.values[1][2:4])


def test_concatenated_bank_preserves_order_and_updates_slot_count() -> None:
    raw = bank((1, 10, 11))
    contextual = bank((10, 11), offset=100)
    result = concatenate_banks(raw, contextual)
    assert result.token_ids == (1, 10, 11, 10, 11)
    assert result.manifest.slot_count == 5
    np.testing.assert_array_equal(result.keys[0], np.concatenate((raw.keys[0], contextual.keys[0])))


def test_descriptor_alignment_fails_closed_for_missing_or_ambiguous_tokens() -> None:
    with pytest.raises(ValueError, match="exactly once"):
        descriptor_positions_in_wrapped_tokens((1, 10, 11), (1, 20, 12, 13))
    with pytest.raises(ValueError, match="exactly once"):
        descriptor_positions_in_wrapped_tokens((1, 10, 11), (1, 10, 11, 20, 10, 11))
