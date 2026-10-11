from __future__ import annotations

import hashlib

from experiments.mi1.c14_calibration import CONDITIONS, build_c14_plan


def test_c14_freezes_separate_atomic_recall_calibration_and_confirmation() -> None:
    plan = build_c14_plan(c13_readout_sha256="a" * 64)

    assert plan["call_count"] == 64
    assert len(plan["coordinates"]) == 64
    assert len(plan["confirmation_coordinates_frozen_but_not_run"]) == 64
    assert len({row["fixture_id"] for row in plan["coordinates"]}) == 4
    assert set(row["fixture_id"] for row in plan["confirmation_coordinates_frozen_but_not_run"]) == {
        "A29",
        "A30",
        "A31",
        "A32",
    }
    assert tuple(plan["conditions"]) == CONDITIONS

    for row in plan["coordinates"] + plan["confirmation_coordinates_frozen_but_not_run"]:
        if row["bank_source"] is not None:
            assert hashlib.sha256(row["bank_source"].encode()).hexdigest() == row[
                "bank_source_sha256"
            ]
        else:
            assert row["bank_source_sha256"] is None
        request_text = " ".join(message["content"] for message in row["request"]["messages"])
        if row["condition"].startswith("latent_"):
            assert row["bank_source"] not in request_text
        assert row["request"]["cache_prompt"] is False


def test_c14_confirmation_gain_selection_prefers_minimum_passing_strength() -> None:
    criteria = build_c14_plan(c13_readout_sha256="b" * 64)["confirmation_selection_rule"]
    assert "lower passing gain" in criteria
