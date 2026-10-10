from __future__ import annotations

from typing import Any

from experiments.mi1.fixtures.freeze_suite import build_suite
from experiments.mi1.scoring import score_test_a


def _row(
    attempt_id: str,
    fixture: dict[str, Any],
    condition: str,
    seed: int,
    answer: str | None,
) -> dict[str, Any]:
    expected = fixture["expected_by_condition"][condition]
    path = (
        fixture["checks"]["bank_A_path"]
        if expected == fixture["bank_A"]["expected_answer"]
        else fixture["checks"]["bank_B_path"]
        if expected == fixture["bank_B"]["expected_answer"]
        else []
    )
    final = f"{answer}\nPath: {' -> '.join(path)}" if answer and path else answer or ""
    return {
        "attempt_id": attempt_id,
        "request": {
            "metadata": {
                "suite": "test_a",
                "fixture_id": fixture["fixture_id"],
                "condition": condition,
                "seed": seed,
            }
        },
        "outcome": {
            "status": "COMPLETE" if answer is not None else "FAILED",
            "payload": {"final": final, "finish_reason": "stop" if answer else None},
        },
    }


def test_test_a_scores_paired_counterfactual_path_and_unknown() -> None:
    suite = build_suite()
    fixture = suite["test_a"]["fixtures"][0]
    seed = suite["test_a"]["seeds"][0]
    rows = [
        _row("a1", fixture, "latent_A", seed, fixture["bank_A"]["expected_answer"]),
        _row("a2", fixture, "latent_B", seed, fixture["bank_B"]["expected_answer"]),
        _row("a3", fixture, "no_bank", seed, "unknown"),
    ]
    result = score_test_a(suite, rows)
    assert result["scheduled_coordinates"] == 144
    assert result["observed_coordinates"] == 3
    assert result["missing_coordinates"] == 141
    assert result["latent_counterfactual"]["observed_switches"] == 1
    assert result["latent_counterfactual"]["both_correct_switches"] == 1
    accuracy = result["condition_accuracy"]
    assert accuracy["latent_A"] == {"correct": 1, "n": 24, "rate": 1 / 24}
    assert accuracy["no_bank"] == {"correct": 1, "n": 24, "rate": 1 / 24}


def test_missing_failure_and_wrong_path_remain_in_denominator() -> None:
    suite = build_suite()
    fixture = suite["test_a"]["fixtures"][0]
    seed = suite["test_a"]["seeds"][0]
    wrong_path = {
        "attempt_id": "bad-path",
        "request": {
            "metadata": {
                "suite": "test_a",
                "fixture_id": fixture["fixture_id"],
                "condition": "latent_A",
                "seed": seed,
            }
        },
        "outcome": {
            "status": "COMPLETE",
            "payload": {
                "final": f"{fixture['bank_A']['expected_answer']}\nPath: wrong",
                "finish_reason": "stop",
            },
        },
    }
    failed = _row("failed", fixture, "latent_B", seed, None)
    result = score_test_a(suite, [wrong_path, failed])
    assert result["missing_coordinates"] == 142
    assert result["condition_accuracy"]["latent_A"]["correct"] == 0
    assert result["condition_accuracy"]["latent_B"]["correct"] == 0
    assert sum(row["n"] for row in result["condition_accuracy"].values()) == 144


def test_test_a_scores_live_openai_compatible_journal_payload() -> None:
    suite = build_suite()
    fixture = suite["test_a"]["fixtures"][0]
    seed = suite["test_a"]["seeds"][0]
    answer = fixture["bank_A"]["expected_answer"]
    path = " -> ".join(fixture["checks"]["bank_A_path"])
    row = _row("live-shape", fixture, "visible_A", seed, answer)
    row["outcome"]["payload"] = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": f"{answer}\nPath: {path}",
                    "reasoning_content": "I can follow the supplied directed links.",
                },
            }
        ]
    }
    row["request"] = {
        "attempt_id": "live-shape",
        "metadata": {
            "coordinate": {
                "metadata": {
                    "suite": "test_a",
                    "fixture_id": fixture["fixture_id"],
                    "condition": "visible_A",
                    "seed": seed,
                }
            }
        },
        "request": {"messages": []},
    }

    result = score_test_a(suite, [row])

    assert result["observed_coordinates"] == 1
    assert result["condition_accuracy"]["visible_A"] == {"correct": 1, "n": 24, "rate": 1 / 24}
    scored = next(item for item in result["coordinates"] if item.get("attempt_id") == "live-shape")
    assert scored["finish_reason"] == "stop"
    assert scored["correct"] is True
