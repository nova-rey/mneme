"""Transactional publication of validated Phase One interpretations.

This module is deliberately a persistence boundary, not a retrieval or
controller.  A validated residue is recorded together with its source
evidence and then published as a complete immutable graph snapshot.  The
model is never called here; retrying a validation/publication operation is
therefore safe and idempotent.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from ..development import (
    ConsequenceAssessment,
    ConsequenceResult,
    DevelopmentalLearner,
    EdgeState,
    LearnerState,
    Observation,
    RouteState,
    apply_consequence,
)
from ..development.learner import CreditWindow
from ..state.storage import SQLiteStore, _utc
from .graph import GraphConcept, GraphEdge, GraphRoute, discover_routes, materialize_graph
from .residue import Residue, ResidueValidationError, validate_residue
from .resolution import ResolutionDecision, normalize_lookup_label


class PublicationError(RuntimeError):
    """A residue cannot be published against the current accepted state."""


class StalePublication(PublicationError):
    """The interpretation was prepared against an obsolete manifest."""


def _stable_concept_key(label: str, kind: str, context: Any = ()) -> str:
    """Build a content identity for a resolved semantic concept.

    Local extractor keys are deliberately excluded.  This is used only for
    the Phase Two binding ledger; Phase One graph row keys remain unchanged.
    """

    return "concept:" + _digest(
        {
            "label": normalize_lookup_label(label),
            "kind": kind,
            "context": context,
        }
    )


def _stable_edge_key(
    source_key: str, target_key: str, relationship: str, polarity: str, context: Any = ()
) -> str:
    return "edge:" + _digest(
        {
            "source": source_key,
            "target": target_key,
            "relationship": relationship,
            "polarity": polarity,
            "context": context,
        }
    )


def _observation_target(observation: Observation) -> str:
    target = observation.edge_key or observation.target_key
    if not target:
        raise PublicationError("development observation has no target key")
    return str(target)


def _edge_state_from_json(value: Mapping[str, Any]) -> EdgeState:
    """Restore the complete learner state retained in an update payload."""

    return EdgeState(
        target_key=str(value.get("target_key", value.get("edge_key", "legacy"))),
        context=str(value.get("context", "general")),
        accessibility=int(value.get("accessibility", 0)),
        support=int(value.get("support", 0)),
        consequence=int(value.get("consequence", 0)),
        relevant_opportunities=int(value.get("relevant_opportunities", 0)),
        inactivity_ticks=int(value.get("inactivity_ticks", 0)),
        unsupported_streak=int(value.get("unsupported_streak", 0)),
        lifetime_by_group=tuple(
            (str(key), int(amount))
            for key, amount in sorted(dict(value.get("lifetime_by_group", {})).items())
        ),
        induced_by_group=tuple(
            (str(key), int(amount))
            for key, amount in sorted(dict(value.get("induced_by_group", {})).items())
        ),
        rolling_credits=tuple(
            CreditWindow(int(item["opportunity"]), int(item["amount"]))
            for item in value.get("rolling_credits", [])
        ),
        last_consolidation_opportunity=(
            int(value["last_consolidation_opportunity"])
            if value.get("last_consolidation_opportunity") is not None
            else None
        ),
        raw_occurrence_count=int(value.get("raw_occurrence_count", 0)),
    )


def _route_state_from_json(value: Mapping[str, Any]) -> RouteState:
    """Restore one contextual route state from a learner snapshot payload."""

    by_exposure = tuple(
        (str(key), int(amount))
        for key, amount in sorted(dict(value.get("by_exposure", {})).items())
    )
    rolling = tuple(
        CreditWindow(int(item["opportunity"]), int(item["amount"]))
        for item in value.get("rolling_consequences", [])
    )
    return RouteState(
        route_key=str(value["route_key"]),
        context=str(value.get("context", "general")),
        consequence=int(value.get("consequence", 0)),
        by_exposure=by_exposure,
        rolling_consequences=rolling,
        applied_assessments=tuple(str(item) for item in value.get("applied_assessments", [])),
    )


@dataclass(frozen=True)
class PublicationReceipt:
    operation_id: str
    interpretation_id: str
    status: str
    lineage_revision: int
    graph_revision: int
    manifest_id: str
    snapshot_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "interpretation_id": self.interpretation_id,
            "status": self.status,
            "lineage_revision": self.lineage_revision,
            "graph_revision": self.graph_revision,
            "manifest_id": self.manifest_id,
            "snapshot_id": self.snapshot_id,
        }


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _json(value: Any) -> str:
    def convert(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(key): convert(val) for key, val in item.items()}
        if isinstance(item, (tuple, list)):
            return [convert(entry) for entry in item]
        return item

    return json.dumps(convert(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _source_bundle(db: Any, episode_id: str) -> dict[str, Any]:
    """Capture the immutable source bundle offered to an extractor."""

    operation = db.execute(
        "SELECT operation_id FROM episodes WHERE episode_id=?", (episode_id,)
    ).fetchone()
    if operation is None:
        raise PublicationError("interpretation episode is missing")
    rows = db.execute(
        "SELECT s.source_id,s.ordinal,s.role,s.supplier,s.content,s.content_digest,"
        "b.purpose,b.independent_evidence "
        "FROM sources s JOIN source_bindings b ON b.source_id=s.source_id "
        "WHERE s.operation_id=? ORDER BY s.ordinal,s.source_id",
        (operation[0],),
    ).fetchall()
    return {
        "episode_id": episode_id,
        "sources": [
            {
                "slot": f"s{index}",
                "source_id": str(row[0]),
                "ordinal": int(row[1]),
                "role": str(row[2]),
                "supplier": str(row[3]),
                "content": str(row[4]),
                "content_digest": str(row[5]),
                "purpose": str(row[6]),
                "independent_evidence": bool(row[7]),
            }
            for index, row in enumerate(rows)
        ],
    }


def _copy_graph(db: Any, source_snapshot: str, destination_snapshot: str) -> None:
    for row in db.execute(
        "SELECT concept_key,label,normalized_label,kind,confidence,salience,candidate_id "
        "FROM graph_concepts WHERE snapshot_id=? ORDER BY concept_key",
        (source_snapshot,),
    ):
        db.execute(
            "INSERT INTO graph_concepts VALUES(?,?,?,?,?,?,?,?)",
            (destination_snapshot, *tuple(row)),
        )
    for row in db.execute(
        "SELECT edge_key,source_key,target_key,relationship,polarity,context_json,evidence_json "
        "FROM graph_edges WHERE snapshot_id=? ORDER BY edge_key",
        (source_snapshot,),
    ):
        db.execute(
            "INSERT INTO graph_edges VALUES(?,?,?,?,?,?,?,?)", (destination_snapshot, *tuple(row))
        )
    for row in db.execute(
        "SELECT route_key,edge_keys_json,source_json FROM graph_routes "
        "WHERE snapshot_id=? ORDER BY route_key",
        (source_snapshot,),
    ):
        db.execute("INSERT INTO graph_routes VALUES(?,?,?,?)", (destination_snapshot, *tuple(row)))


def _snapshot_digest(db: Any, snapshot_id: str) -> str:
    concepts = [
        tuple(row)
        for row in db.execute(
            "SELECT concept_key,label,normalized_label,kind,confidence,salience "
            "FROM graph_concepts WHERE snapshot_id=? ORDER BY concept_key",
            (snapshot_id,),
        )
    ]
    edges = [
        tuple(row)
        for row in db.execute(
            "SELECT edge_key,source_key,target_key,relationship,polarity,context_json,"
            "evidence_json "
            "FROM graph_edges WHERE snapshot_id=? ORDER BY edge_key",
            (snapshot_id,),
        )
    ]
    routes = [
        tuple(row)
        for row in db.execute(
            "SELECT route_key,edge_keys_json,source_json FROM graph_routes "
            "WHERE snapshot_id=? ORDER BY route_key",
            (snapshot_id,),
        )
    ]
    return _digest({"concepts": concepts, "edges": edges, "routes": routes})


def _discover_snapshot_routes(db: Any, snapshot_id: str) -> None:
    """Persist deterministic paths derived from the complete graph snapshot."""

    concepts = tuple(
        GraphConcept(
            str(row[0]),
            str(row[1]),
            str(row[3]),
            annotations={"confidence": float(row[4]), "salience": float(row[5])},
        )
        for row in db.execute(
            "SELECT concept_key,label,normalized_label,kind,confidence,salience "
            "FROM graph_concepts WHERE snapshot_id=? ORDER BY concept_key",
            (snapshot_id,),
        )
    )
    edges = tuple(
        GraphEdge(
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3]),
            tuple(json.loads(str(row[6]))),
            json.loads(str(row[5])),
        )
        for row in db.execute(
            "SELECT edge_key,source_key,target_key,relationship,polarity,context_json,"
            "evidence_json FROM graph_edges WHERE snapshot_id=? ORDER BY edge_key",
            (snapshot_id,),
        )
    )
    existing = tuple(
        GraphRoute(
            str(row[0]),
            tuple(json.loads(str(row[1]))),
            tuple(json.loads(str(row[2]))),
        )
        for row in db.execute(
            "SELECT route_key,edge_keys_json,source_json FROM graph_routes "
            "WHERE snapshot_id=? ORDER BY route_key",
            (snapshot_id,),
        )
    )
    known_keys = {route.key for route in existing}
    for route in discover_routes(concepts, edges, existing):
        if route.key in known_keys:
            continue
        db.execute(
            "INSERT INTO graph_routes VALUES(?,?,?,?)",
            (snapshot_id, route.key, _json(list(route.edge_keys)), _json(list(route.evidence))),
        )
        known_keys.add(route.key)


def _unique_graph_key(base: str, used: set[str]) -> str:
    """Return a deterministic collision-safe key for a materialized row."""

    if base not in used:
        return base
    suffix = 2
    candidate = f"{base}~{suffix}"
    while candidate in used:
        suffix += 1
        candidate = f"{base}~{suffix}"
    return candidate


def _canonicalize_colliding_graph_keys(
    graph_edges: tuple[GraphEdge, ...],
    graph_routes: tuple[GraphRoute, ...],
    existing_edges: set[str],
    existing_routes: set[str],
) -> tuple[tuple[GraphEdge, ...], tuple[GraphRoute, ...]]:
    """Keep interpretation-local keys unique in the accumulated snapshot.

    Residue keys are local to one interpretation.  A later extractor call may
    validly reuse ``e1`` for a different source-backed relationship.  Snapshot
    rows require lineage-wide keys, so only colliding incoming rows receive a
    deterministic content-derived suffix; non-colliding historical keys remain
    readable.  The suffix contains no administrative identifier.
    """

    used_edges = set(existing_edges)
    edge_key_map: dict[str, str] = {}
    canonical_edges: list[GraphEdge] = []
    for edge in graph_edges:
        key = edge.key
        if key in used_edges:
            digest = _digest(
                {
                    "source": edge.source,
                    "target": edge.target,
                    "relationship": edge.relationship,
                    "evidence": edge.content_dict()["evidence"],
                }
            )[:16]
            key = _unique_graph_key(f"{edge.key}~{digest}", used_edges)
        used_edges.add(key)
        edge_key_map[edge.key] = key
        annotations = dict(edge.annotations or {})
        if key != edge.key:
            annotations["local_key"] = edge.key
        canonical_edges.append(
            GraphEdge(key, edge.source, edge.target, edge.relationship, edge.evidence, annotations)
        )

    used_routes = set(existing_routes)
    canonical_routes: list[GraphRoute] = []
    for route in graph_routes:
        edge_keys = tuple(edge_key_map.get(key, key) for key in route.edge_keys)
        key = route.key
        if key in used_routes:
            digest = _digest(
                {"edge_keys": edge_keys, "evidence": route.content_dict()["evidence"]}
            )[:16]
            key = _unique_graph_key(f"{route.key}~{digest}", used_routes)
        used_routes.add(key)
        annotations = dict(route.annotations or {})
        if key != route.key:
            annotations["local_key"] = route.key
        canonical_routes.append(GraphRoute(key, edge_keys, route.evidence, annotations))
    return tuple(canonical_edges), tuple(canonical_routes)


class InterpretationPublisher:
    """Prepare, record and atomically publish one interpretation."""

    def __init__(self, store: SQLiteStore, instance_id: str):
        self.store = store
        self.instance_id = instance_id

    def prepare(
        self,
        episode_id: str,
        *,
        operation_id: str | None = None,
        configuration_digest: str = "",
    ) -> str:
        operation_id = operation_id or str(uuid.uuid4())
        with self.store.transaction() as db:
            episode = db.execute(
                "SELECT origin_instance_id FROM episodes WHERE episode_id=?", (episode_id,)
            ).fetchone()
            if episode is None or str(episode[0]) != self.instance_id:
                raise PublicationError("episode is not accepted by this lineage")
            current = self.store.current()
            old = db.execute(
                "SELECT episode_id,configuration_digest FROM interpretation_operations "
                "WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if old is not None:
                if str(old[0]) != episode_id or str(old[1]) != configuration_digest:
                    raise PublicationError("interpretation operation idempotency conflict")
                return operation_id
            duplicate = db.execute(
                "SELECT operation_id FROM interpretation_operations WHERE episode_id=?",
                (episode_id,),
            ).fetchone()
            if duplicate is not None:
                return str(duplicate[0])
            now = _utc()
            db.execute(
                "INSERT INTO interpretation_operations VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    episode_id,
                    self.instance_id,
                    str(current["current_manifest_id"]),
                    "PREPARED",
                    0,
                    configuration_digest,
                    None,
                    now,
                    now,
                ),
            )
        return operation_id

    def record_attempt(
        self,
        operation_id: str,
        result: Mapping[str, Any] | str,
        *,
        attempt: int = 0,
        status: str = "RESULT_READY",
        validation_errors: list[str] | None = None,
        host_ref: str | None = None,
    ) -> None:
        if attempt < 0 or status not in {"STARTED", "RESULT_READY", "INVALID", "UNCERTAIN"}:
            raise PublicationError("invalid interpretation attempt")
        result_json = result if isinstance(result, str) else _json(result)
        with self.store.transaction() as db:
            op = db.execute(
                "SELECT operation_id,episode_id,current_attempt,status "
                "FROM interpretation_operations "
                "WHERE operation_id=? AND instance_id=?",
                (operation_id, self.instance_id),
            ).fetchone()
            if op is None:
                raise PublicationError("unknown interpretation operation")
            prior = db.execute(
                "SELECT result_json,status FROM interpretation_attempts "
                "WHERE operation_id=? AND attempt=?",
                (operation_id, attempt),
            ).fetchone()
            if prior is not None:
                if prior[1] == "STARTED" and status != "STARTED":
                    now = _utc()
                    db.execute(
                        "UPDATE interpretation_attempts SET result_json=?,status=?,"
                        "validation_errors_json=? WHERE operation_id=? AND attempt=?",
                        (
                            result_json,
                            status,
                            _json(validation_errors or []),
                            operation_id,
                            attempt,
                        ),
                    )
                    db.execute(
                        "UPDATE interpretation_operations SET current_attempt=?,status=?,"
                        "updated_at=? "
                        "WHERE operation_id=?",
                        (attempt, "FAILED" if status == "INVALID" else status, now, operation_id),
                    )
                    return
                if prior[0] != result_json or prior[1] != status:
                    raise PublicationError("interpretation attempt is immutable")
                return
            if attempt > int(op[2]) + 1:
                raise PublicationError("interpretation attempts must be sequential")
            if attempt > 1:
                raise PublicationError("only one extraction repair is permitted")
            request_json = _json(_source_bundle(db, str(op[1])))
            now = _utc()
            db.execute(
                "INSERT INTO interpretation_attempts VALUES(?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    attempt,
                    host_ref,
                    request_json,
                    result_json,
                    status,
                    _json(validation_errors or []),
                    now,
                ),
            )
            db.execute(
                "UPDATE interpretation_operations SET current_attempt=?,status=?,updated_at=? "
                "WHERE operation_id=?",
                (attempt, "FAILED" if status == "INVALID" else status, now, operation_id),
            )

    def publish(
        self,
        operation_id: str,
        residue: Residue,
        *,
        expected_manifest_id: str | None = None,
        extractor_version: str = "residue-v1",
        resolver_version: str = "explicit-v1",
        resolution_decisions: Mapping[str, ResolutionDecision] | None = None,
        observations: tuple[Observation, ...] | list[Observation] = (),
        consequences: tuple[ConsequenceAssessment, ...] | list[ConsequenceAssessment] = (),
        learner: DevelopmentalLearner | None = None,
        development_operation_id: str | None = None,
        opportunity: int | None = None,
        assessor_version: str = "",
    ) -> PublicationReceipt:
        observation_rows = tuple(observations)
        consequence_rows = tuple(consequences)
        learner_requested = bool(
            observation_rows or consequence_rows or learner is not None or development_operation_id
        )
        with self.store.transaction() as db:
            # Graph rows reference the snapshot envelope, whose digest is
            # computed only after materialization. Defer FK checks until the
            # enclosing atomic publication commits.
            db.execute("PRAGMA defer_foreign_keys = ON")
            op = db.execute(
                "SELECT * FROM interpretation_operations WHERE operation_id=? AND instance_id=?",
                (operation_id, self.instance_id),
            ).fetchone()
            if op is None:
                raise PublicationError("unknown interpretation operation")
            if op["status"] == "ACCEPTED":
                row = db.execute(
                    "SELECT i.interpretation_id,m.revision,m.graph_revision,m.manifest_id,"
                    "m.graph_snapshot_id "
                    "FROM interpretations i JOIN manifests m ON m.revision=i.accepted_revision "
                    "WHERE i.operation_id=? AND m.instance_id=?",
                    (operation_id, self.instance_id),
                ).fetchone()
                if row is None:
                    raise PublicationError("accepted interpretation is missing its manifest")
                return PublicationReceipt(
                    operation_id,
                    str(row[0]),
                    "ACCEPTED",
                    int(row[1]),
                    int(row[2]),
                    str(row[3]),
                    str(row[4]),
                )
            current = db.execute(
                "SELECT * FROM current_state WHERE active_instance_id=?", (self.instance_id,)
            ).fetchone()
            if current is None:
                raise PublicationError("lineage has no current state")
            if learner_requested:
                policy = db.execute(
                    "SELECT learning_allowed FROM policies WHERE policy_id=("
                    "SELECT policy_id FROM manifests WHERE manifest_id=? )",
                    (current["current_manifest_id"],),
                ).fetchone()
                if policy is None or not bool(policy[0]):
                    raise PublicationError("learning permission is not enabled")
            expected = expected_manifest_id or str(op["base_manifest_id"])
            if str(current["current_manifest_id"]) != expected:
                raise StalePublication("interpretation base manifest is stale")
            episode = db.execute(
                "SELECT accepted_revision FROM episodes WHERE episode_id=?", (op["episode_id"],)
            ).fetchone()
            if episode is None:
                raise PublicationError("interpretation episode is missing")
            if not isinstance(residue, Residue):
                raise PublicationError("publish requires a validated Residue")
            # Revalidate at the publication boundary.  The service normally
            # passes a residue returned by validate_residue(), but this keeps
            # a manually constructed/deserialized Residue from bypassing
            # source-slot, span, and 0.70 admission checks.
            try:
                source_bundle = _source_bundle(db, str(op["episode_id"]))
                source_map = {
                    str(source["slot"]): str(source["content"])
                    for source in source_bundle["sources"]
                }
                residue = validate_residue(residue.to_dict(), source_map)
            except ResidueValidationError as exc:
                raise PublicationError(f"residue is not publishable: {exc}") from exc
            latest_attempt = db.execute(
                "SELECT attempt,status FROM interpretation_attempts "
                "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
                (operation_id,),
            ).fetchone()
            if latest_attempt is not None and str(latest_attempt[1]) in {"INVALID", "UNCERTAIN"}:
                raise PublicationError("interpretation result is not publishable")
            if latest_attempt is None:
                now_attempt = _utc()
                db.execute(
                    "INSERT INTO interpretation_attempts VALUES(?,?,?,?,?,?,?,?)",
                    (
                        operation_id,
                        0,
                        None,
                        "{}",
                        _json(residue.to_dict()),
                        "VALID",
                        "[]",
                        now_attempt,
                    ),
                )
                db.execute(
                    "UPDATE interpretation_operations SET current_attempt=0,"
                    "status='RESULT_READY',updated_at=? "
                    "WHERE operation_id=?",
                    (now_attempt, operation_id),
                )

            old_manifest = db.execute(
                "SELECT * FROM manifests WHERE manifest_id=?", (expected,)
            ).fetchone()
            if old_manifest is None:
                raise PublicationError("interpretation base manifest is missing")
            old_snapshot = old_manifest["graph_snapshot_id"]
            old_graph_revision = int(old_manifest["graph_revision"])
            graph = materialize_graph(residue, snapshot_id=str(uuid.uuid4()), graph_revision=0)
            has_content = bool(graph.concepts or graph.edges or graph.routes)
            graph_revision = old_graph_revision + (1 if has_content else 0)
            snapshot_id = str(graph.snapshot_id)
            if old_snapshot is not None and has_content:
                _copy_graph(db, str(old_snapshot), snapshot_id)
            elif old_snapshot is not None and not has_content:
                snapshot_id = str(old_snapshot)
            if has_content:
                existing_concepts = {
                    str(row[0])
                    for row in db.execute(
                        "SELECT concept_key FROM graph_concepts WHERE snapshot_id=?", (snapshot_id,)
                    )
                }
                existing_edges = {
                    str(row[0])
                    for row in db.execute(
                        "SELECT edge_key FROM graph_edges WHERE snapshot_id=?", (snapshot_id,)
                    )
                }
                existing_routes = {
                    str(row[0])
                    for row in db.execute(
                        "SELECT route_key FROM graph_routes WHERE snapshot_id=?", (snapshot_id,)
                    )
                }
                graph_edges, graph_routes = _canonicalize_colliding_graph_keys(
                    graph.edges,
                    graph.routes,
                    existing_edges,
                    existing_routes,
                )
                for graph_concept in graph.concepts:
                    if graph_concept.key in existing_concepts:
                        continue
                    db.execute(
                        "INSERT INTO graph_concepts VALUES(?,?,?,?,?,?,?,?)",
                        (
                            snapshot_id,
                            graph_concept.key,
                            graph_concept.label,
                            graph_concept.label.casefold(),
                            graph_concept.kind,
                            float(graph_concept.annotations.get("confidence", 0.0))
                            if graph_concept.annotations
                            else 0.0,
                            float(graph_concept.annotations.get("salience", 0.0))
                            if graph_concept.annotations
                            else 0.0,
                            None,
                        ),
                    )
                for edge in graph_edges:
                    if edge.key in existing_edges:
                        continue
                    db.execute(
                        "INSERT INTO graph_edges VALUES(?,?,?,?,?,?,?,?)",
                        (
                            snapshot_id,
                            edge.key,
                            edge.source,
                            edge.target,
                            edge.relationship,
                            "asserted",
                            _json(edge.annotations or {}),
                            _json(list(edge.evidence)),
                        ),
                    )
                for route in graph_routes:
                    db.execute(
                        "INSERT OR IGNORE INTO graph_routes VALUES(?,?,?,?)",
                        (
                            snapshot_id,
                            route.key,
                            _json(list(route.edge_keys)),
                            _json(list(route.evidence)),
                        ),
                    )
                _discover_snapshot_routes(db, snapshot_id)
                digest = _snapshot_digest(db, snapshot_id)
                db.execute(
                    "INSERT INTO graph_snapshots VALUES(?,?,?,?,?,?,?)",
                    (
                        snapshot_id,
                        self.instance_id,
                        int(current["current_revision"]) + 1,
                        graph_revision,
                        old_snapshot,
                        digest,
                        _utc(),
                    ),
                )
            elif old_snapshot is None:
                digest = _snapshot_digest(db, snapshot_id)
                db.execute(
                    "INSERT INTO graph_snapshots VALUES(?,?,?,?,?,?,?)",
                    (
                        snapshot_id,
                        self.instance_id,
                        int(current["current_revision"]) + 1,
                        0,
                        None,
                        digest,
                        _utc(),
                    ),
                )

            interpretation_id = str(uuid.uuid4())
            now = _utc()
            db.execute(
                "INSERT INTO interpretations VALUES(?,?,?,?,?,?,?,?)",
                (
                    interpretation_id,
                    operation_id,
                    op["episode_id"],
                    1,
                    extractor_version,
                    resolver_version,
                    int(current["current_revision"]) + 1,
                    now,
                ),
            )
            concept_labels = {
                str(concept["key"]): str(concept["label"])
                for concept in residue.core_concepts
            }
            if old_snapshot is not None:
                for row in db.execute(
                    "SELECT concept_key,label FROM graph_concepts WHERE snapshot_id=?",
                    (old_snapshot,),
                ):
                    concept_labels.setdefault(str(row[0]), str(row[1]))
            candidate_ids: dict[str, str] = {}
            decisions: dict[str, ResolutionDecision] = {}
            for concept in residue.core_concepts:
                # Persist the conservative resolution outcome alongside the
                # candidate. Callers may provide an explicit alias or
                # ambiguity decision keyed by the residue-local concept;
                # otherwise the normalized label is an exact decision.
                local_key = str(concept["key"])
                decision = (
                    resolution_decisions.get(local_key)
                    if resolution_decisions is not None
                    else None
                )
                if decision is None:
                    label = str(concept["label"])
                    decision = ResolutionDecision(
                        input_label=label,
                        normalized_label=normalize_lookup_label(label),
                        canonical_key=local_key,
                        method="exact",
                    )
                decisions[local_key] = decision
                canonical_label = concept_labels.get(
                    str(decision.canonical_key), decision.input_label
                )
                db.execute(
                    "INSERT INTO resolution_decisions VALUES(?,?,?,?,?,?,?,?)",
                    (
                        str(uuid.uuid4()),
                        interpretation_id,
                        local_key,
                        canonical_label,
                        decision.normalized_label,
                        decision.method,
                        _json(
                            {
                                "decision": decision.to_dict(),
                                "source_spans": concept.get("source_spans", ()),
                            }
                        ),
                        now,
                    ),
                )
                candidate_id = str(uuid.uuid4())
                candidate_ids[local_key] = candidate_id
                db.execute(
                    "INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        candidate_id,
                        interpretation_id,
                        concept["key"],
                        concept["label"],
                        concept["label"].casefold(),
                        concept["kind"],
                        float(concept.get("confidence", 0.0)),
                        float(concept.get("salience", 0.0)),
                        _json(concept.get("context", [])),
                    ),
                )
                for ordinal, span in enumerate(concept.get("source_spans", ())):
                    db.execute(
                        "INSERT INTO evidence_spans VALUES(?,?,?,?,?,?)",
                        (
                            candidate_id,
                            ordinal,
                            span["source_slot"],
                            span["start"],
                            span["end"],
                            _digest(span),
                        ),
                    )
            new_revision = int(current["current_revision"]) + 1
            manifest_id = str(uuid.uuid4())
            learner_result = None
            learner_snapshot_id: str | None = None
            learner_configuration_digest: str | None = None
            learner_opportunity: int | None = None
            binding_rows: list[
                tuple[str, str, str, str | None, str, str, str, int, str]
            ] = []
            if learner_requested:
                # Bindings are content identities.  The extractor's local
                # keys and row UUIDs remain provenance, never learner keys.
                concepts_by_key = {
                    str(concept["key"]): concept for concept in residue.core_concepts
                }
                stable_by_local: dict[str, str] = {}
                for local_key, concept in concepts_by_key.items():
                    decision = decisions[local_key]
                    target = concepts_by_key.get(str(decision.canonical_key), concept)
                    historical = None
                    if str(decision.canonical_key) not in concepts_by_key:
                        historical = db.execute(
                            "SELECT canonical_key FROM semantic_bindings "
                            "WHERE instance_id=? AND local_key=? ORDER BY created_at LIMIT 1",
                            (self.instance_id, str(decision.canonical_key)),
                        ).fetchone()
                    stable_by_local[local_key] = (
                        str(historical[0])
                        if historical is not None
                        else _stable_concept_key(
                            str(target["label"]),
                            str(target["kind"]),
                            target.get("context", ()),
                        )
                    )
                for local_key, concept in concepts_by_key.items():
                    binding_id = _digest(
                        {
                            "instance": self.instance_id,
                            "interpretation": interpretation_id,
                            "local_key": local_key,
                        }
                    )
                    binding_rows.append(
                        (
                            binding_id,
                            self.instance_id,
                            interpretation_id,
                            candidate_ids[local_key],
                            local_key,
                            stable_by_local[local_key],
                            str(concept["label"]),
                            1,
                            _json(
                                {
                                    "interpretation_id": interpretation_id,
                                    "candidate_id": candidate_ids[local_key],
                                    "source_spans": concept.get("source_spans", ()),
                                }
                            ),
                        )
                    )
                for edge_record in residue.edge_candidates:
                    edge_map = edge_record
                    edge_key = str(edge_map["key"])
                    stable_source = stable_by_local.get(str(edge_map["from"]))
                    stable_target = stable_by_local.get(str(edge_map["to"]))
                    if stable_source is None or stable_target is None:
                        raise PublicationError("edge has no stable concept binding")
                    stable_edge = _stable_edge_key(
                        stable_source,
                        stable_target,
                        str(edge_map["relationship"]),
                        str(edge_map.get("polarity", "asserted")),
                        edge_map.get("context", ()),
                    )
                    binding_id = _digest(
                        {
                            "instance": self.instance_id,
                            "interpretation": interpretation_id,
                            "local_key": edge_key,
                            "kind": "edge",
                        }
                    )
                    binding_rows.append(
                        (
                            binding_id,
                            self.instance_id,
                            interpretation_id,
                            None,
                            edge_key,
                            stable_edge,
                            str(edge_map["relationship"]),
                            1,
                            _json(
                                {
                                    "interpretation_id": interpretation_id,
                                    "edge_key": edge_key,
                                    "source_spans": edge_map.get("source_spans", ()),
                                }
                            ),
                        )
                    )
                edge_binding_rows = [row for row in binding_rows if row[3] is None]
                edge_binding_by_local = {str(row[4]): row for row in edge_binding_rows}
                edge_binding_by_canonical: dict[str, list[tuple[Any, ...]]] = {}
                for row in edge_binding_rows:
                    edge_binding_by_canonical.setdefault(str(row[5]), []).append(row)

                # Learner state is keyed by the stable semantic edge identity,
                # while the local extractor key remains available for audit and
                # source provenance.  Normalize observations before the pure
                # transition so a later interpretation using a different local
                # key accumulates on the same canonical edge.
                normalized_observations: list[Observation] = []
                normalized_targets: dict[int, tuple[str, str, str]] = {}
                for index, observation in enumerate(observation_rows):
                    local_target = _observation_target(observation)
                    binding = edge_binding_by_local.get(local_target)
                    if binding is None:
                        canonical_matches = edge_binding_by_canonical.get(local_target, [])
                        if len(canonical_matches) != 1:
                            raise PublicationError(
                                "observation has no unique accepted edge binding: "
                                f"{local_target}"
                            )
                        binding = canonical_matches[0]
                    canonical_target = str(binding[5])
                    normalized = replace(
                        observation,
                        target_key=canonical_target,
                        edge_key=canonical_target,
                    )
                    normalized_observations.append(normalized)
                    normalized_targets[index] = (local_target, canonical_target, str(binding[0]))
                learner_obj = learner or DevelopmentalLearner()
                learner_opportunity = opportunity
                if learner_opportunity is None:
                    learner_opportunity = int(old_manifest["opportunity"] or 0) + 1
                if learner_opportunity < 1:
                    raise PublicationError("learner opportunity must be positive")
                prior_state: dict[tuple[str, str], EdgeState] = {}
                latest_values = db.execute(
                    "SELECT v.edge_key,v.context,u.after_json FROM learner_values v "
                    "JOIN learner_updates u ON u.update_id=v.update_id "
                    "WHERE v.instance_id=? ORDER BY v.opportunity,v.rowid",
                    (self.instance_id,),
                )
                for value in latest_values:
                    key = (str(value[0]), str(value[1]))
                    prior_state[key] = _edge_state_from_json(json.loads(str(value[2])))
                prior_routes: tuple[RouteState, ...] = ()
                latest_snapshot = db.execute(
                    "SELECT configuration_json FROM learner_snapshots "
                    "WHERE instance_id=? ORDER BY opportunity DESC,rowid DESC LIMIT 1",
                    (self.instance_id,),
                ).fetchone()
                if latest_snapshot is not None:
                    snapshot_payload = json.loads(str(latest_snapshot[0]))
                    raw_state = snapshot_payload.get("state", {})
                    raw_routes = (
                        raw_state.get("routes", {}) if isinstance(raw_state, Mapping) else {}
                    )
                    if isinstance(raw_routes, Mapping):
                        prior_routes = tuple(
                            _route_state_from_json(value)
                            for _key, value in sorted(raw_routes.items())
                            if isinstance(value, Mapping)
                        )
                learner_result = learner_obj.apply(
                    prior_state,
                    tuple(normalized_observations),
                    opportunity=learner_opportunity,
                )
                learner_state = LearnerState(
                    edge_states=tuple(
                        sorted(learner_result.state.values(), key=lambda item: item.key)
                    ),
                    route_states=prior_routes,
                    global_opportunity=int(learner_opportunity),
                )
                for consequence in consequence_rows:
                    consequence_result = apply_consequence(learner_state, consequence)
                    if not isinstance(consequence_result, ConsequenceResult):
                        raise PublicationError("consequence transition returned an invalid state")
                    learner_state = consequence_result.state
                learner_configuration = {
                    key: value
                    for key, value in learner_obj.config.__dict__.items()
                }
                learner_configuration_digest = _digest(learner_configuration)
                learner_snapshot_id = str(uuid.uuid4())
            integrity = _digest(
                {"instance_id": self.instance_id, "revision": new_revision, "snapshot": snapshot_id}
            )
            db.execute(
                "INSERT INTO manifests("
                "manifest_id,instance_id,revision,parent_manifest_id,inherited_base_manifest_id,"
                "policy_id,self_ref_id,format_version,controller_version,integrity_digest,"
                "accepted_history_digest,graph_snapshot_id,graph_revision,accepted_episode_count,"
                "self_view_id,self_view_version,learner_snapshot_id,learner_configuration_digest,"
                "binding_version,opportunity,coverage_json,authority_revision) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id,
                    self.instance_id,
                    new_revision,
                    expected,
                    old_manifest["inherited_base_manifest_id"],
                    old_manifest["policy_id"],
                    old_manifest["self_ref_id"],
                    old_manifest["format_version"],
                    "mneme-p1.1",
                    integrity,
                    old_manifest["accepted_history_digest"],
                    snapshot_id,
                    graph_revision,
                    old_manifest["accepted_episode_count"],
                    old_manifest["self_view_id"],
                    old_manifest["self_view_version"],
                    learner_snapshot_id,
                    learner_configuration_digest,
                    1 if learner_requested else old_manifest["binding_version"],
                    learner_opportunity
                    if learner_opportunity is not None
                    else old_manifest["opportunity"],
                    _json(
                        {
                            f"{_observation_target(row)}:{row.context}": row.covered
                            for row in observation_rows
                        }
                    )
                    if learner_requested
                    else old_manifest["coverage_json"],
                    old_manifest["authority_revision"],
                ),
            )
            if learner_requested:
                development_id = development_operation_id or operation_id
                development = db.execute(
                    "SELECT episode_id,instance_id,base_manifest_id,opportunity,stage "
                    "FROM development_operations WHERE operation_id=?",
                    (development_id,),
                ).fetchone()
                if development is None:
                    db.execute(
                        "INSERT INTO development_operations VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (
                            development_id,
                            self.instance_id,
                            op["episode_id"],
                            expected,
                            int(learner_opportunity or 1),
                            "ACCEPTED",
                            "accepted",
                            str(op["configuration_digest"]),
                            now,
                            now,
                        ),
                    )
                elif (
                    str(development[0]) != str(op["episode_id"])
                    or str(development[1]) != self.instance_id
                    or str(development[2]) != expected
                ):
                    raise PublicationError("development operation idempotency conflict")
                for consequence in consequence_rows:
                    db.execute(
                        "INSERT INTO outcome_assessments("
                        "assessment_id,instance_id,operation_id,target_route_id,context,outcome,"
                        "direction,exposure_id,relevant,evidence_json,source_json,status,"
                        "authority_revision,supersedes_assessment_id,created_at) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            consequence.operation_id,
                            self.instance_id,
                            development_id,
                            consequence.route_key,
                            consequence.context,
                            consequence.outcome,
                            consequence.direction,
                            consequence.exposure_id,
                            int(consequence.relevant),
                            _json({"assessment": consequence.to_dict()}),
                            _json(
                                {
                                    "development_operation_id": development_id,
                                    "exposure_id": consequence.exposure_id,
                                }
                            ),
                            "ACCEPTED",
                            int(old_manifest["authority_revision"] or 0),
                            None,
                            now,
                        ),
                    )
                for row in binding_rows:
                    db.execute(
                        "INSERT INTO semantic_bindings VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (*row, resolver_version, now),
                    )
                for index, observation in enumerate(observation_rows):
                    observation_target, canonical_target, binding_id = normalized_targets[index]
                    db.execute(
                        "INSERT INTO development_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            _digest(
                                {
                                    "operation": development_id,
                                    "edge": observation_target,
                                    "context": observation.context,
                                    "observation": observation.observation_id,
                                }
                            ),
                            development_id,
                            binding_id,
                            observation_target,
                            observation.context,
                            getattr(observation.source_role, "value", str(observation.source_role)),
                            getattr(observation.status, "value", str(observation.status)),
                            getattr(observation.dependence, "value", str(observation.dependence)),
                            observation.group_key,
                            int(observation.covered),
                            int(observation.actual_exposure),
                            _json(
                                {
                                    "observation_id": observation.observation_id,
                                    "occurrence_key": observation.occurrence_key,
                                    "provenance_group_keys": list(
                                        observation.provenance_group_keys
                                    ),
                                    "relevant": observation.relevant,
                                    "eligible": observation.eligible,
                                    "assessor_version": assessor_version,
                                }
                            ),
                            learner_result.reasons.get(
                                (canonical_target, observation.context), "unchanged"
                            )
                            if learner_result is not None
                            else None,
                            now,
                        ),
                    )
                if learner_result is not None:
                    observed_keys = {
                        (observation.target_key, observation.context)
                        for observation in normalized_observations
                    }
                    persist_keys = sorted(set(learner_result.state) | observed_keys)
                    for key in persist_keys:
                        edge_key, context = key
                        before = prior_state.get(key, EdgeState())
                        after = learner_result.state.get(key, before)
                        update_id = _digest(
                            {
                                "operation": development_id,
                                "edge": edge_key,
                                "context": context,
                                "opportunity": learner_opportunity,
                            }
                        )
                        delta = learner_result.deltas.get(key, 0)
                        db.execute(
                            "INSERT INTO learner_updates VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (
                                update_id,
                                development_id,
                                update_id,
                                int(learner_opportunity or 1),
                                edge_key,
                                context,
                                delta,
                                learner_result.reasons.get(key, "unchanged"),
                                _json(before.to_dict()),
                                _json(after.to_dict()),
                                now,
                            ),
                        )
                        db.execute(
                            "INSERT INTO learner_values VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (
                                _digest(
                                    {"update": update_id, "edge": edge_key, "context": context}
                                ),
                                self.instance_id,
                                update_id,
                                edge_key,
                                context,
                                after.accessibility,
                                after.support,
                                after.consequence,
                                sum(amount for _group, amount in after.lifetime_by_group),
                                sum(amount for _group, amount in after.induced_by_group),
                                sum(item.amount for item in after.rolling_credits),
                                after.last_consolidation_opportunity,
                                after.inactivity_ticks,
                                int(learner_opportunity or 1),
                                _digest({"edge": edge_key, "context": context, **after.to_dict()}),
                                now,
                            ),
                        )
                    state_payload = {
                        "global_opportunity": learner_state.global_opportunity,
                        "edges": {
                            f"{edge}:{context}": value.to_dict()
                            for (edge, context), value in sorted(
                                (
                                    key,
                                    learner_result.state.get(
                                        key, prior_state.get(key, EdgeState(*key))
                                    ),
                                )
                                for key in persist_keys
                            )
                        },
                        "routes": {
                            f"{route.route_key}:{route.context}": route.to_dict()
                            for route in learner_state.route_states
                        },
                    }
                    db.execute(
                        "INSERT INTO learner_snapshots VALUES(?,?,?,?,?,?,?,?)",
                        (
                            learner_snapshot_id,
                            self.instance_id,
                            manifest_id,
                            int(learner_opportunity or 1),
                            learner_obj.config.version,
                            _json(
                                {
                                    "configuration": learner_obj.config.__dict__,
                                    "state": state_payload,
                                }
                            ),
                            _digest(
                                {
                                    "configuration": learner_obj.config.__dict__,
                                    "state": state_payload,
                                }
                            ),
                            now,
                        ),
                    )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.instance_id,
                    new_revision,
                    current["current_revision"],
                    operation_id,
                    "interpretation_published",
                    None,
                    manifest_id,
                    now,
                ),
            )
            db.execute(
                "UPDATE current_state SET current_revision=?,current_manifest_id=? "
                "WHERE singleton=1",
                (new_revision, manifest_id),
            )
            db.execute(
                "UPDATE interpretation_operations SET status='ACCEPTED',updated_at=? "
                "WHERE operation_id=?",
                (now, operation_id),
            )
            return PublicationReceipt(
                operation_id,
                interpretation_id,
                "ACCEPTED",
                new_revision,
                graph_revision,
                manifest_id,
                snapshot_id,
            )


def publish_interpretation(
    store: SQLiteStore,
    instance_id: str,
    operation_id: str,
    residue: Residue,
    **kwargs: Any,
) -> PublicationReceipt:
    """Convenience entrypoint for one atomic publication."""

    return InterpretationPublisher(store, instance_id).publish(operation_id, residue, **kwargs)


__all__ = [
    "InterpretationPublisher",
    "PublicationError",
    "PublicationReceipt",
    "StalePublication",
    "publish_interpretation",
]
