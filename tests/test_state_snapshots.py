import sqlite3

import pytest

from mneme.contracts import GenerationRequest
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.reader import CheckpointReader
from mneme.state.service import ContinuityService
from mneme.state.snapshots import create_checkpoint, fork_from_checkpoint
from mneme.state.storage import SchemaError, SQLiteStore


def test_checkpoint_is_read_only_and_fork_preserves_history(tmp_path):
    working = SQLiteStore(tmp_path / "a.sqlite3")
    instance = working.create_root(permissions=StoragePermissions(True, True))
    service = ContinuityService(working, instance, FakeHost())
    request = GenerationRequest(({"role": "user", "content": "checkpoint"},), seed=1)
    operation = service.prepare_episode(request)
    service.generate_operation(operation.operation_id)
    service.accept_episode(operation.operation_id)
    checkpoint = tmp_path / "checkpoint.sqlite3"
    checkpoint_id = create_checkpoint(working, checkpoint)
    working.close()
    with CheckpointReader(checkpoint) as reader:
        assert reader.manifest()["checkpoint_id"] == checkpoint_id
        assert len(reader.episodes()) == 1
        with pytest.raises(sqlite3.OperationalError):
            reader.store.connection.execute("CREATE TABLE should_fail(x)")
    child = tmp_path / "child.sqlite3"
    child_id = fork_from_checkpoint(checkpoint, child)
    with SQLiteStore(child, read_only=True) as loaded:
        assert loaded.current()["active_instance_id"] == child_id
        assert loaded.connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1
        ancestry = loaded.connection.execute(
            "SELECT parent_instance_id,fork_checkpoint_id,fork_manifest_id FROM lineages "
            "WHERE instance_id=?",
            (child_id,),
        ).fetchone()
        parent_manifest = loaded.connection.execute(
            "SELECT source_manifest_id FROM checkpoints WHERE checkpoint_id=?",
            (checkpoint_id,),
        ).fetchone()[0]
        assert tuple(ancestry) == (instance, checkpoint_id, parent_manifest)
        assert loaded.connection.execute(
            "SELECT COUNT(*) FROM revisions WHERE instance_id=?", (instance,)
        ).fetchone()[0] == 2
        child_manifest = loaded.connection.execute(
            "SELECT integrity_digest FROM manifests WHERE instance_id=? AND revision=0",
            (child_id,),
        ).fetchone()[0]
        assert child_manifest
        assert loaded.verify() == []
    with SQLiteStore(child) as writable_child:
        with pytest.raises(sqlite3.IntegrityError, match="immutable record"):
            writable_child.connection.execute(
                "UPDATE lineages SET scope_id='mutated' WHERE instance_id=?", (instance,)
            )


def test_reader_orders_inherited_history_before_child_local_revision(tmp_path):
    working = SQLiteStore(tmp_path / "parent.sqlite3")
    parent = working.create_root(permissions=StoragePermissions(True, True))
    service = ContinuityService(working, parent, FakeHost())
    for text in ("parent-one", "parent-two"):
        operation = service.prepare_episode(GenerationRequest(({"role": "user", "content": text},)))
        service.generate_operation(operation.operation_id)
        service.accept_episode(operation.operation_id)
    checkpoint = tmp_path / "parent-checkpoint.sqlite3"
    create_checkpoint(working, checkpoint)
    working.close()

    child_path = tmp_path / "child.sqlite3"
    child = fork_from_checkpoint(checkpoint, child_path)
    with SQLiteStore(child_path) as child_store:
        child_service = ContinuityService(child_store, child, FakeHost())
        operation = child_service.prepare_episode(
            GenerationRequest(({"role": "user", "content": "child-one"},))
        )
        child_service.generate_operation(operation.operation_id)
        child_service.accept_episode(operation.operation_id)
        child_checkpoint = tmp_path / "child-checkpoint.sqlite3"
        create_checkpoint(child_store, child_checkpoint)

    with CheckpointReader(child_checkpoint) as reader:
        assert [row["origin_instance_id"] for row in reader.episodes()] == [
            parent,
            parent,
            child,
        ]
        assert [row["instance_id"] for row in reader.history()] == [parent, parent, child]


def test_published_checkpoint_cannot_be_reopened_writable(tmp_path):
    working = SQLiteStore(tmp_path / "a.sqlite3")
    working.create_root(permissions=StoragePermissions(True, True))
    checkpoint = tmp_path / "checkpoint.sqlite3"
    create_checkpoint(working, checkpoint)
    working.close()
    with pytest.raises(SchemaError, match="published checkpoint is read-only"):
        SQLiteStore(checkpoint)


def test_reader_selects_checkpoint_for_current_revision(tmp_path):
    working = SQLiteStore(tmp_path / "a.sqlite3")
    instance = working.create_root(permissions=StoragePermissions(True, True))
    service = ContinuityService(working, instance, FakeHost())

    first = service.prepare_episode(
        GenerationRequest(({"role": "user", "content": "first"},), seed=1)
    )
    service.generate_operation(first.operation_id)
    service.accept_episode(first.operation_id)
    first_checkpoint = tmp_path / "first.sqlite3"
    first_id = create_checkpoint(working, first_checkpoint)

    second = service.prepare_episode(
        GenerationRequest(({"role": "user", "content": "second"},), seed=2)
    )
    service.generate_operation(second.operation_id)
    service.accept_episode(second.operation_id)
    second_checkpoint = tmp_path / "second.sqlite3"
    second_id = create_checkpoint(working, second_checkpoint)
    working.close()

    with CheckpointReader(first_checkpoint) as reader:
        assert reader.manifest()["checkpoint_id"] == first_id
        assert reader.manifest()["source_revision"] == 1
        assert len(reader.episodes()) == 1
    with CheckpointReader(second_checkpoint) as reader:
        assert reader.manifest()["checkpoint_id"] == second_id
        assert reader.manifest()["source_revision"] == 2
        assert len(reader.episodes()) == 2


def test_read_only_open_does_not_create_parent_directory(tmp_path):
    missing = tmp_path / "missing" / "checkpoint.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        CheckpointReader(missing)
    assert not missing.parent.exists()


def test_copy_permission_blocks_checkpoint(tmp_path):
    with SQLiteStore(tmp_path / "a.sqlite3") as store:
        store.create_root(permissions=StoragePermissions(True, False))
        with pytest.raises(Exception, match="permission"):
            create_checkpoint(store, tmp_path / "blocked.sqlite3")
