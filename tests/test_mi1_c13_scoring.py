from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.c13_scoring import score_c13


def test_c13_scoring_applies_frozen_gate_and_prefers_selected_sites(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    attempts_dir = evidence / "attempts"
    attempts_dir.mkdir(parents=True)
    conditions = (
        "no_bank",
        "cue_no_bank_assertive",
        "visible_A",
        "visible_B",
        "latent_A_selected_assertive_fourfold",
        "latent_B_selected_assertive_fourfold",
        "latent_A_broad_assertive_fourfold",
        "latent_B_broad_assertive_fourfold",
        "latent_irrelevant_broad_assertive_fourfold",
    )
    coordinates = []
    attempts = []
    for fixture in ("A13", "A14"):
        for seed in (1, 2):
            for condition in conditions:
                answer = (
                    "unknown"
                    if condition in {"no_bank", "cue_no_bank_assertive", "latent_irrelevant_broad_assertive_fourfold"}
                    else "Target" if condition.endswith("A")
                    else "Decoy" if condition.endswith("B")
                    else "unknown"
                )
                if condition.startswith("latent_A_"):
                    answer = "Target"
                elif condition.startswith("latent_B_"):
                    answer = "Decoy"
                coordinate_id = f"{fixture}-{condition}-{seed}"
                source = {
                    "coordinate_id": coordinate_id,
                    "fixture_id": fixture,
                    "seed": seed,
                    "condition": condition,
                    "bank_source": "- Start activates Target.\n"
                    if condition.startswith("latent_A_")
                    else "- Start activates Decoy.\n"
                    if condition.startswith("latent_B_")
                    else None,
                    "bank_config": {"selector": "selected" if "selected" in condition else "all_heads"},
                    "expected": {"answer": answer},
                }
                coordinates.append(source)
                outcome_file = f"{coordinate_id}.complete.json"
                (attempts_dir / outcome_file).write_text(
                    json.dumps(
                        {
                            "attempt_id": coordinate_id,
                            "status": "COMPLETE",
                            "payload": {
                                "choices": [
                                    {
                                        "finish_reason": "stop",
                                        "message": {
                                            "content": answer,
                                            "reasoning_content": "Start activates Target."
                                            if source["bank_source"]
                                            else "No supplied facts.",
                                        },
                                    }
                                ]
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                attempts.append(
                    {
                        "attempt_id": coordinate_id,
                        "status": "COMPLETE",
                        "outcome_file": outcome_file,
                        "request_sha256": "request",
                        "outcome_sha256": "outcome",
                    }
                )
    (evidence / "index.json").write_text(json.dumps({"attempts": attempts}), encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "experiment": "test C13",
                "call_count": len(coordinates),
                "criteria": {
                    "calibration_per_polarity_minimum": 4,
                    "visible_each_polarity_minimum": 4,
                    "unknown_controls_minimum": 4,
                },
                "coordinates": coordinates,
            }
        ),
        encoding="utf-8",
    )

    scored = score_c13(plan, evidence)

    assert scored["complete_coordinates"] == len(coordinates)
    assert scored["calibration_gate_passed"] is True
    assert scored["routing_modes_passing_predeclared_gate"] == ["selected", "broad"]
    assert scored["selected_confirmation_routing_mode"] == "selected"
    assert scored["condition_rates"]["visible_B"]["exact_label_hits"] == 4


def test_c13_scoring_rejects_unplanned_or_duplicate_attempts(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps({"call_count": 0, "coordinates": [], "criteria": {}}),
        encoding="utf-8",
    )
    (evidence / "index.json").write_text(
        json.dumps({"attempts": [{"attempt_id": "unplanned", "status": "COMPLETE"}]}),
        encoding="utf-8",
    )

    try:
        score_c13(plan, evidence)
    except ValueError as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("unplanned C13 evidence must be rejected")
