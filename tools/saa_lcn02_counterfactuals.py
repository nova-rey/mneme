"""Reproduce model-free fixed-landing and traversal counterfactuals for LCN-02.

This tool only constructs synthetic graphs and calls the existing SAA and
projection functions.  Its incoming-edge traversal is a reachability-only
diagnostic; it does not construct or modify a ``FieldResult``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mneme.development import (
    EdgeState,
    FieldConfig,
    LearnerState,
    ProjectionPolicy,
    compute_saa_field,
    project_saa_neighborhood,
)
from mneme.memory.graph import GraphConcept, GraphEdge

SOURCE_BASE_SHA = "45e251f368f5d1986d6027c484cdf61e7344b61c"
QUERY = "unfamiliar abstract question"
FIXED_LANDING_SEED = 1

FIXED_LABELS = (
    ("a", "shared tools"),
    ("b", "reservation windows"),
    ("c", "return timing"),
    ("d", "availability status"),
    ("e", "clear ownership"),
    ("f", "maintenance"),
    ("g", "safety"),
    ("x", "garden planning"),
    ("y", "seasonal planting"),
    ("z", "community workshop"),
)

FIXED_ROWS_A = (
    ("e0", "a", "b", "supports"),
    ("e1", "b", "c", "enables"),
    ("e2", "c", "d", "causes"),
    ("e3", "b", "e", "constrains"),
    ("e4", "e", "f", "supports"),
    ("remote", "x", "y", "associated_with"),
)

FIXED_ROWS_B = (
    ("e0", "a", "b", "supports"),
    ("e1", "b", "c", "enables"),
    ("e2", "c", "f", "causes"),
    ("e3", "b", "e", "constrains"),
    ("e4", "e", "d", "supports"),
    ("remote", "x", "y", "associated_with"),
)

FIXED_ROWS_REMOTE_CONTROL = (*FIXED_ROWS_A[:-1], ("remote", "x", "z", "associated_with"))


def _concepts(labels: tuple[tuple[str, str], ...]) -> tuple[GraphConcept, ...]:
    return tuple(GraphConcept(key, label, "concept") for key, label in labels)


def _edges(rows: tuple[tuple[str, str, str, str], ...]) -> tuple[GraphEdge, ...]:
    return tuple(
        GraphEdge(key, source, target, relation, ({"synthetic": True},))
        for key, source, target, relation in rows
    )


def _learner(strengths: dict[str, int]) -> LearnerState:
    return LearnerState(
        edge_states=tuple(
            EdgeState(key, accessibility=value, support=value)
            for key, value in sorted(strengths.items())
        )
    )


def _labels(concepts: tuple[GraphConcept, ...]) -> dict[str, str]:
    return {concept.key: concept.label for concept in concepts}


def _json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _result_record(
    concepts: tuple[GraphConcept, ...],
    edges: tuple[GraphEdge, ...],
    learner: LearnerState,
    config: FieldConfig,
    seed: int,
    *,
    query: str = QUERY,
) -> dict[str, Any]:
    result = compute_saa_field(
        query,
        concepts,
        edges,
        learner,
        config=config,
        field_seed=seed,
    )
    projection = project_saa_neighborhood(
        result,
        _labels(concepts),
        policy=ProjectionPolicy(descriptor_mode="synthetic_fixture_only"),
    )
    return {
        "query": query,
        "field_seed": seed,
        "field_result": result.to_dict(),
        "projection_audit": projection.to_audit_dict(),
        "optional_synthetic_descriptor": projection.to_portable_dict(),
    }


def _reachability_counterfactual(
    edges: tuple[GraphEdge, ...],
    eligible_edge_keys: set[str],
    landing_edge_key: str,
    *,
    max_depth: int,
    max_records: int = 64,
) -> dict[str, Any]:
    """Enumerate bounded access paths, retaining semantic edge orientation.

    Both ordinary outgoing navigation and diagnostic incoming navigation are
    recorded. Incoming navigation only makes the opposite endpoint reachable;
    it never asserts the inverse proposition.
    """

    by_key = {edge.key: edge for edge in edges}
    landing = by_key[landing_edge_key]
    queue: deque[tuple[str, int, tuple[str, ...], frozenset[str], frozenset[str]]] = deque(
        (
            endpoint,
            0,
            (landing_edge_key,),
            frozenset((endpoint,)),
            frozenset((landing_edge_key,)),
        )
        for endpoint in (landing.source, landing.target)
    )
    records: list[dict[str, Any]] = []
    while queue and len(records) < max_records:
        node, depth, path, visited_nodes, visited_edges = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in sorted(edges, key=lambda row: row.key):
            if edge.key not in eligible_edge_keys or edge.key in visited_edges:
                continue
            if edge.source == node:
                access_to = edge.target
                navigation = "outgoing"
            elif edge.target == node:
                access_to = edge.source
                navigation = "incoming_access_only"
            else:
                continue
            if access_to in visited_nodes:
                continue
            next_path = (*path, edge.key)
            record = {
                "edge_key": edge.key,
                "semantic_source": edge.source,
                "relationship": edge.relationship,
                "semantic_target": edge.target,
                "navigation_from": node,
                "navigation_to": access_to,
                "navigation_mode": navigation,
                "depth": depth + 1,
                "path_edge_keys": list(next_path),
                "asserts_inverse_semantics": False,
            }
            records.append(record)
            queue.append(
                (
                    access_to,
                    depth + 1,
                    next_path,
                    visited_nodes | {access_to},
                    visited_edges | {edge.key},
                )
            )
            if len(records) >= max_records:
                break
    return {
        "kind": "reachability_only_counterfactual_not_field_result",
        "max_depth": max_depth,
        "max_records": max_records,
        "records": records,
        "truncated": bool(queue),
        "semantic_direction_preserved": True,
        "inverse_relationships_created": False,
    }


def build_receipt() -> dict[str, Any]:
    strengths = {
        "e0": 900_000,
        "e1": 700_000,
        "e2": 600_000,
        "e3": 500_000,
        "e4": 400_000,
        "remote": 200_000,
    }
    concepts = _concepts(FIXED_LABELS)
    learner = _learner(strengths)
    config = FieldConfig(max_depth=3, max_contributors=12)
    rows = {
        "history_a": FIXED_ROWS_A,
        "history_b": FIXED_ROWS_B,
        "history_a_remote_rewire_control": FIXED_ROWS_REMOTE_CONTROL,
    }
    fixed_results: dict[str, Any] = {}
    for name, graph_rows in rows.items():
        edges = _edges(graph_rows)
        fixed_results[name] = {
            "graph": {
                "concepts": [concept.to_dict() for concept in concepts],
                "edges": [edge.to_dict() for edge in edges],
                "sha256": _json_digest(
                    {
                        "concepts": [concept.to_dict() for concept in concepts],
                        "edges": [edge.to_dict() for edge in edges],
                    }
                ),
            },
            "learner_state": learner.to_dict(),
            "config": asdict(config),
            **_result_record(concepts, edges, learner, config, FIXED_LANDING_SEED),
        }

    tested_seeds = tuple(range(6))
    seed_sweep = []
    for seed in tested_seeds:
        landings = {}
        for name in ("history_a", "history_b"):
            result = compute_saa_field(
                QUERY,
                concepts,
                _edges(rows[name]),
                learner,
                config=config,
                field_seed=seed,
            )
            landings[name] = result.selected_landing
        seed_sweep.append({"field_seed": seed, "landings": landings})

    direction_labels = (
        ("a", "landing alpha"),
        ("b", "landing bravo"),
        ("c", "incoming association concept"),
        ("d", "outgoing consequence"),
        ("e", "incoming causal source"),
        ("f", "part concept"),
    )
    direction_rows = (
        ("e0", "a", "b", "supports"),
        ("incoming", "c", "a", "associated_with"),
        ("outgoing", "b", "d", "enables"),
    )
    direction_strengths = {"e0": 900_000, "incoming": 500_000, "outgoing": 500_000}
    direction_concepts = _concepts(direction_labels)
    direction_edges = _edges(direction_rows)
    direction_learner = _learner(direction_strengths)
    direction_config = FieldConfig(max_depth=2, max_contributors=8)
    direction_result = compute_saa_field(
        "unrelated",
        direction_concepts,
        direction_edges,
        direction_learner,
        config=direction_config,
        field_seed=1,
    )
    direction_projection = project_saa_neighborhood(direction_result, _labels(direction_concepts))
    direction_candidates = {key for key, _ in direction_result.accessibility_distribution}
    incoming_counterfactual = _reachability_counterfactual(
        direction_edges,
        direction_candidates,
        direction_result.selected_landing or "",
        max_depth=direction_config.max_depth,
    )

    caution_rows = (
        ("e0", "a", "b", "supports"),
        ("cause_in", "e", "a", "causes"),
        ("part_in", "f", "a", "part_of"),
        ("prevent_out", "b", "d", "prevents"),
    )
    caution_strengths = {key: 500_000 for key, *_ in caution_rows}
    caution_strengths["e0"] = 900_000
    caution_edges = _edges(caution_rows)
    caution_learner = _learner(caution_strengths)
    caution_result = compute_saa_field(
        "unrelated",
        direction_concepts,
        caution_edges,
        caution_learner,
        config=direction_config,
        field_seed=1,
    )
    caution_cf = _reachability_counterfactual(
        caution_edges,
        {key for key, _ in caution_result.accessibility_distribution},
        caution_result.selected_landing or "",
        max_depth=direction_config.max_depth,
    )

    # Re-run the previously published LCN-01 cap/de-dup fixture with the
    # production implementation; the prior receipt supplies the raw pre-dedup
    # two-path witness, which FieldResult does not expose.
    cap_labels = tuple(
        (key, label)
        for key, label in zip(
            "abcdefgh",
            ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"),
            strict=True,
        )
    )
    cap_rows = (
        ("e0", "a", "b", "supports"),
        ("e1", "a", "c", "enables"),
        ("e2", "b", "c", "causes"),
        ("e3", "c", "d", "constrains"),
        ("e4", "a", "e", "supports"),
        ("e5", "b", "f", "prevents"),
        ("e6", "e", "g", "depends_on"),
        ("e7", "f", "h", "retains"),
    )
    cap_concepts = _concepts(cap_labels)
    cap_edges = _edges(cap_rows)
    cap_learner = _learner({key: 800_000 for key, *_ in cap_rows})
    cap_config = FieldConfig(max_depth=2, max_contributors=7)
    cap_result = compute_saa_field(
        "unrelated abstract question",
        cap_concepts,
        cap_edges,
        cap_learner,
        config=cap_config,
        field_seed=14,
    )
    cap_projection = project_saa_neighborhood(cap_result, _labels(cap_concepts))

    return {
        "schema_version": 1,
        "package_id": "SAA-LCN02-FIXED-LANDING",
        "mode": "synthetic_model_free_counterfactuals",
        "source_base_sha": SOURCE_BASE_SHA,
        "archival_amendment": {
            "name": "MNEME_Conceptual_Amendment_Landing_Centered_Neighborhoods_2026-10-15.md",
            "status": "unavailable_in_supplied_environment",
            "handling": "not reconstructed, paraphrased, or attributed",
        },
        "fixed_landing_contrast": {
            "query": QUERY,
            "field_seed": FIXED_LANDING_SEED,
            "seed_search": {
                "performed": True,
                "method": (
                    "bounded exploratory scan of integer seeds 0 through 5; selected the first "
                    "seed yielding e0 in both actual results"
                ),
                "candidate_seeds_tested": list(tested_seeds),
                "common_landing_sweep": seed_sweep,
                "selection_conditioning": (
                    "seed 1 was chosen because both histories selected the required common e0 "
                    "landing; all six tested seeds selected the same edge in A and B, while "
                    "only seeds 1, 3, and 4 landed on e0"
                ),
            },
            "field_config": asdict(config),
            "learner_strengths": strengths,
            "changed_edge_keys_history_a_vs_b": ["e2", "e4"],
            "fixed_edge_keys": ["e0", "e1", "e3", "remote"],
            "histories": fixed_results,
        },
        "disconnected_remote_control": {
            "comparison": "history_a versus history_a_remote_rewire_control",
            "only_changed_edge_key": "remote",
            "result_a": {
                "distribution": fixed_results["history_a"]["field_result"][
                    "accessibility_distribution"
                ],
                "landing": fixed_results["history_a"]["field_result"]["selected_landing"],
                "projection": fixed_results["history_a"]["projection_audit"],
            },
            "remote_rewire": {
                "distribution": fixed_results["history_a_remote_rewire_control"]["field_result"][
                    "accessibility_distribution"
                ],
                "landing": fixed_results["history_a_remote_rewire_control"]["field_result"][
                    "selected_landing"
                ],
                "projection": fixed_results["history_a_remote_rewire_control"]["projection_audit"],
            },
        },
        "directionality": {
            "fixture": {
                "concepts": [concept.to_dict() for concept in direction_concepts],
                "edges": [edge.to_dict() for edge in direction_edges],
                "learner_state": direction_learner.to_dict(),
                "config": asdict(direction_config),
                "query": "unrelated",
                "field_seed": 1,
                "field_result": direction_result.to_dict(),
                "projection_audit": direction_projection.to_audit_dict(),
                "counterfactual": incoming_counterfactual,
            },
            "directional_relation_caution": {
                "concepts": [concept.to_dict() for concept in direction_concepts],
                "edges": [edge.to_dict() for edge in caution_edges],
                "learner_state": caution_learner.to_dict(),
                "field_result": caution_result.to_dict(),
                "counterfactual": caution_cf,
                "warning": (
                    "incoming navigation preserves C causes A and F part_of A; it does not "
                    "assert A causes C or A part_of F"
                ),
            },
        },
        "cap_and_attenuation": {
            "source_receipt": (
                "docs/receipts/MNEME_SAA_Neighborhood_Projection_Baseline_20261015.json"
                "#/dedup_and_cap_fixture"
            ),
            "prior_raw_path_witness": [
                ["e0", "e1", "e3"],
                ["e0", "e2", "e3"],
            ],
            "prior_raw_path_witness_provenance": (
                "LCN-01 receipt; raw propagation alternatives are not exposed by FieldResult"
            ),
            "fixture": {
                "concepts": [concept.to_dict() for concept in cap_concepts],
                "edges": [edge.to_dict() for edge in cap_edges],
                "learner_state": cap_learner.to_dict(),
                "config": asdict(cap_config),
                "query": "unrelated abstract question",
                "field_seed": 14,
                "field_result": cap_result.to_dict(),
                "projection_audit": cap_projection.to_audit_dict(),
            },
        },
        "interpretation": {
            "observed": [
                "LCN02 fixed landing results come from actual compute_saa_field calls and both "
                "select e0 with seed 1.",
                "The fixed histories have identical vocabulary, edge inventory, learner "
                "strengths, and distribution by edge key; only e2/e4 endpoints differ.",
                "The disconnected remote-edge rewire changes no landing or projected local view.",
                "Production propagation omits the positive incoming edge because adjacency is "
                "keyed only by edge.source.",
                "The counterfactual only describes bounded reachability and retains each edge's "
                "original semantic source, relation, and target.",
                "The cap fixture omits e7 upstream; projection reflects contributions supplied "
                "by FieldResult and does not recover e7 or the alternate deduplicated e3 path.",
            ],
            "unproven": [
                "No preserved developmental history was changed or analyzed.",
                "No frequency/prevalence of incoming-edge loss is established.",
                "No model uptake or behavioral benefit is established.",
                "No relation-specific inverse/access policy is approved by this diagnostic.",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    payload = build_receipt()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
