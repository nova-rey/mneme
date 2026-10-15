from __future__ import annotations

from dataclasses import replace

from mneme.development import (
    EdgeState,
    FieldConfig,
    LearnerState,
    ProjectionPolicy,
    compute_saa_field,
    project_saa_neighborhood,
)
from mneme.memory.graph import GraphConcept, GraphEdge


def _graph(labels: tuple[tuple[str, str], ...], rows: tuple[tuple[str, str, str, str], ...]):
    concepts = tuple(GraphConcept(key, label, "concept") for key, label in labels)
    edges = tuple(
        GraphEdge(key, source, target, relation, ({"synthetic": True},))
        for key, source, target, relation in rows
    )
    return concepts, edges


def _learner(strengths: dict[str, int]) -> LearnerState:
    return LearnerState(
        edge_states=tuple(
            EdgeState(key, accessibility=value, support=value)
            for key, value in sorted(strengths.items())
        )
    )


def _labels(concepts: tuple[GraphConcept, ...]) -> dict[str, str]:
    return {item.key: item.label for item in concepts}


def _crosslink_scene():
    labels = (
        ("a", "alpha"), ("b", "bravo"), ("c", "charlie"), ("d", "delta"),
        ("e", "echo"), ("f", "foxtrot"), ("g", "golf"), ("h", "hotel"),
        ("x", "xray"), ("y", "yankee"),
    )
    rows = (
        ("e0", "a", "b", "supports"),
        ("e1", "a", "c", "enables"),
        ("e2", "b", "c", "causes"),
        ("e3", "c", "d", "constrains"),
        ("e4", "d", "a", "prevents"),
        ("e5", "a", "e", "supports"),
        ("e6", "b", "f", "precedes"),
        ("e7", "e", "g", "depends_on"),
        ("e8", "f", "h", "part_of"),
        ("e9", "x", "y", "associated_with"),
    )
    concepts, edges = _graph(labels, rows)
    state = _learner({key: 800_000 for key, *_ in rows})
    config = FieldConfig(version="f0-saa-v1", max_depth=3, max_contributors=20)
    return concepts, edges, state, config


def test_projection_is_deterministic_and_does_not_mutate_field_or_default_payload():
    concepts, edges = _graph(
        (("a", "shared tools"), ("b", "reservation windows"), ("c", "return timing")),
        (("e0", "a", "b", "supports"), ("e1", "b", "c", "enables")),
    )
    state = _learner({"e0": 800_000, "e1": 700_000})
    result = compute_saa_field("shared tools", concepts, edges, state, field_seed=3)
    before = result.to_dict()
    first = project_saa_neighborhood(result, _labels(concepts))
    second = project_saa_neighborhood(result, _labels(concepts))

    assert first.to_audit_dict() == second.to_audit_dict()
    assert first.to_portable_dict() is None
    assert first.audit_size_bytes <= ProjectionPolicy().max_serialized_bytes
    assert result.to_dict() == before
    assert result.accessibility_distribution == tuple(
        (row["candidate"], row["probability"])
        for row in before["accessibility_distribution"]
    )
    assert result.payload == before["payload"]


def test_same_vocabulary_different_earned_cross_links_make_distinct_views():
    labels = (
        ("tool", "shared tools"), ("window", "reservation windows"),
        ("return", "return timing"), ("status", "availability status"),
        ("roles", "clear ownership"),
    )
    edges_a = (
        ("e1", "tool", "window", "supports"),
        ("e2", "window", "return", "enables"),
        ("e3", "return", "status", "causes"),
        ("e4", "roles", "tool", "constrains"),
    )
    edges_b = (
        ("e1", "roles", "status", "supports"),
        ("e2", "status", "window", "enables"),
        ("e3", "return", "status", "causes"),
        ("e4", "window", "tool", "constrains"),
    )
    concepts_a, graph_a = _graph(labels, edges_a)
    concepts_b, graph_b = _graph(labels, edges_b)
    state = _learner({"e1": 900_000, "e2": 800_000, "e3": 700_000, "e4": 600_000})
    result_a = compute_saa_field(
        "shared tool lending plan", concepts_a, graph_a, state, field_seed=0
    )
    result_b = compute_saa_field(
        "shared tool lending plan", concepts_b, graph_b, state, field_seed=0
    )
    projection_a = project_saa_neighborhood(result_a, _labels(concepts_a))
    projection_b = project_saa_neighborhood(result_b, _labels(concepts_b))

    assert result_a.selected_landing == "e2"
    assert result_b.selected_landing == "e4"
    assert result_a.accessibility_distribution != result_b.accessibility_distribution
    assert result_a.payload != result_b.payload
    assert [item.key for item in projection_a.edges] == ["e2", "e3"]
    assert [item.key for item in projection_b.edges] == ["e4"]
    assert projection_a.paths[1].edge_keys == ("e2", "e3")
    assert projection_a.nodes != projection_b.nodes
    assert projection_a.to_portable_dict() is None
    assert projection_b.to_portable_dict() is None

    explicit_a = project_saa_neighborhood(
        result_a,
        _labels(concepts_a),
        policy=ProjectionPolicy(descriptor_mode="synthetic_fixture_only"),
    )
    explicit_b = project_saa_neighborhood(
        result_b,
        _labels(concepts_b),
        policy=ProjectionPolicy(descriptor_mode="synthetic_fixture_only"),
    )
    assert explicit_a.to_portable_dict() != explicit_b.to_portable_dict()
    serialized = str(explicit_a.to_portable_dict())
    assert "e2" not in serialized and "800000" not in serialized
    assert "source_slot" not in serialized and "synthetic" not in serialized


def test_reachable_direction_multiple_parents_cycles_and_disconnected_island():
    concepts, edges, state, config = _crosslink_scene()
    # With this equal-weight pay table, seed 31 lands on e0 (alpha -> bravo).
    result = compute_saa_field("unfamiliar", concepts, edges, state, config=config, field_seed=31)
    assert result.selected_landing == "e0"
    projection = project_saa_neighborhood(result, _labels(concepts))
    by_key = {item.key: item for item in projection.edges}

    assert by_key["e1"].path == ("e0", "e1")
    assert by_key["e3"].path == ("e0", "e1", "e3")
    assert by_key["e2"].role == "cross_link"
    assert by_key["e2"].source == "b" and by_key["e2"].target == "c"
    # e4 returns to landing endpoint a through the c/d route and stays a
    # directed cross-link; the disconnected x -> y island is never projected.
    assert by_key["e4"].role == "cross_link"
    assert by_key["e8"].relationship == "part_of"
    assert "e9" not in by_key
    assert {"x", "y"}.isdisjoint({item.key for item in projection.nodes})
    assert all(item.edge_keys[0] == "e0" for item in projection.paths)


def test_incoming_edges_at_landing_endpoints_are_not_reversed_into_view():
    concepts, edges = _graph(
        (("a", "alpha"), ("b", "bravo"), ("c", "charlie"), ("x", "xray")),
        (
            ("e0", "b", "a", "supports"),
            ("e1", "a", "c", "enables"),
            ("e2", "x", "b", "causes"),
        ),
    )
    state = _learner({"e0": 900_000, "e1": 100_000, "e2": 100_000})
    result = compute_saa_field("unrelated", concepts, edges, state, field_seed=0)
    assert result.selected_landing == "e0"
    projection = project_saa_neighborhood(result, _labels(concepts))
    assert [item.key for item in projection.edges] == ["e0", "e1"]
    assert "e2" not in {item.key for item in projection.edges}


def test_changed_landing_changes_local_organization_of_same_graph():
    concepts, edges, state, config = _crosslink_scene()
    first_result = compute_saa_field(
        "unfamiliar", concepts, edges, state, config=config, field_seed=31
    )
    second_result = compute_saa_field(
        "unfamiliar", concepts, edges, state, config=config, field_seed=1
    )
    assert first_result.accessibility_distribution == second_result.accessibility_distribution
    assert first_result.selected_landing == "e0"
    assert second_result.selected_landing == "e1"

    first = project_saa_neighborhood(first_result, _labels(concepts))
    second = project_saa_neighborhood(second_result, _labels(concepts))
    assert first.landing_edge_key != second.landing_edge_key
    assert first.edges[0].role == second.edges[0].role == "landing"
    assert first.nodes != second.nodes
    assert first.to_audit_dict() != second.to_audit_dict()


def test_projection_caps_nodes_edges_hops_paths_and_serialized_bytes():
    concepts, edges, state, config = _crosslink_scene()
    result = compute_saa_field("unfamiliar", concepts, edges, state, config=config, field_seed=31)
    limited = project_saa_neighborhood(
        result,
        _labels(concepts),
        policy=ProjectionPolicy(
            max_nodes=3,
            max_edges=2,
            max_hops=1,
            max_paths=2,
            max_serialized_bytes=1024,
        ),
    )
    assert len(limited.nodes) <= 3
    assert len(limited.edges) <= 2
    assert len(limited.paths) <= 2
    assert limited.audit_size_bytes <= 1024
    reasons = dict(limited.omissions)
    assert reasons.get("edge_cap", 0) + reasons.get("hop_cap", 0) + reasons.get("node_cap", 0) > 0

    tiny = project_saa_neighborhood(
        result,
        _labels(concepts),
        policy=ProjectionPolicy(
            max_nodes=2,
            max_edges=1,
            max_hops=0,
            max_paths=1,
            max_serialized_bytes=512,
        ),
    )
    assert tiny.audit_size_bytes <= 512
    assert len(tiny.edges) <= 1

    input_limited = project_saa_neighborhood(
        result,
        _labels(concepts),
        policy=ProjectionPolicy(max_input_contributions=1),
    )
    assert dict(input_limited.omissions).get("input_scan_cap", 0) > 0
    assert len(input_limited.edges) <= 1


def test_quarantine_ineligible_zero_strength_and_absent_edges_never_enter_descriptor():
    concepts, edges = _graph(
        (("a", "alpha"), ("b", "bravo"), ("c", "charlie"), ("d", "delta"), ("x", "beluga whale")),
        (
            ("e0", "a", "b", "supports"),
            ("e1", "b", "c", "enables"),
            ("e2", "b", "d", "prevents"),
            ("fake", "a", "x", "associated_with"),
        ),
    )
    state = _learner({"e0": 900_000, "e1": 800_000, "e2": 0, "fake": 600_000})
    result = compute_saa_field(
        "unrelated",
        concepts,
        edges,
        state,
        quarantined_edges={"e1"},
        ineligible_edges={"fake"},
        field_seed=0,
    )
    projection = project_saa_neighborhood(
        result,
        _labels(concepts),
        policy=ProjectionPolicy(descriptor_mode="synthetic_fixture_only"),
    )
    ids = {item.key for item in projection.edges}
    portable = projection.to_portable_dict()
    assert "e1" not in ids and "fake" not in ids and "e2" not in ids
    assert "beluga whale" not in str(portable)
    assert dict(projection.omissions).get("ineligible_or_quarantined", 0) >= 1


def test_no_history_disabled_or_missing_landing_has_no_fabricated_view():
    concepts, edges = _graph(
        (("a", "alpha"), ("b", "bravo")),
        (("e0", "a", "b", "supports"),),
    )
    no_history = compute_saa_field("alpha", concepts, edges, LearnerState(), field_seed=9)
    no_history_view = project_saa_neighborhood(no_history, _labels(concepts))
    assert no_history.selected_landing is None
    assert no_history_view.edges == ()
    assert dict(no_history_view.omissions)["no_selected_landing"] == 1

    disabled = compute_saa_field(
        "alpha", concepts, edges, _learner({"e0": 800_000}), field_seed=9, field_enabled=False
    )
    disabled_view = project_saa_neighborhood(disabled, _labels(concepts))
    assert disabled_view.edges == ()
    assert dict(disabled_view.omissions)["field_disabled"] == 1


def test_projection_refuses_wrongly_rooted_and_conflicting_duplicate_rows():
    concepts, edges = _graph(
        (("a", "alpha"), ("b", "bravo"), ("c", "charlie")),
        (("e0", "a", "b", "supports"), ("e1", "b", "c", "enables")),
    )
    state = _learner({"e0": 800_000, "e1": 700_000})
    result = compute_saa_field("unrelated", concepts, edges, state, field_seed=0)
    # Deliberately corrupt only a copied result for adversarial validation.
    wrong_path = replace(result.contributions[-1], path=("other", "e1"))
    conflict = replace(result.contributions[-1], source="c", target="b")
    malformed = replace(
        result,
        contributions=(*result.contributions, wrong_path, conflict),
    )
    projection = project_saa_neighborhood(malformed, _labels(concepts))
    reasons = dict(projection.omissions)
    assert reasons.get("invalid_or_unrooted_path", 0) >= 1
    assert reasons.get("conflicting_duplicate_edge_key", 0) >= 1
    assert len({item.key for item in projection.edges}) == len(projection.edges)


def test_descriptor_drops_unsupported_relation_without_substituting_a_generic_one():
    concepts, edges = _graph(
        (("a", "alpha"), ("b", "bravo")),
        (("e0", "a", "b", "supports"),),
    )
    state = _learner({"e0": 800_000})
    result = compute_saa_field("unrelated", concepts, edges, state, field_seed=4)
    unsupported = replace(
        result,
        contributions=tuple(
            replace(row, relationship="invented_relation") for row in result.contributions
        ),
    )
    projection = project_saa_neighborhood(
        unsupported,
        _labels(concepts),
        policy=ProjectionPolicy(descriptor_mode="synthetic_fixture_only"),
    )
    assert projection.to_portable_dict() is None
    assert dict(projection.descriptor_omissions)["descriptor_relation_unsupported"] == 1
    assert projection.edges[0].relationship == "invented_relation"
