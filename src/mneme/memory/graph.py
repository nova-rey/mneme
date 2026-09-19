"""Pure graph materialization for validated Phase One residues.

This module materializes a complete immutable graph snapshot.  It does not
search, rank, inject routes, update weights, or infer identity.  Administrative
snapshot identifiers are kept in the snapshot envelope but are excluded from
the content digest so that the digest compares graph content rather than
lineage bookkeeping.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .residue import Residue, ResidueValidationError


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _public_record(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, tuple):
            result[key] = [
                _public_record(entry) if isinstance(entry, Mapping) else entry for entry in item
            ]
        elif isinstance(item, Mapping):
            result[key] = _public_record(item)
        else:
            result[key] = item
    return result


@dataclass(frozen=True)
class GraphConcept:
    key: str
    label: str
    kind: str
    evidence: tuple[Mapping[str, Any], ...] = ()
    annotations: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(_freeze(item) for item in self.evidence))
        if self.annotations is not None:
            object.__setattr__(self, "annotations", _freeze(self.annotations))

    def content_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "evidence": [_public_record(value) for value in self.evidence],
        }
        if self.annotations:
            result["annotations"] = _public_record(self.annotations)
        return result

    def to_dict(self) -> dict[str, Any]:
        return self.content_dict()


@dataclass(frozen=True)
class GraphEdge:
    key: str
    source: str
    target: str
    relationship: str
    evidence: tuple[Mapping[str, Any], ...] = ()
    annotations: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(_freeze(item) for item in self.evidence))
        if self.annotations is not None:
            object.__setattr__(self, "annotations", _freeze(self.annotations))

    def content_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "key": self.key,
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
            "evidence": [_public_record(value) for value in self.evidence],
        }
        if self.annotations:
            result["annotations"] = _public_record(self.annotations)
        return result

    def to_dict(self) -> dict[str, Any]:
        return self.content_dict()


@dataclass(frozen=True)
class GraphRoute:
    key: str
    edge_keys: tuple[str, ...]
    evidence: tuple[Mapping[str, Any], ...] = ()
    annotations: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_keys", tuple(self.edge_keys))
        object.__setattr__(self, "evidence", tuple(_freeze(item) for item in self.evidence))
        if self.annotations is not None:
            object.__setattr__(self, "annotations", _freeze(self.annotations))

    def content_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "key": self.key,
            "edge_keys": list(self.edge_keys),
            "evidence": [_public_record(value) for value in self.evidence],
        }
        if self.annotations:
            result["annotations"] = _public_record(self.annotations)
        return result

    def to_dict(self) -> dict[str, Any]:
        return self.content_dict()


@dataclass(frozen=True)
class GraphSnapshot:
    """A complete immutable materialized graph snapshot."""

    snapshot_id: str
    origin_lineage_id: str | None
    graph_revision: int
    concepts: tuple[GraphConcept, ...]
    edges: tuple[GraphEdge, ...]
    routes: tuple[GraphRoute, ...]
    resolver_revision: int = 0
    policy_version: str = "phase-one-fixed-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "concepts", tuple(self.concepts))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "routes", tuple(self.routes))

    @property
    def content_digest(self) -> str:
        return _digest(self.content_dict())

    def content_dict(self) -> dict[str, Any]:
        return {
            "concepts": [
                concept.content_dict()
                for concept in sorted(self.concepts, key=lambda value: value.key)
            ],
            "edges": [
                edge.content_dict() for edge in sorted(self.edges, key=lambda value: value.key)
            ],
            "routes": [
                route.content_dict() for route in sorted(self.routes, key=lambda value: value.key)
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "origin_lineage_id": self.origin_lineage_id,
            "graph_revision": self.graph_revision,
            "resolver_revision": self.resolver_revision,
            "policy_version": self.policy_version,
            "content_digest": self.content_digest,
            **self.content_dict(),
        }


def _annotation(record: Mapping[str, Any], excluded: frozenset[str]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key not in excluded}


def materialize_graph(
    residue: Residue,
    *,
    snapshot_id: str = "unpublished",
    origin_lineage_id: str | None = None,
    graph_revision: int = 0,
    resolver_revision: int = 0,
    policy_version: str = "phase-one-fixed-v1",
) -> GraphSnapshot:
    """Materialize a validated residue without adding or ranking graph state."""

    concepts: list[GraphConcept] = []
    for record in residue.core_concepts:
        key = record["key"]
        label = record["label"]
        kind = record["kind"]
        if not isinstance(key, str) or not isinstance(label, str) or not isinstance(kind, str):
            raise ResidueValidationError("validated concept has invalid identity fields")
        evidence = tuple(record.get("source_spans", ()))
        excluded = frozenset({"key", "id", "label", "kind", "node_type", "source_spans"})
        concepts.append(GraphConcept(key, label, kind, evidence, _annotation(record, excluded)))

    edges: list[GraphEdge] = []
    for record in residue.edge_candidates:
        source, target = record["from"], record["to"]
        key, relationship = record["key"], record["relationship"]
        if not all(isinstance(value, str) for value in (key, source, target, relationship)):
            raise ResidueValidationError("validated edge has invalid identity fields")
        evidence = tuple(record.get("source_spans", ()))
        excluded = frozenset(
            {
                "key",
                "id",
                "from",
                "to",
                "from_concept",
                "to_concept",
                "relationship",
                "edge_type",
                "source_spans",
            }
        )
        edges.append(
            GraphEdge(key, source, target, relationship, evidence, _annotation(record, excluded))
        )

    routes: list[GraphRoute] = []
    for record in residue.route_candidates:
        key = record["key"]
        edge_keys = record["edge_keys"]
        if not isinstance(key, str) or not isinstance(edge_keys, tuple):
            raise ResidueValidationError("validated route has invalid identity fields")
        evidence = tuple(record.get("source_spans", ()))
        excluded = frozenset({"key", "id", "edge_keys", "edges", "source_spans"})
        routes.append(GraphRoute(key, edge_keys, evidence, _annotation(record, excluded)))

    return GraphSnapshot(
        snapshot_id=snapshot_id,
        origin_lineage_id=origin_lineage_id,
        graph_revision=graph_revision,
        concepts=tuple(concepts),
        edges=tuple(edges),
        routes=tuple(routes),
        resolver_revision=resolver_revision,
        policy_version=policy_version,
    )


__all__ = [
    "GraphConcept",
    "GraphEdge",
    "GraphRoute",
    "GraphSnapshot",
    "materialize_graph",
]
