"""Focused P0.2 storage and contract invariants."""

import sqlite3
import subprocess
import sys

import pytest

from mneme.contracts import GenerationRequest
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions, accepted_history_digest, canonical_digest
from mneme.state.service import ContinuityService
from mneme.state.snapshots import create_checkpoint, fork_from_checkpoint
from mneme.state.storage import SCHEMA_VERSION, SchemaError, SQLiteStore


def test_root_creation_is_revision_zero_and_durable(tmp_path):
    path = tmp_path / "root.sqlite3"
    with SQLiteStore(path) as store:
        instance = store.create_root(
            scope_id="test", permissions=StoragePermissions(store=True, export=True)
        )
        current = store.current()
        assert current["active_instance_id"] == instance
        assert current["current_revision"] == 0
        assert store.accepted_history(instance) == []
        assert store.accepted_history_digest(instance) == accepted_history_digest([])
        assert store.verify() == []
    with SQLiteStore(path, read_only=True) as reopened:
        assert reopened.current()["active_instance_id"] == instance
        assert reopened.connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert tuple(
            reopened.connection.execute(
                "SELECT storage_allowed, export_allowed, interpretation_allowed FROM policies"
            ).fetchone()
        ) == (1, 1, 0)


def test_explicit_interpretation_permission_is_recorded(tmp_path):
    with SQLiteStore(tmp_path / "phase-one.sqlite3") as store:
        store.create_root(permissions=StoragePermissions(True, False, True))
        assert tuple(
            store.connection.execute(
                "SELECT interpretation_allowed, policy_version FROM policies"
            ).fetchone()
        ) == (1, 3)


def test_explicit_transactions_rollback_and_immutable_rows(tmp_path):
    path = tmp_path / "rollback.sqlite3"
    with SQLiteStore(path) as store:
        instance = store.create_root()
        with pytest.raises(RuntimeError):
            with store.transaction() as db:
                db.execute("UPDATE current_state SET current_revision=9")
                raise RuntimeError("simulated interruption")
        assert store.current()["current_revision"] == 0
        with pytest.raises(sqlite3.IntegrityError, match="immutable record"):
            store.connection.execute(
                "UPDATE lineages SET scope_id='changed' WHERE instance_id=?", (instance,)
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable record"):
            store.connection.execute("DELETE FROM manifests")


def test_schema_rejects_newer_version(tmp_path):
    path = tmp_path / "version.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()
        store.connection.execute("PRAGMA user_version = 99")
    with pytest.raises(SchemaError, match="newer"):
        SQLiteStore(path)


def test_digest_excludes_administrative_fields_and_is_not_behavior_claim(tmp_path):
    records = [
        {
            "revision": 1,
            "event_kind": "episode_accepted",
            "episode_id": "e",
            "created_at": "a",
            "instance_id": "a",
        }
    ]
    changed = [{**records[0], "created_at": "b", "instance_id": "b"}]
    assert accepted_history_digest(records) == accepted_history_digest(changed)
    assert canonical_digest({"instance_id": "a"}) != canonical_digest({"instance_id": "b"})


def test_process_interruption_before_commit_recovers_prior_state(tmp_path):
    path = tmp_path / "interrupt.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()
    code = (
        "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN IMMEDIATE'); "
        "c.execute(\"UPDATE current_state SET current_revision=99\"); __import__('os')._exit(9)"
    )
    result = subprocess.run([sys.executable, "-c", code, str(path)], check=False)
    assert result.returncode == 9
    with SQLiteStore(path, read_only=True) as reopened:
        assert reopened.current()["current_revision"] == 0


def test_schema_migration_is_explicit_backed_up_and_additive(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE store_info (
          singleton INTEGER PRIMARY KEY,
          schema_version INTEGER NOT NULL,
          record_version INTEGER NOT NULL,
          artifact_kind TEXT NOT NULL,
          active_instance_id TEXT,
          created_by_version TEXT NOT NULL
        );
        CREATE TABLE manifests (
          manifest_id TEXT PRIMARY KEY,
          instance_id TEXT NOT NULL,
          revision INTEGER NOT NULL,
          parent_manifest_id TEXT,
          inherited_base_manifest_id TEXT,
          policy_id TEXT NOT NULL,
          self_ref_id TEXT NOT NULL,
          format_version INTEGER NOT NULL,
          controller_version TEXT NOT NULL,
          integrity_digest TEXT NOT NULL,
          accepted_history_digest TEXT NOT NULL
        );
        INSERT INTO store_info VALUES(1,1,1,'working',NULL,'legacy');
        PRAGMA user_version=1;
        """
    )
    connection.close()
    with pytest.raises(SchemaError, match="explicit migration"):
        SQLiteStore(path)
    backup = tmp_path / "legacy.before-v2.sqlite3"
    SQLiteStore.migrate(path, backup=backup)
    assert backup.is_file()
    migrated = sqlite3.connect(path)
    assert migrated.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    columns = {row[1] for row in migrated.execute("PRAGMA table_info(manifests)")}
    assert {"graph_snapshot_id", "graph_revision"} <= columns
    assert (
        migrated.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='candidates'"
        ).fetchone()
        is not None
    )
    assert (
        migrated.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='identity_generation_attempts'"
        ).fetchone()
        is not None
    )
    migrated.close()


def test_schema_v8_to_v9_adds_durable_identity_attempts(tmp_path):
    path = tmp_path / "v8.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()
        store.connection.execute("DROP TABLE identity_generation_attempts")
        store.connection.execute("UPDATE store_info SET schema_version=8")
        store.connection.execute("PRAGMA user_version=8")
    backup = tmp_path / "v8.before-v9.sqlite3"
    SQLiteStore.migrate(path, target_version=9, backup=backup)
    assert backup.is_file()
    with SQLiteStore(path, read_only=True) as migrated:
        assert migrated.connection.execute("PRAGMA user_version").fetchone()[0] == 9
        assert migrated.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='identity_generation_attempts'"
        ).fetchone() is not None


def test_schema_v2_to_v3_backfills_local_episode_counts(tmp_path):
    parent_path = tmp_path / "parent.sqlite3"
    checkpoint_path = tmp_path / "parent.checkpoint.sqlite3"
    child_path = tmp_path / "child.sqlite3"
    with SQLiteStore(parent_path) as parent_store:
        parent = parent_store.create_root(permissions=StoragePermissions(True, True))
        service = ContinuityService(parent_store, parent, FakeHost())
        operation = service.prepare_episode(GenerationRequest(({"role": "user", "content": "x"},)))
        service.generate_operation(operation.operation_id)
        service.accept_episode(operation.operation_id)
        create_checkpoint(parent_store, checkpoint_path)
    child = fork_from_checkpoint(checkpoint_path, child_path)

    raw = sqlite3.connect(child_path)
    raw.execute("PRAGMA foreign_keys=OFF")
    for table in (
        "turn_traces",
        "declarations",
        "correction_directives",
        "self_views",
        "identity_events",
    ):
        raw.execute(f"DROP TABLE {table}")
    for trigger in tuple(
        row[0]
        for row in raw.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
    ):
        raw.execute(f'DROP TRIGGER "{trigger}"')
    for column in ("self_view_version", "self_view_id", "accepted_episode_count"):
        raw.execute(f"ALTER TABLE manifests DROP COLUMN {column}")
    for column in ("provider_reuse_allowed", "recall_allowed"):
        raw.execute(f"ALTER TABLE policies DROP COLUMN {column}")
    raw.execute("UPDATE store_info SET schema_version=2")
    raw.execute("PRAGMA user_version=2")
    raw.commit()
    raw.close()

    backup = tmp_path / "child.before-v3.sqlite3"
    SQLiteStore.migrate(child_path, backup=backup)
    with SQLiteStore(child_path, read_only=True) as migrated:
        counts = migrated.connection.execute(
            "SELECT instance_id,revision,accepted_episode_count FROM manifests "
            "WHERE revision IN (0,1) ORDER BY instance_id,revision"
        ).fetchall()
        assert any(row[0] == child and row[1] == 0 and row[2] == 0 for row in counts)
        assert any(row[0] != child and row[1] == 1 and row[2] == 1 for row in counts)
