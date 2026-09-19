"""Read-only inspection helpers for Phase One stores and preview artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..state.reader import CheckpointReader
from ..state.storage import SQLiteStore
from .artifacts import ArtifactStore


class InspectionError(RuntimeError):
    """The requested inspection target is unavailable or inconsistent."""


def _counter_view(manifest: dict[str, Any], episodes: list[dict[str, Any]]) -> dict[str, Any]:
    instance_id = str(manifest.get("source_instance_id", manifest.get("instance_id", "")))
    local = sum(str(item.get("origin_instance_id")) == instance_id for item in episodes)
    return {
        "lineage_revision": int(manifest.get("source_revision", manifest.get("revision", 0))),
        "accepted_episode_count": int(manifest.get("accepted_episode_count", local)),
        "accepted_episode_ordinal": local,
        "inherited_episode_count": max(0, len(episodes) - local),
        "graph_revision": int(manifest.get("graph_revision", 0)),
        "self_view_version": int(manifest.get("self_view_version", 0)),
    }


def inspect_checkpoint(path: str | Path) -> dict[str, Any]:
    """Inspect a checkpoint without opening a writable database handle."""

    with CheckpointReader(path) as reader:
        manifest = reader.manifest()
        episodes = reader.episodes()
        return {
            "kind": "checkpoint",
            "path": str(path),
            "manifest": manifest,
            "counters": _counter_view(manifest, episodes),
            "history_events": len(reader.history()),
            "state_digest": reader.state_digest(),
        }


def inspect_store(path: str | Path) -> dict[str, Any]:
    """Inspect a working lineage and label independent revision counters."""

    with SQLiteStore(path, read_only=True) as store:
        current = store.current()
        manifest_row = store.connection.execute(
            "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
        ).fetchone()
        if manifest_row is None:
            raise InspectionError("current manifest is missing")
        manifest = dict(manifest_row)
        history = store._history_rows(str(current["active_instance_id"]))
        episodes = []
        for row in history:
            if row["episode_id"] is None:
                continue
            episode = store.connection.execute(
                "SELECT * FROM episodes WHERE episode_id=?", (row["episode_id"],)
            ).fetchone()
            if episode is not None:
                episodes.append(dict(episode))
        manifest.update(
            {
                "source_instance_id": current["active_instance_id"],
                "source_revision": current["current_revision"],
            }
        )
        return {
            "kind": "working",
            "path": str(path),
            "instance_id": current["active_instance_id"],
            "manifest": manifest,
            "counters": _counter_view(manifest, episodes),
            "history_events": len(history),
            "state_digest": _state_digest(store),
        }


def inspect_turn(path: str | Path, operation_id: str) -> dict[str, Any]:
    """Return one private controller trace through a read-only store."""

    with SQLiteStore(path, read_only=True) as store:
        row = store.connection.execute(
            "SELECT * FROM turn_traces WHERE operation_id=?", (operation_id,)
        ).fetchone()
        if row is None:
            raise InspectionError(f"turn trace is missing: {operation_id}")
        result = dict(row)
        for field in (
            "query_json",
            "considered_json",
            "selected_json",
            "suppressed_json",
            "applied_json",
            "request_json",
        ):
            try:
                result[field.removesuffix("_json")] = json.loads(str(result[field]))
            except json.JSONDecodeError as exc:
                raise InspectionError(f"turn trace field is invalid: {field}") from exc
        return result


def inspect_run(run_id: str, lab: str | Path, *, verify: bool = True) -> dict[str, Any]:
    """Use the existing immutable artifact inspector for one prepared run."""

    return ArtifactStore(lab).inspect_run(run_id, verify=verify)


def _state_digest(store: SQLiteStore) -> str:
    import hashlib

    digest = hashlib.sha256()
    for table_row in store.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ):
        table = str(table_row[0])
        digest.update(table.encode())
        for row in store.connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
            digest.update(json.dumps(list(row), default=str, sort_keys=True).encode())
    return digest.hexdigest()


__all__ = ["InspectionError", "inspect_checkpoint", "inspect_run", "inspect_store", "inspect_turn"]
