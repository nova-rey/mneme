from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.c14_scoring import score_c14


def test_c14_scoring_reconciles_conditions_and_fails_latent_gate(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    attempts_dir = evidence / "attempts"
    attempts_dir.mkdir(parents=True)
    conditions = (
        "no_bank",
        "cue_no_bank_assertive",
        "visible_A",
        "visible_B",
        "latent_A_selected_twofold",
        "latent_B_selected_twofold",
        "latent_A_selected_fourfold",
        "latent_B_selected_fourfold",
    )
    coordinates = []
    attempts = []
    for condition in conditions:
        latent = condition.startswith("latent_")
        expected = (
            "unknown"
            if condition in {"no_bank", "cue_no_bank_assertive"}
            else "Tulo"
            if condition.endswith("A") or condition.startswith("latent_A")
            else "Fera"
        )
        answer = (
            "unknown"
            if latent or condition in {"no_bank", "cue_no_bank_assertive"}
            else expected
        )
        coordinate_id = f"A25-{condition}-1"
        coordinate = {
            "coordinate_id": coordinate_id,
            "fixture_id": "A25",
            "item": "equipment locker",
            "seed": 1,
            "condition": condition,
            "bank_source": (
                "The stored codeword for the equipment locker is Tulo." if latent else None
            ),
            "bank_config": {"selector": "selected_A" if latent else "none"},
            "expected": {"answer": expected},
        }
        coordinates.append(coordinate)
        outcome_file = f"{coordinate_id}.json"
        (attempts_dir / outcome_file).write_text(
            json.dumps(
                {
                    "attempt_id": coordinate_id,
                    "status": "COMPLETE",
                    "payload": {
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": answer, "reasoning_content": ""},
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
                "experiment": "C14 scorer test",
                "call_count": len(coordinates),
                "criteria": {
                    "latent_each_polarity_minimum": 1,
                    "visible_each_polarity_minimum": 1,
                    "unknown_control_minimum": 1,
                },
                "coordinates": coordinates,
            }
        ),
        encoding="utf-8",
    )

    scored = score_c14(plan, evidence)

    assert scored["complete_coordinates"] == 8
    assert scored["condition_rates"]["visible_A"]["exact_label_hits"] == 1
    assert scored["condition_rates"]["latent_A_selected_twofold"]["exact_label_hits"] == 0
    assert scored["condition_rates"]["latent_B_selected_fourfold"]["exact_label_hits"] == 0
    assert scored["gain_gate_results"] == {"2": False, "4": False}
    assert scored["heldout_confirmation_authorized_by_gate"] is False


def test_c14_scoring_rejects_unplanned_coordinate(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "index.json").write_text(
        json.dumps({"attempts": [{"attempt_id": "unexpected", "status": "COMPLETE"}]}),
        encoding="utf-8",
    )
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {"experiment": "C14 test", "call_count": 0, "criteria": {}, "coordinates": []}
        ),
        encoding="utf-8",
    )

    try:
        score_c14(plan, evidence)
    except ValueError as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("unplanned C14 evidence must be rejected")
