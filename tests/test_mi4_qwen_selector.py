from __future__ import annotations

import numpy as np
import pytest

from experiments.mi1.native.bank import BankManifest, MemoryBank
from experiments.mi1.native.query_capture import QueryCapture, QueryLayerCapture
from experiments.mi4.prepare_bank_variants import build_variants
from experiments.mi4.qwen_batch_contract import validate_single_sequence_bank_prefill
from experiments.mi4.qwen_preflight import _messages, build_generation_request
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


def test_variant_builder_writes_fixed_biases_without_mutating_sources(tmp_path) -> None:
    import json
    import struct

    bank_root = tmp_path / "banks"
    bank_root.mkdir()
    names = ("A_resilience", "B_simplicity", "irrelevant_visual_composition")
    source_bytes = (
        struct.pack("<8sIIII", b"MI1KV002", 2, 36, 1, 0)
        + struct.pack("<IIff", 0, 1, 0.25, 0.5)
        + struct.pack("<f", 0.0)
    )
    for name in names:
        (bank_root / f"{name}.mi1").write_bytes(source_bytes)
    selector = tmp_path / "selector.json"
    selector.write_text(
        json.dumps({"selected_query_sites": [[35, 28], [35, 29]]}), encoding="utf-8"
    )
    result = build_variants(
        bank_root=bank_root, selector_path=selector, output_root=tmp_path / "out"
    )
    assert len(result["variants"]) == 6
    assert {row["bias"] for row in result["variants"]} == {0.5, 1.0}
    assert all(row["size_bytes"] == len(source_bytes) + 16 for row in result["variants"])
    assert all((bank_root / f"{name}.mi1").read_bytes() == source_bytes for name in names)


def test_preflight_request_freezes_cache_off_sampler_and_thinking_mode() -> None:
    protocol = {
        "generation": {
            "system": "system",
            "sampler": {
                "temperature": 0.35,
                "top_k": 40,
                "top_p": 0.9,
                "min_p": 0.05,
                "max_tokens": 8192,
                "cache_prompt": False,
            },
        },
        "neighborhoods": {
            "A_resilience": {"descriptor_text": "A"},
            "B_simplicity": {"descriptor_text": "B"},
        },
        "calibration": {
            "visible_prompt_wrapper": {"prefix": "prefix", "suffix": "suffix"}
        },
    }
    messages = _messages(protocol, "visible_A_resilience", "problem")
    request = build_generation_request(
        messages=messages,
        seed=615103,
        thinking=True,
        sampler=protocol["generation"]["sampler"],
    )
    assert request["cache_prompt"] is False
    assert request["chat_template_kwargs"] == {"enable_thinking": True}
    assert request["seed"] == 615103
    assert messages[1]["content"] == "prefixAsuffixproblem"
