"""P0.3 frozen evaluation and no-writeback tests."""

import pytest

from mneme.contracts import GenerationRequest
from mneme.experiments.artifacts import ArtifactStore
from mneme.experiments.evaluation import EvaluationError, FrozenEvaluationView, run_isolation_check
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore


def _checkpoint(tmp_path):
    working_path = tmp_path / "working.sqlite3"
    with SQLiteStore(working_path) as store:
        instance = store.create_root(permissions=StoragePermissions(True, True))
        service = ContinuityService(store, instance, FakeHost())
        operation = service.prepare_episode(
            GenerationRequest(({"role": "user", "content": "development"},), seed=1)
        )
        service.generate_operation(operation.operation_id)
        service.accept_episode(operation.operation_id)
        checkpoint = tmp_path / "checkpoint.sqlite3"
        checkpoint_id = create_checkpoint(store, checkpoint)
    return checkpoint, checkpoint_id


def _run(tmp_path):
    checkpoint, checkpoint_id = _checkpoint(tmp_path)
    published = ArtifactStore(tmp_path / "lab").publish_run(
        experiment={"name": "isolation", "contract_revision": 1},
        preflight={"ok": True},
        study_plan={"calls": 1},
        bindings={"checkpoint_id": checkpoint_id},
        run_id="run-1",
    )
    return checkpoint, published


def test_frozen_view_generation_leaves_checkpoint_unchanged(tmp_path):
    checkpoint, _ = _run(tmp_path)
    with FrozenEvaluationView(checkpoint) as view:
        before = (view.checkpoint_file_digest, view.state_digest)
        result = view.generate(
            FakeHost(),
            [{"role": "user", "content": "evaluation"}],
            seed=99,
        )
        assert result.content
        assert before == (view.checkpoint_file_digest, view.state_digest)
        assert view.episodes()[0]["accepted_revision"] == 1


def test_isolation_receipt_is_separate_and_idempotent(tmp_path):
    checkpoint, published = _run(tmp_path)
    result = run_isolation_check(
        run_id="run-1",
        lab=published.path.parents[5],
        check_id="check-1",
        checkpoint=checkpoint,
        host=FakeHost(),
        messages=[{"role": "user", "content": "evaluation"}],
        seed=99,
        subject_slot=0,
        probe_ordinal=0,
        repetition=0,
    )
    assert result["status"] == "RESULT"
    assert result["state_digest_before"] == result["state_digest_after"]
    retry = run_isolation_check(
        run_id="run-1",
        lab=published.path.parents[5],
        check_id="check-1",
        checkpoint=checkpoint,
        host=FakeHost(fail=True),
        messages=[{"role": "user", "content": "evaluation"}],
        seed=99,
        subject_slot=0,
        probe_ordinal=0,
        repetition=0,
    )
    assert retry["status"] == "RESULT"
    assert not (published.path / "snapshots" / "development.sqlite3").exists()
    assert (published.path / "evaluation" / "check-1" / "result.json").exists()


def test_uncertain_check_is_not_regenerated(tmp_path):
    checkpoint, published = _run(tmp_path)
    store = ArtifactStore(published.path.parents[5])
    store.begin_check("run-1", "check-uncertain", {"probe": 1})
    with pytest.raises(EvaluationError, match="UNCERTAIN"):
        run_isolation_check(
            run_id="run-1",
            lab=published.path.parents[5],
            check_id="check-uncertain",
            checkpoint=checkpoint,
            host=FakeHost(),
            messages=[{"role": "user", "content": "evaluation"}],
            seed=1,
            subject_slot=0,
            probe_ordinal=1,
            repetition=0,
        )


def test_completed_check_rejects_changed_probe_intent(tmp_path):
    checkpoint, published = _run(tmp_path)
    kwargs = {
        "run_id": "run-1",
        "lab": published.path.parents[5],
        "check_id": "check-conflict",
        "checkpoint": checkpoint,
        "host": FakeHost(),
        "seed": 99,
        "subject_slot": 0,
        "probe_ordinal": 0,
        "repetition": 0,
    }
    run_isolation_check(messages=[{"role": "user", "content": "first"}], **kwargs)
    with pytest.raises(EvaluationError, match="conflicting intent"):
        run_isolation_check(messages=[{"role": "user", "content": "changed"}], **kwargs)
