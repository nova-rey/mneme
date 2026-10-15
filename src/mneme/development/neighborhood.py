"""Bounded, side-effect-free projections of an existing SAA field result.

This module does not select a landing, walk the graph, change pressure, or
alter the ordinary host payload.  It only projects the already selected
``PressureContribution`` rows into an inspectable local view.  Audit labels,
identities, and pressures are kept separate from the optional portable
descriptor.

Portable label disclosure is intentionally restricted to callers that attest
that a fixture is synthetic and approved.  This is not a privacy classifier
and must not be treated as permission to expose live developmental labels.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .field import SAA_FIELD_VERSION, FieldResult, PressureContribution

PROJECTION_SCHEMA_VERSION = "saa-neighborhood-projection-v1"
PORTABLE_DESCRIPTOR_VERSION = "saa-portable-neighborhood-v1"
_PORTABLE_RELATIONS = frozenset(
    {
        "causal",
        "causes",
        "depends_on",
        "enables",
        "supports",
        "retains",
        "maintains",
        "prevents",
        "constrains",
        "part_of",
        "associated_with",
        "related",
        "sequence",
        "precedes",
        "rhythm",
        "varies",
        "reduces",
        "isolates",
    }
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _bounded_integer(value: int) -> int | tuple[str, int]:
    if value.bit_length() <= 256:
        return value
    return ("integer_too_large", value.bit_length())


@dataclass(frozen=True)
class ProjectionPolicy:
    """Hard output limits and explicit disclosure mode for one projection."""

    max_nodes: int = 24
    max_edges: int = 24
    max_hops: int = 4
    max_paths: int = 24
    max_input_contributions: int = 256
    max_identity_chars: int = 128
    max_label_chars: int = 160
    max_serialized_bytes: int = 16_384
    descriptor_mode: Literal["disabled", "synthetic_fixture_only"] = "disabled"

    def __post_init__(self) -> None:
        if self.max_nodes < 0 or self.max_edges < 0 or self.max_paths < 0:
            raise ValueError("projection node, edge, and path limits cannot be negative")
        if not 0 <= self.max_hops <= 8:
            raise ValueError("max_hops must be in [0, 8]")
        if self.max_input_contributions < 1:
            raise ValueError("max_input_contributions must be positive")
        if self.max_identity_chars < 1:
            raise ValueError("max_identity_chars must be positive")
        if self.max_label_chars < 1:
            raise ValueError("max_label_chars must be positive")
        if self.max_serialized_bytes < 512:
            raise ValueError("max_serialized_bytes must be at least 512")
        if self.descriptor_mode not in {"disabled", "synthetic_fixture_only"}:
            raise ValueError("unsupported descriptor disclosure mode")


@dataclass(frozen=True)
class ProjectedNode:
    key: str
    label: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label}


@dataclass(frozen=True)
class ProjectedEdge:
    key: str
    source: str
    relationship: str
    target: str
    path: tuple[str, ...]
    hops: int
    role: Literal["landing", "direct", "farther", "cross_link"]
    pressure: int
    component: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "source": self.source,
            "relationship": self.relationship,
            "target": self.target,
            "path": list(self.path),
            "hops": self.hops,
            "role": self.role,
            "pressure": self.pressure,
            "component": self.component,
        }


@dataclass(frozen=True)
class ProjectedPath:
    contribution_edge: str
    edge_keys: tuple[str, ...]
    hops: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "contribution_edge": self.contribution_edge,
            "edge_keys": list(self.edge_keys),
            "hops": self.hops,
        }


@dataclass(frozen=True)
class PortableRelation:
    source: str
    relationship: str
    target: str
    role: str
    hops: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "relationship": self.relationship,
            "target": self.target,
            "role": self.role,
            "hops": self.hops,
        }


@dataclass(frozen=True)
class PortableNeighborhoodDescriptor:
    schema_version: str
    relations: tuple[PortableRelation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "relations": [item.to_dict() for item in self.relations],
        }


@dataclass(frozen=True)
class NeighborhoodProjection:
    """Research audit view plus a separately requested optional descriptor."""

    schema_version: str
    field_version: str
    field_seed: int | None
    landing_edge_key: str | None
    input_fingerprint: str
    nodes: tuple[ProjectedNode, ...]
    edges: tuple[ProjectedEdge, ...]
    paths: tuple[ProjectedPath, ...]
    omissions: tuple[tuple[str, int], ...]
    descriptor_omissions: tuple[tuple[str, int], ...]
    portable_descriptor: PortableNeighborhoodDescriptor | None

    def to_audit_dict(self) -> dict[str, Any]:
        """Return the identity/label/pressure-bearing research-only view."""

        return {
            "schema_version": self.schema_version,
            "field_version": self.field_version,
            "field_seed": self.field_seed,
            "landing_edge_key": self.landing_edge_key,
            "input_fingerprint": self.input_fingerprint,
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "paths": [item.to_dict() for item in self.paths],
            "omissions": [{"reason": key, "count": value} for key, value in self.omissions],
            "descriptor_omissions": [
                {"reason": key, "count": value}
                for key, value in self.descriptor_omissions
            ],
        }

    def to_portable_dict(self) -> dict[str, Any] | None:
        """Return the opt-in descriptor without audit IDs, scores, or provenance."""

        return None if self.portable_descriptor is None else self.portable_descriptor.to_dict()

    @property
    def audit_size_bytes(self) -> int:
        return len(_canonical_json(self.to_audit_dict()))


def _input_fingerprint(
    result: FieldResult,
    rows: tuple[PressureContribution, ...],
    policy: ProjectionPolicy,
) -> str:
    row_digests = []
    for item in rows:
        row_digests.append(
            {
                "edge": (item.edge_key[: policy.max_identity_chars], len(item.edge_key)),
                "source": (item.source[: policy.max_identity_chars], len(item.source)),
                "target": (item.target[: policy.max_identity_chars], len(item.target)),
                "relationship": (
                    item.relationship[: policy.max_identity_chars],
                    len(item.relationship),
                ),
                "path": [
                    (key[: policy.max_identity_chars], len(key))
                    for key in item.path[: policy.max_hops + 1]
                ],
                "path_length": len(item.path),
                "distance": _bounded_integer(item.distance),
                "pressure": _bounded_integer(item.final_pressure),
                "eligible": item.eligible,
                "component": item.component[:32],
            }
        )
    value = {
        "version": result.config.version,
        "field_seed": (
            None if result.field_seed is None else _bounded_integer(result.field_seed)
        ),
        "selected_landing": (
            None
            if result.selected_landing is None
            else (
                result.selected_landing[: policy.max_identity_chars],
                len(result.selected_landing),
            )
        ),
        "distribution_count": len(result.accessibility_distribution),
        "distribution_prefix": [
            (key[: policy.max_identity_chars], len(key), _bounded_integer(probability))
            for key, probability in result.accessibility_distribution[
                : policy.max_input_contributions
            ]
        ],
        "contribution_count": len(result.contributions),
        "rows": row_digests,
    }
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _valid_path(item: PressureContribution, landing: str) -> bool:
    if not item.edge_key or not item.source or not item.target or not item.path:
        return False
    if item.distance < 0 or item.path[0] != landing or item.path[-1] != item.edge_key:
        return False
    return len(item.path) - 1 == item.distance


def _prepare_candidates(
    result: FieldResult,
    policy: ProjectionPolicy,
    omissions: dict[str, int],
) -> tuple[PressureContribution, ...]:
    if result.config.version != SAA_FIELD_VERSION:
        omissions["unsupported_field_version"] = 1
        return ()
    if not result.field_enabled:
        omissions["field_disabled"] = 1
        return ()
    landing = result.selected_landing
    if landing is not None and len(landing) > policy.max_identity_chars:
        omissions["landing_identity_length_cap"] = 1
        landing = None
    if landing is None:
        omissions["no_selected_landing"] = 1
        return ()

    rows = result.contributions
    if len(rows) > policy.max_input_contributions:
        omissions["input_scan_cap"] = len(rows) - policy.max_input_contributions
    scanned = rows[: policy.max_input_contributions]
    by_key: dict[str, PressureContribution] = {}
    conflicted_keys: set[str] = set()
    for item in scanned:
        if not item.eligible:
            omissions["ineligible_or_quarantined"] = omissions.get(
                "ineligible_or_quarantined", 0
            ) + 1
            continue
        if item.final_pressure <= 0:
            omissions["zero_pressure"] = omissions.get("zero_pressure", 0) + 1
            continue
        if item.final_pressure > result.config.total_budget:
            omissions["pressure_out_of_range"] = omissions.get("pressure_out_of_range", 0) + 1
            continue
        if item.component not in {"landing", "propagated"}:
            omissions["unsupported_component"] = omissions.get("unsupported_component", 0) + 1
            continue
        if item.distance > policy.max_hops:
            omissions["hop_cap"] = omissions.get("hop_cap", 0) + 1
            continue
        if len(item.path) > policy.max_hops + 1:
            omissions["invalid_or_unrooted_path"] = omissions.get(
                "invalid_or_unrooted_path", 0
            ) + 1
            continue
        identifiers = (item.edge_key, item.source, item.target, item.relationship)
        if any(len(value) > policy.max_identity_chars for value in identifiers) or any(
            len(value) > policy.max_identity_chars for value in item.path
        ):
            omissions["identity_length_cap"] = omissions.get("identity_length_cap", 0) + 1
            continue
        if not _valid_path(item, landing):
            omissions["invalid_or_unrooted_path"] = omissions.get(
                "invalid_or_unrooted_path", 0
            ) + 1
            continue
        prior = by_key.get(item.edge_key)
        if item.edge_key in conflicted_keys:
            omissions["conflicting_duplicate_edge_key"] = omissions.get(
                "conflicting_duplicate_edge_key", 0
            ) + 1
            continue
        if prior is not None and (prior.source, prior.target, prior.relationship) != (
            item.source,
            item.target,
            item.relationship,
        ):
            omissions["conflicting_duplicate_edge_key"] = omissions.get(
                "conflicting_duplicate_edge_key", 0
            ) + 1
            by_key.pop(item.edge_key, None)
            conflicted_keys.add(item.edge_key)
            continue
        if prior is not None:
            omissions["duplicate_contribution"] = omissions.get(
                "duplicate_contribution", 0
            ) + 1
            if item.attenuated_pressure > prior.attenuated_pressure or (
                item.attenuated_pressure == prior.attenuated_pressure
                and item.path < prior.path
            ):
                by_key[item.edge_key] = item
        else:
            by_key[item.edge_key] = item

    landing_item = by_key.get(landing)
    if landing_item is None or landing_item.distance != 0:
        omissions["landing_missing_from_selected_contributions"] = 1
        return ()
    others = [item for key, item in by_key.items() if key != landing]
    others.sort(key=lambda item: (item.distance, -item.final_pressure, item.edge_key, item.path))
    return (landing_item, *others)


def _build_projection(
    result: FieldResult,
    labels: Mapping[str, str],
    policy: ProjectionPolicy,
    candidates: tuple[PressureContribution, ...],
    omissions: dict[str, int],
) -> NeighborhoodProjection:
    included: list[ProjectedEdge] = []
    paths: list[ProjectedPath] = []
    nodes: dict[str, ProjectedNode] = {}
    landing = result.selected_landing
    if landing is not None and len(landing) > policy.max_identity_chars:
        landing = None

    for item in candidates:
        if item.distance > policy.max_hops:
            omissions["hop_cap"] = omissions.get("hop_cap", 0) + 1
            continue
        if len(included) >= policy.max_edges:
            omissions["edge_cap"] = omissions.get("edge_cap", 0) + 1
            continue
        if len(paths) >= policy.max_paths:
            omissions["path_cap"] = omissions.get("path_cap", 0) + 1
            continue
        endpoints = (item.source, item.target)
        additions = [key for key in endpoints if key not in nodes]
        if len(nodes) + len(set(additions)) > policy.max_nodes:
            omissions["node_cap"] = omissions.get("node_cap", 0) + 1
            continue

        if item.edge_key == landing:
            role: Literal["landing", "direct", "farther", "cross_link"] = "landing"
        elif item.source in nodes and item.target in nodes:
            role = "cross_link"
        elif item.distance == 1:
            role = "direct"
        else:
            role = "farther"

        for key in endpoints:
            if key in nodes:
                continue
            label = labels.get(key)
            if label is None:
                omissions["missing_node_label"] = omissions.get("missing_node_label", 0) + 1
            elif len(label) > policy.max_label_chars:
                omissions["node_label_length_cap"] = omissions.get(
                    "node_label_length_cap", 0
                ) + 1
                label = None
            nodes[key] = ProjectedNode(key, label)
        included.append(
            ProjectedEdge(
                key=item.edge_key,
                source=item.source,
                relationship=item.relationship,
                target=item.target,
                path=item.path,
                hops=item.distance,
                role=role,
                pressure=item.final_pressure,
                component=item.component,
            )
        )
        paths.append(ProjectedPath(item.edge_key, item.path, item.distance))

    descriptor, descriptor_omissions = _portable_descriptor(
        included, nodes, policy.descriptor_mode, policy.max_serialized_bytes
    )
    projected_landing = landing if any(item.key == landing for item in included) else None
    if landing is not None and projected_landing is None:
        omissions["landing_not_projected"] = omissions.get("landing_not_projected", 0) + 1
    audit_seed = result.field_seed
    if audit_seed is not None and audit_seed.bit_length() > 256:
        omissions["field_seed_integer_cap"] = 1
        audit_seed = None
    projected = NeighborhoodProjection(
        schema_version=PROJECTION_SCHEMA_VERSION,
        field_version=result.config.version,
        field_seed=audit_seed,
        landing_edge_key=projected_landing,
        input_fingerprint=_input_fingerprint(
            result, result.contributions[: policy.max_input_contributions], policy
        ),
        nodes=tuple(nodes.values()),
        edges=tuple(included),
        paths=tuple(paths),
        omissions=tuple(sorted((key, value) for key, value in omissions.items() if value)),
        descriptor_omissions=tuple(sorted(descriptor_omissions.items())),
        portable_descriptor=descriptor,
    )
    return projected


def _portable_descriptor(
    edges: list[ProjectedEdge],
    nodes: Mapping[str, ProjectedNode],
    mode: str,
    max_bytes: int,
) -> tuple[PortableNeighborhoodDescriptor | None, dict[str, int]]:
    if mode == "disabled":
        return None, {}
    relations: list[PortableRelation] = []
    omissions: dict[str, int] = {}
    for edge in edges:
        source = nodes[edge.source].label
        target = nodes[edge.target].label
        relation = edge.relationship.casefold()
        if source is None or target is None:
            omissions["descriptor_label_unavailable"] = omissions.get(
                "descriptor_label_unavailable", 0
            ) + 1
            continue
        if relation not in _PORTABLE_RELATIONS:
            omissions["descriptor_relation_unsupported"] = omissions.get(
                "descriptor_relation_unsupported", 0
            ) + 1
            continue
        relations.append(PortableRelation(source, relation, target, edge.role, edge.hops))
    if not relations:
        return None, omissions
    while relations:
        descriptor = PortableNeighborhoodDescriptor(
            schema_version=PORTABLE_DESCRIPTOR_VERSION,
            relations=tuple(relations),
        )
        if len(_canonical_json(descriptor.to_dict())) <= max_bytes:
            break
        relations.pop()
        omissions["descriptor_serialized_byte_cap"] = omissions.get(
            "descriptor_serialized_byte_cap", 0
        ) + 1
    if not relations:
        return None, omissions
    descriptor = PortableNeighborhoodDescriptor(
        schema_version=PORTABLE_DESCRIPTOR_VERSION,
        relations=tuple(relations),
    )
    return descriptor, omissions


def project_saa_neighborhood(
    result: FieldResult,
    concept_labels: Mapping[str, str],
    *,
    policy: ProjectionPolicy | None = None,
) -> NeighborhoodProjection:
    """Project existing SAA contributions without changing field computation.

    ``concept_labels`` is used only for audit labels and, under the explicitly
    selected ``synthetic_fixture_only`` disclosure mode, the separate portable
    descriptor.  There is no automatic call path from this function to the
    host or persistence layer.
    """

    chosen = policy or ProjectionPolicy()
    omissions: dict[str, int] = {}
    candidates = _prepare_candidates(result, chosen, omissions)
    base_omissions = dict(omissions)
    serialized_drops = 0

    def build() -> NeighborhoodProjection:
        attempt_omissions = dict(base_omissions)
        if serialized_drops:
            attempt_omissions["serialized_byte_cap"] = serialized_drops
        return _build_projection(
            result, concept_labels, chosen, candidates, attempt_omissions
        )

    projection = build()
    while projection.audit_size_bytes > chosen.max_serialized_bytes and projection.edges:
        # Keep the landing until it is the final remaining entry; then fail
        # closed to a minimal empty view if even that cannot fit.
        included_keys = {item.key for item in projection.edges}
        removable = next(
            (
                item.edge_key
                for item in reversed(candidates)
                if item.edge_key in included_keys
            ),
            None,
        )
        if removable is None:
            break
        candidates = tuple(item for item in candidates if item.edge_key != removable)
        serialized_drops += 1
        projection = build()
    if projection.audit_size_bytes <= chosen.max_serialized_bytes:
        return projection

    serialized_drops += len(projection.edges)
    candidates = ()
    return build()


__all__ = [
    "NeighborhoodProjection",
    "PortableNeighborhoodDescriptor",
    "ProjectionPolicy",
    "project_saa_neighborhood",
]
