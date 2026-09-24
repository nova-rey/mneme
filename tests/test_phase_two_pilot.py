from __future__ import annotations

from pathlib import Path

import pytest

from mneme.experiments.artifacts import ArtifactStore
from mneme.experiments.pilot import (
    CallStatus,
    PilotError,
    PilotRun,
    PilotStatus,
    host_role_binding,
)
from mneme.hosts import FakeHost


def _published(tmp_path: Path) -> ArtifactStore:
    store = ArtifactStore(tmp_path / "lab")
    store.publish_run(
        experiment={"name": "p2-developmental-pilot", "contract_revision": 1},
        preflight={"valid": True, "host": {"backend": "fake"}},
        study_plan={"budgets": {"max_model_calls": 8}},
        bindings={"subjects": [{"slot": 0}]},
        run_id="run-1",
    )
    return store


def test_pilot_reservations_are_durable_and_idempotent(tmp_path: Path) -> None:
    store = _published(tmp_path)
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=4, max_output_tokens=40, qualification_calls=3, pilot_calls=1)
    pilot.begin_qualification()
    first = pilot.reserve_call(
        call_id="q-1",
        role="assessor-qualification",
        coordinate={"case": "Q1"},
        max_output_tokens=10,
    )
    assert first["status"] == CallStatus.RESERVED.value
    assert pilot.reserve_call(
        call_id="q-1",
        role="assessor-qualification",
        coordinate={"case": "Q1"},
        max_output_tokens=10,
    ) == first
    assert pilot.dispatch_call("q-1")["status"] == CallStatus.DISPATCHED.value
    returned = pilot.return_call(
        "q-1", result={"classification": "present"}, usage={"output_tokens": 4}, output_tokens=4
    )
    assert returned["status"] == CallStatus.RETURNED.value
    reopened = PilotRun(store, "run-1")
    assert reopened.reservations_report()["counts"][CallStatus.RETURNED.value] == 1
    assert store.verify_run(store.locate_run("run-1"))


def test_qualification_requires_three_terminal_calls_and_blocks_pilot_on_failure(
    tmp_path: Path,
) -> None:
    store = _published(tmp_path)
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=4, max_output_tokens=40, qualification_calls=3, pilot_calls=1)
    pilot.begin_qualification()
    for ordinal in range(3):
        call_id = f"q-{ordinal}"
        pilot.reserve_call(
            call_id=call_id,
            role="assessor-qualification",
            coordinate={"case": f"Q{ordinal + 1}"},
            max_output_tokens=10,
        )
        pilot.dispatch_call(call_id)
        pilot.return_call(call_id, result={"valid": False})
    failed = pilot.complete_qualification(passed=False, details={"reason": "invalid monitor"})
    assert failed["status"] == PilotStatus.FAILED.value
    assert failed["pilot"]["status"] == PilotStatus.FAILED.value
    assert store.inspect_run("run-1")["manifest"]["status"] == PilotStatus.FAILED.value
    with pytest.raises(PilotError, match="qualification passes"):
        pilot.begin_pilot()


def test_uncertain_call_is_retained_and_never_retried(tmp_path: Path) -> None:
    store = _published(tmp_path)
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=4, max_output_tokens=40, qualification_calls=3, pilot_calls=1)
    pilot.begin_qualification()
    pilot.reserve_call(
        call_id="q-1",
        role="assessor-qualification",
        coordinate={"case": "Q1"},
        max_output_tokens=10,
    )
    pilot.dispatch_call("q-1")
    uncertain = pilot.mark_uncertain("q-1", "process interrupted before provider outcome")
    assert uncertain["status"] == CallStatus.UNCERTAIN.value
    with pytest.raises(PilotError, match="expected RESERVED"):
        pilot.dispatch_call("q-1")


def test_reservation_ceiling_and_output_ceiling_fail_closed(tmp_path: Path) -> None:
    store = _published(tmp_path)
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=3, max_output_tokens=9, qualification_calls=3, pilot_calls=0)
    pilot.begin_qualification()
    for ordinal in range(3):
        pilot.reserve_call(
            call_id=f"q-{ordinal}",
            role="assessor-qualification",
            coordinate={"case": ordinal},
            max_output_tokens=3,
        )
    with pytest.raises(PilotError, match="call ceiling"):
        pilot.reserve_call(
            call_id="q-over",
            role="assessor-qualification",
            coordinate={"case": 3},
            max_output_tokens=1,
        )

    other_store = _published(tmp_path / "other")
    other = PilotRun(other_store, "run-1")
    other.prepare(planned_calls=3, max_output_tokens=9, qualification_calls=3, pilot_calls=0)
    other.begin_qualification()
    other.reserve_call(
        call_id="q-1", role="assessor-qualification", coordinate={"case": 1}, max_output_tokens=8
    )
    with pytest.raises(PilotError, match="output-token ceiling"):
        other.reserve_call(
            call_id="q-2",
            role="assessor-qualification",
            coordinate={"case": 2},
            max_output_tokens=2,
        )


def test_pause_resume_preserves_lifecycle_and_redacts_artifact_secrets(tmp_path: Path) -> None:
    store = _published(tmp_path)
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=3, max_output_tokens=9, qualification_calls=3, pilot_calls=0)
    pilot.begin_qualification()
    paused = pilot.pause("operator stop")
    assert paused["status"] == PilotStatus.PAUSED.value
    assert pilot.resume()["status"] == PilotStatus.QUALIFYING.value
    path = pilot.publish_artifact(
        "receipts", "sanitized.json", {"authorization": "secret", "usage": {"output_tokens": 2}}
    )
    assert '"authorization":"[REDACTED]"' in path.read_text(encoding="utf-8")
    assert '"output_tokens":2' in path.read_text(encoding="utf-8")


def test_qualification_pass_then_pilot_finish_and_artifact_report(tmp_path: Path) -> None:
    store = _published(tmp_path)
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=4, max_output_tokens=40, qualification_calls=3, pilot_calls=1)
    pilot.begin_qualification()
    for ordinal in range(3):
        call_id = f"q-{ordinal}"
        pilot.reserve_call(
            call_id=call_id,
            role="assessor-qualification",
            coordinate={"case": f"Q{ordinal + 1}"},
            max_output_tokens=10,
        )
        pilot.dispatch_call(call_id)
        pilot.return_call(call_id, result={"valid": True}, output_tokens=2)
    assert pilot.complete_qualification(passed=True)["status"] == PilotStatus.QUALIFIED.value
    pilot.begin_pilot()
    pilot.reserve_call(
        call_id="p-1",
        role="development-response",
        coordinate={"subject": 0, "episode": 0},
        max_output_tokens=10,
    )
    pilot.dispatch_call("p-1")
    pilot.return_call("p-1", result={"accepted": True}, output_tokens=3)
    pilot.publish_artifact("qualification", "summary.json", {"passed": True})
    pilot.publish_artifact("receipts", "pilot.json", {"status": "COMPLETE"})
    assert pilot.finish(summary={"engineering": "pass"})["status"] == PilotStatus.COMPLETE.value
    report = PilotRun(store, "run-1").reservations_report()
    assert report["counts"][CallStatus.RETURNED.value] == 4
    assert store.verify_run(store.locate_run("run-1"))


def test_mixed_role_binding_requires_matching_assessor_host(tmp_path: Path) -> None:
    store = _published(tmp_path)
    developing = FakeHost(model_id="developing")
    assessor = FakeHost(model_id="assessor")
    pilot = PilotRun(store, "run-1")
    pilot.prepare(
        planned_calls=3,
        max_output_tokens=30,
        qualification_calls=3,
        pilot_calls=0,
        role_bindings={
            "developing": host_role_binding("developing", developing),
            "assessor": host_role_binding("assessor", assessor),
        },
    )
    assert pilot.require_role_host("assessor", assessor)["model_id"] == "assessor"
    with pytest.raises(PilotError, match="fingerprint"):
        pilot.require_role_host("assessor", developing)


def test_completed_dispatch_rejects_changed_expected_host_binding(tmp_path: Path) -> None:
    store = _published(tmp_path)
    host = FakeHost(model_id="assessor")
    pilot = PilotRun(store, "run-1")
    pilot.prepare(planned_calls=3, max_output_tokens=30, qualification_calls=3)
    pilot.begin_qualification()
    pilot.reserve_call(
        call_id="q-1",
        role="assessor-qualification",
        coordinate={"case": "Q1"},
        max_output_tokens=10,
    )
    expected = host.fingerprint().to_dict()
    pilot.dispatch_call("q-1", expected_host_fingerprint=expected)
    altered = dict(expected)
    altered["model_id"] = "other"
    with pytest.raises(PilotError, match="expected_host_fingerprint"):
        pilot.dispatch_call("q-1", expected_host_fingerprint=altered)


def test_role_binding_missing_assessor_fails_closed(tmp_path: Path) -> None:
    store = _published(tmp_path)
    pilot = PilotRun(store, "run-1")
    with pytest.raises(PilotError, match="assessor"):
        pilot.prepare(
            planned_calls=3,
            max_output_tokens=30,
            qualification_calls=3,
            pilot_calls=0,
            role_bindings={"developing": host_role_binding("developing", FakeHost())},
        )
