"""Bounded persistence for live MNEME state.

The original research store is intentionally append-only: every learner value,
materialized graph revision, and learner snapshot is retained in the same
SQLite file.  That is useful for forensic experiments, but it is the wrong
default for a long-lived service.  This module provides a small production
oriented representation with three explicit layers:

* current graph and learner tables contain one row per live object;
* graph revisions contain only changed rows (before/after deltas);
* a bounded learner journal contains only changed learner values.

The research store is not migrated in place.  :func:`migrate_sqlite` reads a
source database without writing to it and creates a new compact store.  This
keeps historical experiment evidence immutable while making equivalence
checks possible on a copy.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

COMPACT_SCHEMA_VERSION = 1
DEFAULT_JOURNAL_RETENTION = 10_000
DEFAULT_TELEMETRY_RETENTION = 10_000


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class CompactStoreError(RuntimeError):
    """Raised when a compact store cannot safely be opened or verified."""


_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS compact_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learner_state (
  edge_key TEXT NOT NULL,
  context TEXT NOT NULL,
  value_json TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  updated_event INTEGER NOT NULL,
  PRIMARY KEY(edge_key, context)
);
CREATE TABLE IF NOT EXISTS learner_journal (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  edge_key TEXT NOT NULL,
  context TEXT NOT NULL,
  operation_id TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS research_telemetry (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_nodes (
  node_key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  content_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_edges (
  edge_key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  content_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_routes (
  route_key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  content_digest TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_revisions (
  revision INTEGER PRIMARY KEY,
  parent_revision INTEGER,
  changes_json TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provenance_refs (
  ref_key TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  source_count INTEGER NOT NULL,
  details_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  revision INTEGER NOT NULL,
  state_digest TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class CompactStore:
    """Current-state plus bounded-delta SQLite persistence.

    ``CompactStore`` deliberately does not pretend to be a drop-in reader for
    the research schema.  It is an explicit persistence mode whose public
    state is small and whose history is reconstructable through graph deltas
    and the bounded learner journal.  Heavy before/after telemetry is opt-in.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        read_only: bool = False,
        journal_retention: int = DEFAULT_JOURNAL_RETENTION,
        telemetry: bool = False,
        telemetry_retention: int = DEFAULT_TELEMETRY_RETENTION,
    ) -> None:
        if journal_retention < 0 or telemetry_retention < 0:
            raise ValueError("journal and telemetry retention cannot be negative")
        self.path = Path(path)
        self.read_only = read_only
        self.journal_retention = journal_retention
        self.telemetry = telemetry
        self.telemetry_retention = telemetry_retention
        if read_only:
            uri = f"file:{self.path.resolve()}?mode=ro"
            self.connection = sqlite3.connect(uri, uri=True, isolation_level=None)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path, isolation_level=None)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA wal_autocheckpoint=1000")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        if not self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='compact_meta'"
        ).fetchone():
            if read_only:
                self.close()
                raise CompactStoreError("compact store schema is missing")
            self.connection.executescript(_SCHEMA)
            self._meta_set("schema_version", str(COMPACT_SCHEMA_VERSION))
            self._meta_set("journal_retention", str(journal_retention))
            self._meta_set("telemetry_enabled", "1" if telemetry else "0")
            self._meta_set("telemetry_retention", str(telemetry_retention))
        version = self._meta_get("schema_version")
        if version != str(COMPACT_SCHEMA_VERSION):
            self.close()
            raise CompactStoreError(f"unsupported compact schema version {version!r}")

    @classmethod
    def create(
        cls,
        path: str | Path,
        *,
        journal_retention: int = DEFAULT_JOURNAL_RETENTION,
        telemetry: bool = False,
        telemetry_retention: int = DEFAULT_TELEMETRY_RETENTION,
    ) -> CompactStore:
        return cls(
            path,
            journal_retention=journal_retention,
            telemetry=telemetry,
            telemetry_retention=telemetry_retention,
        )

    def close(self) -> None:
        if not self.read_only:
            # Do not leave an unbounded WAL beside the live state file.  The
            # WAL is an operational journal, not part of the long-term state
            # representation; a clean close folds it into the database and
            # truncates the sidecar.
            self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.connection.close()

    def __enter__(self) -> CompactStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _require_write(self) -> None:
        if self.read_only:
            raise CompactStoreError("compact store is read-only")

    def _meta_get(self, key: str) -> str | None:
        row = self.connection.execute("SELECT value FROM compact_meta WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def _meta_set(self, key: str, value: str) -> None:
        self._require_write()
        self.connection.execute(
            "INSERT INTO compact_meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def set_metadata(self, key: str, value: Any) -> None:
        """Persist one small runtime metadata value outside live state rows."""

        if not key or not key.strip():
            raise ValueError("metadata key must be non-empty")
        self._meta_set(str(key), _json(value))

    def metadata(self, key: str, default: Any = None) -> Any:
        """Read one JSON-encoded runtime metadata value."""

        raw = self._meta_get(str(key))
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CompactStoreError(f"metadata {key!r} is not valid JSON") from exc

    def record_telemetry(self, kind: str, payload: Mapping[str, Any]) -> bool:
        """Append bounded optional research telemetry.

        Telemetry is deliberately separate from current state.  Disabled
        telemetry is a no-op so production descendants do not accidentally
        accumulate an unbounded research log.
        """

        self._require_write()
        if not self.telemetry:
            return False
        self.connection.execute(
            "INSERT INTO research_telemetry(kind,payload_json,created_at) VALUES(?,?,?)",
            (str(kind), _json(dict(payload)), self._now()),
        )
        self.connection.execute(
            "DELETE FROM research_telemetry WHERE sequence <= COALESCE((SELECT MAX(sequence) FROM research_telemetry)-?,0)",
            (self.telemetry_retention,),
        )
        return True

    def storage_metrics(self, *, label: str | None = None) -> dict[str, Any]:
        """Return bounded, read-only storage metrics for a runtime receipt."""

        table_counts: dict[str, int] = {}
        for table in (
            "graph_nodes",
            "graph_edges",
            "graph_routes",
            "graph_revisions",
            "learner_state",
            "learner_journal",
            "research_telemetry",
            "provenance_refs",
            "checkpoints",
        ):
            table_counts[table] = int(
                self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            )
        page_count = int(self.connection.execute("PRAGMA page_count").fetchone()[0])
        page_size = int(self.connection.execute("PRAGMA page_size").fetchone()[0])
        freelist = int(self.connection.execute("PRAGMA freelist_count").fetchone()[0])
        files: dict[str, int] = {}
        for suffix in ("", "-wal", "-shm"):
            candidate = self.path if not suffix else self.path.with_name(self.path.name + suffix)
            if candidate.exists():
                files[suffix or "database"] = candidate.stat().st_size
        result: dict[str, Any] = {
            "label": label,
            "path": str(self.path),
            "files": files,
            "database_bytes": files.get("database", 0),
            "page_count": page_count,
            "page_size": page_size,
            "freelist_pages": freelist,
            "table_rows": table_counts,
            "journal_retention": self.journal_retention,
            "telemetry_enabled": self.telemetry,
            "telemetry_retention": self.telemetry_retention,
        }
        return result

    @staticmethod
    def _now() -> str:
        # UTC ISO strings keep journals readable while remaining deterministic
        # enough for audit ordering (the sequence is authoritative).
        import datetime

        return datetime.datetime.now(datetime.UTC).isoformat(timespec="microseconds")

    def _tx(self) -> sqlite3.Connection:
        self._require_write()
        self.connection.execute("BEGIN IMMEDIATE")
        return self.connection

    def _finish(self, success: bool) -> None:
        if success:
            self.connection.commit()
        else:
            self.connection.rollback()

    def _current_rows(self, table: str) -> dict[str, dict[str, Any]]:
        if table not in {"nodes", "edges", "routes"}:
            raise ValueError(f"unsupported graph table {table!r}")
        sql_table = {"nodes": "graph_nodes", "edges": "graph_edges", "routes": "graph_routes"}[table]
        return {
            str(row[0]): json.loads(str(row[1]))
            for row in self.connection.execute(
                f"SELECT { 'node_key' if table == 'nodes' else 'edge_key' if table == 'edges' else 'route_key' },value_json FROM {sql_table}"
            )
        }

    def _replace_graph_table(self, table: str, key: str, value: Mapping[str, Any] | None) -> None:
        sql_table, column = {
            "nodes": ("graph_nodes", "node_key"),
            "edges": ("graph_edges", "edge_key"),
            "routes": ("graph_routes", "route_key"),
        }[table]
        if value is None:
            self.connection.execute(f"DELETE FROM {sql_table} WHERE {column}=?", (key,))
            return
        payload = dict(value)
        encoded = _json(payload)
        self.connection.execute(
            f"INSERT INTO {sql_table}({column},value_json,content_digest) VALUES(?,?,?) "
            f"ON CONFLICT({column}) DO UPDATE SET value_json=excluded.value_json,content_digest=excluded.content_digest",
            (key, encoded, _digest(payload)),
        )

    def put_graph(
        self,
        *,
        nodes: Mapping[str, Mapping[str, Any]],
        edges: Mapping[str, Mapping[str, Any]],
        routes: Mapping[str, Mapping[str, Any]],
    ) -> int:
        """Publish a graph revision containing only changed rows."""
        self._require_write()
        incoming = {"nodes": {str(k): dict(v) for k, v in nodes.items()}, "edges": {str(k): dict(v) for k, v in edges.items()}, "routes": {str(k): dict(v) for k, v in routes.items()}}
        current = {table: self._current_rows(table) for table in incoming}
        changes: list[dict[str, Any]] = []
        for table in ("nodes", "edges", "routes"):
            for key in sorted(set(current[table]) | set(incoming[table])):
                before = current[table].get(key)
                after = incoming[table].get(key)
                if before != after:
                    changes.append({"table": table, "key": key, "before": before, "after": after})
        if not changes:
            row = self.connection.execute("SELECT COALESCE(MAX(revision),0) FROM graph_revisions").fetchone()
            return int(row[0])
        current_revision = int(self._meta_get("graph_revision") or "0")
        revision = current_revision + 1
        parent = current_revision or None
        payload = {"revision": revision, "parent_revision": parent, "changes": changes}
        success = False
        self._tx()
        try:
            for change in changes:
                self._replace_graph_table(str(change["table"]), str(change["key"]), change["after"])
            self.connection.execute(
                "INSERT INTO graph_revisions VALUES(?,?,?,?,?)",
                (revision, parent, _json(changes), _digest(payload), self._now()),
            )
            self._meta_set("graph_revision", str(revision))
            self._finish(True)
            success = True
        finally:
            if not success:
                self._finish(False)
        return revision

    def put_learner(
        self,
        edge_key: str,
        context: str,
        value: Mapping[str, Any],
        *,
        operation_id: str = "unknown",
        research_telemetry: Mapping[str, Any] | None = None,
    ) -> bool:
        """Upsert one live learner value and journal only actual changes."""
        self._require_write()
        key = (str(edge_key), str(context))
        encoded = _json(dict(value))
        digest = _digest(dict(value))
        old = self.connection.execute(
            "SELECT value_json,content_digest FROM learner_state WHERE edge_key=? AND context=?",
            key,
        ).fetchone()
        changed = old is None or str(old[1]) != digest
        success = False
        self._tx()
        try:
            if changed:
                next_event = int(self._meta_get("event_sequence") or "0") + 1
                before = None if old is None else str(old[0])
                self.connection.execute(
                    "INSERT INTO learner_state VALUES(?,?,?,?,?) "
                    "ON CONFLICT(edge_key,context) DO UPDATE SET value_json=excluded.value_json,"
                    "content_digest=excluded.content_digest,updated_event=excluded.updated_event",
                    (*key, encoded, digest, next_event),
                )
                self.connection.execute(
                    "INSERT INTO learner_journal(edge_key,context,operation_id,before_json,after_json,content_digest,created_at) VALUES(?,?,?,?,?,?,?)",
                    (*key, str(operation_id), before, encoded, digest, self._now()),
                )
                self._meta_set("event_sequence", str(next_event))
            if research_telemetry is not None and self.telemetry:
                self.connection.execute(
                    "INSERT INTO research_telemetry(kind,payload_json,created_at) VALUES(?,?,?)",
                    ("learner_update", _json(dict(research_telemetry)), self._now()),
                )
                self.connection.execute(
                    "DELETE FROM research_telemetry WHERE sequence <= COALESCE((SELECT MAX(sequence) FROM research_telemetry)-?,0)",
                    (self.telemetry_retention,),
                )
            if changed and self.journal_retention >= 0:
                self.connection.execute(
                    "DELETE FROM learner_journal WHERE sequence <= COALESCE((SELECT MAX(sequence) FROM learner_journal)-?,0)",
                    (self.journal_retention,),
                )
            self._finish(True)
            success = True
        finally:
            if not success:
                self._finish(False)
        return changed

    def put_learner_batch(
        self,
        records: Sequence[tuple[str, str, Mapping[str, Any], str]],
    ) -> int:
        """Apply learner values in one transaction and return changed count.

        Live callers can use one record at a time.  Batch publication is also
        useful for recovery and stress tests because it bounds transaction
        overhead without changing the unchanged-value suppression semantics.
        """
        self._require_write()
        changed_count = 0
        success = False
        self._tx()
        try:
            for edge_key, context, value, operation_id in records:
                key = (str(edge_key), str(context))
                encoded = _json(dict(value))
                digest = _digest(dict(value))
                old = self.connection.execute(
                    "SELECT value_json,content_digest FROM learner_state WHERE edge_key=? AND context=?",
                    key,
                ).fetchone()
                if old is not None and str(old[1]) == digest:
                    continue
                next_event = int(self._meta_get("event_sequence") or "0") + 1
                self.connection.execute(
                    "INSERT INTO learner_state VALUES(?,?,?,?,?) ON CONFLICT(edge_key,context) DO UPDATE SET "
                    "value_json=excluded.value_json,content_digest=excluded.content_digest,updated_event=excluded.updated_event",
                    (*key, encoded, digest, next_event),
                )
                self.connection.execute(
                    "INSERT INTO learner_journal(edge_key,context,operation_id,before_json,after_json,content_digest,created_at) VALUES(?,?,?,?,?,?,?)",
                    (*key, str(operation_id), None if old is None else str(old[0]), encoded, digest, self._now()),
                )
                self._meta_set("event_sequence", str(next_event))
                changed_count += 1
            if self.journal_retention >= 0:
                self.connection.execute(
                    "DELETE FROM learner_journal WHERE sequence <= COALESCE((SELECT MAX(sequence) FROM learner_journal)-?,0)",
                    (self.journal_retention,),
                )
            self._finish(True)
            success = True
        finally:
            if not success:
                self._finish(False)
        return changed_count

    def learner_state(self) -> dict[tuple[str, str], dict[str, Any]]:
        return {
            (str(row[0]), str(row[1])): json.loads(str(row[2]))
            for row in self.connection.execute("SELECT edge_key,context,value_json FROM learner_state")
        }

    def graph_state(self) -> dict[str, dict[str, dict[str, Any]]]:
        return {table: self._current_rows(table) for table in ("nodes", "edges", "routes")}

    def state_digest(self) -> str:
        learner = [
            {"edge_key": edge_key, "context": context, "value": value}
            for (edge_key, context), value in sorted(self.learner_state().items())
        ]
        return _digest({"graph": self.graph_state(), "learner": learner})

    def graph_at(self, revision: int) -> dict[str, dict[str, dict[str, Any]]]:
        if revision < 0:
            raise ValueError("revision cannot be negative")
        current_revision = int(self._meta_get("graph_revision") or "0")
        if revision > current_revision:
            raise CompactStoreError(f"graph revision {revision} is not available")
        graph: dict[str, dict[str, dict[str, Any]]] = {"nodes": {}, "edges": {}, "routes": {}}
        for row in self.connection.execute(
            "SELECT revision,changes_json FROM graph_revisions WHERE revision<=? ORDER BY revision",
            (revision,),
        ):
            for change in json.loads(str(row[1])):
                table = str(change["table"])
                key = str(change["key"])
                after = change.get("after")
                if after is None:
                    graph[table].pop(key, None)
                else:
                    graph[table][key] = dict(after)
        return graph

    def add_provenance_ref(
        self, ref_key: str, *, kind: str, content_digest: str, source_count: int, details: Mapping[str, Any]
    ) -> None:
        self._require_write()
        self.connection.execute(
            "INSERT INTO provenance_refs VALUES(?,?,?,?,?) ON CONFLICT(ref_key) DO UPDATE SET "
            "kind=excluded.kind,content_digest=excluded.content_digest,source_count=excluded.source_count,details_json=excluded.details_json",
            (str(ref_key), str(kind), str(content_digest), int(source_count), _json(dict(details))),
        )

    def checkpoint(self, destination: str | Path, *, checkpoint_id: str | None = None) -> str:
        """Atomically create one compact checkpoint with a free-space guard."""
        self._require_write()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise CompactStoreError(f"checkpoint destination exists: {destination}")
        self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        pages = int(self.connection.execute("PRAGMA page_count").fetchone()[0])
        page_size = int(self.connection.execute("PRAGMA page_size").fetchone()[0])
        estimate = pages * page_size
        free = shutil.disk_usage(destination.parent).free
        if free < max(estimate * 2, 16 * 1024 * 1024):
            raise CompactStoreError(f"insufficient free space for atomic checkpoint: {free} < {estimate * 2}")
        checkpoint_id = checkpoint_id or str(uuid.uuid4())
        fd, raw_staging = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".staging", dir=destination.parent)
        os.close(fd)
        staging = Path(raw_staging)
        try:
            target = sqlite3.connect(staging, isolation_level=None)
            try:
                # The live store uses WAL for bounded writer contention, but a
                # checkpoint must be self-contained.  Leaving a sibling WAL
                # beside a renamed staging file would make the published
                # database unreadable after the staging name disappears.
                target.execute("PRAGMA journal_mode=DELETE")
                self.connection.backup(target)
            finally:
                target.close()
            with sqlite3.connect(staging) as check:
                check.execute("PRAGMA journal_mode=DELETE")
                check.execute("INSERT INTO checkpoints VALUES(?,?,?,?)", (checkpoint_id, int(self._meta_get("graph_revision") or "0"), self.state_digest(), self._now()))
            os.replace(staging, destination)
            self.connection.execute("INSERT INTO checkpoints VALUES(?,?,?,?) ON CONFLICT(checkpoint_id) DO NOTHING", (checkpoint_id, int(self._meta_get("graph_revision") or "0"), self.state_digest(), self._now()))
            return checkpoint_id
        finally:
            staging.unlink(missing_ok=True)

    def verify(self) -> list[str]:
        problems: list[str] = []
        integrity = self.connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            problems.append(f"integrity_check={integrity}")
        foreign = self.connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign:
            problems.append(f"foreign_key_check={len(foreign)}")
        revisions = [int(row[0]) for row in self.connection.execute("SELECT revision FROM graph_revisions ORDER BY revision")]
        if revisions and revisions != list(range(1, max(revisions) + 1)):
            problems.append("graph revision sequence has a gap")
        for row in self.connection.execute("SELECT edge_key,context,value_json,content_digest FROM learner_state"):
            if _digest(json.loads(str(row[2]))) != str(row[3]):
                problems.append(f"learner digest mismatch: {row[0]}:{row[1]}")
        return problems


def _source_graph(source: sqlite3.Connection, instance_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest_id = str(source.execute("SELECT current_manifest_id FROM current_state").fetchone()[0])
    snapshot_id = source.execute("SELECT graph_snapshot_id FROM manifests WHERE manifest_id=?", (manifest_id,)).fetchone()[0]
    if snapshot_id is None:
        return {}, {}, {}
    # Keep the source column names and values; snapshot_id is an administrative
    # locator and is intentionally absent from the compact logical object.
    nodes = {}
    for row in source.execute("SELECT concept_key,label,normalized_label,kind,confidence,salience,candidate_id FROM graph_concepts WHERE snapshot_id=?", (snapshot_id,)):
        nodes[str(row[0])] = dict(row)
    edges = {}
    for row in source.execute("SELECT edge_key,source_key,target_key,relationship,polarity,context_json,evidence_json FROM graph_edges WHERE snapshot_id=?", (snapshot_id,)):
        edges[str(row[0])] = dict(row)
    routes = {}
    for row in source.execute("SELECT route_key,edge_keys_json,source_json FROM graph_routes WHERE snapshot_id=?", (snapshot_id,)):
        routes[str(row[0])] = dict(row)
    return nodes, edges, routes


def migrate_sqlite(source_path: str | Path, destination_path: str | Path, *, journal_retention: int = DEFAULT_JOURNAL_RETENTION) -> dict[str, Any]:
    """Migrate a research SQLite store into a compact store without mutation."""
    source = Path(source_path)
    destination = Path(destination_path)
    if destination.exists():
        raise CompactStoreError(f"destination exists: {destination}")
    raw = sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True)
    raw.row_factory = sqlite3.Row
    try:
        head = raw.execute("SELECT active_instance_id,current_revision FROM current_state").fetchone()
        if head is None:
            raise CompactStoreError("source has no current state")
        instance_id, revision = str(head[0]), int(head[1])
        nodes, edges, routes = _source_graph(raw, instance_id)
        edge_bindings = {
            str(row[0]): str(row[1])
            for row in raw.execute(
                "SELECT local_key,canonical_key FROM semantic_bindings "
                "WHERE instance_id=? ORDER BY created_at,rowid",
                (instance_id,),
            )
        }
        learner: dict[tuple[str, str], dict[str, Any]] = {}
        rows = raw.execute(
            "SELECT v.edge_key,v.context,v.accessibility,v.support,v.consequence,v.lifetime_credit,"
            "v.induced_credit,v.rolling_credit,v.last_consolidation_opportunity,v.inactivity_ticks,"
            "v.opportunity,v.content_digest,u.after_json FROM learner_values v "
            "JOIN learner_updates u ON u.update_id=v.update_id WHERE v.instance_id=? ORDER BY v.rowid",
            (instance_id,),
        )
        for row in rows:
            payload = json.loads(str(row[12]))
            learner[(str(row[0]), str(row[1]))] = payload
        with CompactStore.create(destination, journal_retention=journal_retention) as compact:
            compact.put_graph(nodes=nodes, edges=edges, routes=routes)
            # Graph rows retain their local materialization keys for audit, but
            # runtime SAA must resolve them to the canonical learner identity.
            # Keep this as a compact mapping rather than copying the full
            # immutable semantic-binding table into the descendant store.
            compact.set_metadata("edge_bindings", edge_bindings)
            for (edge_key, context), value in learner.items():
                compact.put_learner(edge_key, context, value, operation_id="migration")
            for table in ("sources", "operations", "development_observations", "outcome_assessments", "semantic_bindings"):
                exists = raw.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                count = 0 if exists is None else int(raw.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                compact.add_provenance_ref(table, kind="research_reference", content_digest=_digest({"table": table, "count": count}), source_count=count, details={"source": str(source), "table": table})
            digest = compact.state_digest()
            verify = compact.verify()
        return {
            "source": str(source),
            "destination": str(destination),
            "source_revision": revision,
            "nodes": len(nodes),
            "edges": len(edges),
            "routes": len(routes),
            "edge_bindings": len(edge_bindings),
            "learner_values": len(learner),
            "state_digest": digest,
            "verification": verify,
        }
    finally:
        raw.close()


__all__ = [
    "COMPACT_SCHEMA_VERSION",
    "DEFAULT_JOURNAL_RETENTION",
    "DEFAULT_TELEMETRY_RETENTION",
    "CompactStore",
    "CompactStoreError",
    "migrate_sqlite",
]
