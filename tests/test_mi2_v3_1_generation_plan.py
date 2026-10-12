from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "mi2_run_calibration_v3_1.py"
SPEC = importlib.util.spec_from_file_location("mi2_run_calibration_v3_1", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def plan_fixture() -> dict[str, Any]:
    rows = []
    for item_id in MODULE.CALIBRATION_IDS:
        rows.append(
            {
                "id": item_id,
                "question_utf8": f"question for {item_id}",
                "question_sha256": "a" * 64,
                "process_score_criteria": ["class", "operation", "scope"],
                "official_answer_component_count": 1,
                "official_answers_sha256": "b" * 64,
            }
        )
    return {
        "package_id": MODULE.PACKAGE_ID,
        "calibration_version": "v3.1",
        "calibration": {
            "items": rows,
            "conditions": list(MODULE.CONDITIONS),
            "seeds": list(MODULE.SEEDS),
        },
        "paper_card": {
            "trigger": "trigger",
            "action": "action",
            "trap_check": "check",
        },
        "prompt_contract": {"system_baseline": "base", "visible_system": "visible"},
        "seed_and_runtime": {
            "sampler": {
                "seed_values": list(MODULE.SEEDS),
                "temperature": 0.35,
                "top_k": 40,
                "top_p": 0.9,
                "min_p": 0.05,
                "max_tokens": 8192,
                "stream": True,
            },
            "name": "google/gemma-4-E4B-it",
            "reasoning": "ON",
            "prompt_cache": False,
            "context_size": 8192,
        },
        "heldout_embargo": {"items": [{"id": "must-not-enter-execution"}]},
    }


def test_frozen_execution_projection_contains_only_calibration_rows() -> None:
    execution = MODULE.frozen_execution_inputs(plan_fixture())
    assert [row["id"] for row in execution["items"]] == list(MODULE.CALIBRATION_IDS)
    assert "heldout_embargo" not in execution
    MODULE.assert_no_heldout_fields(execution)


def test_frozen_matrix_is_exactly_thirty_unique_coordinates() -> None:
    execution = MODULE.frozen_execution_inputs(plan_fixture())
    ids = MODULE.matrix_ids(execution)
    assert len(ids) == 30
    assert len(set(ids)) == 30
    assert all(identifier.startswith("v31_cal_atomic_") for identifier in ids)


def test_latent_request_does_not_put_card_in_chat_prompt() -> None:
    execution = MODULE.frozen_execution_inputs(plan_fixture())
    coordinate = MODULE.make_coordinate(
        execution,
        {"selected_query_sites": [[layer, head] for layer in range(4) for head in range(4)]},
        MODULE.PLAN_SHA256,
        MODULE.SELECTOR_SHA256,
        execution["items"][0],
        "LATENT_TARGET_BANK_BIAS_0.5",
        481001,
    )
    serialized_messages = str(coordinate["request"]["messages"])
    assert execution["target_card"] not in serialized_messages
    assert coordinate["bank_source"] == execution["target_card"]
    assert coordinate["request"]["cache_prompt"] is False
    assert coordinate["request"]["max_tokens"] == 8192


def test_coordinate_builder_rejects_nonfrozen_item_or_condition() -> None:
    execution = MODULE.frozen_execution_inputs(plan_fixture())
    row = execution["items"][0]
    with pytest.raises(ValueError, match="outside the approved calibration matrix"):
        MODULE.make_coordinate(
            execution,
            {"selected_query_sites": []},
            MODULE.PLAN_SHA256,
            MODULE.SELECTOR_SHA256,
            {**row, "id": "atomic/1-99"},
            "BASELINE",
            481001,
        )


def test_execution_inputs_reject_heldout_keys() -> None:
    with pytest.raises(ValueError, match="heldout field leaked"):
        MODULE.assert_no_heldout_fields({"nested": {"heldout_prompt": "secret"}})
