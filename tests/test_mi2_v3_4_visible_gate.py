from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "mi2_run_visible_gate_v3_4.py"
SPEC = importlib.util.spec_from_file_location("mi2_v3_4", MODULE_PATH)
assert SPEC and SPEC.loader
mi2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mi2)


def frozen_paths() -> tuple[Path, Path, Path]:
    receipts = ROOT / "docs" / "receipts"
    return (
        receipts / "MI2_Calibration_v3_4_Candidate_20261012.json",
        receipts / "MI2_Calibration_v3_4_Preheldout_Freeze_20261012.json",
        receipts / "MI2_v3_4_Visible_Gate_Approval_20261012.json",
    )


def test_frozen_v3_4_cohort_and_execution_matrix_are_exact() -> None:
    candidate, freeze_sha, approval_sha = mi2.load_plan(*frozen_paths())
    matrix = mi2.build_matrix(candidate)
    assert freeze_sha == mi2.FREEZE_SHA256
    assert approval_sha == mi2.APPROVAL_SHA256
    assert len(candidate["tasks"]) == 33
    assert len(matrix) == 198
    assert sum(row["condition"] == "BASELINE" for row in matrix) == 99
    assert sum(row["condition"] == "VISIBLE_GUIDANCE" for row in matrix) == 99
    assert (
        sum(row["trigger_applicability"] == "direct_quantum_process" for row in candidate["tasks"])
        == 31
    )
    assert all(row["request"]["cache_prompt"] is False for row in matrix)
    assert all(row["request"]["seed"] in mi2.SEEDS for row in matrix)


def test_matched_coordinates_change_only_the_visible_system_card() -> None:
    candidate, _, _ = mi2.load_plan(*frozen_paths())
    matrix = mi2.build_matrix(candidate)
    baseline = {
        (row["task_id"], row["seed"]): row for row in matrix if row["condition"] == "BASELINE"
    }
    visible = {
        (row["task_id"], row["seed"]): row
        for row in matrix
        if row["condition"] == "VISIBLE_GUIDANCE"
    }
    assert set(baseline) == set(visible)
    for key in baseline:
        left, right = baseline[key], visible[key]
        assert left["messages"][1] == right["messages"][1]
        assert left["request"] | {"messages": []} == right["request"] | {"messages": []}
        assert left["messages"][0]["content"] != right["messages"][0]["content"]


def test_v3_4_sign_test_uses_frozen_one_sided_exact_rule() -> None:
    assert mi2.sign_test_p(20, 5) < 0.05
    assert mi2.sign_test_p(15, 15) > 0.05
    assert mi2.sign_test_p(0, 0) == 1.0


def test_first_baseline_matrix_response_must_replay_preflight(tmp_path: Path) -> None:
    candidate, _, _ = mi2.load_plan(*frozen_paths())
    journal = mi2.EvidenceJournal(tmp_path, hard_call_limit=mi2.MAX_CALLS)
    matrix_id = next(
        row["coordinate_id"]
        for row in mi2.build_matrix(candidate)
        if row["condition"] == "BASELINE"
        and row["task_id"] == candidate["tasks"][0]["id"]
        and row["seed"] == mi2.SEEDS[0]
    )
    for attempt_id in (*mi2.PREFLIGHT_IDS, matrix_id):
        response = {
            "choices": [
                {
                    "message": {"reasoning_content": "same reasoning", "content": "same answer"},
                    "finish_reason": "stop",
                }
            ]
        }
        journal.begin(attempt_id, {"seed": mi2.SEEDS[0]}, {"phase": "test"})
        journal.complete(attempt_id, response, {"finish_reason": "stop"})
    assert mi2.baseline_replay_status(candidate, tmp_path)["status"] == "PASS"


def test_frozen_input_tampering_fails_closed(tmp_path: Path) -> None:
    candidate_path, freeze_path, approval_path = frozen_paths()
    altered = tmp_path / "candidate.json"
    altered.write_bytes(candidate_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        mi2.load_plan(altered, freeze_path, approval_path)
