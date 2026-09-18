import sqlite3

import pytest

from mneme.contracts import GenerationRequest
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.reader import CheckpointReader
from mneme.state.service import ContinuityService
from mneme.state.snapshots import create_checkpoint, fork_from_checkpoint
from mneme.state.storage import SQLiteStore


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


def test_copy_permission_blocks_checkpoint(tmp_path):
    with SQLiteStore(tmp_path / "a.sqlite3") as store:
        store.create_root(permissions=StoragePermissions(True, False))
        with pytest.raises(Exception, match="permission"):
            create_checkpoint(store, tmp_path / "blocked.sqlite3")
