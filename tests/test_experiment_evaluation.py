"""P0.3 frozen evaluation and no-writeback tests."""

import pytest

from mneme.contracts import GenerationRequest
from mneme.experiments.artifacts import ArtifactStore, content_digest, file_digest
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


def _bound_run(tmp_path):
    checkpoint, checkpoint_id = _checkpoint(tmp_path)
    published = ArtifactStore(tmp_path / "bound-lab").publish_run(
        experiment={"name": "bound-isolation", "contract_revision": 1},
        preflight={"ok": True},
        study_plan={"calls": 1},
        bindings={
            "subjects": [{"slot": 0, "start": "start"}],
            "checkpoints": {
                "start": {
                    "checkpoint_id": checkpoint_id,
                    "snapshot_path": "start.sqlite3",
                }
            },
        },
        run_id="bound-run",
        snapshots={"start.sqlite3": checkpoint.read_bytes()},
    )
    return checkpoint, checkpoint_id, published


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
    store.begin_check(
        "run-1",
        "check-uncertain",
        {
            "subject_slot": 0,
            "probe_ordinal": 1,
            "repetition": 0,
            "checkpoint_sha256": file_digest(checkpoint),
            "seed": 1,
            "messages_sha256": content_digest([{"role": "user", "content": "evaluation"}]),
            "parameters_sha256": content_digest({}),
            "system_sha256": None,
        },
    )
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


def test_completed_check_retry_returns_requested_check_not_last_check(tmp_path):
    checkpoint, published = _run(tmp_path)
    common = {
        "run_id": "run-1",
        "lab": published.path.parents[5],
        "checkpoint": checkpoint,
        "host": FakeHost(),
        "seed": 99,
        "subject_slot": 0,
        "repetition": 0,
    }
    first = run_isolation_check(
        check_id="check-a", probe_ordinal=0, messages=[{"role": "user", "content": "a"}], **common
    )
    second = run_isolation_check(
        check_id="check-b", probe_ordinal=1, messages=[{"role": "user", "content": "b"}], **common
    )
    retry = run_isolation_check(
        check_id="check-a", probe_ordinal=0, messages=[{"role": "user", "content": "a"}], **common
    )
    assert retry["check_id"] == "check-a"
    assert retry["output"] == first["output"]
    assert retry["output"] != second["output"]


def test_missing_bound_private_snapshot_is_rejected(tmp_path):
    checkpoint, _, published = _bound_run(tmp_path)
    (published.path / "snapshots" / "start.sqlite3").unlink()
    with pytest.raises(EvaluationError, match="bound evaluation snapshot is missing"):
        run_isolation_check(
            run_id="bound-run",
            lab=published.path.parents[5],
            check_id="missing-bound-snapshot",
            checkpoint=checkpoint,
            host=FakeHost(),
            messages=[{"role": "user", "content": "evaluation"}],
            seed=99,
            subject_slot=0,
            probe_ordinal=0,
            repetition=0,
        )


def test_different_valid_copy_of_bound_checkpoint_is_rejected(tmp_path):
    checkpoint, _, published = _bound_run(tmp_path)
    alternate = tmp_path / "alternate.sqlite3"
    alternate.write_bytes(checkpoint.read_bytes())
    with pytest.raises(EvaluationError, match="private snapshot"):
        run_isolation_check(
            run_id="bound-run",
            lab=published.path.parents[5],
            check_id="alternate-copy",
            checkpoint=alternate,
            host=FakeHost(),
            messages=[{"role": "user", "content": "evaluation"}],
            seed=99,
            subject_slot=0,
            probe_ordinal=0,
            repetition=0,
        )


def test_correct_bound_private_snapshot_is_accepted(tmp_path):
    checkpoint, _, published = _bound_run(tmp_path)
    bound = published.path / "snapshots" / "start.sqlite3"
    result = run_isolation_check(
        run_id="bound-run",
        lab=published.path.parents[5],
        check_id="correct-bound-snapshot",
        checkpoint=bound,
        host=FakeHost(),
        messages=[{"role": "user", "content": "evaluation"}],
        seed=99,
        subject_slot=0,
        probe_ordinal=0,
        repetition=0,
    )
    assert result["status"] == "RESULT"
