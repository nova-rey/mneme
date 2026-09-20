"""Append-only Phase Two authority records.

Quarantine and reviewed identity decisions live beside, but do not mutate,
the accepted developmental ledger.  Consumers resolve the latest authority
event and rebuild materialized learner state from immutable observations.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..identity import validate_name
from ..state.policy import PolicyError, PolicyService
from ..state.storage import SQLiteStore, _utc


class AuthorityError(RuntimeError):
    """An authority transition cannot be accepted."""


@dataclass(frozen=True)
class QuarantineRecord:
    event_id: str
    target_kind: str
    target_id: str
    action: str
    reason: str
    authority_revision: int


class QuarantineService:
    """Record and inspect reversible quarantine decisions."""

    def __init__(self, store: SQLiteStore, instance_id: str):
        self.store = store
        self.instance_id = instance_id

    def _require_learning(self) -> None:
        try:
            PolicyService(self.store, self.instance_id).require("learn")
        except PolicyError as exc:
            raise AuthorityError(str(exc)) from exc

    def _next_revision(self, db: Any) -> int:
        row = db.execute(
            "SELECT COALESCE(MAX(authority_revision),0) FROM quarantine_events "
            "WHERE instance_id=?",
            (self.instance_id,),
        ).fetchone()
        return int(row[0]) + 1

    def _transition(
        self,
        action: str,
        target_kind: str,
        target_id: str,
        reason: str,
        source: Mapping[str, Any] | None,
    ) -> QuarantineRecord:
        self._require_learning()
        if action not in {"ADD", "RELEASE"}:
            raise AuthorityError("invalid quarantine action")
        if not target_kind or not target_id or not reason:
            raise AuthorityError("quarantine target and reason are required")
        with self.store.transaction() as db:
            revision = self._next_revision(db)
            event_id = str(uuid.uuid4())
            prior = db.execute(
                "SELECT event_id FROM quarantine_events WHERE instance_id=? "
                "AND target_kind=? AND target_id=? ORDER BY authority_revision DESC LIMIT 1",
                (self.instance_id, target_kind, target_id),
            ).fetchone()
            db.execute(
                "INSERT INTO quarantine_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    self.instance_id,
                    target_kind,
                    target_id,
                    action,
                    reason,
                    json.dumps(dict(source or {}), sort_keys=True),
                    revision,
                    prior[0] if prior else None,
                    _utc(),
                ),
            )
            return QuarantineRecord(
                event_id, target_kind, target_id, action, reason, revision
            )

    def add(
        self,
        target_kind: str,
        target_id: str,
        reason: str,
        *,
        source: Mapping[str, Any] | None = None,
    ) -> QuarantineRecord:
        return self._transition("ADD", target_kind, target_id, reason, source)

    def release(
        self,
        event_id: str,
        *,
        source: Mapping[str, Any] | None = None,
    ) -> QuarantineRecord:
        row = self.store.connection.execute(
            "SELECT target_kind,target_id,reason FROM quarantine_events "
            "WHERE event_id=? AND instance_id=? AND action='ADD'",
            (event_id, self.instance_id),
        ).fetchone()
        if row is None:
            raise AuthorityError("active quarantine event is missing")
        return self._transition("RELEASE", str(row[0]), str(row[1]), str(row[2]), source)

    def is_quarantined(self, target_kind: str, target_id: str) -> bool:
        row = self.store.connection.execute(
            "SELECT action FROM quarantine_events WHERE instance_id=? "
            "AND target_kind=? AND target_id=? ORDER BY authority_revision DESC LIMIT 1",
            (self.instance_id, target_kind, target_id),
        ).fetchone()
        return bool(row and str(row[0]) == "ADD")


class IdentityReviewService:
    """Durably stage, record, and explicitly accept identity proposals."""

    def __init__(self, store: SQLiteStore, instance_id: str):
        self.store = store
        self.instance_id = instance_id

    def prepare(
        self,
        proposal: Mapping[str, Any],
        *,
        operation_key: str,
    ) -> str:
        if not operation_key or not proposal:
            raise AuthorityError("identity proposal and operation key are required")
        current = self.store.current()
        review_id = str(uuid.uuid4())
        now = _utc()
        with self.store.transaction() as db:
            prior = db.execute(
                "SELECT review_id FROM identity_review_operations WHERE operation_key=?",
                (operation_key,),
            ).fetchone()
            if prior is not None:
                return str(prior[0])
            db.execute(
                "INSERT INTO identity_review_operations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    review_id,
                    self.instance_id,
                    current["current_manifest_id"],
                    operation_key,
                    json.dumps(dict(proposal), sort_keys=True),
                    "PREPARED",
                    None,
                    None,
                    0,
                    now,
                    now,
                ),
            )
        return review_id

    def record_attempt(
        self,
        review_id: str,
        result: Mapping[str, Any] | str | None,
        *,
        attempt: int = 0,
        status: str = "RESULT_READY",
        usage: Mapping[str, Any] | None = None,
        host_ref: str | None = None,
        errors: tuple[str, ...] = (),
    ) -> None:
        if attempt < 0 or status not in {
            "STARTED",
            "RESULT_READY",
            "VALID",
            "INVALID",
            "UNCERTAIN",
        }:
            raise AuthorityError("invalid identity review attempt")
        encoded = result if isinstance(result, str) else json.dumps(result, sort_keys=True)
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT review_id FROM identity_review_operations WHERE review_id=? "
                "AND instance_id=?",
                (review_id, self.instance_id),
            ).fetchone()
            if row is None:
                raise AuthorityError("unknown identity review")
            db.execute(
                "INSERT OR REPLACE INTO identity_review_attempts VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    review_id,
                    attempt,
                    "{}",
                    encoded,
                    json.dumps(dict(usage or {}), sort_keys=True),
                    host_ref,
                    status,
                    json.dumps(list(errors), sort_keys=True),
                    _utc(),
                    _utc(),
                ),
            )
            db.execute(
                "UPDATE identity_review_operations SET stage=?,updated_at=? WHERE review_id=?",
                (
                    {
                        "INVALID": "REJECTED",
                        "VALID": "RESULT_READY",
                        "RESULT_READY": "RESULT_READY",
                    }.get(status, status),
                    _utc(),
                    review_id,
                ),
            )

    def accept(self, review_id: str, *, name: str) -> str:
        name = validate_name(name)
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT stage FROM identity_review_operations WHERE review_id=? "
                "AND instance_id=?",
                (review_id, self.instance_id),
            ).fetchone()
            if row is None or str(row[0]) not in {"RESULT_READY", "VALID"}:
                raise AuthorityError("identity review is not ready for acceptance")
            db.execute(
                "UPDATE identity_review_operations SET stage='ACCEPTED',decision_json=?,"
                "accepted_revision=(SELECT current_revision FROM current_state),updated_at=? "
                "WHERE review_id=?",
                (json.dumps({"name": name}, sort_keys=True), _utc(), review_id),
            )
        return review_id


__all__ = ["AuthorityError", "IdentityReviewService", "QuarantineRecord", "QuarantineService"]
