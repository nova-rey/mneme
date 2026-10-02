"""Runtime adapter for descendants backed by :class:`CompactStore`.

The historical response controller is intentionally coupled to the research
SQLite schema.  A descendant that starts from a compact D100 copy must not
silently fall back to that schema, so this module provides the small runtime
boundary needed by the new trial:

* graph and learner state are loaded from current compact rows;
* development publishes one graph delta and changed learner values;
* SAA is evaluated against that same state and treatment health is checked;
* bounded storage metrics can be recorded at thread boundaries.

This is a state adapter, not a second learner or graph implementation.  The
existing pure graph, learner, SAA, introspection, and health modules remain the
semantic authorities.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..development.field import (
    SAA_FIELD_VERSION,
    FieldConfig,
    FieldResult,
    compute_saa_field,
)
from ..development.health import assess_saa_treatment_health
from ..development.learner import CreditWindow, EdgeState, LearnerState, RouteState
from .compact import CompactStore

if TYPE_CHECKING:
    from ..memory.graph import GraphConcept, GraphEdge, GraphRoute


class CompactRuntimeError(RuntimeError):
    """A compact-backed runtime cannot safely continue."""


@dataclass(frozen=True)
class CompactGraphView:
    """Current graph objects reconstructed from compact rows."""

    concepts: tuple[GraphConcept, ...]
    edges: tuple[GraphEdge, ...]
    routes: tuple[GraphRoute, ...]


@dataclass(frozen=True)
class CompactFieldEvaluation:
    """SAA result plus the health classification for one generation."""

    field: FieldResult
    health: Mapping[str, Any]


def _json_value(value: Any, *, field: str) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise CompactRuntimeError(f"compact {field} is not valid JSON") from exc
    return value


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    value = _json_value(value, field=field)
    if not isinstance(value, Mapping):
        raise CompactRuntimeError(f"compact {field} must be an object")
    return value


def _edge_state(value: Mapping[str, Any], *, edge_key: str, context: str) -> EdgeState:
    return EdgeState(
        target_key=str(value.get("target_key", edge_key)),
        context=str(value.get("context", context)),
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
        episode_keys=tuple(str(item) for item in value.get("episode_keys", [])),
    )


def _route_state(value: Mapping[str, Any]) -> RouteState:
    return RouteState(
        route_key=str(value["route_key"]),
        context=str(value.get("context", "general")),
        consequence=int(value.get("consequence", 0)),
        by_exposure=tuple(
            (str(key), int(amount))
            for key, amount in sorted(dict(value.get("by_exposure", {})).items())
        ),
        rolling_consequences=tuple(
            CreditWindow(int(item["opportunity"]), int(item["amount"]))
            for item in value.get("rolling_consequences", [])
        ),
        applied_assessments=tuple(str(item) for item in value.get("applied_assessments", [])),
    )


class CompactRuntime:
    """Small stateful runtime boundary for a compact-backed descendant."""

    def __init__(self, store: CompactStore):
        self.store = store

    def _edge_identity_maps(self) -> tuple[dict[str, str], dict[str, str]]:
        """Return canonical/local edge-key maps preserved by migration.

        Historical research stores use canonical learner keys (``edge:...``)
        while materialized graph snapshots use local keys (``e-...``).  A
        compact descendant must resolve that identity explicitly; treating
        the two namespaces as interchangeable silently turns a developed
        field into a cold/binding-mismatch field after fork or restart.
        Stores created without semantic bindings simply return empty maps.
        """

        table = self.store.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='semantic_bindings'"
        ).fetchone()
        if table is None:
            return {}, {}
        canonical_to_local: dict[str, str] = {}
        local_to_canonical: dict[str, str] = {}
        for row in self.store.connection.execute(
            "SELECT canonical_key,local_key FROM semantic_bindings"
        ):
            canonical, local = str(row[0]), str(row[1])
            if canonical and local:
                canonical_to_local[canonical] = local
                local_to_canonical[local] = canonical
        return canonical_to_local, local_to_canonical

    def resolve_edge_key(self, key: str) -> str:
        """Resolve a persisted canonical learner key to graph-local identity."""

        return self._edge_identity_maps()[0].get(str(key), str(key))

    def graph(self) -> CompactGraphView:
        """Reconstruct graph objects from current compact rows."""

        # Import lazily: ``mneme.memory`` imports development/state contracts
        # during package initialization, so an eager graph import here would
        # create a circular import for otherwise unrelated host/controller use.
        from ..memory.graph import GraphConcept, GraphEdge, GraphRoute

        state = self.store.graph_state()
        raw_bindings = self.store.metadata("edge_bindings", {})
        edge_bindings = (
            {str(key): str(value) for key, value in raw_bindings.items()}
            if isinstance(raw_bindings, Mapping)
            else {}
        )
        concepts: list[GraphConcept] = []
        for key, raw in sorted(state["nodes"].items()):
            row = _mapping(raw, field=f"graph node {key}")
            evidence = _json_value(row.get("evidence", row.get("source_spans", ())), field="node evidence")
            if not isinstance(evidence, (list, tuple)):
                evidence = ()
            annotations = dict(row)
            for field in ("key", "concept_key", "label", "normalized_label", "kind", "node_type", "evidence", "source_spans"):
                annotations.pop(field, None)
            concepts.append(
                GraphConcept(
                    str(row.get("key", row.get("concept_key", key))),
                    str(row.get("label", row.get("normalized_label", key))),
                    str(row.get("kind", row.get("node_type", "unknown"))),
                    tuple(item for item in evidence if isinstance(item, Mapping)),
                    annotations,
                )
            )

        edges_by_key: dict[str, GraphEdge] = {}
        for key, raw in sorted(state["edges"].items()):
            row = _mapping(raw, field=f"graph edge {key}")
            local_key = str(row.get("key", row.get("edge_key", key)))
            canonical_key = edge_bindings.get(local_key, local_key)
            evidence = _json_value(row.get("evidence", row.get("evidence_json", ())), field="edge evidence")
            annotations_raw = row.get("annotations", row.get("context_json", {}))
            edge_annotations = _mapping(annotations_raw, field="edge annotations")
            edge_annotations = dict(edge_annotations)
            if canonical_key != local_key:
                edge_annotations["local_key"] = local_key
                edge_annotations["canonical_key"] = canonical_key
            candidate = GraphEdge(
                canonical_key,
                str(row.get("source", row.get("source_key", ""))),
                str(row.get("target", row.get("target_key", ""))),
                str(row.get("relationship", "")),
                tuple(item for item in evidence if isinstance(item, Mapping))
                if isinstance(evidence, (list, tuple))
                else (),
                dict(edge_annotations),
            )
            prior = edges_by_key.get(canonical_key)
            if prior is None:
                edges_by_key[canonical_key] = candidate
            else:
                prior_evidence = list(prior.evidence)
                seen = {json.dumps(dict(item), sort_keys=True) for item in prior_evidence}
                for item in candidate.evidence:
                    marker = json.dumps(dict(item), sort_keys=True)
                    if marker not in seen:
                        seen.add(marker)
                        prior_evidence.append(item)
                edges_by_key[canonical_key] = GraphEdge(
                    prior.key,
                    prior.source,
                    prior.target,
                    prior.relationship,
                    tuple(prior_evidence),
                    dict(prior.annotations or {}),
                )
        edges = list(edges_by_key.values())

        routes: list[GraphRoute] = []
        for key, raw in sorted(state["routes"].items()):
            row = _mapping(raw, field=f"graph route {key}")
            edge_keys = _json_value(row.get("edge_keys", row.get("edge_keys_json", ())), field="route edges")
            edge_keys = (
                [edge_bindings.get(str(item), str(item)) for item in edge_keys]
                if isinstance(edge_keys, (list, tuple))
                else edge_keys
            )
            evidence = _json_value(row.get("evidence", row.get("source_json", ())), field="route evidence")
            routes.append(
                GraphRoute(
                    str(row.get("key", row.get("route_key", key))),
                    tuple(str(item) for item in edge_keys) if isinstance(edge_keys, (list, tuple)) else (),
                    tuple(item for item in evidence if isinstance(item, Mapping))
                    if isinstance(evidence, (list, tuple))
                    else (),
                )
            )
        return CompactGraphView(tuple(concepts), tuple(edges), tuple(routes))

    def learner(self) -> LearnerState:
        """Reconstruct current edge and route learner state."""

        rows = self.store.learner_state()
        canonical_to_local, _ = self._edge_identity_maps()
        edges = tuple(
            _edge_state(
                value,
                edge_key=canonical_to_local.get(edge_key, edge_key),
                context=context,
            )
            for (edge_key, context), value in sorted(rows.items())
        )
        raw_routes = self.store.metadata("learner_routes", {})
        routes: tuple[RouteState, ...] = ()
        if isinstance(raw_routes, list):
            routes = tuple(
                sorted(
                    (_route_state(_mapping(item, field="learner route")) for item in raw_routes),
                    key=lambda item: item.key,
                )
            )
        return LearnerState(
            edge_states=edges,
            route_states=routes,
            global_opportunity=int(self.store.metadata("global_opportunity", 0)),
        )

    def publish_state(
        self,
        graph: CompactGraphView | Mapping[str, Mapping[str, Mapping[str, Any]]],
        learner: LearnerState,
        *,
        operation_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Publish one descendant state using deltas and changed values only."""

        if isinstance(graph, CompactGraphView):
            nodes = {item.key: item.content_dict() for item in graph.concepts}
            edges = {item.key: item.content_dict() for item in graph.edges}
            routes = {item.key: item.content_dict() for item in graph.routes}
        else:
            nodes = {str(key): dict(value) for key, value in graph.get("nodes", {}).items()}
            edges = {str(key): dict(value) for key, value in graph.get("edges", {}).items()}
            routes = {str(key): dict(value) for key, value in graph.get("routes", {}).items()}
        revision = self.store.put_graph(nodes=nodes, edges=edges, routes=routes)
        canonical_to_local, _ = self._edge_identity_maps()
        records = [
            (
                canonical_to_local.get(state.target_key, state.target_key),
                state.context,
                state.to_dict(),
                operation_id,
            )
            for state in learner.edge_states
        ]
        changed = self.store.put_learner_batch(records)
        self.store.set_metadata("global_opportunity", learner.global_opportunity)
        self.store.set_metadata("learner_routes", [item.to_dict() for item in learner.route_states])
        if metadata:
            for key, value in metadata.items():
                self.store.set_metadata(str(key), value)
        return {
            "graph_revision": revision,
            "learner_changed": changed,
            "state_digest": self.store.state_digest(),
        }

    def evaluate_saa(
        self,
        query: str,
        *,
        field_seed: int,
        config: FieldConfig | None = None,
        field_adjustments: Mapping[str, int] | None = None,
        expression_adjustments: Mapping[str, int] | None = None,
        blocked_edges: Iterable[str] = (),
        enabled: bool = True,
        fail_on_unhealthy: bool = True,
    ) -> CompactFieldEvaluation:
        """Compute SAA from compact state and apply the treatment-health gate."""

        graph = self.graph()
        learner = self.learner()
        config = config or FieldConfig(version=SAA_FIELD_VERSION, exploration="on")
        blocked = set(str(item) for item in blocked_edges)
        field = compute_saa_field(
            query,
            graph.concepts,
            graph.edges,
            learner,
            config=config,
            field_enabled=enabled,
            field_seed=int(field_seed),
            quarantined_edges=blocked,
            ineligible_edges=(),
            accessibility_adjustments=field_adjustments or {},
            expression_adjustments=expression_adjustments or {},
        )
        health = assess_saa_treatment_health(field, learner, graph.edges, blocked_edges=blocked)
        if fail_on_unhealthy and health["status"] in {
            "binding_mismatch",
            "empty_distribution",
            "missing_landing",
            "zero_pressure",
            "empty_payload",
        }:
            raise CompactRuntimeError(
                "compact SAA treatment-health failure: "
                f"{json.dumps(dict(health), sort_keys=True, separators=(',', ':'))}"
            )
        return CompactFieldEvaluation(field, health)

    def record_thread_metrics(self, thread: int | str) -> dict[str, Any]:
        """Return and optionally retain one bounded thread-boundary metric."""

        metric = self.store.storage_metrics(label=f"thread-{thread}")
        self.store.record_telemetry("thread_storage", metric)
        return metric

    def verify(self) -> list[str]:
        return self.store.verify()


__all__ = [
    "CompactFieldEvaluation",
    "CompactGraphView",
    "CompactRuntime",
    "CompactRuntimeError",
]
