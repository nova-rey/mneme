from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "mi2_run_visible_gate_v3_3_1.py"
SPEC = importlib.util.spec_from_file_location("mi2_run_visible_gate_v3_3_1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
FREEZE_PATH = ROOT / "docs/receipts/MI2_Calibration_v3_3_1_Preheldout_Freeze_20261012.json"
APPROVAL_PATH = ROOT / "docs/receipts/MI2_v3_3_1_Visible_Gate_Approval_20261012.json"
CANDIDATE_PATH = ROOT / "docs/receipts/MI2_Calibration_v3_3_1_Candidate_20261012.json"


@pytest.fixture
def frozen() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    value = MODULE.load_frozen(FREEZE_PATH, APPROVAL_PATH, CANDIDATE_PATH)
    return cast(tuple[dict[str, Any], dict[str, Any], dict[str, Any]], value)


def test_hash_pinned_freeze_approval_and_candidate(frozen) -> None:
    freeze, approval, candidate = frozen
    assert freeze["frozen_candidate"] == candidate
    assert approval["freeze"]["sha256"] == MODULE.FREEZE_SHA256
    assert approval["candidate"]["sha256"] == MODULE.CANDIDATE_SHA256
    assert approval["authorized_limits"]["maximum_calls"] == 14
    assert approval["explicit_exclusions"]


def test_execution_projection_contains_only_three_frozen_quantum_items(frozen) -> None:
    _freeze, _approval, candidate = frozen
    execution = MODULE.execution_projection(candidate)
    MODULE.assert_no_forbidden_fields(execution)
    assert [row["id"] for row in execution["tasks"]] == list(MODULE.TASK_IDS)
    assert execution["reasoning"] == "ON"
    assert execution["cache_prompt"] is False
    assert MODULE.TARGET_CARD_OPENING in execution["visible_system_text"]
    assert MODULE.TARGET_CARD_OPENING not in execution["baseline_system_text"]


def test_matrix_is_exactly_six_baseline_and_six_visible_coordinates(frozen) -> None:
    _freeze, _approval, candidate = frozen
    execution = MODULE.execution_projection(candidate)
    matrix = MODULE.build_matrix(execution)
    baseline = MODULE.condition_matrix(execution, "BASELINE")
    visible = MODULE.condition_matrix(execution, "VISIBLE_GUIDANCE")
    assert len(matrix) == MODULE.MATRIX_COUNT == 12
    assert len(baseline) == len(visible) == 6
    assert {row["task_id"] for row in matrix} == set(MODULE.TASK_IDS)
    assert {row["seed"] for row in matrix} == set(MODULE.SEEDS)
    assert all(row["request"]["cache_prompt"] is False for row in matrix)
    assert all(row["request"]["chat_template_kwargs"]["enable_thinking"] for row in matrix)
    assert all("latent" not in row["coordinate_id"] for row in matrix)
    assert all("heldout" not in row["coordinate_id"] for row in matrix)


def test_preflight_is_two_identical_baseline_calls_on_frozen_coordinate(frozen) -> None:
    _freeze, _approval, candidate = frozen
    execution = MODULE.execution_projection(candidate)
    task = next(row for row in execution["tasks"] if row["id"] == "quantum/1-1041")
    messages = [
        {"role": "system", "content": execution["baseline_system_text"]},
        {"role": "user", "content": task["question"]},
    ]
    requests = [MODULE.make_request(execution, messages, MODULE.SEEDS[0]) for _ in (0, 1)]
    assert len(MODULE.PREFLIGHT_IDS) == 2
    assert requests[0] == requests[1]
    assert requests[0]["cache_prompt"] is False
    assert requests[0]["seed"] == 481001


def test_only_visible_prompt_contains_the_frozen_card(frozen) -> None:
    _freeze, _approval, candidate = frozen
    execution = MODULE.execution_projection(candidate)
    matrix = MODULE.build_matrix(execution)
    baseline = next(row for row in matrix if row["condition"] == "BASELINE")
    visible = next(row for row in matrix if row["condition"] == "VISIBLE_GUIDANCE")
    assert not MODULE.execution_target_card_in_prompt(baseline["messages"][0]["content"])
    assert MODULE.execution_target_card_in_prompt(visible["messages"][0]["content"])


def test_forbidden_execution_fields_fail_closed() -> None:
    with pytest.raises(ValueError, match="forbidden field"):
        MODULE.assert_no_forbidden_fields({"nested": {"latent_condition": "not authorized"}})
    with pytest.raises(ValueError, match="forbidden field"):
        MODULE.assert_no_forbidden_fields({"heldout_task": "not authorized"})


def test_frozen_candidate_and_approval_hash_mismatch_fail_closed(tmp_path: Path) -> None:
    tampered = tmp_path / "candidate.json"
    tampered.write_text(CANDIDATE_PATH.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="candidate hash mismatch"):
        MODULE.load_frozen(FREEZE_PATH, APPROVAL_PATH, tampered)


def test_dry_run_writes_receipt_without_network_or_generation(tmp_path: Path) -> None:
    output = tmp_path / "dry-run.json"
    journal = tmp_path / "journal"
    command = [
        sys.executable,
        str(MODULE_PATH),
        "--plan",
        str(FREEZE_PATH),
        "--approval",
        str(APPROVAL_PATH),
        "--candidate",
        str(CANDIDATE_PATH),
        "--journal-root",
        str(journal),
        "--stage",
        "dry-run",
        "--dry-run-output",
        str(output),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["generation_dispatched"] is False
    assert receipt["max_total_calls"] == 14
    assert receipt["task_ids"] == list(MODULE.TASK_IDS)
    assert len(receipt["preflight_ids"]) == 2
    assert receipt["matrix_count"] == 12
    assert "DRY_RUN_VALIDATED_NO_NETWORK_NO_GENERATION" in completed.stdout
    assert not journal.exists()


def test_condition_matrix_rejects_unapproved_condition(frozen) -> None:
    _freeze, _approval, candidate = frozen
    execution = MODULE.execution_projection(candidate)
    with pytest.raises(ValueError, match="outside the v3.3.1 approval"):
        MODULE.condition_matrix(execution, "LATENT")
