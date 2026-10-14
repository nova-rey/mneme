from __future__ import annotations

import json
from pathlib import Path

from experiments.mi4.coordinates import build_heldout_coordinates, validate_heldout_coordinate
from experiments.mi4.run_calibration import CalibrationBudget, build_plan


def test_mi4_calibration_plan_is_exactly_frozen_d1_d2_matrix() -> None:
    protocol = json.loads(Path("experiments/mi4/frozen_protocol.json").read_text())
    plan = build_plan(protocol)

    assert len(plan) == 18
    assert {row["fixture_id"] for row in plan} == {
        "D1_after_school_program",
        "D2_community_repair_group",
    }
    assert {row["condition"] for row in plan} == {
        "no_bank",
        "visible_A_resilience",
        "visible_B_simplicity",
        "latent_A_bias_0.5",
        "latent_A_bias_1.0",
        "latent_B_bias_0.5",
        "latent_B_bias_1.0",
        "latent_irrelevant_bias_0.5",
        "latent_irrelevant_bias_1.0",
    }
    assert all(row["thinking"] is True for row in plan)
    assert all(row["request"]["cache_prompt"] is False for row in plan)
    assert all(row["request"]["seed"] == 615103 for row in plan)


def test_mi4_calibration_plan_keeps_visible_text_and_latent_bank_separate() -> None:
    protocol = json.loads(Path("experiments/mi4/frozen_protocol.json").read_text())
    plan = build_plan(protocol)
    latent_rows = [row for row in plan if row["bank"] is not None]
    visible_rows = [row for row in plan if row["condition"].startswith("visible_")]

    assert all(row["bank"] is None for row in visible_rows)
    assert all(row["bank"] is not None for row in latent_rows)
    assert all(
        "Here are conceptual principles"
        not in " ".join(message["content"] for message in row["request"]["messages"])
        for row in latent_rows
    )


def test_mi4_budget_is_bounded_and_has_no_mi1_prior_provenance(tmp_path: Path) -> None:
    path = tmp_path / "budget.json"
    budget = CalibrationBudget(path, hard_limit=1, protocol_sha256="a" * 64)
    budget.reserve("cal_D1_no_bank", "calibration")

    value = json.loads(path.read_text())
    assert value["reservations"] == [{"attempt_id": "cal_D1_no_bank", "phase": "calibration"}]
    assert "prior_calibration_evidence" not in value
    assert budget.counts()["total"] == 1

    try:
        budget.reserve("cal_D1_visible_A", "calibration")
    except RuntimeError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("MI4 calibration budget exceeded its frozen limit")


def test_mi4_heldout_plan_has_96_frozen_cache_disabled_coordinates() -> None:
    protocol = json.loads(Path("experiments/mi4/frozen_protocol.json").read_text())
    plan = build_heldout_coordinates(protocol)

    assert len(plan) == 96
    assert {row["condition"] for row in plan} == set(protocol["heldout"]["conditions"])
    assert {row["thinking"] for row in plan} == {False, True}
    assert {row["seed"] for row in plan} == {615103, 615109}
    for coordinate in plan:
        validate_heldout_coordinate(protocol, coordinate)
        assert coordinate["request"]["cache_prompt"] is False
