"""Durable, explicit modeled temporal advances.

Modeled advances are learner operations without a conversation episode.  They
are recorded in their own immutable ledger and published together with the
materialized learner snapshot, so a retry cannot create a second transition or
an artificial developmental episode.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from ..state.policy import PolicyError, PolicyService
from ..state.storage import SQLiteStore
from .recovery import ReplayError, rebuild_learner, replay_learner, verify_replay


class ModeledAdvanceError(RuntimeError):
    """A modeled advance cannot be accepted safely."""


@dataclass(frozen=True)
class ModeledAdvanceRecord:
    operation_id: str
    instance_id: str
    base_manifest_id: str
    context: str
    steps: int
    targets: tuple[tuple[str, str], ...]
    opportunity: int
    revision: int
    manifest_id: str
    accepted_episode_count: int
    graph_revision: int
    status: str = "ACCEPTED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "instance_id": self.instance_id,
            "base_manifest_id": self.base_manifest_id,
            "context": self.context,
            "steps": self.steps,
            "targets": [list(item) for item in self.targets],
            "opportunity": self.opportunity,
            "revision": self.revision,
            "manifest_id": self.manifest_id,
            "accepted_episode_count": self.accepted_episode_count,
            "graph_revision": self.graph_revision,
            "status": self.status,
        }


class ModeledAdvanceService:
    """Authorize, persist, and replay one explicit modeled time transition."""

    def __init__(self, store: SQLiteStore, instance_id: str | None = None) -> None:
        self.store = store
        self.instance_id = instance_id or str(store.current()["active_instance_id"])

    def _require_learning(self) -> None:
        try:
            PolicyService(self.store, self.instance_id).require("learn")
        except PolicyError as exc:
            raise ModeledAdvanceError(str(exc)) from exc

    def _existing(self, operation_id: str) -> ModeledAdvanceRecord | None:
        row = self.store.connection.execute(
            "SELECT operation_id,instance_id,base_manifest_id,context,steps,target_json,"
            "opportunity FROM modeled_advance_operations WHERE operation_id=? AND instance_id=?",
            (operation_id, self.instance_id),
        ).fetchone()
        if row is None:
            return None
        targets = _decode_targets(str(row[5]))
        manifest = self.store.connection.execute(
            "SELECT m.revision,m.manifest_id,m.accepted_episode_count,m.graph_revision "
            "FROM manifests m JOIN revisions r ON r.manifest_id=m.manifest_id "
            "WHERE r.event_id=?",
            (f"modeled-advance:{operation_id}",),
        ).fetchone()
        if manifest is None:
            raise ModeledAdvanceError("modeled advance materialization is missing")
        return ModeledAdvanceRecord(
            str(row[0]), str(row[1]), str(row[2]), str(row[3]), int(row[4]), targets,
            int(row[6]) + int(row[4]) - 1, int(manifest[0]), str(manifest[1]),
            int(manifest[2]), int(manifest[3]),
        )

    def advance(
        self,
        context: str,
        steps: int,
        *,
        operation_id: str | None = None,
    ) -> ModeledAdvanceRecord:
        if not context.strip():
            raise ModeledAdvanceError("advance context is required")
        if steps <= 0:
            raise ModeledAdvanceError("advance steps must be positive")
        if bool(getattr(self.store, "read_only", False)):
            raise ModeledAdvanceError("modeled advance requires a writable working store")
        self._require_learning()
        current = self.store.current()
        base_manifest_id = str(current["current_manifest_id"])
        operation_id = operation_id or str(uuid.uuid4())
        existing = self._existing(operation_id)
        if existing is not None:
            if existing.context != context or existing.steps != steps:
                raise ModeledAdvanceError("modeled advance idempotency conflict")
            return existing

        # The target set is bound before publication.  New associations that
        # appear later do not receive retroactive aging from this operation.
        try:
            state = replay_learner(self.store).state
        except ReplayError as exc:
            raise ModeledAdvanceError(str(exc)) from exc
        targets = tuple(
            sorted(
                (item.target_key, item.context)
                for item in state.edge_states
                if item.context == context
            )
        )
        if not targets:
            raise ModeledAdvanceError("no learner targets match the advance context")
        try:
            replay_check = verify_replay(self.store)
        except ReplayError as exc:
            raise ModeledAdvanceError(str(exc)) from exc
        if not replay_check["matches_materialized"]:
            raise ModeledAdvanceError("learner materialization does not match replay")
        try:
            result = rebuild_learner(
                self.store,
                reason=f"modeled advance:{operation_id}",
                modeled_advance={
                    "operation_id": operation_id,
                    "instance_id": self.instance_id,
                    "base_manifest_id": base_manifest_id,
                    "context": context,
                    "steps": steps,
                    "targets": targets,
                },
            )
        except (ReplayError, ValueError, TypeError) as exc:
            raise ModeledAdvanceError(str(exc)) from exc
        manifest = self.store.connection.execute(
            "SELECT accepted_episode_count,graph_revision FROM manifests WHERE manifest_id=?",
            (str(result["manifest_id"]),),
        ).fetchone()
        if manifest is None:
            raise ModeledAdvanceError("modeled advance materialization is missing")
        return ModeledAdvanceRecord(
            operation_id,
            self.instance_id,
            base_manifest_id,
            context,
            steps,
            targets,
            int(result["state_opportunity"]),
            int(result["revision"]),
            str(result["manifest_id"]),
            int(manifest[0]),
            int(manifest[1]),
        )


def _decode_targets(encoded: str) -> tuple[tuple[str, str], ...]:
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise ModeledAdvanceError("modeled advance targets are invalid") from exc
    if not isinstance(payload, list):
        raise ModeledAdvanceError("modeled advance targets are not a list")
    result: list[tuple[str, str]] = []
    for item in payload:
        if not isinstance(item, list) or len(item) != 2:
            raise ModeledAdvanceError("modeled advance target is invalid")
        result.append((str(item[0]), str(item[1])))
    return tuple(result)


__all__ = ["ModeledAdvanceError", "ModeledAdvanceRecord", "ModeledAdvanceService"]
