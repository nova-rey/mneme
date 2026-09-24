from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.experiments.pilot_study import (
    AssessmentPlan,
    EvaluationPlan,
    PilotSchedule,
    PilotStatus,
    PilotStudy,
    ProductionAssessmentAdapter,
)
from mneme.hosts import FakeHost


@dataclass
class _FakePilot:
    state: str = PilotStatus.QUALIFIED.value
    progress: dict[str, Any] | None = None

    def status(self) -> dict[str, str]:
        return {"status": self.state}

    def begin_pilot(self) -> dict[str, str]:
        self.state = PilotStatus.RUNNING.value
        return self.status()

    def pause(self, _reason: str) -> dict[str, str]:
        self.state = PilotStatus.PAUSED.value
        return self.status()

    def resume(self) -> dict[str, str]:
        self.state = PilotStatus.RUNNING.value
        return self.status()

    def finish(self, *, summary: dict[str, Any]) -> dict[str, Any]:
        self.state = PilotStatus.COMPLETE.value
        self.summary = summary
        return {"status": self.state}

    def fail(self, _reason: str, *, details: dict[str, Any]) -> dict[str, Any]:
        self.state = PilotStatus.FAILED.value
        self.failure = details
        return {"status": self.state}

    def reservations_report(self) -> dict[str, Any]:
        return {"calls": []}

    def publish_artifact(self, _category: str, _name: str, value: dict[str, Any]) -> None:
        self.report = value

    def study_progress(self) -> dict[str, Any]:
        return dict(self.progress or {})

    def record_study_progress(self, **fields: Any) -> None:
        self.progress = {**self.study_progress(), **fields}


class _FakeRuntime:
    def __init__(self) -> None:
        self.subjects = {0: SimpleNamespace(host=FakeHost()), 1: SimpleNamespace(host=FakeHost())}
        self.development_ids: list[str] = []
        self.extraction_ids: list[str] = []
        self.assessment_ids: list[str] = []
        self.evaluation_ids: list[str] = []

    def execute_development(self, **kwargs: Any) -> Any:
        self.development_ids.append(kwargs["call_id"])
        return SimpleNamespace(operation=SimpleNamespace(episode_id=f"episode-{kwargs['call_id']}"))

    def extract(self, **kwargs: Any) -> Any:
        self.extraction_ids.append(kwargs["call_id"])
        return SimpleNamespace(
            residue=object(),
            operation_id=f"operation-{kwargs['call_id']}",
            episode_id=kwargs["episode_id"],
        )

    def provider_call(self, **kwargs: Any) -> Any:
        self.assessment_ids.append(kwargs["call_id"])
        return SimpleNamespace(validated={"admitted": 1}, validation_error=None)

    def evaluate(self, **kwargs: Any) -> Any:
        self.evaluation_ids.append(kwargs["call_id"])
        return SimpleNamespace()


def test_fixed_schedule_has_approved_shape_and_natural_fixture() -> None:
    schedule = PilotSchedule.fixed()

    assert schedule.development_count == 48
    assert schedule.extraction_count == 48
    assert schedule.assessment_count == 48
    assert schedule.evaluation_count == 144
    assert schedule.episodes[0].family == "parts"
    assert schedule.episodes[1].family == "garden"
    assert schedule.episodes[2].family == "practice"
    assert schedule.episodes[11].suppress_practice_reminder is True
    assert {item.ordinal for item in schedule.episodes if item.dependent_recurrence} == {4, 7, 10}
    assert len({probe.family for probe in schedule.probes}) == 12
    assert "VRAM" not in " ".join(item.text for item in schedule.episodes)


def test_study_pause_resume_reuses_stable_coordinates(tmp_path: Path) -> None:
    del tmp_path
    pilot = _FakePilot()
    runtime = _FakeRuntime()
    study = PilotStudy(pilot, runtime)  # type: ignore[arg-type]

    def assessment(*_args: Any) -> AssessmentPlan:
        return AssessmentPlan(
            FakeHost(),
            GenerationRequest(({"role": "user", "content": "assess"},)),
            lambda _content: {"valid": True},
            lambda _validated: 1,
        )

    def evaluation(*_args: Any) -> EvaluationPlan:
        return EvaluationPlan(
            checkpoint="checkpoint.sqlite3",
            private_snapshot="checkpoint.sqlite3",
            host=FakeHost(),
            messages=({"role": "user", "content": "probe"},),
        )

    paused = study.run(assessment=assessment, evaluation=evaluation, stop_after_episodes=1)
    assert paused.status == PilotStatus.PAUSED.value
    assert paused.development_completed == 1
    assert runtime.development_ids == ["development-s0-e0"]

    completed = study.run(assessment=assessment, evaluation=evaluation)
    assert completed.status == PilotStatus.COMPLETE.value
    assert completed.development_completed == 48
    assert completed.extractions_valid == 48
    assert completed.assessments_completed == 48
    assert completed.evaluations_completed == 144
    assert completed.admitted_relationships == 48
    assert runtime.development_ids.count("development-s0-e0") == 1
    assert len(set(runtime.development_ids)) == 48
    assert runtime.evaluation_ids[-1] == "evaluation-s1-p11-r5"


def test_production_assessment_adapter_serializes_complete_monitor_and_resolves_sources() -> None:
    class _Connection:
        def execute(self, _query: str, _args: tuple[str, ...]) -> Any:
            return SimpleNamespace(
                fetchall=lambda: [
                    ("source-0", 0, "A supports B.", "user", "external_evidence", None),
                    (
                        "source-1",
                        1,
                        "The host repeated A supports B.",
                        "model_output",
                        "model_output",
                        None,
                    ),
                ]
            )

    runtime = SimpleNamespace(
        subjects={0: SimpleNamespace(store=SimpleNamespace(connection=_Connection()))}
    )
    adapter = ProductionAssessmentAdapter(runtime, FakeHost())  # type: ignore[arg-type]
    development = SimpleNamespace(operation=SimpleNamespace(operation_id="development-s0-e0"))
    extraction = SimpleNamespace(
        episode_id="episode-s0-e0",
        operation_id="interpretation-s0-e0",
        residue=SimpleNamespace(
            edge_candidates=(
                {"key": "edge-ab", "from": "A", "to": "B", "relationship": "supports"},
            )
        ),
    )

    plan = adapter(0, PilotSchedule.fixed().episodes[0], development, extraction)
    assert plan.semantic_request is not None
    payload = plan.semantic_request.to_dict()
    monitor = payload["monitors"][0]
    assert monitor["relation"] == {"from": "A", "to": "B", "relation": "supports"}
    assert monitor["required_source_slots"] == ["s0", "s1"]
    assert monitor["correspondence_source_slots"] == ["s0", "s1"]
    result = {
        "schema_version": "p2-assessor-v6",
        "assessments": [
            {
                "monitor_id": "candidate",
                "status": "present",
                "relation_support": "supported",
                "expression_status": "affirmed",
                "coverage": {"complete": True, "source_slots": ["s0", "s1"], "reason": None},
                "evidence": {"source_slot": "s0", "quote": "A supports B."},
                "corresponding_source_slots": [],
            }
        ],
    }
    resolved = plan.validator(json.dumps(result))
    assert resolved[0].provenance.dependence == "external_supported"


def test_edge_less_residue_is_excluded_without_provider_assessment() -> None:
    published: list[dict[str, Any]] = []

    class _Pilot:
        def publish_artifact(self, _category: str, _name: str, value: dict[str, Any]) -> None:
            published.append(value)

    class _Runtime:
        pilot = _Pilot()

        def publish_interpretation(self, **_kwargs: Any) -> Any:
            return SimpleNamespace(
                operation_id="interpretation-s0-e0",
                lineage_revision=1,
                graph_revision=0,
                to_dict=lambda: {"operation_id": "interpretation-s0-e0"},
            )

    runtime = _Runtime()
    adapter = ProductionAssessmentAdapter(runtime, FakeHost())  # type: ignore[arg-type]
    development = SimpleNamespace(operation=SimpleNamespace(operation_id="development-s0-e0"))
    extraction = SimpleNamespace(
        episode_id="episode-s0-e0",
        operation_id="interpretation-s0-e0",
        residue=SimpleNamespace(core_concepts=(), edge_candidates=()),
    )

    plan = adapter(0, PilotSchedule.fixed().episodes[0], development, extraction)
    assert plan.excluded_reason == "extraction contained no relationship edge"
    assert plan.request is None
    assert plan.publish(None) == 0
    assert published[0]["status"] == "EXCLUDED"


def test_study_continues_after_excluded_edge_less_residue() -> None:
    pilot = _FakePilot()
    runtime = _FakeRuntime()
    study = PilotStudy(pilot, runtime)  # type: ignore[arg-type]

    def assessment(*_args: Any) -> AssessmentPlan:
        return AssessmentPlan(
            FakeHost(),
            None,
            None,
            lambda _value: 0,
            excluded_reason="extraction contained no relationship edge",
        )

    paused = study.run(assessment=assessment, evaluation=None, stop_after_episodes=1)
    assert paused.status == PilotStatus.PAUSED.value
    assert paused.assessments_completed == 1
    assert paused.admitted_relationships == 0
    assert runtime.assessment_ids == []
