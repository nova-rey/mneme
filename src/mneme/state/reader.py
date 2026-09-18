"""Strict read-only view used for historical checkpoint inspection/evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import SQLiteStore


class CheckpointReader:
    def __init__(self, path: str | Path):
        self.store = SQLiteStore(path, read_only=True)
        kind = self.store.connection.execute("SELECT artifact_kind FROM store_info").fetchone()[0]
        if kind != "checkpoint":
            self.store.close()
            raise ValueError("not a published checkpoint")

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> CheckpointReader:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def manifest(self) -> dict[str, Any]:
        row = self.store.connection.execute(
            "SELECT m.*,c.checkpoint_id FROM manifests m JOIN checkpoints c ON c.source_manifest_id=m.manifest_id"
        ).fetchone()
        if row is None:
            raise ValueError("checkpoint manifest missing")
        return dict(row)

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
