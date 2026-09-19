"""Strict read-only view used for historical checkpoint inspection/evaluation."""

from __future__ import annotations

import hashlib
import json
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
        # Local revision numbers restart at zero after a fork.  Reconstruct
        # the reader view through the manifest ancestry so inherited episodes
        # precede child-local episodes even when their local ordinals collide.
        result: list[dict[str, Any]] = []
        for revision in self.store._history_rows(str(self.manifest()["source_instance_id"])):
            episode_id = revision["episode_id"]
            if episode_id is None:
                continue
            episode = self.store.connection.execute(
                "SELECT * FROM episodes WHERE episode_id=?", (episode_id,)
            ).fetchone()
            if episode is None:
                raise ValueError("checkpoint history references a missing episode")
            result.append(dict(episode))
        return result

    def history(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.store._history_rows(str(self.manifest()["source_instance_id"]))
            if int(row["revision"]) > 0
        ]

    def state_digest(self) -> str:
        """Digest all logical rows without opening a writable database handle."""

        digest = hashlib.sha256()
        tables = self.store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        for table_row in tables:
            table = str(table_row[0])
            columns = [
                str(row[1])
                for row in self.store.connection.execute(f'PRAGMA table_info("{table}")')
            ]
            digest.update(json.dumps({"table": table, "columns": columns}, sort_keys=True).encode())
            for row in self.store.connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                values = [value.hex() if isinstance(value, bytes) else value for value in row]
                digest.update(json.dumps(values, sort_keys=False, default=str).encode())
        return digest.hexdigest()
