"""Network-free P0.4 integrated runner tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mneme.experiments.artifacts import ArtifactStore, file_digest
from mneme.experiments.runner import (
    IntegratedRunner,
    RunnerError,
    RunnerUncertain,
    SubjectExecution,
)
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore


def _records() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    development = [
        {
            "record_id": "dev-0",
            "messages": [{"role": "user", "content": "development one"}],
        },
        {
            "record_id": "dev-1",
            "messages": [{"role": "user", "content": "development two"}],
        },
    ]
    evaluation = [
        {
            "record_id": "eval-0",
            "messages": [{"role": "user", "content": "held out probe"}],
        }
    ]
    return development, evaluation


def _prepared_run(
    tmp_path: Path,
    *,
    controller: bool = False,
) -> tuple[ArtifactStore, Path, SQLiteStore, str, list[dict[str, object]], list[dict[str, object]]]:
    host = FakeHost()
    store = SQLiteStore(tmp_path / "subject.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True))
    checkpoint = tmp_path / "start.sqlite3"
    checkpoint_id = create_checkpoint(store, checkpoint, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    current = store.current()
    development, evaluation = _records()
    fingerprint = host.fingerprint().to_dict()
    fingerprint_sha = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    plan = {
        "experiment": {"name": "runner-control", "contract_revision": 1, "content_digest": None},
        "assignments": [
            {
                "subject_slot": 0,
                "development_order": ["dev-0", "dev-1"],
                "evaluation_order": ["eval-0"],
            }
        ],
        "streams": [
            {"domain": "development_generation", "subject_slot": 0, "episode": 0, "seed": 10},
            {"domain": "development_generation", "subject_slot": 0, "episode": 1, "seed": 11},
            {
                "domain": "evaluation_generation",
                "subject_slot": 0,
                "probe": 0,
                "repetition": 0,
                "seed": 12,
            },
            {
                "domain": "evaluation_generation",
                "subject_slot": 0,
                "probe": 0,
                "repetition": 1,
                "seed": 13,
            },
        ],
        "host": {
            "fingerprint": fingerprint,
            "fingerprint_sha256": fingerprint_sha,
            "capabilities": host.capabilities().to_dict(),
            "sampling": "controlled",
        },
        "budgets": {"max_model_calls": 5},
    }
    experiment = {
        "name": "runner-control",
        "contract_revision": 1,
        "purpose": "test",
        "host": {"backend": "fake"},
        "generation": {"parameters": {"max_new_tokens": 8}},
    }
    if controller:
        experiment["controller"] = {"mode": "develop", "memory": "off"}
    bindings = {
        "subjects": [{"slot": 0, "start": "start"}],
        "checkpoints": {
            "start": {
                "path": str(checkpoint),
                "checkpoint_id": checkpoint_id,
                "instance_id": instance,
                "revision": current["current_revision"],
                "manifest_id": current["current_manifest_id"],
                "sha256": file_digest(checkpoint),
                "snapshot_path": "start.sqlite3",
            }
        },
    }
    store_artifacts = ArtifactStore(tmp_path / "lab")
    published = store_artifacts.publish_run(
        experiment=experiment,
        preflight={"valid": True},
        study_plan=plan,
        bindings=bindings,
        run_id="run-001",
        snapshots={"start.sqlite3": checkpoint.read_bytes()},
    )
    return store_artifacts, published.path, store, instance, development, evaluation


def test_integrated_runner_pauses_resumes_exactly_once_and_isolates_evaluation(
    tmp_path: Path,
) -> None:
    artifacts, run_path, store, instance, development, evaluation = _prepared_run(tmp_path)
    runner = IntegratedRunner(
        "run-001",
        artifacts.root,
        {0: SubjectExecution(0, store, FakeHost())},
    )
    paused = runner.execute_run({0: development}, pause_after={0: 1})
    assert paused["status"] == "PAUSED"
    assert store.current()["current_revision"] == 1

    resumed = IntegratedRunner(
        "run-001",
        artifacts.root,
        {0: SubjectExecution(0, store, FakeHost())},
    ).execute_run(
        {0: development},
        {
            0: {
                "records": evaluation,
                "checkpoint": tmp_path / "boundary.sqlite3",
                "private_snapshot": tmp_path / "private.sqlite3",
                "repetitions": 2,
            }
        },
    )
    assert resumed["status"] == "COMPLETE"
    assert store.current()["current_revision"] == 2
    assert store.connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 2
    assert store.connection.execute("SELECT COUNT(*) FROM generation_records").fetchone()[0] == 2
    checks = artifacts.inspect_run("run-001", verify=True)["checks"]
    assert len([item for item in checks if item.get("status") == "RESULT"]) == 2
    assert artifacts.verify_run(run_path)

    # A restart/retry reuses accepted operations and completed probes.
    before_calls = store.connection.execute("SELECT COUNT(*) FROM generation_records").fetchone()[0]
    again = IntegratedRunner(
        "run-001",
        artifacts.root,
        {0: SubjectExecution(0, store, FakeHost())},
    ).execute_run(
        {0: development},
        {
            0: {
                "records": evaluation,
                "checkpoint": tmp_path / "boundary.sqlite3",
                "private_snapshot": tmp_path / "private.sqlite3",
                "repetitions": 2,
            }
        },
    )
    assert again["status"] == "COMPLETE"
    assert (
        store.connection.execute("SELECT COUNT(*) FROM generation_records").fetchone()[0]
        == before_calls
    )


def test_runner_never_injects_previous_output_into_later_request(tmp_path: Path) -> None:
    artifacts, _, store, _, development, _ = _prepared_run(tmp_path)
    runner = IntegratedRunner(
        "run-001", artifacts.root, {0: SubjectExecution(0, store, FakeHost())}
    )
    runner.execute_development(0, development)
    requests = [
        json.loads(row[0])
        for row in store.connection.execute("SELECT request_json FROM run_manifests ORDER BY rowid")
    ]
    assert len(requests) == 2
    assert requests[1]["messages"] == development[1]["messages"]
    assert requests[0]["messages"] != requests[1]["messages"]


def test_runner_controller_path_preserves_declared_context_and_accepts_once(tmp_path: Path) -> None:
    artifacts, _, store, _, development, _ = _prepared_run(tmp_path, controller=True)
    development[0]["messages"] = [
        {"role": "system", "content": "declared system"},
        {"role": "user", "content": "development one"},
    ]
    runner = IntegratedRunner(
        "run-001", artifacts.root, {0: SubjectExecution(0, store, FakeHost())}
    )
    evidence = runner.execute_development(0, development)
    assert [item.status for item in evidence] == ["ACCEPTED", "ACCEPTED"]
    requests = [
        json.loads(row[0])
        for row in store.connection.execute("SELECT request_json FROM run_manifests ORDER BY rowid")
    ]
    assert requests[0]["messages"] == development[0]["messages"]
    assert store.connection.execute("SELECT COUNT(*) FROM turn_traces").fetchone()[0] == 2
    assert store.connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 2


def test_uncertain_provider_operation_is_not_regenerated(tmp_path: Path) -> None:
    artifacts, _, store, _, development, _ = _prepared_run(tmp_path)
    failing = IntegratedRunner(
        "run-001", artifacts.root, {0: SubjectExecution(0, store, FakeHost(fail=True))}
    )
    with pytest.raises(RunnerUncertain):
        failing.execute_development(0, development)
    assert store.connection.execute("SELECT COUNT(*) FROM generation_records").fetchone()[0] == 0
    with pytest.raises(RunnerUncertain):
        failing.execute_development(0, development)


def test_runner_rejects_wrong_order_and_host_fingerprint(tmp_path: Path) -> None:
    artifacts, _, store, _, development, _ = _prepared_run(tmp_path)
    runner = IntegratedRunner(
        "run-001", artifacts.root, {0: SubjectExecution(0, store, FakeHost())}
    )
    with pytest.raises(RunnerError, match="prepared order"):
        runner.execute_development(0, list(reversed(development)))
