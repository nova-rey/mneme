from __future__ import annotations

from pathlib import Path
from typing import Any

from mneme.development import EdgeState, LearnerState
from tools.run_p23_saa_ten_thread import call_budget_breakdown, maximum_call_budget
from tools.run_p23_saa_ten_thread_live import (
    _consequence_subtest,
    _measurement_field_check,
    _record_measurement_unknown,
)


class _Pilot:
    def __init__(self) -> None:
        self.artifacts: list[tuple[str, str, dict[str, Any]]] = []

    def publish_artifact(self, category: str, name: str, value: dict[str, Any]) -> None:
        self.artifacts.append((category, name, value))


class _Controller:
    def __init__(self) -> None:
        self.state = LearnerState(
            edge_states=(
                EdgeState("e1", context="general", accessibility=100_000, support=100_000),
            )
        )

    def _pin(self) -> object:
        return object()

    def _learner_state(self, _pin: object) -> LearnerState:
        return self.state


def test_assessor_validation_miss_is_recorded_without_credit_or_absence() -> None:
    pilot = _Pilot()

    _record_measurement_unknown(
        pilot,
        call_id="assess-T04-7",
        coordinate={"thread": "T04", "turn": 7},
        operation_id="development-SAA-T04-7",
        validation_error="invalid monitor row",
    )

    assert len(pilot.artifacts) == 1
    category, name, receipt = pilot.artifacts[0]
    assert category == "assessment"
    assert name == "assess-T04-7-measurement-unknown.json"
    assert receipt["status"] == "measurement_unknown / interpretation_unavailable"
    assert receipt["admitted_relationships"] == 0
    assert receipt["learner_credit"] == 0
    assert receipt["absence_evidence"] is False
    assert receipt["validation_error"] == "invalid monitor row"


def test_measurement_field_gate_ignores_cold_start_and_off_removal() -> None:
    check = _measurement_field_check(
        [{"condition": "SAA", "field": {"field_enabled": True, "total_pressure": 20000}}],
        [
            {
                "condition": "SAA",
                "probe": 0,
                "field": {"field_enabled": True, "total_pressure": 20000},
            }
        ],
        [
            {"condition": "SAA_ON", "field": {"field_enabled": True, "total_pressure": 20000}},
            {"condition": "SAA_OFF", "field": None},
            {
                "condition": "SAA_RESTORED",
                "field": {"field_enabled": True, "total_pressure": 20000},
            },
        ],
    )
    assert check == {"checked": 4, "invalid": [], "valid": True}


def test_measurement_field_gate_rejects_zero_measurement_pressure() -> None:
    check = _measurement_field_check(
        [{"condition": "SAA", "field": {"field_enabled": True, "total_pressure": 0}}],
        [],
        [],
    )
    assert check["valid"] is False
    assert check["invalid"] == [{"condition": "SAA", "coordinate": None, "total_pressure": 0.0}]


def test_frozen_call_budget_matches_all_configured_coordinates() -> None:
    budget = call_budget_breakdown()
    assert budget["qualification"] == 3
    assert budget["consequence_provider_calls"] == 0
    assert maximum_call_budget() == sum(budget.values()) == 392


def test_consequence_subtest_adjusts_contextual_route_without_mutating_primary() -> None:
    result = _consequence_subtest(_Controller(), Path("checkpoint.sqlite3"))
    assert result["status"] == "PASS"
    assert result["primary_state_mutated"] is False
    assert result["positive_external"]["route_score"][1] > result["before"]["route_score"][1]
    assert result["negative_external"]["route_score"][1] < result["before"]["route_score"][1]
    assert result["edge_state_preserved"] is True
