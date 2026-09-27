from __future__ import annotations

import pytest

from mneme.development import (
    FIXED_SCALE,
    LEGACY_FIELD_VERSION,
    SAA_FIELD_VERSION,
    EdgeState,
    FieldConfig,
    LearnerState,
    compute_field,
    compute_saa_field,
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
    assert "drip irrigation" not in result.payload.casefold()
    assert "soil moisture" not in result.payload.casefold()
    assert "causes" not in result.payload.casefold()


def test_renderer_exposes_abstract_tendencies_not_graph_labels():
    concepts, edges = _graph(
        ("a", "aviation"),
        ("b", "redundancy"),
        edges=(("e1", "a", "b", "supports"),),
    )
    result = compute_field("unrelated", concepts, edges, _state("e1"))
    assert result.payload.startswith("Potentially accessible framings:")
    assert "aviation" not in result.payload.casefold()
    assert "redundancy" not in result.payload.casefold()
    assert "supports" not in result.payload.casefold()
    assert "Supporting components" in result.payload
    assert len(result.payload) <= 900


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


def test_saa_cold_start_and_required_seed_are_fail_closed():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), edges=(("e1", "a", "b", "supports"),)
    )
    empty = compute_saa_field("unrelated", concepts, edges, LearnerState(), field_seed=7)
    assert empty.config.version == SAA_FIELD_VERSION
    assert empty.selected_landing is None
    assert empty.accessibility_distribution == ()
    with pytest.raises(ValueError, match="field_seed"):
        compute_saa_field("alpha", concepts, edges, _state("e1"))


def test_saa_replays_and_keeps_novel_context_flatter():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "supports"),
        ),
    )
    state = _state("e1", "e2")
    familiar = compute_saa_field("alpha", concepts, edges, state, field_seed=19)
    novel = compute_saa_field("unrelated topic", concepts, edges, state, field_seed=19)
    replay = compute_saa_field("unrelated topic", concepts, edges, state, field_seed=19)
    assert familiar.distribution_flatness < novel.distribution_flatness
    assert novel.to_dict() == replay.to_dict()
    assert novel.selected_landing is not None
    assert novel.landing_ticket is not None


def test_saa_same_seed_can_land_differently_for_different_history():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "rhythm"),
        ),
    )
    first = compute_saa_field(
        "unrelated", concepts, edges, _state("e1", strength=900_000), field_seed=3
    )
    second = compute_saa_field(
        "unrelated", concepts, edges, _state("e2", strength=900_000), field_seed=3
    )
    assert first.selected_landing != second.selected_landing


def test_saa_renderer_preserves_directional_neighborhood_shape():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"),
        edges=(("e1", "a", "b", "supports"),),
    )
    support = compute_saa_field("unrelated", concepts, edges, _state("e1"), field_seed=5)
    concepts2, edges2 = _graph(
        ("a", "alpha"), ("b", "beta"),
        edges=(("e1", "a", "b", "rhythm"),),
    )
    rhythm = compute_saa_field("unrelated", concepts2, edges2, _state("e1"), field_seed=5)
    assert support.payload != rhythm.payload
    assert "alpha" not in support.payload.casefold()
    assert "beta" not in rhythm.payload.casefold()
    assert len(support.payload) <= 900


def test_saa_propagation_is_bounded_and_quarantine_blocks_landing():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "supports"),
        ),
    )
    state = _state("e1", "e2")
    result = compute_saa_field("unrelated", concepts, edges, state, field_seed=4)
    accepted = [item for item in result.contributions if item.eligible]
    assert len(accepted) <= 4
    assert result.total_pressure <= FIXED_SCALE
    blocked = compute_saa_field(
        "unrelated", concepts, edges, state, quarantined_edges={"e1", "e2"}, field_seed=4
    )
    assert blocked.selected_landing is None
    assert blocked.total_pressure == 0


def test_saa_requires_a_dedicated_field_seed_and_has_a_version():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), edges=(("e1", "a", "b", "supports"),)
    )
    state = _state("e1")
    with pytest.raises(ValueError, match="field_seed"):
        compute_saa_field("unrelated", concepts, edges, state)
    result = compute_saa_field("unrelated", concepts, edges, state, field_seed=4)
    assert result.config.version == SAA_FIELD_VERSION
    assert result.field_seed == 4


def test_saa_cold_start_has_no_fabricated_landing():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), edges=(("e1", "a", "b", "supports"),)
    )
    result = compute_saa_field("alpha", concepts, edges, LearnerState(), field_seed=1)
    assert result.accessibility_distribution == ()
    assert result.selected_landing is None
    assert result.total_pressure == 0


def test_saa_novel_context_flattens_but_does_not_erase_history():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "depends_on"),
            ("e3", "c", "a", "rhythm"),
        ),
    )
    state = _state("e1", "e2", "e3")
    familiar = compute_saa_field("alpha", concepts, edges, state, field_seed=7)
    novel = compute_saa_field("unrelated", concepts, edges, state, field_seed=7)
    assert familiar.distribution_flatness < novel.distribution_flatness
    assert novel.accessibility_distribution
    assert novel.total_pressure > 0


def test_saa_same_seed_replays_and_different_history_changes_pay_table():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "depends_on"),
        ),
    )
    first = compute_saa_field("unrelated", concepts, edges, _state("e1", "e2"), field_seed=11)
    replay = compute_saa_field("unrelated", concepts, edges, _state("e1", "e2"), field_seed=11)
    altered = compute_saa_field("unrelated", concepts, edges, _state("e1"), field_seed=11)
    assert first.to_dict() == replay.to_dict()
    assert first.selected_landing == replay.selected_landing
    assert first.accessibility_distribution != altered.accessibility_distribution


def test_introspection_adjustment_changes_production_saa_odds_without_new_edge():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"), ("d", "delta"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "c", "d", "supports"),
        ),
    )
    state = _state("e1", "e2")
    before = compute_saa_field("unrelated", concepts, edges, state, field_seed=7)
    after = compute_saa_field(
        "unrelated", concepts, edges, state, field_seed=7,
        accessibility_adjustments={"e1": 200_000},
    )
    assert (
        dict(before.accessibility_distribution)["e1"]
        < dict(after.accessibility_distribution)["e1"]
    )
    assert {item.edge_key for item in after.contributions} <= {"e1", "e2"}


def test_saa_different_field_seed_can_land_differently():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "depends_on"),
        ),
    )
    state = _state("e1", "e2")
    landings = {
        compute_saa_field("unrelated", concepts, edges, state, field_seed=seed).selected_landing
        for seed in range(20)
    }
    assert len(landings) > 1


def test_saa_quarantine_removes_candidate_from_distribution():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "depends_on"),
        ),
    )
    result = compute_saa_field(
        "unrelated", concepts, edges, _state("e1", "e2"),
        quarantined_edges={"e1"}, field_seed=2,
    )
    assert "e1" not in dict(result.accessibility_distribution)
    assert result.selected_landing == "e2"


def test_saa_local_propagation_attenuates_and_stays_bounded():
    concepts, edges = _graph(
        ("a", "alpha"), ("b", "beta"), ("c", "gamma"), ("d", "delta"),
        edges=(
            ("e1", "a", "b", "supports"),
            ("e2", "b", "c", "depends_on"),
            ("e3", "c", "d", "rhythm"),
        ),
    )
    config = FieldConfig(version=SAA_FIELD_VERSION, max_depth=2, max_contributors=4)
    result = compute_saa_field(
        "alpha", concepts, edges, _state("e1", "e2", "e3"), config=config, field_seed=0
    )
    by_edge = {item.edge_key: item for item in result.contributions}
    assert result.total_pressure <= config.total_budget
    assert result.selected_landing is not None
    assert by_edge[result.selected_landing].component == "landing"
    propagated = [
        item for item in by_edge.values()
        if item.edge_key != result.selected_landing
    ]
    assert all(item.distance <= config.max_depth for item in propagated)
    assert all(
        item.final_pressure < by_edge[result.selected_landing].final_pressure
        for item in propagated
    )


def test_saa_renderer_distinguishes_directional_neighborhoods_without_labels():
    concepts, supports = _graph(
        ("a", "redundancy"), ("b", "fallback"),
        edges=(("e1", "a", "b", "supports"),),
    )
    _, rhythm = _graph(
        ("a", "rhythm"), ("b", "variation"),
        edges=(("e1", "a", "b", "rhythm"),),
    )
    state = _state("e1")
    first = compute_saa_field("unrelated", concepts, supports, state, field_seed=0)
    second = compute_saa_field("unrelated", concepts, rhythm, state, field_seed=0)
    assert first.payload != second.payload
    for payload in (first.payload, second.payload):
        assert "redundancy" not in payload.casefold()
        assert "rhythm" not in payload.casefold()
        assert "e1" not in payload


def test_low_information_overlap_does_not_make_novelty_familiar():
    concepts, edges = _graph(
        ("it", "It"), ("a", "meaningful process"), ("b", "outcome"),
        edges=(
            ("e1", "it", "b", "supports"),
            ("e2", "a", "b", "supports"),
        ),
    )
    result = compute_saa_field("it", concepts, edges, _state("e1", "e2"), field_seed=17)
    it = next(item for item in result.active_concepts if item.label == "It")
    assert it.contextual_activation == 0
    assert result.novelty > 0


def test_meaningful_multiword_overlap_still_establishes_context():
    concepts, edges = _graph(
        ("a", "shared process"), ("b", "outcome"),
        edges=(("e1", "a", "b", "supports"),),
    )
    result = compute_saa_field(
        "that shared process is useful", concepts, edges, _state("e1"), field_seed=19
    )
    assert result.active_concepts[0].contextual_activation > 0
    assert result.novelty < 1_000_000


def test_renderer_preserves_generic_facets_without_thread_specific_labels():
    concepts, edges = _graph(
        ("a", "budget constraint"), ("b", "fallback option"),
        edges=(("e1", "a", "b", "supports"),),
    )
    first = compute_saa_field("unrelated", concepts, edges, _state("e1"), field_seed=3)
    concepts2, edges2 = _graph(
        ("a", "shared coordination"), ("b", "trust schedule"),
        edges=(("e1", "a", "b", "supports"),),
    )
    second = compute_saa_field("unrelated", concepts2, edges2, _state("e1"), field_seed=3)
    assert first.payload != second.payload
    assert "budget constraint" not in first.payload.casefold()
    assert "shared coordination" not in second.payload.casefold()
