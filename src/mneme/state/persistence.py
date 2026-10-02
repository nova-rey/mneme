"""Explicit persistence-mode selection for new MNEME workloads.

CompactStore is the default writable store for new developmental instances.
SQLiteStore remains available as an explicitly selected historical research
compatibility mode.  Keeping this decision in one small module prevents CLI
and runner entry points from silently choosing the snapshot-oriented schema.
"""

from __future__ import annotations

import sqlite3
from enum import StrEnum
from pathlib import Path
from typing import Any

from .compact import CompactStore
from .storage import SQLiteStore


class PersistenceMode(StrEnum):
    """Supported persistence roles for a writable MNEME instance."""

    COMPACT = "compact"
    LEGACY_RESEARCH = "legacy"


class PersistenceModeError(RuntimeError):
    """A persistence mode was omitted or incompatible with the operation."""


def detect_persistence_mode(path: str | Path) -> PersistenceMode | None:
    """Detect an existing store without opening it for writes."""

    candidate = Path(path)
    if not candidate.exists() or candidate.stat().st_size == 0:
        return None
    connection = sqlite3.connect(f"file:{candidate.resolve()}?mode=ro", uri=True)
    try:
        compact = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='compact_meta'"
        ).fetchone()
        if compact is not None:
            return PersistenceMode.COMPACT
        legacy = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='store_info'"
        ).fetchone()
        if legacy is not None:
            return PersistenceMode.LEGACY_RESEARCH
    finally:
        connection.close()
    return None


def create_compact_instance(
    path: str | Path,
    *,
    instance_id: str,
    scope_id: str = "local",
    telemetry: bool = False,
    journal_retention: int | None = None,
    telemetry_retention: int | None = None,
) -> CompactStore:
    """Create a named compact developmental instance.

    Identity and role metadata live in the compact metadata table rather than
    in a second identity schema.  The returned store is open and owned by the
    caller's context manager.
    """

    kwargs: dict[str, Any] = {"telemetry": telemetry}
    if journal_retention is not None:
        kwargs["journal_retention"] = journal_retention
    if telemetry_retention is not None:
        kwargs["telemetry_retention"] = telemetry_retention
    store = CompactStore.create(path, **kwargs)
    store.set_metadata(
        "instance",
        {
            "instance_id": str(instance_id),
            "scope_id": str(scope_id),
            "persistence_mode": PersistenceMode.COMPACT.value,
            "developmental_writable": True,
        },
    )
    return store


def require_legacy_research_store(path: str | Path, *, operation: str) -> SQLiteStore:
    """Open a historical store only after an explicit compatibility choice."""

    mode = detect_persistence_mode(path)
    if mode is PersistenceMode.COMPACT:
        raise PersistenceModeError(
            f"{operation} is a legacy-research operation but {path} is CompactStore; "
            "use a compact-compatible runtime or an explicitly migrated historical copy"
        )
    return SQLiteStore(path)


def require_compact_store(path: str | Path, *, operation: str) -> CompactStore:
    """Open a compact store and reject an accidental legacy developmental path."""

    mode = detect_persistence_mode(path)
    if mode is PersistenceMode.LEGACY_RESEARCH:
        raise PersistenceModeError(
            f"{operation} requires CompactStore, but {path} is the historical SQLiteStore; "
            "perform an explicit copy-only migration first"
        )
    if mode is None:
        raise PersistenceModeError(f"{operation} requires an existing CompactStore: {path}")
    return CompactStore(path)


__all__ = [
    "PersistenceMode",
    "PersistenceModeError",
    "create_compact_instance",
    "detect_persistence_mode",
    "require_compact_store",
    "require_legacy_research_store",
]
