from __future__ import annotations

import hashlib
import json

from experiments.mi1.c15_calibration import (
    CONDITIONS,
    build_c15_plan,
    encoded_bank_text,
)


def test_c15_freeze_has_matched_controls_and_frozen_heldout_coordinates() -> None:
    plan = build_c15_plan(c14_readout_sha256="a" * 64, selector_map_sha256="b" * 64)
    assert plan["status"] == "FROZEN_BEFORE_CALIBRATION_GENERATION"
    assert plan["call_count"] == 80
    assert len(plan["coordinates"]) == 80
    assert plan["conditions"] == list(CONDITIONS)
    ids = [row["coordinate_id"] for row in plan["coordinates"]]
    assert len(ids) == len(set(ids))
    assert plan["confirmation_call_count"] == 72
    assert len(plan["confirmation_coordinates_frozen_not_authorized_until_gate"]) == 72


def test_chat_special_banks_preserve_same_fact_with_explicit_role_tokens() -> None:
    fixture = {"fixture_id": "X", "item": "tool box", "target": "Ruma", "decoy": "Kedo"}
    raw = encoded_bank_text(fixture, "A", "raw")
    system = encoded_bank_text(fixture, "A", "system_turn")
    user = encoded_bank_text(fixture, "A", "user_turn")
    assert system == f"<|turn>system\n{raw}<turn|>\n"
    assert user == f"<|turn>user\n{raw}<turn|>\n"
    assert raw in system and raw in user


def test_c15_freeze_binds_exact_source_digest_and_tokenization_mode() -> None:
    plan = build_c15_plan(c14_readout_sha256="a" * 64, selector_map_sha256="b" * 64)
    rows = {
        row["condition"]: row
        for row in plan["coordinates"]
        if row["fixture_id"] == "A33" and row["seed"] == 34201
    }
    for condition in ("latent_raw_A", "latent_system_turn_A", "latent_user_turn_A"):
        row = rows[condition]
        assert hashlib.sha256(row["bank_source"].encode()).hexdigest() == row["bank_source_sha256"]
    assert rows["latent_raw_A"]["tokenization_mode"] == "raw"
    assert rows["latent_system_turn_A"]["tokenization_mode"] == "chat-special"
    assert rows["latent_user_turn_A"]["tokenization_mode"] == "chat-special"
    for row in rows.values():
        canonical = json.dumps(
            row["request"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        assert hashlib.sha256(canonical.encode()).hexdigest() == row["request_sha256"]
