from __future__ import annotations

from mneme.development import (
    FieldConfig,
    FieldResult,
    PressureContribution,
    ProjectionPolicy,
    compute_saa_field,
    project_saa_neighborhood,
)
from tools.saa_lcn02_counterfactuals import (
    FIXED_LABELS,
    FIXED_ROWS_A,
    FIXED_ROWS_B,
    FIXED_ROWS_REMOTE_CONTROL,
    _concepts,
    _edges,
    _labels,
    _learner,
    _reachability_counterfactual,
)


def _edge_by_key(result: FieldResult, key: str) -> PressureContribution:
    return next(item for item in result.contributions if item.edge_key == key)


def test_fixed_landing_different_earned_topology_changes_projected_paths_only() -> None:
    concepts = _concepts(FIXED_LABELS)
    learner = _learner(
        {
            "e0": 900_000,
            "e1": 700_000,
            "e2": 600_000,
            "e3": 500_000,
            "e4": 400_000,
            "remote": 200_000,
        }
    )
    config = FieldConfig(max_depth=3, max_contributors=12)
    result_a = compute_saa_field(
        "unfamiliar abstract question",
        concepts,
        _edges(FIXED_ROWS_A),
        learner,
        config=config,
        field_seed=1,
    )
    result_b = compute_saa_field(
        "unfamiliar abstract question",
        concepts,
        _edges(FIXED_ROWS_B),
        learner,
        config=config,
        field_seed=1,
    )

    assert result_a.selected_landing == result_b.selected_landing == "e0"
    assert result_a.landing_ticket == result_b.landing_ticket == 140_891
    assert dict(result_a.accessibility_distribution) == dict(result_b.accessibility_distribution)
    assert {edge.key for edge in _edges(FIXED_ROWS_A)} == {
        edge.key for edge in _edges(FIXED_ROWS_B)
    }
    assert result_a.payload == result_b.payload

    policy = ProjectionPolicy(descriptor_mode="synthetic_fixture_only")
    projection_a = project_saa_neighborhood(result_a, _labels(concepts), policy=policy)
    projection_b = project_saa_neighborhood(result_b, _labels(concepts), policy=policy)
    projected_a = {edge.key: edge for edge in projection_a.edges}
    projected_b = {edge.key: edge for edge in projection_b.edges}
    assert projected_a["e2"].source == projected_b["e2"].source == "c"
    assert projected_a["e2"].target == "d"
    assert projected_b["e2"].target == "f"
    assert projected_a["e4"].source == projected_b["e4"].source == "e"
    assert projected_a["e4"].target == "f"
    assert projected_b["e4"].target == "d"
    assert projected_a["e2"].path == projected_b["e2"].path == ("e0", "e1", "e2")
    assert projected_a["e4"].path == projected_b["e4"].path == ("e0", "e3", "e4")
    # Topology changed the endpoints, but abstract relation vocabulary did not.
    assert projection_a.to_portable_dict() != projection_b.to_portable_dict()


def test_disconnected_remote_rewire_does_not_change_projected_local_neighborhood() -> None:
    concepts = _concepts(FIXED_LABELS)
    learner = _learner(
        {
            "e0": 900_000,
            "e1": 700_000,
            "e2": 600_000,
            "e3": 500_000,
            "e4": 400_000,
            "remote": 200_000,
        }
    )
    config = FieldConfig(max_depth=3, max_contributors=12)
    result_a = compute_saa_field(
        "unfamiliar abstract question",
        concepts,
        _edges(FIXED_ROWS_A),
        learner,
        config=config,
        field_seed=1,
    )
    remote_rewired = compute_saa_field(
        "unfamiliar abstract question",
        concepts,
        _edges(FIXED_ROWS_REMOTE_CONTROL),
        learner,
        config=config,
        field_seed=1,
    )
    projection_a = project_saa_neighborhood(result_a, _labels(concepts))
    projection_remote = project_saa_neighborhood(remote_rewired, _labels(concepts))

    assert result_a.selected_landing == remote_rewired.selected_landing == "e0"
    assert dict(result_a.accessibility_distribution) == dict(
        remote_rewired.accessibility_distribution
    )
    assert projection_a.to_audit_dict() == projection_remote.to_audit_dict()
    assert "remote" not in {edge.key for edge in projection_remote.edges}


def test_production_omits_earned_incoming_edge_and_counterfactual_preserves_orientation() -> None:
    concepts = _concepts(
        (
            ("a", "landing alpha"),
            ("b", "landing bravo"),
            ("c", "incoming association concept"),
            ("d", "outgoing consequence"),
        )
    )
    edges = _edges(
        (
            ("e0", "a", "b", "supports"),
            ("incoming", "c", "a", "associated_with"),
            ("outgoing", "b", "d", "enables"),
        )
    )
    learner = _learner({"e0": 900_000, "incoming": 500_000, "outgoing": 500_000})
    config = FieldConfig(max_depth=2, max_contributors=8)
    result = compute_saa_field("unrelated", concepts, edges, learner, config=config, field_seed=1)

    assert result.selected_landing == "e0"
    assert "incoming" in dict(result.accessibility_distribution)
    assert "incoming" not in {item.edge_key for item in result.contributions}
    assert _edge_by_key(result, "outgoing").path == ("e0", "outgoing")

    counterfactual = _reachability_counterfactual(
        edges,
        set(dict(result.accessibility_distribution)),
        result.selected_landing,
        max_depth=config.max_depth,
    )
    assert counterfactual["kind"] == "reachability_only_counterfactual_not_field_result"
    incoming = next(row for row in counterfactual["records"] if row["edge_key"] == "incoming")
    assert incoming["navigation_mode"] == "incoming_access_only"
    assert (incoming["semantic_source"], incoming["relationship"], incoming["semantic_target"]) == (
        "c",
        "associated_with",
        "a",
    )
    assert (incoming["navigation_from"], incoming["navigation_to"]) == ("a", "c")
    assert incoming["asserts_inverse_semantics"] is False
    assert counterfactual["inverse_relationships_created"] is False


def test_incoming_causal_and_part_of_access_does_not_assert_inverse_relation() -> None:
    concepts = _concepts(
        (
            ("a", "landing alpha"),
            ("b", "landing bravo"),
            ("e", "incoming causal source"),
            ("f", "part concept"),
            ("d", "outgoing consequence"),
        )
    )
    edges = _edges(
        (
            ("e0", "a", "b", "supports"),
            ("cause_in", "e", "a", "causes"),
            ("part_in", "f", "a", "part_of"),
            ("prevent_out", "b", "d", "prevents"),
        )
    )
    learner = _learner(
        {"e0": 900_000, "cause_in": 500_000, "part_in": 500_000, "prevent_out": 500_000}
    )
    config = FieldConfig(max_depth=2, max_contributors=8)
    result = compute_saa_field("unrelated", concepts, edges, learner, config=config, field_seed=1)
    assert result.selected_landing == "e0"
    assert {item.edge_key for item in result.contributions} == {"e0", "prevent_out"}

    counterfactual = _reachability_counterfactual(
        edges,
        set(dict(result.accessibility_distribution)),
        result.selected_landing,
        max_depth=config.max_depth,
    )
    by_key = {row["edge_key"]: row for row in counterfactual["records"]}
    assert by_key["cause_in"]["semantic_source"] == "e"
    assert by_key["cause_in"]["semantic_target"] == "a"
    assert by_key["cause_in"]["navigation_from"] == "a"
    assert by_key["cause_in"]["navigation_to"] == "e"
    assert by_key["part_in"]["semantic_source"] == "f"
    assert by_key["part_in"]["semantic_target"] == "a"
    assert by_key["part_in"]["relationship"] == "part_of"
    assert all(row["asserts_inverse_semantics"] is False for row in by_key.values())


def test_existing_cap_and_recursive_attenuation_are_not_reconstructed_by_projection() -> None:
    labels = tuple(
        (key, label)
        for key, label in zip(
            "abcdefgh",
            ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"),
            strict=True,
        )
    )
    concepts = _concepts(labels)
    rows = (
        ("e0", "a", "b", "supports"),
        ("e1", "a", "c", "enables"),
        ("e2", "b", "c", "causes"),
        ("e3", "c", "d", "constrains"),
        ("e4", "a", "e", "supports"),
        ("e5", "b", "f", "prevents"),
        ("e6", "e", "g", "depends_on"),
        ("e7", "f", "h", "retains"),
    )
    edges = _edges(rows)
    learner = _learner({key: 800_000 for key, *_ in rows})
    config = FieldConfig(max_depth=2, max_contributors=7)
    result = compute_saa_field(
        "unrelated abstract question", concepts, edges, learner, config=config, field_seed=14
    )
    projection = project_saa_neighborhood(result, _labels(concepts))
    candidate_keys = set(dict(result.accessibility_distribution))
    contribution_keys = {item.edge_key for item in result.contributions}
    projected_keys = {item.key for item in projection.edges}

    assert result.selected_landing == "e0"
    assert "e7" in candidate_keys
    assert "e7" not in contribution_keys and "e7" not in projected_keys
    assert _edge_by_key(result, "e3").path == ("e0", "e1", "e3")
    assert _edge_by_key(result, "e1").attenuated_pressure == 416_000
    assert _edge_by_key(result, "e3").attenuated_pressure == 112_486
    assert _edge_by_key(result, "e3").final_pressure == 41_832
    assert {item.key for item in projection.edges} == contribution_keys
