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
from mneme.memory.residue import admit_residue_items, normalize_relationship_items


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
                "confidence": 0.8,
                "origin": "model_output",
            }
        ],
        "route_candidates": [
            {
                "key": "r1",
                "edge_keys": ["e1"],
                "source_spans": [{"source_slot": "s0", "start": 0, "end": 18}],
                "confidence": 0.8,
                "origin": "model_output",
            }
        ],
    }


def test_empty_residue_is_valid() -> None:
    residue = validate_residue({}, {"s0": "input"})

    assert residue.core_concepts == ()
    assert residue.edge_candidates == ()
    assert residue.route_candidates == ()


def test_rich_language_can_yield_empty_residue_without_literalizing_metaphor() -> None:
    source = "The kitchen holds you; the rest is decorative language."
    residue = validate_residue({}, {"s0": source}, require_evidence_quotes=True)
    assert residue.core_concepts == ()
    assert residue.edge_candidates == ()


def test_mixed_literal_and_figurative_material_keeps_only_supported_edge() -> None:
    source = "The routine became a grounding ritual. The kitchen holds you."
    payload = {
        "core_concepts": [
            {
                "key": "routine",
                "label": "routine",
                "kind": "behavior",
                "confidence": 0.92,
                "evidence": [{"source": "s0", "evidence": "The routine"}],
            },
            {
                "key": "ritual",
                "label": "grounding ritual",
                "kind": "pattern",
                "confidence": 0.91,
                "evidence": [{"source": "s0", "evidence": "grounding ritual"}],
            },
            {
                "key": "kitchen",
                "label": "kitchen",
                "kind": "object",
                "confidence": 0.88,
                "evidence": [{"source": "s0", "evidence": "The kitchen"}],
            },
            {
                "key": "person",
                "label": "you",
                "kind": "person",
                "confidence": 0.88,
                "evidence": [{"source": "s0", "evidence": "you"}],
            },
        ],
        "edge_candidates": [
            {
                "key": "e1",
                "from": "routine",
                "to": "ritual",
                "relationship": "association",
                "confidence": 0.92,
                "evidence": [{"source": "s0", "evidence": "became a grounding ritual"}],
            },
            {
                "key": "e2",
                "from": "kitchen",
                "to": "person",
                "relationship": "literalizes",
                "confidence": 0.91,
                "evidence": [{"source": "s0", "evidence": "The kitchen holds you"}],
            },
        ],
    }
    normalized, decisions = normalize_relationship_items(payload)
    residue = validate_residue(normalized, {"s0": source}, require_evidence_quotes=True)
    assert [edge["key"] for edge in residue.edge_candidates] == ["e1"]
    assert any(
        decision["kind"] == "unsupported_relationship" and decision["key"] == "e2"
        for decision in decisions
    )


def test_abstract_but_supported_association_is_admissible() -> None:
    source = "The routine became a grounding ritual."
    payload = {
        "core_concepts": [
            {
                "key": "routine",
                "label": "routine",
                "kind": "behavior",
                "confidence": 0.9,
                "evidence": [{"source": "s0", "evidence": "The routine"}],
            },
            {
                "key": "ritual",
                "label": "grounding ritual",
                "kind": "pattern",
                "confidence": 0.9,
                "evidence": [{"source": "s0", "evidence": "grounding ritual"}],
            },
        ],
        "edge_candidates": [
            {
                "key": "e1",
                "from": "routine",
                "to": "ritual",
                "relationship": "association",
                "confidence": 0.9,
                "evidence": [{"source": "s0", "evidence": "became a grounding ritual"}],
            }
        ],
    }
    residue = validate_residue(payload, {"s0": source}, require_evidence_quotes=True)
    assert residue.edge_candidates[0]["relationship"] == "association"


def _capacity_concept(index: int, *, confidence: float = 0.9) -> dict[str, object]:
    word = f"concept-{index:02d}"
    return {
        "key": f"c{index}",
        "label": word,
        "kind": "concept",
        "evidence": [{"source": "s0", "evidence": word}],
        "confidence": confidence,
    }


def test_capacity_admits_sixteen_of_seventeen_valid_concepts_without_repair() -> None:
    payload = {"core_concepts": [_capacity_concept(index) for index in range(17)]}
    normalized, decisions = admit_residue_items(
        payload,
        {"s0": " ".join(f"concept-{index:02d}" for index in range(17))},
        require_evidence_quotes=True,
    )
    assert len(normalized["core_concepts"]) == 16
    assert sum(decision["kind"] == "not_admitted_capacity" for decision in decisions) == 1
    residue = validate_residue(
        normalized,
        {"s0": " ".join(f"concept-{index:02d}" for index in range(17))},
        require_evidence_quotes=True,
    )
    assert len(residue.core_concepts) == 16


def test_capacity_applies_to_relationships_and_routes() -> None:
    source = "a b"
    concepts = [
        {
            "key": "a",
            "label": "a",
            "kind": "concept",
            "evidence": [{"source": "s0", "evidence": "a"}],
            "confidence": 0.9,
        },
        {
            "key": "b",
            "label": "b",
            "kind": "concept",
            "evidence": [{"source": "s0", "evidence": "b"}],
            "confidence": 0.9,
        },
    ]
    edges = [
        {
            "key": f"e{i}",
            "from": "a",
            "to": "b",
            "relationship": "supports",
            "context": [f"ctx-{i}"],
            "evidence": [{"source": "s0", "evidence": "a"}],
            "confidence": 0.9,
        }
        for i in range(26)
    ]
    payload = {"core_concepts": concepts, "edge_candidates": edges}
    normalized, decisions = admit_residue_items(
        payload, {"s0": source}, require_evidence_quotes=True
    )
    assert len(normalized["edge_candidates"]) == 24
    assert sum(decision["kind"] == "not_admitted_capacity" for decision in decisions) == 2
    route_payload = {
        "core_concepts": concepts,
        "edge_candidates": [edges[0]],
        "route_candidates": [
            {
                "key": f"r{i}",
                "edge_keys": ["e0"],
                "context": [f"route-{i}"],
                "evidence": [{"source": "s0", "evidence": "a"}],
                "confidence": 0.9,
            }
            for i in range(9)
        ],
    }
    route_normalized, route_decisions = admit_residue_items(
        route_payload, {"s0": source}, require_evidence_quotes=True
    )
    assert len(route_normalized["route_candidates"]) == 8
    assert sum(decision["kind"] == "not_admitted_capacity" for decision in route_decisions) == 1


def test_malformed_candidate_does_not_discard_unrelated_valid_candidate() -> None:
    payload = {
        "core_concepts": [
            _capacity_concept(1),
            {"key": "bad", "label": "bad", "kind": "not-approved", "confidence": 0.9},
        ]
    }
    normalized, decisions = admit_residue_items(
        payload, {"s0": "concept-01"}, require_evidence_quotes=True
    )
    assert [item["key"] for item in normalized["core_concepts"]] == ["c1"]
    assert decisions[0]["kind"] == "rejected_item"


def test_duplicate_candidates_are_canonicalized_and_selection_ignores_insertion_order() -> None:
    first = [
        _capacity_concept(1, confidence=0.8),
        _capacity_concept(2, confidence=0.9),
        _capacity_concept(1, confidence=0.8),
    ]
    second = list(reversed(first))
    sources = {"s0": "concept-01 concept-02"}
    one, decisions_one = admit_residue_items(
        {"core_concepts": first}, sources, require_evidence_quotes=True
    )
    two, decisions_two = admit_residue_items(
        {"core_concepts": second}, sources, require_evidence_quotes=True
    )
    assert one["core_concepts"] == two["core_concepts"]
    assert any(decision["kind"] == "duplicate_item" for decision in decisions_one)
    assert any(decision["kind"] == "duplicate_item" for decision in decisions_two)


def test_normalization_rejects_discontinuous_optional_route_without_losing_edges() -> None:
    payload = {
        "core_concepts": [
            {"key": "a", "label": "A", "kind": "concept", "confidence": 0.9},
            {"key": "b", "label": "B", "kind": "concept", "confidence": 0.9},
            {"key": "c", "label": "C", "kind": "concept", "confidence": 0.9},
        ],
        "edge_candidates": [
            {"key": "e1", "from": "a", "to": "b", "relationship": "supports", "confidence": 0.9},
            {"key": "e2", "from": "c", "to": "a", "relationship": "supports", "confidence": 0.9},
        ],
        "route_candidates": [{"key": "r1", "edge_keys": ["e1", "e2"], "confidence": 0.9}],
    }
    normalized, decisions = normalize_relationship_items(payload)
    assert len(normalized["edge_candidates"]) == 2
    assert normalized["route_candidates"] == []
    assert decisions[-1]["kind"] == "invalid_route_item"


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


@pytest.mark.parametrize(
    ("source", "quotation", "expected"),
    [
        ("Resource Bandwidth", "Resource", (0, 8)),
        ("café 😀 — ready", "😀", (5, 6)),
        ("It’s “ready”", "“ready”", (5, 12)),
        ("starts here", "starts", (0, 6)),
        ("ends here", "here", (5, 9)),
    ],
)
def test_model_evidence_quote_resolves_to_unicode_code_point_span(
    source: str, quotation: str, expected: tuple[int, int]
) -> None:
    payload = {
        "core_concepts": [
            {
                "key": "a",
                "label": "Evidence",
                "kind": "concept",
                "evidence": [{"source": "s0", "evidence": quotation}],
                "confidence": 0.9,
            }
        ]
    }

    residue = validate_residue(payload, {"s0": source})

    assert residue.core_concepts[0]["source_spans"] == (
        {"source_slot": "s0", "start": expected[0], "end": expected[1]},
    )
    assert "evidence" not in residue.core_concepts[0]


@pytest.mark.parametrize(
    ("source", "evidence", "error"),
    [
        ("Resource Bandwidth", "", "must not be empty"),
        ("Resource Bandwidth", "resource bandwidth", "does not occur verbatim"),
        ("Resource Bandwidth", "Missing", "does not occur verbatim"),
    ],
)
def test_model_evidence_quote_must_be_nonempty_and_verbatim(
    source: str, evidence: str, error: str
) -> None:
    payload = {
        "core_concepts": [
            {
                "key": "a",
                "label": "Evidence",
                "kind": "concept",
                "evidence": [{"source": "s0", "evidence": evidence}],
                "confidence": 0.9,
            }
        ]
    }

    with pytest.raises(ResidueValidationError, match=error):
        validate_residue(payload, {"s0": source})


def test_model_evidence_quote_rejects_missing_slot_and_ambiguous_occurrence() -> None:
    def payload(source: str, quotation: str) -> dict[str, object]:
        return {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "Evidence",
                    "kind": "concept",
                    "evidence": [{"source": source, "evidence": quotation}],
                    "confidence": 0.9,
                }
            ]
        }

    with pytest.raises(ResidueValidationError, match="fabricated or unavailable"):
        validate_residue(payload("s9", "Resource"), {"s0": "Resource Bandwidth"})
    with pytest.raises(ResidueValidationError, match="does not occur verbatim"):
        validate_residue(
            payload("s1", "Resource"),
            {"s0": "Resource Bandwidth", "s1": "Other source"},
        )
    with pytest.raises(ResidueValidationError, match="ambiguous"):
        validate_residue(payload("s0", "alpha"), {"s0": "alpha alpha"})
    with pytest.raises(ResidueValidationError, match="ambiguous"):
        validate_residue(payload("s0", "aa"), {"s0": "aaa"})


def test_model_evidence_quote_resolves_multiple_unique_spans_deterministically() -> None:
    payload = {
        "core_concepts": [
            {
                "key": "a",
                "label": "Evidence",
                "kind": "concept",
                "evidence": [
                    {"source": "s0", "evidence": "Resource"},
                    {"source": "s0", "evidence": "Bandwidth"},
                ],
                "confidence": 0.9,
            }
        ]
    }
    sources = {"s0": "Resource Bandwidth"}

    first = validate_residue(payload, sources)
    second = validate_residue(payload, sources)

    expected = (
        {"source_slot": "s0", "start": 0, "end": 8},
        {"source_slot": "s0", "start": 9, "end": 18},
    )
    assert first.core_concepts[0]["source_spans"] == expected
    assert second.core_concepts[0]["source_spans"] == expected
    assert first.content_digest == second.content_digest


def test_model_evidence_quote_cannot_be_mixed_with_numeric_spans() -> None:
    payload = {
        "core_concepts": [
            {
                "key": "a",
                "label": "Evidence",
                "kind": "concept",
                "evidence": [{"source": "s0", "evidence": "Resource"}],
                "source_spans": [{"source_slot": "s0", "start": 0, "end": 8}],
                "confidence": 0.9,
            }
        ]
    }

    with pytest.raises(ResidueValidationError, match="only one of evidence"):
        validate_residue(payload, {"s0": "Resource Bandwidth"})


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


@pytest.mark.parametrize(
    ("field", "index", "missing"),
    [
        ("core_concepts", 0, "source_spans"),
        ("edge_candidates", 0, "source_spans"),
        ("route_candidates", 0, "source_spans"),
        ("core_concepts", 0, "confidence"),
        ("edge_candidates", 0, "confidence"),
        ("route_candidates", 0, "confidence"),
    ],
)
def test_graph_material_requires_source_spans_and_confidence(
    field: str, index: int, missing: str
) -> None:
    payload = residue_payload()
    records = payload[field]
    assert isinstance(records, list)
    records[index].pop(missing)  # type: ignore[union-attr]

    with pytest.raises(ResidueValidationError, match="graph material requires"):
        validate_residue(payload, {"s0": "Resource Bandwidth"})


@pytest.mark.parametrize("confidence", [0.0, 0.69, 0.699999])
def test_graph_material_below_admission_threshold_is_rejected(confidence: float) -> None:
    payload = residue_payload()
    concepts = payload["core_concepts"]
    assert isinstance(concepts, list)
    concepts[0]["confidence"] = confidence

    with pytest.raises(ResidueValidationError, match="admission threshold 0.70"):
        validate_residue(payload, {"s0": "Resource Bandwidth"})


def test_graph_material_at_admission_threshold_is_accepted() -> None:
    payload = residue_payload()
    concepts = payload["core_concepts"]
    assert isinstance(concepts, list)
    concepts[0]["confidence"] = 0.70

    residue = validate_residue(payload, {"s0": "Resource Bandwidth"})
    assert residue.core_concepts[0]["confidence"] == 0.70


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
        {
            "key": "c",
            "label": "Context",
            "kind": "concept",
            "source_spans": [{"source_slot": "s0", "start": 0, "end": 7}],
            "confidence": 0.8,
        }
    )
    payload["edge_candidates"].append(  # type: ignore[union-attr]
        {
            "key": "e2",
            "from": "b",
            "to": "c",
            "relationship": "related",
            "source_spans": [{"source_slot": "s0", "start": 0, "end": 18}],
            "confidence": 0.8,
        }
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
    reordered = materialize_graph(validate_residue(reversed_payload, {"s0": "Resource Bandwidth"}))
    assert first.content_digest == reordered.content_digest
