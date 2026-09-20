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

from ..identity import _digest, validate_name
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


@dataclass(frozen=True)
class FeedbackRecord:
    """An explicitly attributable contextual feedback proposal."""

    assessment_id: str
    operation_id: str
    route_key: str
    context: str
    direction: int
    status: str
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
            record = QuarantineRecord(event_id, target_kind, target_id, action, reason, revision)
        # Authority changes are not safe while stale learner materializations
        # remain readable.  Rebuild from the immutable observation ledger
        # after the event is durable; the rebuild publishes a new manifest and
        # leaves all prior snapshots/rows available for audit.
        try:
            from .recovery import rebuild_learner

            rebuild_learner(self.store, reason=f"quarantine:{event_id}")
        except Exception as exc:
            raise AuthorityError(
                "quarantine authority recorded but learner rebuild failed"
            ) from exc
        return record

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
            "SELECT q.target_kind,q.target_id,q.reason FROM quarantine_events q "
            "WHERE q.event_id=? AND q.instance_id=? AND q.action='ADD' "
            "AND q.authority_revision=(SELECT MAX(q2.authority_revision) "
            "FROM quarantine_events q2 WHERE q2.instance_id=q.instance_id "
            "AND q2.target_kind=q.target_kind AND q2.target_id=q.target_id)",
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
                "SELECT * FROM identity_review_operations WHERE review_id=? "
                "AND instance_id=?",
                (review_id, self.instance_id),
            ).fetchone()
            if row is None:
                raise AuthorityError("unknown identity review")
            if str(row["stage"]) != "RESULT_READY":
                raise AuthorityError("identity review is not ready for acceptance")
            valid = db.execute(
                "SELECT 1 FROM identity_review_attempts WHERE review_id=? AND status='VALID' "
                "AND result_json IS NOT NULL",
                (review_id,),
            ).fetchone()
            if valid is None:
                raise AuthorityError("identity review has no valid persisted result")
            current = db.execute(
                "SELECT * FROM current_state WHERE active_instance_id=?", (self.instance_id,)
            ).fetchone()
            if current is None or current["current_manifest_id"] != row["base_manifest_id"]:
                raise AuthorityError("identity review base is stale")
            manifest = db.execute(
                "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
            ).fetchone()
            if manifest is None:
                raise AuthorityError("current identity manifest is missing")
            prior_event = None
            if manifest["self_view_id"] is not None:
                prior_event = db.execute(
                    "SELECT name_event_id FROM self_views WHERE self_view_id=?",
                    (manifest["self_view_id"],),
                ).fetchone()
                event_kind = "supersede"
                if prior_event is None:
                    raise AuthorityError("current self-view name event is missing")
                supersedes = prior_event[0]
            else:
                event_kind = "adopt"
                supersedes = None
            revision = int(current["current_revision"]) + 1
            version = int(manifest["self_view_version"]) + 1
            event_id = str(uuid.uuid4())
            view_id = str(uuid.uuid4())
            now = _utc()
            content = {"name": name}
            content_json = json.dumps(content, sort_keys=True, separators=(",", ":"))
            content_digest = _digest(content)
            db.execute(
                "INSERT INTO identity_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    self.instance_id,
                    event_kind,
                    name,
                    None,
                    json.dumps({"review_id": review_id}, sort_keys=True),
                    revision,
                    version,
                    supersedes,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO self_views VALUES(?,?,?,?,?,?,?,?)",
                (
                    view_id,
                    self.instance_id,
                    version,
                    name,
                    event_id,
                    content_json,
                    content_digest,
                    now,
                ),
            )
            manifest_id = str(uuid.uuid4())
            integrity = _digest(
                {
                    "instance_id": self.instance_id,
                    "revision": revision,
                    "self_view_id": view_id,
                    "self_view_version": version,
                }
            )
            db.execute(
                "INSERT INTO manifests(manifest_id,instance_id,revision,parent_manifest_id,"
                "inherited_base_manifest_id,policy_id,self_ref_id,format_version,"
                "controller_version,integrity_digest,accepted_history_digest,graph_snapshot_id,"
                "graph_revision,accepted_episode_count,self_view_id,self_view_version,"
                "learner_snapshot_id,learner_configuration_digest,binding_version,opportunity,"
                "coverage_json,authority_revision) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id,
                    self.instance_id,
                    revision,
                    manifest["manifest_id"],
                    manifest["inherited_base_manifest_id"],
                    manifest["policy_id"],
                    manifest["self_ref_id"],
                    manifest["format_version"],
                    "mneme-p2.2",
                    integrity,
                    manifest["accepted_history_digest"],
                    manifest["graph_snapshot_id"],
                    manifest["graph_revision"],
                    manifest["accepted_episode_count"],
                    view_id,
                    version,
                    manifest["learner_snapshot_id"],
                    manifest["learner_configuration_digest"],
                    manifest["binding_version"],
                    manifest["opportunity"],
                    manifest["coverage_json"],
                    manifest["authority_revision"],
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.instance_id,
                    revision,
                    current["current_revision"],
                    event_id,
                    "identity_review_accepted",
                    None,
                    manifest_id,
                    now,
                ),
            )
            db.execute(
                "UPDATE current_state SET current_revision=?,current_manifest_id=? "
                "WHERE singleton=1",
                (revision, manifest_id),
            )
            db.execute(
                "UPDATE identity_review_operations SET stage='ACCEPTED',decision_json=?,"
                "accepted_revision=?,updated_at=? "
                "WHERE review_id=?",
                (json.dumps({"name": name}, sort_keys=True), revision, now, review_id),
            )
        return review_id


class FeedbackService:
    """Persist and accept operator feedback through the outcome ledger.

    Feedback is deliberately narrow: it must identify an already accepted
    developmental operation and route, so the learner can replay the same
    attributable consequence without treating free-form prose as authority.
    """

    def __init__(self, store: SQLiteStore, instance_id: str):
        self.store = store
        self.instance_id = instance_id

    def _require_learning(self) -> None:
        try:
            PolicyService(self.store, self.instance_id).require("learn")
        except PolicyError as exc:
            raise AuthorityError(str(exc)) from exc

    def propose(self, proposal: Mapping[str, Any]) -> FeedbackRecord:
        self._require_learning()
        operation_id = str(proposal.get("operation_id", ""))
        route_key = str(proposal.get("route_key", proposal.get("target_route_id", "")))
        context = str(proposal.get("context", "general"))
        direction = int(proposal.get("direction", 0))
        if not operation_id or not route_key or not context or direction not in {-1, 1}:
            raise AuthorityError(
                "feedback requires operation_id, route_key, context, and direction +/-1"
            )
        outcome = str(proposal.get("outcome", "known"))
        if outcome not in {"known", "unknown"}:
            raise AuthorityError("feedback outcome must be known or unknown")
        if self.store.connection.execute(
            "SELECT 1 FROM development_operations WHERE operation_id=? AND instance_id=? "
            "AND stage='ACCEPTED'",
            (operation_id, self.instance_id),
        ).fetchone() is None:
            raise AuthorityError("feedback operation must be an accepted developmental operation")
        assessment_id = "feedback:" + _digest(
            {"instance_id": self.instance_id, "proposal": dict(proposal)}
        )
        current = self.store.current()
        authority_revision = int(current["current_revision"] or 0)
        with self.store.transaction() as db:
            existing = db.execute(
                "SELECT assessment_id FROM outcome_assessments WHERE assessment_id=?",
                (assessment_id,),
            ).fetchone()
            if existing is None:
                db.execute(
                    "INSERT INTO outcome_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        assessment_id,
                        self.instance_id,
                        operation_id,
                        route_key,
                        context,
                        outcome,
                        direction,
                        proposal.get("exposure_id"),
                        int(bool(proposal.get("relevant", True))),
                        json.dumps(dict(proposal), sort_keys=True),
                        json.dumps({"source": "operator_feedback"}, sort_keys=True),
                        "UNCERTAIN",
                        authority_revision,
                        None,
                        _utc(),
                    ),
                )
        return FeedbackRecord(
            assessment_id,
            operation_id,
            route_key,
            context,
            direction,
            "UNCERTAIN",
            authority_revision,
        )

    def accept(self, assessment_id: str) -> FeedbackRecord:
        self._require_learning()
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT operation_id,target_route_id,context,outcome,direction,"
                "authority_revision,status "
                "FROM outcome_assessments WHERE assessment_id=? AND instance_id=?",
                (assessment_id, self.instance_id),
            ).fetchone()
            if row is None:
                raise AuthorityError("unknown feedback proposal")
            if str(row[6]) not in {"UNCERTAIN", "REJECTED"}:
                raise AuthorityError("feedback proposal is not pending")
            revision = int(row[5]) + 1
            accepted_id = assessment_id + ":accepted"
            prior = db.execute(
                "SELECT assessment_id FROM outcome_assessments "
                "WHERE supersedes_assessment_id=? AND status='ACCEPTED'",
                (assessment_id,),
            ).fetchone()
            if prior is not None:
                accepted_id = str(prior[0])
            else:
                source = db.execute(
                    "SELECT exposure_id,relevant,evidence_json,source_json FROM "
                    "outcome_assessments WHERE assessment_id=?",
                    (assessment_id,),
                ).fetchone()
                if source is None:
                    raise AuthorityError("feedback proposal disappeared")
                db.execute(
                    "INSERT INTO outcome_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        accepted_id,
                        self.instance_id,
                        str(row[0]),
                        str(row[1]),
                        str(row[2]),
                        str(row[3]),
                        int(row[4]),
                        source[0],
                        int(source[1]),
                        source[2],
                        source[3],
                        "ACCEPTED",
                        revision,
                        assessment_id,
                        _utc(),
                    ),
                )
            record = FeedbackRecord(
                accepted_id,
                str(row[0]),
                str(row[1]),
                str(row[2]),
                int(row[4]),
                "ACCEPTED",
                revision,
            )
        from .recovery import rebuild_learner

        rebuild_learner(self.store, reason=f"feedback:{assessment_id}")
        return record

__all__ = [
    "AuthorityError",
    "FeedbackRecord",
    "FeedbackService",
    "IdentityReviewService",
    "QuarantineRecord",
    "QuarantineService",
]
