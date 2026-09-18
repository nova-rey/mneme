"""Strict read-only view used for historical checkpoint inspection/evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import SQLiteStore


class CheckpointReader:
    def __init__(self, path: str | Path, checkpoint_id: str | None = None):
        self.store = SQLiteStore(path, read_only=True)
        kind = self.store.connection.execute("SELECT artifact_kind FROM store_info").fetchone()[0]
        if kind != "checkpoint":
            self.store.close()
            raise ValueError("not a published checkpoint")
        current = self.store.current()
        query = """
            SELECT c.*,m.manifest_id AS matched_manifest_id
            FROM checkpoints c
            JOIN manifests m ON m.manifest_id=c.source_manifest_id
            WHERE c.source_instance_id=?
              AND c.source_revision=?
              AND c.source_manifest_id=?
        """
        parameters: tuple[object, ...] = (
            current["active_instance_id"],
            current["current_revision"],
            current["current_manifest_id"],
        )
        if checkpoint_id is not None:
            query += " AND c.checkpoint_id=?"
            parameters += (checkpoint_id,)
        rows = self.store.connection.execute(query, parameters).fetchall()
        if len(rows) != 1:
            self.store.close()
            if checkpoint_id is not None and not rows:
                raise ValueError("checkpoint identity does not match the published snapshot")
            raise ValueError("published checkpoint has no unique current descriptor")
        self._checkpoint = dict(rows[0])

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> CheckpointReader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def manifest(self) -> dict[str, Any]:
        row = self.store.connection.execute(
            "SELECT * FROM manifests WHERE manifest_id=?",
            (self._checkpoint["source_manifest_id"],),
        ).fetchone()
        if row is None:
            raise ValueError("checkpoint manifest missing")
        result = dict(row)
        result["checkpoint_id"] = self._checkpoint["checkpoint_id"]
        result["source_instance_id"] = self._checkpoint["source_instance_id"]
        result["source_revision"] = self._checkpoint["source_revision"]
        result["checkpoint_integrity_digest"] = self._checkpoint["integrity_digest"]
        return result

    def episodes(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.store.connection.execute(
                "SELECT * FROM episodes ORDER BY accepted_revision"
            )
        ]

    def history(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.store.connection.execute(
                "SELECT * FROM revisions WHERE revision>0 ORDER BY revision"
            )
        ]
