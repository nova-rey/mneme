"""Read-only replay and quarantine-aware learner verification.

The accepted observation and assessment ledgers are authoritative.  This
module deliberately does not call a host and does not mutate a lineage while
replaying them.  It provides the inspection/rebuild input needed by the
Phase Two authority boundary; callers that publish a rebuilt materialized tip
must do so through their normal serialized writer.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from ..state.storage import SQLiteStore, _utc
from .learner import (
    ConsequenceAssessment,
    CreditWindow,
    EdgeState,
    LearnerState,
    Observation,
    TransitionInput,
    apply_transition,
)


class ReplayError(RuntimeError):
    """The durable developmental ledger cannot be replayed safely."""


@dataclass(frozen=True)
class ReplayReport:
    """A deterministic, machine-readable replay result."""

    state: LearnerState
    operation_count: int
    skipped_operation_ids: tuple[str, ...]
    active_quarantine: tuple[dict[str, str], ...]

    @property
    def digest(self) -> str:
        return _state_digest(self.state)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "state_digest": self.digest,
            "operation_count": self.operation_count,
            "skipped_operation_ids": list(self.skipped_operation_ids),
            "active_quarantine": [dict(item) for item in self.active_quarantine],
        }


def _state_digest(state: LearnerState) -> str:
    import hashlib

    payload = {
        "edge_states": [item.to_dict() for item in state.edge_states],
        "route_states": [item.to_dict() for item in state.route_states],
        "global_opportunity": state.global_opportunity,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _digest(value: Any) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _active_quarantine(store: SQLiteStore, instance_id: str) -> tuple[dict[str, str], ...]:
    rows = store.connection.execute(
        "SELECT target_kind,target_id,reason,authority_revision FROM quarantine_events "
        "WHERE instance_id=? AND authority_revision IN ("
        "SELECT MAX(authority_revision) FROM quarantine_events "
        "WHERE instance_id=? GROUP BY target_kind,target_id) AND action='ADD' "
        "ORDER BY target_kind,target_id",
        (instance_id, instance_id),
    )
    return tuple(
        {
            "target_kind": str(row[0]),
            "target_id": str(row[1]),
            "reason": str(row[2]),
            "authority_revision": str(row[3]),
        }
        for row in rows
    )


def _operation_quarantined(
    store: SQLiteStore,
    instance_id: str,
    operation_id: str,
    edge_keys: set[str],
    route_keys: set[str],
) -> bool:
    active = _active_quarantine(store, instance_id)
    if any(item["target_kind"] == "lineage" for item in active):
        return True
    if edge_keys.intersection(
        item["target_id"] for item in active if item["target_kind"] in {"edge", "concept"}
    ):
        return True
    if any(
        item["target_kind"] == "route" and item["target_id"] in route_keys
        for item in active
    ):
        return True
    interpretation = store.connection.execute(
        "SELECT i.interpretation_id FROM interpretations i "
        "JOIN interpretation_operations o ON o.operation_id=i.operation_id "
        "WHERE o.episode_id=(SELECT episode_id FROM development_operations "
        "WHERE operation_id=?)",
        (operation_id,),
    ).fetchone()
    if interpretation is not None and any(
        item["target_kind"] == "interpretation" and item["target_id"] == str(interpretation[0])
        for item in active
    ):
        return True
    source_ids = {
        str(row[0])
        for row in store.connection.execute(
            "SELECT source_id FROM sources WHERE operation_id=?", (operation_id,)
        )
    }
    return bool(
        source_ids.intersection(
            item["target_id"] for item in active if item["target_kind"] == "source"
        )
    )


def _lineage_history(store: SQLiteStore, instance_id: str) -> tuple[str, ...]:
    """Return the inherited lineage chain from oldest ancestor to active child.

    Forks copy the immutable parent ledger into the child database, while
    child-local operations are recorded under the child lineage.  Replay must
    therefore select the complete ancestry explicitly; filtering only on the
    active child silently drops the state from which the fork was created.
    """

    chain: list[str] = []
    current: str | None = instance_id
    seen: set[str] = set()
    while current is not None:
        if current in seen:
            raise ReplayError("lineage ancestry contains a cycle")
        seen.add(current)
        row = store.connection.execute(
            "SELECT parent_instance_id FROM lineages WHERE instance_id=?", (current,)
        ).fetchone()
        if row is None:
            raise ReplayError(f"lineage ancestry is missing {current}")
        chain.append(current)
        current = str(row[0]) if row[0] is not None else None
    chain.reverse()
    return tuple(chain)


def _observations(store: SQLiteStore, operation_id: str) -> tuple[Observation, ...]:
    operation = store.connection.execute(
        "SELECT opportunity FROM development_operations WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    if operation is None:
        raise ReplayError(f"development operation is missing: {operation_id}")
    fallback_group = f"compat:{int(operation[0])}"
    rows = store.connection.execute(
        "SELECT d.observation_id,COALESCE(b.canonical_key,d.edge_key),d.context,"
        "d.source_role,d.status,d.dependence,d.dependence_group,d.covered,d.actual_exposure "
        ",d.evidence_json FROM development_observations d LEFT JOIN semantic_bindings b "
        "ON b.binding_id=d.binding_id WHERE d.operation_id=? ORDER BY d.observation_id",
        (operation_id,),
    )
    observations: list[Observation] = []
    for row in rows:
        evidence: dict[str, Any] = {}
        try:
            decoded = json.loads(str(row[9]))
            if isinstance(decoded, dict):
                evidence = decoded
        except json.JSONDecodeError:
            pass
        provenance = evidence.get("provenance_group_keys", ())
        if not isinstance(provenance, (list, tuple)):
            provenance = ()
        occurrence = evidence.get("occurrence_key")
        occurrence_key = str(occurrence) if occurrence else fallback_group
        group = evidence.get("group_key") or evidence.get("effective_group_key")
        group_key = str(group) if group else (occurrence_key or fallback_group)
        observations.append(
            Observation(
                target_key=str(row[1]),
                context=str(row[2]),
                source_role=str(row[3]),
                status=str(row[4]),
                dependence=str(row[5]),
                relation_support=(
                    str(evidence["relation_support"])
                    if evidence.get("relation_support")
                    else None
                ),
                expression_status=(
                    str(evidence["expression_status"])
                    if evidence.get("expression_status")
                    else None
                ),
                semantic_schema_version=(
                    str(evidence["semantic_schema_version"])
                    if evidence.get("semantic_schema_version")
                    else None
                ),
                group_key=str(row[6]) if row[6] is not None else group_key,
                provenance_group_keys=tuple(str(item) for item in provenance),
                occurrence_key=occurrence_key,
                covered=bool(row[7]),
                relevant=bool(evidence.get("relevant", True)),
                actual_exposure=bool(row[8]),
                eligible=bool(evidence.get("eligible", True)),
                observation_id=str(row[0]),
            )
        )
    return tuple(observations)


def _consequences(store: SQLiteStore, operation_id: str) -> tuple[ConsequenceAssessment, ...]:
    rows = store.connection.execute(
        "SELECT assessment_id,target_route_id,context,outcome,direction,exposure_id,relevant,"
        "evidence_json FROM outcome_assessments WHERE operation_id=? AND status='ACCEPTED' "
        "ORDER BY assessment_id",
        (operation_id,),
    )
    result: list[ConsequenceAssessment] = []
    for row in rows:
        payload: dict[str, Any] = {}
        try:
            decoded = json.loads(str(row[7]))
            if isinstance(decoded, dict) and isinstance(decoded.get("assessment"), dict):
                payload = decoded["assessment"]
        except json.JSONDecodeError:
            payload = {}
        outcome = str(row[3])
        direction = int(row[4])
        if outcome not in {"known", "unknown"}:
            raise ReplayError(f"invalid durable outcome: {outcome}")
        if direction not in {-1, 1}:
            raise ReplayError(f"invalid durable direction: {direction}")
        result.append(
            ConsequenceAssessment(
                operation_id=str(row[0]),
                route_key=str(row[1]),
                context=str(row[2]),
                outcome=cast(Literal["known", "unknown"], outcome),
                direction=cast(Literal[-1, 1], direction),
                exposure_id=str(row[5]) if row[5] is not None else None,
                relevant=bool(row[6]),
                opportunity=(
                    int(payload["opportunity"])
                    if payload.get("opportunity") is not None
                    else None
                ),
            )
        )
    return tuple(result)


def _modeled_targets(store: SQLiteStore, operation_id: str) -> tuple[tuple[str, str], ...]:
    row = store.connection.execute(
        "SELECT target_json FROM modeled_advance_operations WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    if row is None:
        raise ReplayError(f"modeled advance operation is missing: {operation_id}")
    try:
        payload = json.loads(str(row[0]))
    except json.JSONDecodeError as exc:
        raise ReplayError(f"modeled advance targets are invalid: {operation_id}") from exc
    if not isinstance(payload, list):
        raise ReplayError(f"modeled advance targets are not a list: {operation_id}")
    targets: list[tuple[str, str]] = []
    for item in payload:
        if not isinstance(item, list) or len(item) != 2:
            raise ReplayError(f"modeled advance target is invalid: {operation_id}")
        target, context = str(item[0]), str(item[1])
        if not target or not context:
            raise ReplayError(f"modeled advance target is empty: {operation_id}")
        targets.append((target, context))
    return tuple(targets)


def replay_learner(
    store: SQLiteStore, *, include_quarantined: bool = False
) -> ReplayReport:
    """Replay accepted developmental observations without writing the store."""

    current = store.current()
    instance_id = str(current["active_instance_id"])
    active = _active_quarantine(store, instance_id)
    state = LearnerState.empty()
    skipped: list[str] = []
    lineage_ids = _lineage_history(store, instance_id)
    placeholders = ",".join("?" for _ in lineage_ids)
    operations = store.connection.execute(
        "SELECT operation_id,opportunity,terminal_disposition,'development' AS kind "
        "FROM development_operations "
        f"WHERE instance_id IN ({placeholders}) AND stage='ACCEPTED' "
        "UNION ALL "
        "SELECT operation_id,opportunity,'accepted' AS terminal_disposition,'modeled' AS kind "
        "FROM modeled_advance_operations "
        f"WHERE instance_id IN ({placeholders}) "
        "ORDER BY opportunity,operation_id",
        (*lineage_ids, *lineage_ids),
    )
    count = 0
    for row in operations:
        operation_id = str(row[0])
        kind = str(row[3])
        if kind == "modeled":
            steps_row = store.connection.execute(
                "SELECT steps FROM modeled_advance_operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if steps_row is None:
                raise ReplayError(f"modeled advance operation is missing: {operation_id}")
            try:
                steps = int(steps_row[0])
            except (TypeError, ValueError) as exc:
                raise ReplayError(f"modeled advance steps are invalid: {operation_id}") from exc
            observations: tuple[Observation, ...] = ()
            edge_keys: set[str] = set()
            consequences: tuple[ConsequenceAssessment, ...] = ()
        else:
            steps = 0
            observations = _observations(store, operation_id)
            edge_keys = {item.target_key for item in observations}
            consequences = _consequences(store, operation_id)
        route_keys = {item.route_key for item in consequences}
        if not include_quarantined and _operation_quarantined(
            store, instance_id, operation_id, edge_keys, route_keys
        ):
            skipped.append(operation_id)
            continue
        try:
            result = apply_transition(
                state,
                TransitionInput(
                    operation_id,
                    observations=observations,
                    terminal_disposition=str(row[2] or "accepted"),
                    consequences=consequences,
                    modeled_advance_ticks=steps,
                    advance_targets=(
                        _modeled_targets(store, operation_id) if kind == "modeled" else ()
                    ),
                ),
            )
        except Exception as exc:  # convert corrupt durable rows to one boundary error
            raise ReplayError(f"cannot replay developmental operation {operation_id}") from exc
        state = result.state
        count += 1
    return ReplayReport(state, count, tuple(skipped), active)


def verify_replay(store: SQLiteStore) -> dict[str, Any]:
    """Compare ledger replay with the current materialized learner snapshot."""

    report = replay_learner(store)
    row = store.connection.execute(
        "SELECT configuration_json,content_digest FROM learner_snapshots "
        "WHERE instance_id=? ORDER BY opportunity DESC,rowid DESC LIMIT 1",
        (str(store.current()["active_instance_id"]),),
    ).fetchone()
    materialized_digest: str | None = None
    if row is not None:
        try:
            payload = json.loads(str(row[0]))
            state = payload.get("state", {}) if isinstance(payload, dict) else {}
            materialized_digest = _state_digest_from_snapshot(state)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ReplayError("latest learner snapshot is malformed") from exc
    return {
        **report.to_dict(),
        "materialized_state_digest": materialized_digest,
        "matches_materialized": (
            materialized_digest is not None and materialized_digest == report.digest
        ),
        "rebuild_required": bool(report.skipped_operation_ids),
    }


def rebuild_learner(
    store: SQLiteStore,
    *,
    reason: str,
    modeled_advance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a quarantine-aware learner materialization from the ledger.

    The accepted operation/observation ledger remains immutable.  A rebuild
    appends a new manifest and snapshot and appends latest-value rows for every
    previously materialized edge, including zero tombstones for edges removed
    by quarantine.  This keeps readers that consume ``learner_values`` from
    accidentally retaining a revoked value while preserving the old snapshot
    for audit.
    """

    if not reason:
        raise ReplayError("rebuild reason is required")
    if bool(getattr(store, "read_only", False)):
        raise ReplayError("learner rebuild requires a writable working store")
    current = store.current()
    instance_id = str(current["active_instance_id"])
    with store.transaction() as db:
        latest = db.execute(
            "SELECT * FROM current_state WHERE active_instance_id=?", (instance_id,)
        ).fetchone()
        if latest is None or str(latest["current_manifest_id"]) != str(
            current["current_manifest_id"]
        ):
            raise ReplayError("learner rebuild base became stale")
        base = db.execute(
            "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
        ).fetchone()
        if base is None:
            raise ReplayError("current manifest is missing")
        if modeled_advance is not None:
            operation_id = str(modeled_advance.get("operation_id", ""))
            advance_instance = str(modeled_advance.get("instance_id", ""))
            context = str(modeled_advance.get("context", ""))
            steps = int(modeled_advance.get("steps", 0))
            targets = modeled_advance.get("targets", ())
            if (
                not operation_id
                or advance_instance != instance_id
                or str(modeled_advance.get("base_manifest_id", ""))
                != str(base["manifest_id"])
                or not context
                or steps <= 0
                or not isinstance(targets, (tuple, list))
            ):
                raise ReplayError("invalid modeled advance operation")
            target_rows = [[str(item[0]), str(item[1])] for item in targets]
            db.execute(
                "INSERT INTO modeled_advance_operations VALUES(?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    instance_id,
                    str(base["manifest_id"]),
                    context,
                    steps,
                    json.dumps(target_rows, ensure_ascii=False, separators=(",", ":")),
                    int(base["opportunity"] or 0) + 1,
                    _utc(),
                ),
            )
        # Include a newly inserted modeled operation in the same transaction as
        # its materialized manifest.  A crash before commit therefore leaves
        # neither half of the accepted transition visible.
        report = replay_learner(store)
        materialized_opportunity = (
            report.state.global_opportunity
            if modeled_advance is not None
            else int(base["opportunity"] or 0)
        )
        now = _utc()
        revision = int(current["current_revision"]) + 1
        event_id = (
            f"modeled-advance:{modeled_advance['operation_id']}"
            if modeled_advance is not None
            else f"learner-rebuild:{uuid.uuid4()}"
        )
        manifest_id = str(uuid.uuid4())
        authority_revision = int(base["authority_revision"] or 0)
        active = _active_quarantine(store, instance_id)
        if active:
            authority_revision = max(
                authority_revision,
                max(int(item["authority_revision"]) for item in active),
            )
        state_payload = {
            "global_opportunity": report.state.global_opportunity,
            "edges": {
                f"{item.target_key}:{item.context}": item.to_dict()
                for item in report.state.edge_states
            },
            "routes": {
                f"{item.route_key}:{item.context}": item.to_dict()
                for item in report.state.route_states
            },
        }
        config = {"version": "learner-v1", "rebuild_reason": reason}
        snapshot_id = str(uuid.uuid4())
        snapshot_content = {"configuration": config, "state": state_payload}
        snapshot_digest = _digest(snapshot_content)
        integrity = _digest(
            {"instance_id": instance_id, "revision": revision, "event": event_id, "reason": reason}
        )
        db.execute(
            "INSERT INTO manifests(manifest_id,instance_id,revision,parent_manifest_id,"
            "inherited_base_manifest_id,policy_id,self_ref_id,format_version,controller_version,"
            "integrity_digest,accepted_history_digest,graph_snapshot_id,graph_revision,"
            "accepted_episode_count,self_view_id,self_view_version,learner_snapshot_id,"
            "learner_configuration_digest,binding_version,opportunity,coverage_json,"
            "authority_revision) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                manifest_id,
                instance_id,
                revision,
                base["manifest_id"],
                base["inherited_base_manifest_id"],
                base["policy_id"],
                base["self_ref_id"],
                base["format_version"],
                "mneme-p2.2",
                integrity,
                base["accepted_history_digest"],
                base["graph_snapshot_id"],
                base["graph_revision"],
                base["accepted_episode_count"],
                base["self_view_id"],
                base["self_view_version"],
                snapshot_id,
                snapshot_digest,
                base["binding_version"],
                materialized_opportunity,
                base["coverage_json"],
                authority_revision,
            ),
        )
        db.execute(
            "INSERT INTO learner_snapshots VALUES(?,?,?,?,?,?,?,?)",
            (
                snapshot_id,
                instance_id,
                manifest_id,
                materialized_opportunity,
                "learner-v1",
                json.dumps(
                    snapshot_content,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                snapshot_digest,
                now,
            ),
        )
        db.execute(
            "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
            (
                instance_id,
                revision,
                current["current_revision"],
                event_id,
                "modeled_advance" if modeled_advance is not None else "learner_rebuilt",
                None,
                manifest_id,
                now,
            ),
        )
        # Readers use the latest learner_values row for each edge.  Append
        # tombstones for old keys and values for the rebuilt state, retaining
        # every prior row for audit.  A prior accepted development operation
        # supplies the required foreign-key owner for these materialized rows.
        lineage_ids = _lineage_history(store, instance_id)
        placeholders = ",".join("?" for _ in lineage_ids)
        owner = db.execute(
            "SELECT operation_id FROM development_operations "
            f"WHERE instance_id IN ({placeholders}) "
            "ORDER BY opportunity DESC,operation_id DESC LIMIT 1",
            lineage_ids,
        ).fetchone()
        old_keys = {
            (str(row[0]), str(row[1]))
            for row in db.execute(
                "SELECT edge_key,context FROM learner_values WHERE instance_id=?", (instance_id,)
            )
        }
        new_edges = {(item.target_key, item.context): item for item in report.state.edge_states}
        if owner is not None:
            operation_id = str(owner[0])
            opportunity = max(1, materialized_opportunity)
            for key in sorted(old_keys | set(new_edges)):
                edge = new_edges.get(key, EdgeState(key[0], key[1]))
                update_id = str(uuid.uuid4())
                db.execute(
                    "INSERT INTO learner_updates VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        update_id,
                        operation_id,
                        f"authority-rebuild:{revision}:{key[0]}:{key[1]}",
                        opportunity,
                        key[0],
                        key[1],
                        0,
                        "authority_rebuild",
                        json.dumps(edge.to_dict(), sort_keys=True),
                        json.dumps(edge.to_dict(), sort_keys=True),
                        now,
                    ),
                )
                db.execute(
                    "INSERT INTO learner_values VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()), instance_id, update_id, key[0], key[1],
                        edge.accessibility, edge.support, edge.consequence,
                        sum(amount for _group, amount in edge.lifetime_by_group),
                        sum(amount for _group, amount in edge.induced_by_group),
                        sum(item.amount for item in edge.rolling_credits),
                        edge.last_consolidation_opportunity, edge.inactivity_ticks,
                        opportunity, _digest(edge.to_dict()), now,
                    ),
                )
        db.execute(
            "UPDATE current_state SET current_revision=?,current_manifest_id=? WHERE singleton=1",
            (revision, manifest_id),
        )
    return {
        "instance_id": instance_id,
        "revision": revision,
        "manifest_id": manifest_id,
        "snapshot_id": snapshot_id,
        "reason": reason,
        "state_digest": report.digest,
        "state_opportunity": report.state.global_opportunity,
        "skipped_operation_ids": list(report.skipped_operation_ids),
    }


def _state_digest_from_snapshot(value: Any) -> str:
    if not isinstance(value, dict):
        raise ReplayError("learner snapshot state is not an object")
    from .learner import EdgeState, RouteState

    edge_rows: list[EdgeState] = []
    for key, item in sorted(dict(value.get("edges", {})).items()):
        if not isinstance(item, dict):
            continue
        edge_rows.append(
            EdgeState(
                target_key=str(item.get("target_key", key.split(":", 1)[0])),
                context=str(item.get("context", key.split(":", 1)[-1])),
                accessibility=int(item.get("accessibility", 0)),
                support=int(item.get("support", 0)),
                consequence=int(item.get("consequence", 0)),
                relevant_opportunities=int(item.get("relevant_opportunities", 0)),
                inactivity_ticks=int(item.get("inactivity_ticks", 0)),
                unsupported_streak=int(item.get("unsupported_streak", 0)),
                lifetime_by_group=tuple(
                    sorted(
                        (str(group), int(amount))
                        for group, amount in dict(
                            item.get("lifetime_by_group", {})
                        ).items()
                    )
                ),
                induced_by_group=tuple(
                    sorted(
                        (str(group), int(amount))
                        for group, amount in dict(
                            item.get("induced_by_group", {})
                        ).items()
                    )
                ),
                rolling_credits=tuple(
                    CreditWindow(int(entry["opportunity"]), int(entry["amount"]))
                    for entry in item.get("rolling_credits", [])
                ),
                last_consolidation_opportunity=(
                    int(item["last_consolidation_opportunity"])
                    if item.get("last_consolidation_opportunity") is not None
                    else None
                ),
                raw_occurrence_count=int(item.get("raw_occurrence_count", 0)),
            )
        )
    edges = tuple(edge_rows)
    routes = tuple(
        RouteState(
            route_key=str(item.get("route_key", key.split(":", 1)[0])),
            context=str(item.get("context", key.split(":", 1)[-1])),
            consequence=int(item.get("consequence", 0)),
            by_exposure=tuple(
                sorted(
                    (str(k), int(v))
                    for k, v in dict(item.get("by_exposure", {})).items()
                )
            ),
            rolling_consequences=tuple(
                CreditWindow(int(x["opportunity"]), int(x["amount"]))
                for x in item.get("rolling_consequences", [])
            ),
            applied_assessments=tuple(str(x) for x in item.get("applied_assessments", [])),
        )
        for key, item in sorted(dict(value.get("routes", {})).items())
        if isinstance(item, dict)
    )
    return _state_digest(
        LearnerState(
            edge_states=edges,
            route_states=routes,
            global_opportunity=int(value.get("global_opportunity", 0)),
        )
    )


__all__ = ["ReplayError", "ReplayReport", "rebuild_learner", "replay_learner", "verify_replay"]
