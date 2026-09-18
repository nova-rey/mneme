from __future__ import annotations

import json
from pathlib import Path

import pytest

from mneme.experiments.baseline import (
    BaselineError,
    BaselineObservation,
    build_baseline_report,
    measure_baseline,
)


def _observations() -> list[BaselineObservation]:
    return [
        BaselineObservation(0, 0, 0, "same answer"),
        BaselineObservation(0, 0, 1, "same answer"),
        BaselineObservation(0, 1, 0, "long answer here"),
        BaselineObservation(0, 1, 1, "different answer"),
        BaselineObservation(1, 0, 0, "same answer"),
        BaselineObservation(1, 1, 0, "other answer"),
    ]


def test_baseline_measurement_compares_scientific_coordinates() -> None:
    result = measure_baseline(_observations())

    assert result["observation_count"] == 6
    assert result["subject_count"] == 2
    assert result["probe_count"] == 2
    assert result["within_instance"]["pair_count"] == 2
    assert result["between_instance"]["pair_count"] == 2
    assert result["within_instance"]["exact_match_rate"] == pytest.approx(0.5)
    assert result["between_instance"]["exact_match_rate"] == pytest.approx(0.5)
    assert 0 <= result["within_instance"]["mean_lexical_jaccard"] <= 1


def test_measurement_rejects_duplicate_observation_coordinates() -> None:
    observations = [{
        "subject_slot": 0,
        "probe_ordinal": 0,
        "repetition": 0,
        "output": "first",
    }, {
        "subject_slot": 0,
        "probe_ordinal": 0,
        "repetition": 0,
        "output": "second",
    }]
    with pytest.raises(BaselineError, match="duplicate observation coordinate"):
        measure_baseline(observations)


def test_report_is_machine_readable_sanitized_and_human_inspectable(tmp_path: Path) -> None:
    report = build_baseline_report(
        experiment_name="shared-input-control",
        contract_revision=3,
        contract_sha256="a" * 64,
        software_revision="deadbeef",
        subject_bindings=[
            {"slot": 0, "lineage_id": "lineage-a", "checkpoint_id": "checkpoint-a"},
        ],
        host={
            "model_id": "mneme-fake-v1",
            "provider": "builtin",
            "capabilities": ["text_generation", "seed_control"],
            "execution": {"api_token": "must-not-appear", "mode": "deterministic"},
        },
        budgets={"planned_calls": 8, "max_model_calls": 8},
        observations=_observations(),
        actual_usage={"calls": 6, "raw_output": "must-not-appear"},
        evaluation_isolation={"unchanged": True},
        restart_resume={"resumed": True},
    )

    payload = report.to_dict()
    assert payload["scientific_identity"] == {
        "name": "shared-input-control",
        "contract_revision": 3,
        "label": "shared-input-control / revision 3",
    }
    serialized = report.to_json()
    assert json.loads(serialized)["measurements"]["observation_count"] == 6
    assert "must-not-appear" not in serialized
    assert "same answer" not in serialized
    assert "DISABLED" in report.text()
    assert "individuality or personality" in report.text()

    json_path = tmp_path / "baseline.json"
    text_path = tmp_path / "baseline.txt"
    report.write(json_path, text_path)
    assert json.loads(json_path.read_text())["report_kind"] == "mneme-no-learning-baseline"
    assert "ordinary no-learning output variation" in text_path.read_text()


def test_empty_pair_groups_are_explicitly_unavailable() -> None:
    result = measure_baseline([BaselineObservation(0, 0, 0, "one")])
    assert result["within_instance"]["pair_count"] == 0
    assert result["within_instance"]["exact_match_rate"] is None
    assert result["between_instance"]["pair_count"] == 0


def test_report_rejects_invalid_identity() -> None:
    with pytest.raises(BaselineError, match="contract_revision"):
        build_baseline_report(
            experiment_name="baseline",
            contract_revision=0,
            contract_sha256="a" * 64,
            software_revision="head",
            subject_bindings=[],
            host={},
            budgets={},
            observations=[],
        )
