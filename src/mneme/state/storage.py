"""Explicit SQLite storage for MNEME P0.2's durable accepted history."""

from __future__ import annotations

import contextlib
import fcntl
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from .contracts import (
    ArtifactKind,
    StoragePermissions,
    accepted_history_digest,
    canonical_digest,
    new_id,
    validate_id,
)

SCHEMA_VERSION = 1
APPLICATION_ID = 0x4D4E454D  # ASCII "MNEM"

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS store_info (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  schema_version INTEGER NOT NULL,
  record_version INTEGER NOT NULL,
  artifact_kind TEXT NOT NULL CHECK (artifact_kind IN ('working','checkpoint')),
  active_instance_id TEXT,
  created_by_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lineages (
  instance_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  self_ref_id TEXT NOT NULL UNIQUE,
  parent_instance_id TEXT REFERENCES lineages(instance_id),
  fork_checkpoint_id TEXT,
  fork_manifest_id TEXT
);
CREATE TABLE IF NOT EXISTS policies (
  policy_id TEXT PRIMARY KEY,
  scope_id TEXT NOT NULL,
  storage_allowed INTEGER NOT NULL CHECK (storage_allowed IN (0,1)),
  export_allowed INTEGER NOT NULL CHECK (export_allowed IN (0,1)),
  policy_version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS host_records (
  host_ref TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  model_id TEXT NOT NULL,
  model_revision TEXT,
  runtime TEXT NOT NULL,
  fingerprint_json TEXT NOT NULL,
  canonical_digest TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS manifests (
  manifest_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK (revision >= 0),
  parent_manifest_id TEXT REFERENCES manifests(manifest_id),
  inherited_base_manifest_id TEXT REFERENCES manifests(manifest_id),
  policy_id TEXT NOT NULL REFERENCES policies(policy_id),
  self_ref_id TEXT NOT NULL,
  format_version INTEGER NOT NULL,
  controller_version TEXT NOT NULL,
  integrity_digest TEXT NOT NULL,
  accepted_history_digest TEXT NOT NULL,
  UNIQUE(instance_id, revision),
  FOREIGN KEY(instance_id) REFERENCES lineages(instance_id)
);
CREATE TABLE IF NOT EXISTS run_manifests (
  run_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  pinned_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  host_ref TEXT NOT NULL REFERENCES host_records(host_ref),
  policy_id TEXT NOT NULL REFERENCES policies(policy_id),
  experiment_ref TEXT,
  controller_version TEXT NOT NULL,
  context_mode TEXT NOT NULL,
  seed INTEGER,
  rng_plan_version TEXT,
  request_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations (
  operation_id TEXT PRIMARY KEY,
  episode_id TEXT NOT NULL UNIQUE,
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  base_revision INTEGER NOT NULL CHECK (base_revision >= 0),
  run_id TEXT NOT NULL UNIQUE REFERENCES run_manifests(run_id),
  intent_digest TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PREPARED','STARTED','RESULT_READY','ACCEPTED','UNCERTAIN','ABANDONED')),
  generation_id TEXT,
  request_json TEXT,
  failure_code TEXT,
  supersedes_operation_id TEXT REFERENCES operations(operation_id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL REFERENCES operations(operation_id),
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  role TEXT NOT NULL,
  supplier TEXT NOT NULL,
  content TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  UNIQUE(operation_id, ordinal)
);
CREATE TABLE IF NOT EXISTS generation_records (
  generation_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL UNIQUE REFERENCES operations(operation_id),
  host_ref TEXT NOT NULL REFERENCES host_records(host_ref),
  output_source_id TEXT NOT NULL UNIQUE REFERENCES sources(source_id),
  returned_model TEXT NOT NULL,
  returned_provider TEXT NOT NULL,
  effective_parameters_json TEXT NOT NULL,
  usage_json TEXT,
  latency_ms REAL NOT NULL,
  finish_reason TEXT,
  provider_evidence_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
  episode_id TEXT PRIMARY KEY,
  operation_id TEXT NOT NULL UNIQUE REFERENCES operations(operation_id),
  origin_instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  accepted_revision INTEGER NOT NULL CHECK (accepted_revision > 0),
  generation_id TEXT UNIQUE REFERENCES generation_records(generation_id),
  occurred_at TEXT NOT NULL,
  accepted_at TEXT NOT NULL,
  UNIQUE(origin_instance_id, accepted_revision)
);
CREATE TABLE IF NOT EXISTS revisions (
  instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  revision INTEGER NOT NULL CHECK (revision >= 0),
  previous_revision INTEGER CHECK (previous_revision IS NULL OR previous_revision >= 0),
  event_id TEXT NOT NULL UNIQUE,
  event_kind TEXT NOT NULL,
  episode_id TEXT UNIQUE REFERENCES episodes(episode_id),
  manifest_id TEXT UNIQUE REFERENCES manifests(manifest_id),
  accepted_at TEXT NOT NULL,
  PRIMARY KEY(instance_id, revision)
);
CREATE TABLE IF NOT EXISTS current_state (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  active_instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  current_revision INTEGER NOT NULL CHECK (current_revision >= 0),
  current_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id)
);
CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  source_instance_id TEXT NOT NULL REFERENCES lineages(instance_id),
  source_revision INTEGER NOT NULL CHECK (source_revision >= 0),
  source_manifest_id TEXT NOT NULL REFERENCES manifests(manifest_id),
  created_at TEXT NOT NULL,
  format_version INTEGER NOT NULL,
  integrity_digest TEXT NOT NULL
);
"""

_IMMUTABLE = (
    "lineages",
    "policies",
    "host_records",
    "manifests",
    "run_manifests",
    "sources",
    "generation_records",
    "episodes",
    "revisions",
    "checkpoints",
)


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class SchemaError(RuntimeError):
    """The database is not a supported MNEME store."""


class SQLiteStore:
    """One working lineage database, with explicit transaction boundaries."""

    def __init__(self, path: str | Path, *, read_only: bool = False) -> None:
        self.path = Path(path)
        self.read_only = read_only
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if read_only:
            uri = f"file:{self.path.resolve()}?mode=ro"
            self.connection = sqlite3.connect(uri, uri=True, isolation_level=None)
        else:
            existed = self.path.exists() and self.path.stat().st_size > 0
            self.connection = sqlite3.connect(self.path, isolation_level=None)
            if not existed:
                self.connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                self.connection.execute("PRAGMA journal_mode = DELETE")
                self.connection.execute("PRAGMA synchronous = EXTRA")
            self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        if (
            not read_only
            and not self.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='store_info'"
            ).fetchone()
        ):
            self._initialize()
        self._check_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SQLiteStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextlib.contextmanager
    def transaction(self, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        if self.read_only:
            raise sqlite3.OperationalError("read-only store")
        with self.writer_lock():
            self.connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield self.connection
            except BaseException:
                self.connection.rollback()
                raise
            else:
                self.connection.commit()

    @contextlib.contextmanager
    def writer_lock(self) -> Iterator[None]:
        if self.read_only:
            raise sqlite3.OperationalError("read-only store")
        lock_path = self.path.parent / "writer.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _initialize(self) -> None:
        with self.transaction():
            self.connection.executescript(_SCHEMA)
            self.connection.execute("PRAGMA user_version = 1")
            for table in _IMMUTABLE:
                self.connection.executescript(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_update "
                    f"BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END; "
                    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_delete "
                    f"BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END;"
                )

    def _check_schema(self) -> None:
        row = self.connection.execute("PRAGMA user_version").fetchone()
        version = int(row[0]) if row else 0
        if version > SCHEMA_VERSION:
            raise SchemaError(f"unsupported newer schema version {version}")
        if version != SCHEMA_VERSION:
            raise SchemaError(f"unsupported schema version {version}; expected {SCHEMA_VERSION}")
        info = self.connection.execute("SELECT schema_version FROM store_info").fetchone()
        if info is not None and int(info[0]) != SCHEMA_VERSION:
            raise SchemaError("store_info schema version disagrees with PRAGMA user_version")

    def create_root(
        self,
        *,
        scope_id: str = "local",
        self_ref_id: str | None = None,
        instance_id: str | None = None,
        permissions: StoragePermissions = StoragePermissions(),
        controller_version: str = "mneme-p0.2",
    ) -> str:
        """Create the immutable root lineage and revision-zero manifest."""
        instance_id = validate_id(instance_id or new_id(), field="instance_id")
        self_ref_id = validate_id(self_ref_id or new_id(), field="self_ref_id")
        policy_id = new_id()
        manifest_id = new_id()
        now = _utc()
        history_digest = accepted_history_digest([])
        integrity = canonical_digest(
            {"instance_id": instance_id, "revision": 0, "self_ref_id": self_ref_id}
        )
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM store_info").fetchone() is not None:
                raise ValueError("store already has a lineage")
            db.execute(
                "INSERT INTO store_info VALUES (1,?,?,?,?,?)",
                (SCHEMA_VERSION, 1, ArtifactKind.WORKING, instance_id, controller_version),
            )
            db.execute(
                "INSERT INTO lineages VALUES (?,?,?,?,?,?,?)",
                (instance_id, now, scope_id, self_ref_id, None, None, None),
            )
            db.execute(
                "INSERT INTO policies VALUES (?,?,?,?,?)",
                (policy_id, scope_id, int(permissions.store), int(permissions.export), 1),
            )
            db.execute(
                "INSERT INTO manifests VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id,
                    instance_id,
                    0,
                    None,
                    None,
                    policy_id,
                    self_ref_id,
                    1,
                    controller_version,
                    integrity,
                    history_digest,
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES (?,?,?,?,?,?,?,?)",
                (instance_id, 0, None, new_id(), "lineage_created", None, manifest_id, now),
            )
            db.execute("INSERT INTO current_state VALUES (1,?,?,?)", (instance_id, 0, manifest_id))
        return instance_id

    def current(self) -> sqlite3.Row:
        row = self.connection.execute("SELECT * FROM current_state").fetchone()
        if row is None:
            raise SchemaError("store has no active lineage")
        return cast(sqlite3.Row, row)

    def accepted_history(self, instance_id: str | None = None) -> list[sqlite3.Row]:
        instance_id = instance_id or str(self.current()["active_instance_id"])
        validate_id(instance_id, field="instance_id")
        return list(
            self.connection.execute(
                """SELECT r.*, e.episode_id FROM revisions r LEFT JOIN episodes e ON e.episode_id=r.episode_id WHERE r.instance_id=? AND r.revision>0 ORDER BY r.revision""",
                (instance_id,),
            )
        )

    def verify(self) -> list[str]:
        problems: list[str] = []
        fk = list(self.connection.execute("PRAGMA foreign_key_check"))
        problems.extend(f"foreign key: {tuple(row)}" for row in fk)
        head = self.current()
        manifest = self.connection.execute(
            "SELECT * FROM manifests WHERE manifest_id=?", (head["current_manifest_id"],)
        ).fetchone()
        if manifest is None or manifest["revision"] != head["current_revision"]:
            problems.append("current_state does not point to its revision manifest")
        return problems

    def accepted_history_digest(self, instance_id: str | None = None) -> str:
        instance_id = instance_id or str(self.current()["active_instance_id"])
        records = []
        for row in self.connection.execute(
            "SELECT e.accepted_revision,o.operation_id,g.output_source_id "
            "FROM episodes e JOIN operations o ON o.operation_id=e.operation_id "
            "JOIN generation_records g ON g.generation_id=e.generation_id "
            "WHERE e.origin_instance_id=? ORDER BY e.accepted_revision",
            (instance_id,),
        ):
            records.append(
                {
                    "revision": row[0],
                    "input_content": self.connection.execute(
                        "SELECT content FROM sources WHERE operation_id=? AND ordinal=0",
                        (row[1],),
                    ).fetchone()[0],
                    "output_content": self.connection.execute(
                        "SELECT content FROM sources WHERE source_id=?", (row[2],)
                    ).fetchone()[0],
                }
            )
        return accepted_history_digest(records)  # type: ignore[arg-type]
