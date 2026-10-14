from __future__ import annotations

import json
from pathlib import Path

from experiments.mi4.run_calibration import build_plan


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
