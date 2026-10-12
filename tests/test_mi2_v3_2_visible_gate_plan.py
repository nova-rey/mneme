from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "mi2_run_visible_gate_v3_2.py"
SPEC = importlib.util.spec_from_file_location("mi2_run_visible_gate_v3_2", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PLAN_PATH = ROOT / "docs/receipts/MI2_Calibration_v3_2_Preheldout_Freeze_20261012.json"
APPROVAL_PATH = ROOT / "docs/receipts/MI2_v3_2_Visible_Gate_Approval_20261012.json"


@pytest.fixture
def frozen() -> tuple[dict[str, Any], dict[str, Any]]:
    value = MODULE.load_frozen(PLAN_PATH, APPROVAL_PATH)
    return cast(tuple[dict[str, Any], dict[str, Any]], value)


def test_approved_hashes_and_projection_exclude_unapproved_scopes(
    frozen: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    plan, _approval = frozen
    execution = MODULE.execution_projection(plan)
    MODULE.assert_no_forbidden_fields(execution)
    assert [row["id"] for row in execution["tasks"]] == list(MODULE.TASK_IDS)
    assert "latent" not in json.dumps(execution).lower()
    assert "heldout" not in json.dumps(execution).lower()
    assert execution["cache_prompt"] is False
    assert execution["reasoning"] == "ON"


def test_exact_matrix_has_only_three_tasks_two_conditions_two_seeds(
    frozen: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    plan, _approval = frozen
    execution = MODULE.execution_projection(plan)
    matrix = MODULE.build_matrix(execution)
    assert len(matrix) == 12
    assert len({row["coordinate_id"] for row in matrix}) == 12
    assert {row["task_id"] for row in matrix} == set(MODULE.TASK_IDS)
    assert {row["condition"] for row in matrix} == set(MODULE.CONDITIONS)
    assert {row["seed"] for row in matrix} == set(MODULE.SEEDS)
    assert all(row["request"]["cache_prompt"] is False for row in matrix)
    assert all(row["request"]["chat_template_kwargs"]["enable_thinking"] for row in matrix)
    assert all("latent" not in row["coordinate_id"] for row in matrix)


def test_baseline_ceiling_is_checked_before_visible_calls(
    frozen: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    plan, _approval = frozen
    execution = MODULE.execution_projection(plan)
    baseline = MODULE.condition_matrix(execution, "BASELINE")
    visible = MODULE.condition_matrix(execution, "VISIBLE_GUIDANCE")
    assert len(baseline) == len(visible) == 6
    assert {row["task_id"] for row in baseline} == set(MODULE.TASK_IDS)
    assert {row["task_id"] for row in visible} == set(MODULE.TASK_IDS)


def test_only_visible_prompt_contains_target_card(
    frozen: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    plan, _approval = frozen
    execution = MODULE.execution_projection(plan)
    matrix = MODULE.build_matrix(execution)
    baseline = next(row for row in matrix if row["condition"] == "BASELINE")
    visible = next(row for row in matrix if row["condition"] == "VISIBLE_GUIDANCE")
    assert not MODULE.execution_target_card_in_prompt(str(baseline["messages"][0]["content"]))
    assert MODULE.execution_target_card_in_prompt(str(visible["messages"][0]["content"]))


def test_forbidden_execution_fields_fail_closed() -> None:
    with pytest.raises(ValueError, match="forbidden field"):
        MODULE.assert_no_forbidden_fields({"nested": {"latent_condition": "not authorized"}})
    with pytest.raises(ValueError, match="forbidden field"):
        MODULE.assert_no_forbidden_fields({"heldout_task": "not authorized"})


def test_scoring_refuses_to_run_before_all_fourteen_calls_are_durable(
    frozen: tuple[dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    plan, _approval = frozen
    execution = MODULE.execution_projection(plan)
    (tmp_path / "index.json").write_text(
        json.dumps({"attempts": []}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="all 14 exact approved calls"):
        MODULE.score_gate(execution, {"coordinates": []}, tmp_path)


def test_baseline_ceiling_scoring_refuses_to_run_before_six_durable_calls(
    frozen: tuple[dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    plan, _approval = frozen
    execution = MODULE.execution_projection(plan)
    (tmp_path / "index.json").write_text(
        json.dumps({"attempts": []}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="both determinism preflight"):
        MODULE.score_baseline_ceiling(execution, {"coordinates": []}, tmp_path)


def test_baseline_ceiling_gate_rejects_any_visible_attempt(
    frozen: tuple[dict[str, Any], dict[str, Any]], tmp_path: Path
) -> None:
    plan, _approval = frozen
    execution = MODULE.execution_projection(plan)
    visible_id = MODULE.condition_matrix(execution, "VISIBLE_GUIDANCE")[0]["coordinate_id"]
    (tmp_path / "index.json").write_text(
        json.dumps({"attempts": [{"attempt_id": visible_id, "status": "COMPLETE"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="before any visible call"):
        MODULE.score_baseline_ceiling(execution, {"coordinates": []}, tmp_path)

