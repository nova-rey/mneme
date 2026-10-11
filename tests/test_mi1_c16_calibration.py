from __future__ import annotations

import hashlib
import json

from experiments.mi1.c16_calibration import (
    CONDITIONS,
    assistant_bank_text,
    build_c16_plan,
)


def test_c16_freezes_assistant_role_calibration_and_disjoint_confirmation() -> None:
    plan = build_c16_plan(c15b_readout_sha256="a" * 64, selector_map_sha256="b" * 64)
    assert plan["status"] == "FROZEN_BEFORE_CALIBRATION_GENERATION"
    assert len(plan["coordinates"]) == plan["call_count"] == 48
    assert len(plan["confirmation_coordinates_frozen_not_authorized_until_gate"]) == 40
    assert plan["conditions"] == list(CONDITIONS)
    calibration_ids = {row["fixture_id"] for row in plan["coordinates"]}
    confirmation_ids = {
        row["fixture_id"]
        for row in plan["confirmation_coordinates_frozen_not_authorized_until_gate"]
    }
    assert calibration_ids.isdisjoint(confirmation_ids)


def test_c16_assistant_bank_uses_same_fact_and_special_role_tokens() -> None:
    fixture = {"fixture_id": "X", "item": "tool case", "target": "Ruma", "decoy": "Kedo"}
    text = assistant_bank_text(fixture, "A")
    assert text == "<|turn>assistant\nThe stored codeword for the tool case is Ruma.<turn|>\n"
    plan = build_c16_plan(c15b_readout_sha256="a" * 64, selector_map_sha256="b" * 64)
    row = next(row for row in plan["coordinates"] if row["condition"] == "latent_assistant_turn_A")
    assert hashlib.sha256(row["bank_source"].encode()).hexdigest() == row["bank_source_sha256"]
    assert row["tokenization_mode"] == "chat-special"
    assert row["expected"] == {"answer": row["bank_fact"].split(" is ")[1][:-1]}


def test_c16_requests_are_seeded_no_cache_and_confirmation_is_frozen() -> None:
    plan = build_c16_plan(c15b_readout_sha256="a" * 64, selector_map_sha256="b" * 64)
    for row in plan["coordinates"]:
        assert row["request"]["cache_prompt"] is False
        assert row["request"]["seed"] == row["seed"]
        canonical = json.dumps(
            row["request"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        assert hashlib.sha256(canonical.encode()).hexdigest() == row["request_sha256"]
