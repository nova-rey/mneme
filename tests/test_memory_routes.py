from __future__ import annotations

import json

from mneme.memory import GraphConcept, GraphEdge, GraphRoute, discover_routes


def _concept(key: str, label: str | None = None) -> GraphConcept:
    return GraphConcept(key, label or key, "concept", evidence=({"source_slot": "s0"},))


def _edge(key: str, source: str, target: str, *, marker: str | None = None) -> GraphEdge:
    return GraphEdge(
        key,
        source,
        target,
        "causes",
        evidence=({"source_slot": "s0", "marker": marker or key},),
    )


def test_discover_routes_joins_edges_across_interpretations_without_route_candidate() -> None:
    routes = discover_routes(
        [_concept("a"), _concept("b"), _concept("c")],
        [_edge("e2", "b", "c"), _edge("e1", "a", "b")],
    )

    paths = {route.edge_keys for route in routes}
    assert ("e1", "e2") in paths
    route = next(route for route in routes if route.edge_keys == ("e1", "e2"))
    assert [item["edge_key"] for item in route.evidence] == ["e1", "e2"]
    assert route.key.startswith("derived:")


def test_repeated_same_edge_does_not_fabricate_a_multihop_route() -> None:
    routes = discover_routes(
        [_concept("a"), _concept("b")],
        [_edge("e1", "a", "b"), _edge("e2", "a", "b")],
    )

    assert all(len(route.edge_keys) == 1 for route in routes)


def test_disconnected_edges_remain_disconnected_and_direction_is_respected() -> None:
    routes = discover_routes(
        [_concept("a"), _concept("b"), _concept("c"), _concept("d")],
        [_edge("e1", "a", "b"), _edge("e2", "c", "d")],
    )

    assert all(len(route.edge_keys) == 1 for route in routes)
    assert ("e1", "e2") not in {route.edge_keys for route in routes}

    reverse_routes = discover_routes(
        [_concept("a"), _concept("b"), _concept("c")],
        [_edge("e1", "a", "b"), _edge("e2", "c", "b")],
    )
    assert all(len(route.edge_keys) == 1 for route in reverse_routes)


def test_only_canonical_resolver_keys_bridge_aliases() -> None:
    # Different local keys remain disconnected even when their labels look
    # equivalent. Resolution must explicitly canonicalize the bridge key first.
    unmerged = discover_routes(
        [_concept("a", "rain jacket"), _concept("bridge-1", "rain jacket"), _concept("c")],
        [_edge("e1", "a", "bridge-1"), _edge("e2", "bridge-2", "c")],
    )
    assert all(len(route.edge_keys) == 1 for route in unmerged)

    merged = discover_routes(
        [_concept("a", "rain jacket"), _concept("bridge", "rain jacket"), _concept("c")],
        [_edge("e1", "a", "bridge"), _edge("e2", "bridge", "c")],
    )
    assert ("e1", "e2") in {route.edge_keys for route in merged}


def test_routes_are_insertion_independent_and_bounds_are_enforced() -> None:
    concepts = [_concept(key) for key in ("a", "b", "c", "d", "e")]
    forward = [
        _edge("e1", "a", "b"),
        _edge("e2", "b", "c"),
        _edge("e3", "c", "d"),
        _edge("e4", "d", "e"),
    ]
    first = discover_routes(concepts, forward)
    second = discover_routes(list(reversed(concepts)), list(reversed(forward)))

    assert [route.to_dict() for route in first] == [route.to_dict() for route in second]
    assert all(1 <= len(route.edge_keys) <= 3 for route in first)
    assert all(len(route.edge_keys) != 4 for route in first)
    assert len(first) <= 8
    assert all("edge_key" in item for route in first for item in route.evidence)
    json.dumps([route.to_dict() for route in first])


def test_edges_without_evidence_are_ineligible_for_discovered_routes() -> None:
    concepts = [_concept("a"), _concept("b"), _concept("c")]
    edges = [
        _edge("e1", "a", "b"),
        GraphEdge("e2", "b", "c", "causes", evidence=()),
    ]

    routes = discover_routes(concepts, edges)

    assert all(route.edge_keys != ("e1", "e2") for route in routes)


def test_explicit_route_is_preserved_without_duplicate_derived_copy() -> None:
    explicit = GraphRoute(
        "model-route",
        ("e1", "e2"),
        ({"source_slot": "s0", "start": 0, "end": 1},),
    )
    routes = discover_routes(
        [_concept("a"), _concept("b"), _concept("c")],
        [_edge("e1", "a", "b"), _edge("e2", "b", "c")],
        [explicit],
    )

    assert [route.key for route in routes].count("model-route") == 1
    assert sum(route.edge_keys == ("e1", "e2") for route in routes) == 1
