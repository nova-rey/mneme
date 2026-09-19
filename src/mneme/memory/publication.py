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
from dataclasses import dataclass
from typing import Any

from ..state.storage import SQLiteStore, _utc
from .graph import materialize_graph
from .residue import Residue, ResidueValidationError, validate_residue
from .resolution import ResolutionDecision, normalize_lookup_label


class PublicationError(RuntimeError):
    """A residue cannot be published against the current accepted state."""


class StalePublication(PublicationError):
    """The interpretation was prepared against an obsolete manifest."""


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
    ) -> PublicationReceipt:
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
                for edge in graph.edges:
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
                for route in graph.routes:
                    db.execute(
                        "INSERT OR IGNORE INTO graph_routes VALUES(?,?,?,?)",
                        (
                            snapshot_id,
                            route.key,
                            _json(list(route.edge_keys)),
                            _json(list(route.evidence)),
                        ),
                    )
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
            integrity = _digest(
                {"instance_id": self.instance_id, "revision": new_revision, "snapshot": snapshot_id}
            )
            db.execute(
                "INSERT INTO manifests("
                "manifest_id,instance_id,revision,parent_manifest_id,inherited_base_manifest_id,"
                "policy_id,self_ref_id,format_version,controller_version,integrity_digest,"
                "accepted_history_digest,graph_snapshot_id,graph_revision,accepted_episode_count,"
                "self_view_id,self_view_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
