"""Explicit, reversible Phase One correction and declaration records."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import Any

from .state.storage import SQLiteStore, _utc


class CorrectionError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class _RevisionService:
    def __init__(self, store: SQLiteStore, instance_id: str):
        self.store, self.instance_id = store, instance_id

    def _head(self, db: Any) -> Any:
        current = db.execute(
            "SELECT * FROM current_state WHERE active_instance_id=?", (self.instance_id,)
        ).fetchone()
        if current is None:
            raise CorrectionError("lineage has no current state")
        manifest = db.execute(
            "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
        ).fetchone()
        if manifest is None:
            raise CorrectionError("current manifest is missing")
        return current, manifest

    def _manifest(
        self,
        db: Any,
        current: Any,
        base: Any,
        event_id: str,
        kind: str,
        *,
        count: int | None = None,
    ) -> str:
        revision = int(current["current_revision"]) + 1
        manifest_id = str(uuid.uuid4())
        now = _utc()
        db.execute(
            "INSERT INTO manifests(manifest_id,instance_id,revision,parent_manifest_id,"
            "inherited_base_manifest_id,policy_id,self_ref_id,format_version,controller_version,"
            "integrity_digest,accepted_history_digest,graph_snapshot_id,graph_revision,"
            "accepted_episode_count,self_view_id,self_view_version) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                manifest_id,
                self.instance_id,
                revision,
                base["manifest_id"],
                base["inherited_base_manifest_id"],
                base["policy_id"],
                base["self_ref_id"],
                base["format_version"],
                "mneme-p1.2",
                _digest({"instance_id": self.instance_id, "revision": revision, "event": event_id}),
                base["accepted_history_digest"],
                base["graph_snapshot_id"],
                base["graph_revision"],
                base["accepted_episode_count"] if count is None else count,
                base["self_view_id"],
                base["self_view_version"],
            ),
        )
        db.execute(
            "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
            (
                self.instance_id,
                revision,
                current["current_revision"],
                event_id,
                kind,
                None,
                manifest_id,
                now,
            ),
        )
        db.execute(
            "UPDATE current_state SET current_revision=?,current_manifest_id=? WHERE singleton=1",
            (revision, manifest_id),
        )
        return manifest_id


class CorrectionService(_RevisionService):
    def suppress(
        self,
        *,
        route_id: str | None = None,
        expression_type: str | None = None,
        context_tag: str | None = None,
        source: Mapping[str, Any] | None = None,
    ) -> str:
        if not route_id and not expression_type:
            raise CorrectionError("a route or expression target is required")
        with self.store.transaction() as db:
            current, manifest = self._head(db)
            directive_id = str(uuid.uuid4())
            now = _utc()
            db.execute(
                "INSERT INTO correction_directives VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    directive_id,
                    self.instance_id,
                    route_id,
                    expression_type,
                    context_tag,
                    "until_revoked",
                    "ACTIVE",
                    json.dumps(dict(source or {}), sort_keys=True),
                    int(current["current_revision"]) + 1,
                    None,
                    now,
                ),
            )
            self._manifest(db, current, manifest, directive_id, "correction_suppressed")
            return directive_id

    def revoke(self, directive_id: str, *, source: Mapping[str, Any] | None = None) -> str:
        with self.store.transaction() as db:
            prior = db.execute(
                "SELECT target_route_id,expression_type,context_tag FROM correction_directives "
                "WHERE directive_id=? AND instance_id=? AND status='ACTIVE'",
                (directive_id, self.instance_id),
            ).fetchone()
            if prior is None:
                raise CorrectionError("active directive is missing")
            current, manifest = self._head(db)
            event_id, now = str(uuid.uuid4()), _utc()
            db.execute(
                "INSERT INTO correction_directives VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    self.instance_id,
                    prior[0],
                    prior[1],
                    prior[2],
                    "until_revoked",
                    "REVOKED",
                    json.dumps(dict(source or {}), sort_keys=True),
                    int(current["current_revision"]) + 1,
                    directive_id,
                    now,
                ),
            )
            self._manifest(db, current, manifest, event_id, "correction_revoked")
            return event_id


class DeclarationService(_RevisionService):
    def declare(self, value: Mapping[str, Any], *, source: Mapping[str, Any] | None = None) -> str:
        if not value:
            raise CorrectionError("declaration must not be empty")
        with self.store.transaction() as db:
            current, manifest = self._head(db)
            declaration_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO declarations VALUES(?,?,?,?,?,?,?)",
                (
                    declaration_id,
                    self.instance_id,
                    json.dumps(dict(value), sort_keys=True),
                    json.dumps(dict(source or {}), sort_keys=True),
                    "PROPOSED",
                    int(current["current_revision"]),
                    _utc(),
                ),
            )
            return declaration_id


__all__ = ["CorrectionError", "CorrectionService", "DeclarationService"]
