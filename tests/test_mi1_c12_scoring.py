from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.mi1.c12_scoring import score_c12


def _write_case(
    root: Path, coordinate_id: str, answer: str, expected: str, condition: str
) -> dict[str, str]:
    attempts = root / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    request_name = f"{coordinate_id}.request.json"
    outcome_name = f"{coordinate_id}.complete.json"
    coordinate = {
        "coordinate_id": coordinate_id,
        "expected": {"answer": expected},
        "metadata": {"condition": condition, "fixture_id": "A13", "seed": 1},
        "bank_source": "- A activates B.\n" if condition.startswith("latent_") else None,
    }
    (attempts / request_name).write_text(
        json.dumps({"metadata": {"coordinate": coordinate}}), encoding="utf-8"
    )
    (attempts / outcome_name).write_text(
        json.dumps(
            {
                "attempt_id": coordinate_id,
                "status": "COMPLETE",
                "payload": {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": answer, "reasoning_content": "A activates B."},
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "attempt_id": coordinate_id,
        "request_file": request_name,
        "outcome_file": outcome_name,
        "request_sha256": "r",
        "outcome_sha256": "o",
        "status": "COMPLETE",
    }


def test_c12_scoring_uses_exact_answer_and_complete_bank_fact_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    attempt = _write_case(evidence, "c1", "Tulo", "Tulo", "latent_A_zero")
    (evidence / "index.json").write_text(json.dumps({"attempts": [attempt]}), encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "experiment": "test",
                "call_count": 1,
                "criteria": {
                    "latent_each_polarity_minimum": 1,
                    "visible_each_polarity_minimum": 1,
                    "unknown_control_minimum": 1,
                },
                "coordinates": [
                    {
                        "coordinate_id": "c1",
                        "expected": {"answer": "Tulo"},
                        "metadata": {"condition": "latent_A_zero", "fixture_id": "A13", "seed": 1},
                        "bank_source": "- A activates B.\n",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scored = score_c12(plan, evidence)
    assert scored["complete_coordinates"] == 1
    assert scored["coordinates"][0]["answer_correct"] is True
    assert scored["coordinates"][0]["all_source_facts_mentioned"] is True
    assert scored["calibration_gate_passed"] is False


def test_c12_scoring_rejects_duplicate_attempts(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    attempt = _write_case(evidence, "c1", "unknown", "unknown", "no_bank")
    (evidence / "index.json").write_text(
        json.dumps({"attempts": [attempt, attempt]}), encoding="utf-8"
    )
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "experiment": "test",
                "call_count": 1,
                "criteria": {
                    "latent_each_polarity_minimum": 1,
                    "visible_each_polarity_minimum": 1,
                    "unknown_control_minimum": 1,
                },
                "coordinates": [
                    {
                        "coordinate_id": "c1",
                        "expected": {"answer": "unknown"},
                        "metadata": {"condition": "no_bank", "fixture_id": "A13", "seed": 1},
                        "bank_source": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        score_c12(plan, evidence)
