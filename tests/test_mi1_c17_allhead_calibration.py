from __future__ import annotations

from experiments.mi1.c17_allhead_calibration import ALL_HEAD_CONFIG, build_plan


def test_c17_freezes_allhead_gate_and_disjoint_confirmation() -> None:
    plan = build_plan(c16_plan_sha256="a" * 64, c16_readout_sha256="b" * 64)
    assert len(plan["calibration_coordinates"]) == 40
    assert len(plan["confirmation_coordinates"]) == 40
    assert plan["call_count"] == {
        "calibration": 40,
        "confirmation_if_gate_passes": 40,
        "maximum": 80,
    }
    assert {row["fixture_id"] for row in plan["calibration_coordinates"]} == {
        "A41",
        "A42",
        "A43",
        "A44",
    }
    assert {row["fixture_id"] for row in plan["confirmation_coordinates"]} == {
        "A45",
        "A46",
        "A47",
        "A48",
    }
    for row in plan["calibration_coordinates"] + plan["confirmation_coordinates"]:
        assert row["request"]["cache_prompt"] is False
        assert row["metadata"]["suite"] == "c17_allhead_maximum_access"
        if row["condition"].startswith("latent_all_"):
            assert row["bank_config"] == ALL_HEAD_CONFIG
            assert row["bank_action"] == "attach"
            assert "stored codeword" not in row["request"]["messages"][1]["content"]
        else:
            assert row["bank_action"] == "clear"


def test_c17_calibration_gate_is_stricter_than_single_hit() -> None:
    plan = build_plan(c16_plan_sha256="a" * 64, c16_readout_sha256="b" * 64)
    gate = plan["gate"]
    assert gate["latent_all_A_minimum"] == gate["latent_all_B_minimum"] == 6
    assert gate["visible_A_minimum"] == gate["visible_B_minimum"] == 7
    assert gate["no_bank_minimum"] == 7
    assert gate["confirmation_minimum_each_condition"] == 7
