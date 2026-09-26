from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.development.learner import ConsequenceAssessment
from mneme.experiments.pilot_audit import EngineeringAudit
from mneme.experiments.pilot_study import (
    AssessmentPlan,
    EvaluationPlan,
    PilotSchedule,
    PilotStatus,
    PilotStudy,
    PilotStudyReport,
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
    assert pilot.progress["accepted_development_ids"] == ["development-s0-e0"]

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


def test_resume_counts_unique_development_coordinates_after_accepted_retry() -> None:
    pilot = _FakePilot(
        progress={
            # The accepted response for e1 was persisted before its first
            # extraction failed.  A recovery must not count that coordinate
            # twice when its extraction resumes.
            "development_completed": 2,
            "completed_development_ids": ["development-s0-e0"],
            "accepted_development_ids": [
                "development-s0-e0",
                "development-s0-e1",
            ],
            "extractions_valid": 1,
            "extraction_repairs": 0,
            "assessments_completed": 1,
            "admitted_relationships": 1,
            "evaluations_completed": 0,
            "completed_evaluations": [],
        }
    )
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

    completed = study.run(assessment=assessment, evaluation=evaluation)

    assert completed.status == PilotStatus.COMPLETE.value
    assert completed.development_completed == 48
    assert completed.extractions_valid == 48
    assert completed.assessments_completed == 48
    assert completed.evaluations_completed == 144
    # The fake runtime supplies counters only.  A completed count summary is
    # deliberately insufficient without a durable PilotRun audit.
    assert completed.engineering_adequate is False
    assert completed.engineering_audit is not None
    assert completed.engineering_audit.status == "UNAVAILABLE"


def test_engineering_adequacy_requires_durable_audit_even_when_counts_pass() -> None:
    report = PilotStudyReport(
        status=PilotStatus.COMPLETE.value,
        development_completed=48,
        extractions_valid=48,
        extraction_repairs=0,
        assessments_completed=48,
        evaluations_completed=144,
        admitted_relationships=12,
        engineering_audit=EngineeringAudit(
            "UNAVAILABLE",
            ({"name": "durable-pilot-run", "passed": False},),
        ),
    )

    assert report.engineering_adequate is False


def test_resume_reprocesses_accepted_development_after_interpretation_interrupt() -> None:
    pilot = _FakePilot()

    class _IdempotentRuntime(_FakeRuntime):
        def __init__(self) -> None:
            super().__init__()
            self.provider_dispatches: list[str] = []
            self._returned: set[str] = set()

        def execute_development(self, **kwargs: Any) -> Any:
            call_id = str(kwargs["call_id"])
            self.development_ids.append(call_id)
            if call_id not in self._returned:
                self.provider_dispatches.append(call_id)
                self._returned.add(call_id)
            return SimpleNamespace(operation=SimpleNamespace(episode_id=f"episode-{call_id}"))

    runtime = _IdempotentRuntime()
    assessment_attempts = 0

    def assessment(*_args: Any) -> AssessmentPlan:
        nonlocal assessment_attempts
        assessment_attempts += 1
        if assessment_attempts == 1:
            raise ValueError("simulated interruption after accepted development")
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

    study = PilotStudy(pilot, runtime)  # type: ignore[arg-type]
    first = study.run(assessment=assessment, evaluation=evaluation, stop_after_episodes=1)
    assert first.status == PilotStatus.FAILED.value
    assert pilot.progress["accepted_development_ids"] == ["development-s0-e0"]
    assert pilot.progress["completed_development_ids"] == []

    # The test double models a restart into a prepared/qualified run.  The
    # accepted response is reused by the runtime, while interpretation starts
    # again at the preserved coordinate.
    pilot.state = PilotStatus.QUALIFIED.value
    completed = study.run(assessment=assessment, evaluation=evaluation)
    assert completed.status == PilotStatus.COMPLETE.value
    assert runtime.development_ids.count("development-s0-e0") == 2
    assert runtime.provider_dispatches.count("development-s0-e0") == 1


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
            core_concepts=(
                {"key": "key-a", "label": "cloth wick"},
                {"key": "key-b", "label": "soil moisture"},
            ),
            edge_candidates=(
                {
                    "key": "edge-ab",
                    "from": "key-a",
                    "to": "key-b",
                    "relationship": "supports",
                },
            )
        ),
    )

    plan = adapter(0, PilotSchedule.fixed().episodes[0], development, extraction)
    assert plan.semantic_request is not None
    payload = plan.semantic_request.to_dict()
    monitor = payload["monitors"][0]
    assert monitor["relation"] == {
        "from": "cloth wick",
        "to": "soil moisture",
        "relation": "supports",
    }
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


def test_production_assessment_adapter_treats_feedback_as_external_evidence() -> None:
    class _Connection:
        def execute(self, _query: str, _args: tuple[str, ...]) -> Any:
            return SimpleNamespace(
                fetchall=lambda: [
                    (
                        "feedback-source",
                        0,
                        "The basil survived the absence.",
                        "user",
                        "feedback",
                        None,
                    ),
                ]
            )

    runtime = SimpleNamespace(
        subjects={0: SimpleNamespace(store=SimpleNamespace(connection=_Connection()))}
    )
    sources, current_input, replay = ProductionAssessmentAdapter._sources(
        runtime, 0, "episode-s0-e0"
    )
    assert sources[0].role == "external"
    assert current_input == ("s0",)
    assert replay == ()


def test_production_assessment_adapter_assesses_all_edges_and_publishes_exposure() -> None:
    class _Connection:
        def execute(self, _query: str, _args: tuple[str, ...]) -> Any:
            return SimpleNamespace(
                fetchall=lambda: [
                    ("source-0", 0, "A supports B and C.", "user", "external_evidence", None),
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

    publication: dict[str, Any] = {}

    class _Runtime:
        subjects = {0: SimpleNamespace(store=SimpleNamespace(connection=_Connection()))}
        pilot = SimpleNamespace(
            publish_artifact=lambda _category, _name, value: publication.update(value)
        )

        def publish_interpretation(self, **kwargs: Any) -> Any:
            publication["publication_kwargs"] = kwargs
            return SimpleNamespace(
                operation_id="interpretation-s0-e0",
                lineage_revision=2,
                graph_revision=2,
                to_dict=lambda: {"operation_id": "interpretation-s0-e0"},
            )

    adapter = ProductionAssessmentAdapter(
        _Runtime(),
        FakeHost(),
        memory_exposure={
            0: ({"source_slot": "s1", "exposure_id": "memory-1"},),
        },
        contextual_consequences={
            (0, 0): (
                ConsequenceAssessment(
                    operation_id="outcome-s0-e0",
                    route_key="edge-a-b",
                    direction=1,
                    exposure_id="memory-1",
                ),
            )
        },
    )  # type: ignore[arg-type]
    development = SimpleNamespace(operation=SimpleNamespace(operation_id="development-s0-e0"))
    extraction = SimpleNamespace(
        episode_id="episode-s0-e0",
        operation_id="interpretation-s0-e0",
        residue=SimpleNamespace(
            edge_candidates=(
                {"key": "edge-a-b", "from": "A", "to": "B", "relationship": "supports"},
                {"key": "edge-a-c", "from": "A", "to": "C", "relationship": "supports"},
            )
        ),
    )

    plan = adapter(0, PilotSchedule.fixed().episodes[0], development, extraction)
    assert plan.semantic_request is not None
    assert [item.monitor_id for item in plan.semantic_request.monitors] == [
        "candidate:edge-a-b",
        "candidate:edge-a-c",
    ]
    result = {
        "schema_version": "p2-assessor-v6",
        "assessments": [
            {
                "monitor_id": "candidate:edge-a-b",
                "status": "present",
                "relation_support": "supported",
                "expression_status": "affirmed",
                "coverage": {"complete": True, "source_slots": ["s0", "s1"], "reason": None},
                "evidence": {"source_slot": "s1", "quote": "The host repeated A supports B."},
                "corresponding_source_slots": ["s1"],
            },
            {
                "monitor_id": "candidate:edge-a-c",
                "status": "present",
                "relation_support": "supported",
                "expression_status": "affirmed",
                "coverage": {"complete": True, "source_slots": ["s0", "s1"], "reason": None},
                "evidence": {"source_slot": "s0", "quote": "A supports B and C."},
                "corresponding_source_slots": [],
            },
        ],
    }
    resolved = plan.validator(json.dumps(result))
    assert plan.publish(resolved) == 2
    observations = publication["publication_kwargs"]["observations"]
    assert {item.target_key for item in observations} == {"edge-a-b", "edge-a-c"}
    assert (
        next(item for item in observations if item.target_key == "edge-a-b").actual_exposure
        is True
    )
    assert publication["publication_kwargs"]["consequences"][0].route_key == "edge-a-b"


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
