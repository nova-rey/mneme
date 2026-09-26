"""Schema 6 storage and migration invariants for Phase Two."""

import sqlite3

from mneme.state.contracts import StoragePermissions
from mneme.state.storage import SCHEMA_VERSION, SQLiteStore


def test_schema_six_creates_learning_policy_and_development_records(tmp_path):
    path = tmp_path / "phase-two.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root(permissions=StoragePermissions(learn=True))
        assert SCHEMA_VERSION == 11
        assert store.connection.execute(
            "SELECT learning_allowed FROM policies"
        ).fetchone()[0] == 1
        manifest_columns = {
            row[1] for row in store.connection.execute("PRAGMA table_info(manifests)")
        }
        assert {
            "learner_snapshot_id",
            "learner_configuration_digest",
            "binding_version",
            "opportunity",
            "coverage_json",
            "authority_revision",
        } <= manifest_columns
        table_names = {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "development_operations",
            "modeled_advance_operations",
            "semantic_bindings",
            "development_observations",
            "learner_updates",
            "learner_values",
            "learner_snapshots",
            "development_assessor_attempts",
            "identity_generation_attempts",
            "conversation_arcs",
            "conversation_arc_members",
            "conversation_arc_events",
        } <= table_names
        observation_columns = {
            row[1] for row in store.connection.execute("PRAGMA table_info(development_observations)")
        }
        assert {
            "arc_id",
            "arc_reentry",
            "reentry_initiator",
            "reentry_origin_arc_id",
            "refractory_active",
        } <= observation_columns
        arc_columns = {
            row[1] for row in store.connection.execute("PRAGMA table_info(conversation_arcs)")
        }
        assert {"start_turn", "end_turn", "source_roles_json", "outcome_keys_json"} <= arc_columns


def test_schema_five_migration_adds_phase_two_records_and_keeps_backup(tmp_path):
    path = tmp_path / "phase-one.sqlite3"
    backup = tmp_path / "phase-one.before-v6.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()

    raw = sqlite3.connect(path)
    raw.execute("PRAGMA foreign_keys=OFF")
    for table in (
        "development_assessor_attempts",
        "learner_values",
        "learner_snapshots",
        "learner_updates",
        "development_observations",
        "semantic_bindings",
        "development_operations",
        "modeled_advance_operations",
    ):
        raw.execute(f"DROP TABLE {table}")
    raw.execute("ALTER TABLE policies DROP COLUMN learning_allowed")
    for column in (
        "authority_revision",
        "coverage_json",
        "opportunity",
        "binding_version",
        "learner_configuration_digest",
        "learner_snapshot_id",
    ):
        raw.execute(f"ALTER TABLE manifests DROP COLUMN {column}")
    raw.execute("UPDATE store_info SET schema_version=5")
    raw.execute("PRAGMA user_version=5")
    raw.commit()
    raw.close()

    SQLiteStore.migrate(path, backup=backup)
    assert backup.is_file()
    with SQLiteStore(path, read_only=True) as migrated:
        assert migrated.connection.execute("PRAGMA user_version").fetchone()[0] == 11
        assert migrated.connection.execute(
            "SELECT learning_allowed FROM policies"
        ).fetchone()[0] == 0
        assert migrated.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='learner_snapshots'"
        ).fetchone() is not None
        assert not migrated.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE sql LIKE '%__v7_%'"
        ).fetchone()
        assert migrated.connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_schema_eight_contains_review_quarantine_and_recovery_records(tmp_path):
    path = tmp_path / "phase-two.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()
        assert store.connection.execute("PRAGMA user_version").fetchone()[0] == 11
        tables = {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {
            "outcome_assessments",
            "quarantine_events",
            "identity_review_operations",
            "identity_review_attempts",
        } <= tables
        operation_sql = store.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='interpretation_operations'"
        ).fetchone()[0]
        assert "episode_id TEXT NOT NULL UNIQUE" not in operation_sql


def test_schema_nine_migrates_modeled_advance_ledger_with_backup(tmp_path):
    path = tmp_path / "schema-nine.sqlite3"
    backup = tmp_path / "schema-nine.before-v10.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()
    raw = sqlite3.connect(path)
    raw.execute("DROP TABLE modeled_advance_operations")
    raw.execute("UPDATE store_info SET schema_version=9")
    raw.execute("PRAGMA user_version=9")
    raw.commit()
    raw.close()

    SQLiteStore.migrate(path, backup=backup, target_version=10)
    assert backup.is_file()
    with SQLiteStore(path, read_only=True) as migrated:
        assert migrated.connection.execute("PRAGMA user_version").fetchone()[0] == 10
        sql = migrated.connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            "AND name='modeled_advance_operations'"
        ).fetchone()[0]
        assert "operation_id TEXT PRIMARY KEY" in sql
        assert migrated.connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_schema_ten_migrates_conversation_arcs_with_backup(tmp_path):
    path = tmp_path / "schema-ten.sqlite3"
    backup = tmp_path / "schema-ten.before-v11.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA foreign_keys=OFF")
    for table in ("conversation_arc_events", "conversation_arc_members", "conversation_arcs"):
        raw.execute(f"DROP TABLE {table}")
    for column in ("arc_id", "arc_reentry", "reentry_initiator", "reentry_origin_arc_id", "refractory_active"):
        raw.execute(f"ALTER TABLE development_observations DROP COLUMN {column}")
    raw.execute("UPDATE store_info SET schema_version=10")
    raw.execute("PRAGMA user_version=10")
    raw.commit()
    raw.close()

    SQLiteStore.migrate(path, backup=backup)
    assert backup.is_file()
    with SQLiteStore(path, read_only=True) as migrated:
        assert migrated.connection.execute("PRAGMA user_version").fetchone()[0] == 11
        tables = {
            row[0]
            for row in migrated.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"conversation_arcs", "conversation_arc_members", "conversation_arc_events"} <= tables
        assert migrated.connection.execute("PRAGMA foreign_key_check").fetchall() == []
