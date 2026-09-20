from __future__ import annotations

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
)
from mneme.hosts import FakeHost


@dataclass
class _FakePilot:
    state: str = PilotStatus.QUALIFIED.value

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
    assert runtime.development_ids.count("development-s0-e0") == 2
    assert len(set(runtime.development_ids)) == 48
    assert runtime.evaluation_ids[-1] == "evaluation-s1-p11-r5"
