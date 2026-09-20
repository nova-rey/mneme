from mneme.development import (
    FIXED_SCALE,
    DevelopmentalLearner,
    EdgeState,
    Observation,
    apply_consequence,
    route_exposure,
    select_routes,
)


def test_model_origin_observation_is_bounded_and_replayable() -> None:
    learner = DevelopmentalLearner()
    observation = Observation(
        "edge-a",
        source_role="model",
        dependence="no_identified_link",
        observation_id="o1",
    )
    first = learner.apply({}, [observation], opportunity=1)
    second = learner.apply({}, [observation], opportunity=1)
    assert first.state == second.state
    assert first.state[("edge-a", "general")].accessibility == 20_000
    assert first.state[("edge-a", "general")].support == 5_000


def test_current_input_echo_adds_no_model_credit() -> None:
    result = DevelopmentalLearner().apply(
        {},
        [
            Observation(
                "edge-a",
                source_role="model",
                dependence="current_input_echo",
                observation_id="echo",
            )
        ],
        opportunity=1,
    )
    assert result.deltas == {("edge-a", "general"): 0}
    assert result.reasons[("edge-a", "general")] == "support_seen_credit_capped"


def test_presence_cap_is_not_absence_and_unknown_does_not_change_state() -> None:
    learner = DevelopmentalLearner()
    state = {("edge-a", "general"): EdgeState(accessibility=FIXED_SCALE)}
    capped = learner.apply(
        state,
        [Observation("edge-a", observation_id="present", status="present")],
        opportunity=1,
    )
    unknown = learner.apply(
        capped.state,
        [Observation("edge-a", status="unknown", observation_id="unknown")],
        opportunity=2,
    )
    assert capped.state[("edge-a", "general")].inactivity_ticks == 0
    assert unknown.state == capped.state


def test_contextual_closure_and_recovery_control_actual_route_exposure() -> None:
    state = EdgeState(accessibility=400_000, support=100_000)
    assert route_exposure({"e": state}, ("e",))
    restrained = apply_consequence(state, -50_000)
    for _ in range(4):
        restrained = apply_consequence(restrained, -50_000)
    assert restrained.consequence == -250_000
    assert not route_exposure({"e": restrained}, ("e",))
    recovered = apply_consequence(restrained, 50_000)
    assert route_exposure({"e": recovered}, ("e",))


def test_exploration_stays_in_highest_query_coverage_tier() -> None:
    state = {key: EdgeState(accessibility=100_000) for key in ("a", "b", "c", "d")}
    routes = [
        {"route_key": key, "edge_keys": [key], "query_coverage": coverage}
        for key, coverage in (("a", 2), ("b", 2), ("c", 2), ("d", 1))
    ]
    selected = select_routes(routes, state, opportunity=8)
    assert [route["route_key"] for route in selected] == ["a", "c"]
