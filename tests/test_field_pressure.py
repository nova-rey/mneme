from __future__ import annotations

import pytest

from mneme.development import (
    FIXED_SCALE,
    LEGACY_FIELD_VERSION,
    EdgeState,
    FieldConfig,
    LearnerState,
    compute_field,
)
from mneme.memory.graph import GraphConcept, GraphEdge


def _graph(*labels: tuple[str, str], edges: tuple[tuple[str, str, str], ...]):
    concepts = tuple(GraphConcept(key, label, "concept") for key, label in labels)
    graph_edges = tuple(
        GraphEdge(key, source, target, relation, ({"source_slot": "s0"},))
        for key, source, target, relation in edges
    )
    return concepts, graph_edges


def _state(*keys: str, strength: int = 800_000) -> LearnerState:
    return LearnerState(
        edge_states=tuple(
            sorted(
                (EdgeState(key, accessibility=strength, support=strength) for key in keys),
                key=lambda item: item.key,
            ),
        )
    )


def test_direct_neighbor_has_bounded_pressure_and_active_concept():
    concepts, edges = _graph(
        ("a", "drip irrigation"),
        ("b", "soil moisture"),
        edges=(("e1", "a", "b", "causes"),),
    )
    result = compute_field("drip method", concepts, edges, _state("e1"))
    assert result.active_concepts[0].initial_activation > 0
    assert result.contributions[0].final_pressure > 0
    assert result.total_pressure <= FIXED_SCALE
    assert "Potentially accessible framings:" in result.payload


def test_multi_hop_attenuates_and_is_bounded():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "bridge"), ("c", "omega"),
        edges=(("e1", "a", "b", "causes"), ("e2", "b", "c", "enables")),
    )
    result = compute_field("alpha", concepts, edges, _state("e1", "e2"))
    by_edge = {item.edge_key: item for item in result.contributions}
    assert by_edge["e1"].final_pressure > by_edge["e2"].final_pressure
    assert result.total_pressure <= FIXED_SCALE


def test_two_contributors_and_dense_graph_respect_budget():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("x", "xray"), ("y", "yield"),
        edges=(
            ("e1", "a", "x", "supports"), ("e2", "a", "y", "supports"),
            ("e3", "b", "x", "supports"), ("e4", "b", "y", "supports"),
        ),
    )
    result = compute_field(
        "alpha beta", concepts, edges, _state("e1", "e2", "e3", "e4"),
        config=FieldConfig(max_contributors=3),
    )
    assert len(result.contributions) == 3
    assert result.total_pressure <= FIXED_SCALE
    assert len(result.payload) <= 900


def test_quarantined_and_unrelated_context_apply_no_pressure():
    concepts, edges = _graph(
        ("a", "drip irrigation"),
        ("b", "moisture"),
        edges=(("e1", "a", "b", "causes"),),
    )
    quarantined = compute_field(
        "drip method", concepts, edges, _state("e1"), quarantined_edges={"e1"}
    )
    unrelated = compute_field("airplane music", concepts, edges, _state("e1"))
    assert quarantined.total_pressure == 0
    assert quarantined.contributions[0].eligibility_reason == "quarantined"
    assert unrelated.total_pressure > 0
    assert all(item.component == "background" for item in unrelated.contributions)
    assert "Potentially accessible framings:" in unrelated.payload


def test_legacy_v1_retains_relevance_gated_zero_field_behavior():
    concepts, edges = _graph(
        ("a", "drip irrigation"),
        ("b", "moisture"),
        edges=(("e1", "a", "b", "causes"),),
    )
    result = compute_field(
        "airplane music",
        concepts,
        edges,
        _state("e1"),
        config=FieldConfig(version=LEGACY_FIELD_VERSION),
    )
    assert result.total_pressure == 0
    assert result.config.version == LEGACY_FIELD_VERSION


def test_contextual_pressure_dominates_weak_background():
    concepts, edges = _graph(
        ("a", "drip irrigation"),
        ("b", "soil moisture"),
        ("c", "aviation"),
        ("d", "failure monitoring"),
        edges=(
            ("e1", "a", "b", "causes"),
            ("e2", "c", "d", "supports"),
        ),
    )
    result = compute_field("drip method", concepts, edges, _state("e1", "e2"))
    accepted = [item for item in result.contributions if item.eligible]
    assert accepted[0].edge_key == "e1"
    assert accepted[0].component == "contextual"
    assert any(item.component == "background" for item in accepted)


def test_cold_start_has_no_background_field():
    concepts, edges = _graph(
        ("a", "alpha"),
        ("b", "beta"),
        edges=(("e1", "a", "b", "causes"),),
    )
    result = compute_field("alpha", concepts, edges, LearnerState())
    assert result.total_pressure == 0
    assert result.payload == ""


def test_exploration_is_weighted_bounded_and_replayable():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"), ("d", "delta"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "supports"),
            ("e3", "c", "d", "supports"),
        ),
    )
    config = FieldConfig(exploration="on", max_contributors=1)
    first = compute_field(
        "unrelated", concepts, edges, _state("e1", "e2", "e3"),
        config=config, field_seed=19,
    )
    second = compute_field(
        "unrelated", concepts, edges, _state("e1", "e2", "e3"),
        config=config, field_seed=19,
    )
    assert first.to_dict() == second.to_dict()
    assert first.field_seed == 19
    assert sum(item.exploration_selected for item in first.contributions) <= 1
    assert first.total_pressure <= config.total_budget


def test_exploration_requires_separate_field_seed():
    concepts, edges = _graph(
        ("a", "alpha"),
        ("b", "beta"),
        edges=(("e1", "a", "b", "supports"),),
    )
    with pytest.raises(ValueError, match="field_seed"):
        compute_field(
            "unrelated",
            concepts,
            edges,
            _state("e1"),
            config=FieldConfig(exploration="on"),
        )


def test_negative_consequence_does_not_create_positive_pressure():
    concepts, edges = _graph(("a", "alpha"), ("b", "beta"), edges=(("e1", "a", "b", "causes"),))
    state = LearnerState(
        edge_states=(EdgeState("e1", accessibility=100_000, support=100_000, consequence=-250_000),)
    )
    result = compute_field("alpha", concepts, edges, state)
    assert result.total_pressure == 0


def test_replay_is_identical_and_zero_field_is_valid_result():
    concepts, edges = _graph(("a", "alpha"), ("b", "beta"), edges=(("e1", "a", "b", "causes"),))
    state = _state("e1")
    first = compute_field("alpha", concepts, edges, state)
    second = compute_field("alpha", concepts, edges, state)
    assert first.to_dict() == second.to_dict()
    disabled = compute_field("alpha", concepts, edges, state, field_enabled=False)
    assert not disabled.field_enabled
    assert disabled.total_pressure == 0
