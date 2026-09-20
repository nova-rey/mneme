"""Schema 6 storage and migration invariants for Phase Two."""

import sqlite3

from mneme.state.contracts import StoragePermissions
from mneme.state.storage import SCHEMA_VERSION, SQLiteStore


def test_schema_six_creates_learning_policy_and_development_records(tmp_path):
    path = tmp_path / "phase-two.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root(permissions=StoragePermissions(learn=True))
        assert SCHEMA_VERSION == 7
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
            "semantic_bindings",
            "development_observations",
            "learner_updates",
            "learner_values",
            "learner_snapshots",
            "development_assessor_attempts",
        } <= table_names


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
        assert migrated.connection.execute("PRAGMA user_version").fetchone()[0] == 7
        assert migrated.connection.execute(
            "SELECT learning_allowed FROM policies"
        ).fetchone()[0] == 0
        assert migrated.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='learner_snapshots'"
        ).fetchone() is not None


def test_schema_seven_contains_review_and_quarantine_records(tmp_path):
    path = tmp_path / "phase-two.sqlite3"
    with SQLiteStore(path) as store:
        store.create_root()
        assert store.connection.execute("PRAGMA user_version").fetchone()[0] == 7
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
