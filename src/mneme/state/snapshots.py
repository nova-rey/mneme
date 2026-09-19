"""Database-aware checkpoint, fork, and backup publication for P0.2."""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

from .contracts import ArtifactKind, canonical_digest, new_id
from .storage import SQLiteStore, _utc


class SnapshotError(RuntimeError):
    """Checkpoint or fork publication failed."""


def _copy(source: SQLiteStore, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise SnapshotError(f"destination exists: {destination}")
    target = sqlite3.connect(destination, isolation_level=None)
    try:
        source.connection.backup(target)
    finally:
        target.close()


def _sync(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create_checkpoint(
    source: SQLiteStore, destination: str | Path, checkpoint_id: str | None = None
) -> str:
    """Publish a validated, immutable copy of the current accepted state."""
    checkpoint_id = checkpoint_id or new_id()
    current = source.current()
    lineage = source.connection.execute(
        "SELECT * FROM lineages WHERE instance_id=?", (current["active_instance_id"],)
    ).fetchone()
    policy = source.connection.execute(
        "SELECT export_allowed FROM policies WHERE scope_id=?", (lineage["scope_id"],)
    ).fetchone()
    if not policy or not bool(policy[0]):
        raise SnapshotError("export/copy permission denied")
    destination = Path(destination)
    staging = destination.with_suffix(destination.suffix + f".{uuid.uuid4().hex}.staging")
    with source.writer_lock():
        _copy(source, staging)
    try:
        with SQLiteStore(staging) as staged:
            with staged.transaction() as db:
                db.execute("UPDATE store_info SET artifact_kind=?", (ArtifactKind.CHECKPOINT,))
                manifest = db.execute("SELECT current_manifest_id FROM current_state").fetchone()[0]
                db.execute(
                    "INSERT INTO checkpoints VALUES(?,?,?,?,?,?,?)",
                    (
                        checkpoint_id,
                        current["active_instance_id"],
                        current["current_revision"],
                        manifest,
                        _utc(),
                        1,
                        db.execute(
                            "SELECT integrity_digest FROM manifests WHERE manifest_id=?",
                            (manifest,),
                        ).fetchone()[0],
                    ),
                )
            if staged.current()["current_revision"] != current["current_revision"]:
                raise SnapshotError("checkpoint revision changed during backup")
            if staged.verify():
                raise SnapshotError("checkpoint verification failed")
        os.link(staging, destination)
        staging.unlink()
        _sync(destination)
    finally:
        if staging.exists():
            staging.unlink()
    return checkpoint_id


def backup_instance(source: SQLiteStore, destination: str | Path) -> None:
    lineage = source.connection.execute(
        "SELECT scope_id FROM lineages WHERE instance_id=?",
        (source.current()["active_instance_id"],),
    ).fetchone()
    policy = source.connection.execute(
        "SELECT export_allowed FROM policies WHERE scope_id=?", (lineage[0],)
    ).fetchone()
    if not policy or not bool(policy[0]):
        raise SnapshotError("export/copy permission denied")
    destination = Path(destination)
    staging = destination.with_suffix(destination.suffix + f".{uuid.uuid4().hex}.staging")
    with source.writer_lock():
        _copy(source, staging)
    os.link(staging, destination)
    staging.unlink()
    _sync(destination)


def fork_from_checkpoint(
    checkpoint: str | Path, destination: str | Path, child_id: str | None = None
) -> str:
    """Copy a published checkpoint into an independent child lineage."""
    child_id = child_id or new_id()
    checkpoint = Path(checkpoint)
    destination = Path(destination)
    staging = destination.with_suffix(destination.suffix + f".{uuid.uuid4().hex}.staging")
    if destination.exists():
        raise SnapshotError(f"destination exists: {destination}")
    try:
        with SQLiteStore(checkpoint, read_only=True) as source:
            if (
                source.connection.execute("SELECT artifact_kind FROM store_info").fetchone()[0]
                != ArtifactKind.CHECKPOINT
            ):
                raise SnapshotError("fork source is not a checkpoint")
            current = source.current()
            lineage = source.connection.execute(
                "SELECT * FROM lineages WHERE instance_id=?", (current["active_instance_id"],)
            ).fetchone()
            if lineage is None:
                raise SnapshotError("checkpoint active lineage is missing")
            parent_manifest = current["current_manifest_id"]
            source_schema = int(source.connection.execute("PRAGMA user_version").fetchone()[0])
            if source_schema == 1:
                parent_manifest_row = source.connection.execute(
                    "SELECT accepted_history_digest FROM manifests WHERE manifest_id=?",
                    (parent_manifest,),
                ).fetchone()
                parent_manifest_row = (
                    (None, 0, parent_manifest_row[0], None, 0) if parent_manifest_row else None
                )
            elif source_schema == 2:
                parent_manifest_row = source.connection.execute(
                    "SELECT graph_snapshot_id,graph_revision,accepted_history_digest "
                    "FROM manifests WHERE manifest_id=?",
                    (parent_manifest,),
                ).fetchone()
                parent_manifest_row = (
                    (*tuple(parent_manifest_row), None, 0) if parent_manifest_row else None
                )
            else:
                parent_manifest_row = source.connection.execute(
                    "SELECT graph_snapshot_id,graph_revision,accepted_history_digest,"
                    "self_view_id,self_view_version "
                    "FROM manifests WHERE manifest_id=?",
                    (parent_manifest,),
                ).fetchone()
            if parent_manifest_row is None:
                raise SnapshotError("checkpoint current manifest is missing")
            export = source.connection.execute(
                "SELECT export_allowed FROM policies WHERE scope_id=?", (lineage["scope_id"],)
            ).fetchone()
            if not export or not bool(export[0]):
                raise SnapshotError("export/copy permission denied")
            checkpoint_rows = source.connection.execute(
                """
            SELECT checkpoint_id FROM checkpoints
            WHERE source_instance_id=? AND source_revision=? AND source_manifest_id=?
            """,
                (
                    current["active_instance_id"],
                    current["current_revision"],
                    parent_manifest,
                ),
            ).fetchall()
            if len(checkpoint_rows) != 1:
                raise SnapshotError("checkpoint has no unique current descriptor")
            checkpoint_id = checkpoint_rows[0][0]
            _copy(source, staging)
        # A historical v1 checkpoint is never mutated in place.  Upgrade only
        # the private staged copy before converting it to a writable child.
        with sqlite3.connect(staging) as staged_connection:
            staged_version = staged_connection.execute("PRAGMA user_version").fetchone()[0]
        if int(staged_version) == 1:
            migration_backup = Path(f"{staging}.pre-v2")
            SQLiteStore.migrate(staging, backup=migration_backup)
            migration_backup.unlink(missing_ok=True)
        with SQLiteStore._open_checkpoint_for_fork(staging) as child:
            with child.transaction() as db:
                child_id = str(uuid.UUID(child_id))
                child_self = new_id()
                child_manifest = new_id()
                policy = db.execute(
                    "SELECT policy_id FROM policies WHERE scope_id=?", (lineage["scope_id"],)
                ).fetchone()
                if policy is None:
                    raise SnapshotError("checkpoint policy is missing")
                now = _utc()
                child_view_id: str | None = None
                db.execute(
                    "UPDATE store_info SET artifact_kind='working',active_instance_id=?",
                    (child_id,),
                )
                db.execute(
                    "INSERT INTO lineages VALUES(?,?,?,?,?,?,?)",
                    (
                        child_id,
                        now,
                        lineage["scope_id"],
                        child_self,
                        lineage["instance_id"],
                        checkpoint_id,
                        parent_manifest,
                    ),
                )
                if parent_manifest_row[3] is not None:
                    parent_view = db.execute(
                        "SELECT version,name,name_event_id,content_json,content_digest "
                        "FROM self_views WHERE self_view_id=?",
                        (parent_manifest_row[3],),
                    ).fetchone()
                    if parent_view is None:
                        raise SnapshotError("checkpoint self view is missing")
                    # A fork inherits the accepted self-view content, but the
                    # materialized record is local to the child lineage.  Keeping
                    # a parent-owned row in the child manifest would make later
                    # self-view transitions ambiguous across independent stores.
                    child_view_id = new_id()
                    db.execute(
                        "INSERT INTO self_views VALUES(?,?,?,?,?,?,?,?)",
                        (
                            child_view_id,
                            child_id,
                            parent_view[0],
                            parent_view[1],
                            parent_view[2],
                            parent_view[3],
                            parent_view[4],
                            now,
                        ),
                    )
                child_integrity = canonical_digest(
                    {
                        "instance_id": child_id,
                        "revision": 0,
                        "self_ref_id": child_self,
                        "self_view_id": child_view_id,
                        "graph_snapshot_id": parent_manifest_row[0],
                        "graph_revision": parent_manifest_row[1],
                        "accepted_history_digest": parent_manifest_row[2],
                    }
                )
                db.execute(
                    "INSERT INTO manifests("
                    "manifest_id,instance_id,revision,parent_manifest_id,inherited_base_manifest_id,"
                    "policy_id,self_ref_id,format_version,controller_version,integrity_digest,"
                    "accepted_history_digest,graph_snapshot_id,graph_revision,accepted_episode_count,"
                    "self_view_id,self_view_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        child_manifest,
                        child_id,
                        0,
                        None,
                        parent_manifest,
                        policy[0],
                        child_self,
                        1,
                        "mneme-p0.2",
                        child_integrity,
                        parent_manifest_row[2],
                        parent_manifest_row[0],
                        parent_manifest_row[1],
                        0,
                        child_view_id,
                        parent_manifest_row[4],
                    ),
                )
                db.execute(
                    "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                    (child_id, 0, None, new_id(), "fork_created", None, child_manifest, now),
                )
                db.execute("DELETE FROM current_state")
                db.execute(
                    "INSERT INTO current_state VALUES(1,?,?,?)", (child_id, 0, child_manifest)
                )
        os.replace(staging, destination)
        _sync(destination)
        return child_id
    finally:
        if staging.exists():
            staging.unlink()
