"""Offline integration checks for the bounded P2.3 runtime wrapper."""

from __future__ import annotations

import json
from pathlib import Path

from mneme.contracts import GenerationRequest, GenerationResult, TokenUsage
from mneme.experiments.artifacts import ArtifactStore
from mneme.experiments.pilot import PilotRun
from mneme.experiments.pilot_runtime import PilotRuntime, RuntimeSubject
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore


class CountingHost(FakeHost):
    calls: int = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        return super().generate(request)


class ResidueHost(CountingHost):
    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        content = json.dumps(
            {
                "core_concepts": [
                    {
                        "key": "a",
                        "label": "A",
                        "evidence": [{"source": "s0", "evidence": "A"}],
                        "confidence": 0.9,
                    },
                    {
                        "key": "b",
                        "label": "B",
                        "evidence": [{"source": "s0", "evidence": "B"}],
                        "confidence": 0.9,
                    },
                ],
                "edge_candidates": [
                    {
                        "key": "edge-ab",
                        "from": "a",
                        "to": "b",
                        "relationship": "causes",
                        "evidence": [{"source": "s0", "evidence": "A causes B"}],
                        "confidence": 0.9,
                    }
                ],
            }
        )
        return GenerationResult(
            content,
            self.model_id,
            "builtin",
            dict(request.parameters),
            request.seed,
            TokenUsage(10, len(content.split()), 10 + len(content.split())),
            0.0,
            "stop",
            {},
            {"host": self.fingerprint().to_dict()},
        )


def _pilot(tmp_path: Path, *, calls: int = 2) -> PilotRun:
    artifacts = ArtifactStore(tmp_path / "lab")
    artifacts.publish_run(
        experiment={"name": "p2-runtime", "contract_revision": 1},
        preflight={"valid": True},
        study_plan={"budgets": {"max_model_calls": 3 + calls}},
        bindings={"subjects": []},
        run_id="run-1",
    )
    pilot = PilotRun(artifacts, "run-1")
    pilot.prepare(
        planned_calls=3 + calls,
        max_output_tokens=100,
        qualification_calls=3,
        pilot_calls=calls,
    )
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
        pilot.return_call(call_id, result={"valid": True}, output_tokens=1)
    pilot.complete_qualification(passed=True)
    pilot.begin_pilot()
    return pilot


def _subject(tmp_path: Path, host: CountingHost) -> RuntimeSubject:
    store = SQLiteStore(tmp_path / "subject.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(store=True, export=True, interpret=True, learn=True)
    )
    return RuntimeSubject(0, store, instance, host)


def test_development_coordinate_is_exactly_once_and_persisted_before_acceptance(
    tmp_path: Path,
) -> None:
    host = CountingHost()
    subject = _subject(tmp_path, host)
    pilot = _pilot(tmp_path, calls=1)
    runtime = PilotRuntime(pilot, {0: subject})
    request = GenerationRequest(({"role": "user", "content": "A bounded fixture."},))

    first = runtime.execute_development(
        slot=0,
        call_id="development-s0-e0",
        coordinate={"subject": 0, "episode": 0},
        request=request,
        max_output_tokens=20,
    )
    second = runtime.execute_development(
        slot=0,
        call_id="development-s0-e0",
        coordinate={"subject": 0, "episode": 0},
        request=request,
        max_output_tokens=20,
    )

    assert first.operation.status == "ACCEPTED"
    assert second.operation.episode_id == first.operation.episode_id
    assert first.provider_called is True
    assert second.provider_called is False
    assert host.calls == 1
    assert subject.store.connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1
    receipt = pilot.artifacts._read_json(
        pilot.run_path / "development" / "development-s0-e0.json"
    )
    assert receipt["operation"]["status"] == "ACCEPTED"
    assert receipt["result"]["content"]


def test_evaluation_uses_frozen_snapshot_and_never_writes_lineage(
    tmp_path: Path,
) -> None:
    host = CountingHost()
    subject = _subject(tmp_path, host)
    checkpoint = tmp_path / "checkpoint.sqlite3"
    create_checkpoint(subject.store, checkpoint, "checkpoint-0")
    before = dict(subject.store.current())
    pilot = _pilot(tmp_path, calls=1)
    runtime = PilotRuntime(pilot, {0: subject})

    first = runtime.evaluate(
        slot=0,
        call_id="evaluation-s0-p0-r0",
        coordinate={"subject": 0, "probe": 0, "repetition": 0},
        checkpoint=checkpoint,
        private_snapshot=checkpoint,
        host=host,
        messages=({"role": "user", "content": "held out"},),
        max_output_tokens=20,
    )
    second = runtime.evaluate(
        slot=0,
        call_id="evaluation-s0-p0-r0",
        coordinate={"subject": 0, "probe": 0, "repetition": 0},
        checkpoint=checkpoint,
        private_snapshot=checkpoint,
        host=host,
        messages=({"role": "user", "content": "held out"},),
        max_output_tokens=20,
    )

    assert first.provider_called is True
    assert second.provider_called is False
    assert first.result["content"] == second.result["content"]
    assert host.calls == 1
    assert dict(subject.store.current()) == before
    artifact = pilot.artifacts._read_json(
        pilot.run_path / "evaluation" / "evaluation-s0-p0-r0.json"
    )
    assert artifact["developmental_state_before"] == artifact["developmental_state_after"]
    reservation = pilot.run_path / "pilot" / "reservations" / "evaluation-s0-p0-r0.json"
    assert json.loads(reservation.read_text())["status"] == "RETURNED"


def test_evaluation_requires_the_bound_private_snapshot(tmp_path: Path) -> None:
    host = CountingHost()
    subject = _subject(tmp_path, host)
    checkpoint = tmp_path / "checkpoint.sqlite3"
    create_checkpoint(subject.store, checkpoint, "checkpoint-0")
    pilot = _pilot(tmp_path, calls=1)
    runtime = PilotRuntime(pilot, {0: subject})
    other = tmp_path / "other.sqlite3"
    other.write_bytes(checkpoint.read_bytes())

    try:
        runtime.evaluate(
            slot=0,
            call_id="evaluation-s0-p0-r0",
            coordinate={"subject": 0, "probe": 0, "repetition": 0},
            checkpoint=other,
            private_snapshot=checkpoint,
            host=host,
            messages=({"role": "user", "content": "held out"},),
            max_output_tokens=20,
        )
    except Exception as exc:
        assert "private snapshot" in str(exc)
    else:
        raise AssertionError("different checkpoint path was accepted")
    assert host.calls == 0


def test_extraction_and_publication_reuse_durable_boundaries(tmp_path: Path) -> None:
    developing = ResidueHost()
    subject = _subject(tmp_path, developing)
    pilot = _pilot(tmp_path, calls=2)
    runtime = PilotRuntime(pilot, {0: subject})
    development = runtime.execute_development(
        slot=0,
        call_id="development-s0-e0",
        coordinate={"subject": 0, "episode": 0},
        request=GenerationRequest(({"role": "user", "content": "A causes B"},)),
        max_output_tokens=20,
    )
    extraction = runtime.extract(
        slot=0,
        call_id="extraction-s0-e0-a0",
        coordinate={"subject": 0, "episode": 0, "attempt": 0},
        episode_id=development.operation.episode_id,
        extractor_host=developing,
        max_output_tokens=30,
    )
    assert extraction.residue is not None
    assert extraction.validation_error is None
    publication = runtime.publish_interpretation(
        slot=0,
        operation_id=extraction.operation_id,
        residue=extraction.residue,
    )
    assert publication.status == "ACCEPTED"
    assert developing.calls == 2
    assert subject.store.connection.execute(
        "SELECT status FROM interpretation_operations WHERE operation_id=?",
        (extraction.operation_id,),
    ).fetchone()[0] == "ACCEPTED"
