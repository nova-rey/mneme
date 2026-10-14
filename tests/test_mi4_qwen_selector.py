from __future__ import annotations

import numpy as np
import pytest

from experiments.mi1.native.bank import BankManifest, MemoryBank
from experiments.mi1.native.query_capture import QueryCapture, QueryLayerCapture
from experiments.mi4.qwen_batch_contract import validate_single_sequence_bank_prefill
from experiments.mi4.select_qwen_sites import select_sites


def _bank(name: str, slots: int, offset: float) -> MemoryBank:
    keys = {
        layer: np.full((slots, 8, 128), offset + layer / 100, dtype=np.float32)
        for layer in range(36)
    }
    values = {layer: value.copy() for layer, value in keys.items()}
    manifest = BankManifest(
        model_sha256="m" * 64,
        llama_commit="c" * 40,
        architecture="qwen3-4b",
        layer_ids=tuple(range(36)),
        head_dim=128,
        kv_heads_by_layer=(8,) * 36,
        slot_count=slots,
    )
    return MemoryBank(manifest, keys, values, name, tuple(range(slots)))


def _capture(prompt_tokens: int, bank_slots: int) -> QueryCapture:
    layers = {}
    for layer in range(36):
        query = np.ones((prompt_tokens, 32, 128), dtype=np.float32)
        attention = np.zeros((prompt_tokens, 32, 256 + bank_slots), dtype=np.float32)
        attention[:, :, :prompt_tokens] = 0.5 / prompt_tokens
        attention[:, :, 256:] = 0.5 / bank_slots
        layers[layer] = QueryLayerCapture(query, attention)
    return QueryCapture(tuple(range(prompt_tokens)), layers)


def test_qwen_selector_accepts_native_variable_bank_lengths_and_freezes_16_sites() -> None:
    banks = {
        "A_resilience": _bank("a", 409, 1.0),
        "B_simplicity": _bank("b", 415, 0.5),
        "irrelevant_visual_composition": _bank("i", 418, 0.0),
    }
    captures = {
        prompt: {
            name: _capture(token_count, banks[name].manifest.slot_count)
            for name in banks
        }
        for prompt, token_count in (
            ("D1_after_school_program", 31),
            ("D2_community_repair_group", 29),
        )
    }
    result = select_sites(captures, banks)

    assert result["layer_count"] == 36
    assert result["query_heads"] == 32
    assert result["kv_groups"] == 8
    assert len(result["selected_layers"]) == 4
    assert len(result["selected_query_sites"]) == 16
    assert {row["target_bank"] for row in result["capture_facts"]} == set(banks)


def test_qwen_prefill_guard_accepts_one_sequence_and_rejects_multi_sequence() -> None:
    validate_single_sequence_bank_prefill(
        unique_sequences=1,
        token_count=136,
        mask_query_counts=(136, 136, 136),
    )

    with pytest.raises(ValueError, match="one unique sequence"):
        validate_single_sequence_bank_prefill(
            unique_sequences=2,
            token_count=136,
            mask_query_counts=(136,),
        )

    with pytest.raises(ValueError, match="one query row per prompt token"):
        validate_single_sequence_bank_prefill(
            unique_sequences=1,
            token_count=136,
            mask_query_counts=(135,),
        )
