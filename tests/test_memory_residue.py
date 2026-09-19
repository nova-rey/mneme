from __future__ import annotations

import copy
import json
import math

import pytest

from mneme.memory import (
    GraphSnapshot,
    ResidueValidationError,
    materialize_graph,
    validate_residue,
)


def residue_payload() -> dict[str, object]:
    return {
        "store": True,
        "episode_id": "episode-1",
        "core_concepts": [
            {
                "key": "a",
                "label": "Resource constraint",
                "kind": "concept",
                "source_spans": [{"source_slot": "s0", "start": 0, "end": 8}],
                "confidence": 0.9,
                "salience": 0.5,
                "origin": "model_output",
            },
            {
                "key": "b",
                "label": "Bandwidth",
                "kind": "concept",
                "source_spans": [{"source_slot": "s0", "start": 9, "end": 18}],
                "confidence": 0.8,
                "origin": "model_output",
            },
        ],
        "edge_candidates": [
            {
                "key": "e1",
                "from": "a",
                "to": "b",
                "relationship": "explanation",
                "source_spans": [{"source_slot": "s0", "start": 0, "end": 18}],
                "origin": "model_output",
            }
        ],
        "route_candidates": [
            {
                "key": "r1",
                "edge_keys": ["e1"],
                "source_spans": [{"source_slot": "s0", "start": 0, "end": 18}],
                "origin": "model_output",
            }
        ],
    }


def test_empty_residue_is_valid() -> None:
    residue = validate_residue({}, {"s0": "input"})

    assert residue.core_concepts == ()
    assert residue.edge_candidates == ()
    assert residue.route_candidates == ()


def test_valid_residue_preserves_source_evidence_and_model_origin() -> None:
    residue = validate_residue(residue_payload(), {"s0": "Resource Bandwidth"})

    assert residue.core_concepts[0]["origin"] == "model_output"
    assert residue.core_concepts[0]["source_spans"] == (
        {"source_slot": "s0", "start": 0, "end": 8},
    )
    graph = materialize_graph(residue, snapshot_id="snapshot-a", origin_lineage_id="lineage-a")
    assert graph.edges[0].evidence[0]["source_slot"] == "s0"
    assert graph.edges[0].annotations["origin"] == "model_output"
    json.dumps(graph.edges[0].to_dict())
    with pytest.raises(TypeError):
        graph.edges[0].annotations["origin"] = "external"  # type: ignore[index]


def test_unknown_fields_and_fabricated_source_slots_fail_closed() -> None:
    unknown = residue_payload()
    unknown["unexpected"] = True
    with pytest.raises(ResidueValidationError, match="unknown fields"):
        validate_residue(unknown, {"s0": "Resource Bandwidth"})

    fabricated = residue_payload()
    concepts = fabricated["core_concepts"]
    assert isinstance(concepts, list)
    first = concepts[0]
    assert isinstance(first, dict)
    first["source_spans"] = [{"source_slot": "s9", "start": 0, "end": 3}]
    with pytest.raises(ResidueValidationError, match="fabricated"):
        validate_residue(fabricated, {"s0": "Resource Bandwidth"})


@pytest.mark.parametrize("number", [True, False, math.nan, math.inf, -0.1, 1.1])
def test_confidence_and_salience_require_finite_unit_interval_numbers(number: object) -> None:
    payload = residue_payload()
    concepts = payload["core_concepts"]
    assert isinstance(concepts, list)
    first = concepts[0]
    assert isinstance(first, dict)
    first["confidence"] = number

    with pytest.raises(ResidueValidationError, match="confidence"):
        validate_residue(payload, {"s0": "Resource Bandwidth"})


def test_spans_use_unicode_code_points_and_must_be_nonempty_and_in_bounds() -> None:
    payload = residue_payload()
    concepts = payload["core_concepts"]
    assert isinstance(concepts, list)
    first = concepts[0]
    assert isinstance(first, dict)
    first["source_spans"] = [{"source_slot": "s0", "start": 0, "end": 6}]

    # "é" occupies one Python Unicode code point; this is an in-bounds span.
    validate_residue(payload, {"s0": "éclair123456789012"})

    first["source_spans"] = [{"source_slot": "s0", "start": 2, "end": 2}]
    with pytest.raises(ResidueValidationError, match="start < end"):
        validate_residue(payload, {"s0": "éclair123456789012"})

    first["source_spans"] = [{"source_slot": "s0", "start": 0, "end": 19}]
    with pytest.raises(ResidueValidationError, match="start < end"):
        validate_residue(payload, {"s0": "éclair123456789012"})


def test_relationships_and_routes_require_existing_contiguous_references() -> None:
    payload = residue_payload()
    edges = payload["edge_candidates"]
    assert isinstance(edges, list)
    edges[0]["to"] = "missing"
    with pytest.raises(ResidueValidationError, match="endpoint"):
        validate_residue(payload, {"s0": "Resource Bandwidth"})

    payload = residue_payload()
    payload["core_concepts"].append(  # type: ignore[union-attr]
        {"key": "c", "label": "Context", "kind": "concept"}
    )
    payload["edge_candidates"].append(  # type: ignore[union-attr]
        {"key": "e2", "from": "b", "to": "c", "relationship": "related"}
    )
    payload["route_candidates"][0]["edge_keys"] = ["e2", "e1"]  # type: ignore[index]
    with pytest.raises(ResidueValidationError, match="discontinuous"):
        validate_residue(payload, {"s0": "Resource Bandwidth"})


def test_limits_are_enforced() -> None:
    payload = residue_payload()
    concepts = payload["core_concepts"]
    assert isinstance(concepts, list)
    concepts.extend(
        {"key": str(index), "label": f"concept {index}", "kind": "concept"}
        for index in range(2, 17)
    )
    with pytest.raises(ResidueValidationError, match="more than 16"):
        validate_residue(payload, {"s0": "Resource Bandwidth"})


def test_graph_content_digest_excludes_administrative_snapshot_identity() -> None:
    residue = validate_residue(residue_payload(), {"s0": "Resource Bandwidth"})
    first = materialize_graph(
        residue,
        snapshot_id="snapshot-a",
        origin_lineage_id="lineage-a",
        graph_revision=1,
    )
    second = materialize_graph(
        residue,
        snapshot_id="snapshot-b",
        origin_lineage_id="lineage-b",
        graph_revision=9,
    )

    assert isinstance(first, GraphSnapshot)
    assert first.content_digest == second.content_digest
    assert first.to_dict()["snapshot_id"] != second.to_dict()["snapshot_id"]

    reversed_payload = copy.deepcopy(residue_payload())
    reversed_payload["core_concepts"].reverse()  # type: ignore[union-attr]
    reversed_payload["edge_candidates"].reverse()  # type: ignore[union-attr]
    reversed_payload["route_candidates"].reverse()  # type: ignore[union-attr]
    reordered = materialize_graph(
        validate_residue(reversed_payload, {"s0": "Resource Bandwidth"})
    )
    assert first.content_digest == reordered.content_digest
