import pytest

from mneme.development import (
    FIXED_SCALE,
    ConsequenceAssessment,
    DevelopmentalLearner,
    EdgeState,
    LearnerError,
    LearnerState,
    Observation,
    RouteSpec,
    TransitionInput,
    apply_consequence,
    apply_transition,
    route_exposure,
    route_score,
    select_routes,
)
from mneme.development.learner import LIFETIME_CAP


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


def test_contradicted_observation_is_retained_without_positive_credit_or_absence_decay() -> None:
    state = {
            ("edge-a", "general"): EdgeState(
                "edge-a",
                "general",
                accessibility=400_000,
            support=300_000,
            relevant_opportunities=4,
            inactivity_ticks=0,
        )
    }
    result = apply_transition(
        LearnerState(edge_states=tuple(state.values())),
        TransitionInput(
            "negated-1",
            observations=(
                Observation(
                    "edge-a",
                    relation_support="contradicted",
                    expression_status="negated",
                    occurrence_key="negated-occurrence",
                ),
            ),
        ),
    )
    after = result.state.edge("edge-a")
    assert after.accessibility == 400_000
    assert after.support == 300_000
    assert after.relevant_opportunities == 5
    assert after.inactivity_ticks == 0
    assert result.updates[0].credited == 0
    assert result.updates[0].reason == "contradicted_no_positive_credit"

    compatibility = DevelopmentalLearner().apply(
        state,
        [
            Observation(
                "edge-a",
                relation_support="contradicted",
                expression_status="negated",
                occurrence_key="negated-compat",
            )
        ],
        opportunity=5,
    )
    assert compatibility.reasons[("edge-a", "general")] == (
        "contradicted_no_positive_credit"
    )


def test_conflicting_supported_and_contradicted_duplicate_fails_closed() -> None:
    result = DevelopmentalLearner().apply(
        {},
        [
            Observation("edge-a", occurrence_key="same", relation_support="supported"),
            Observation(
                "edge-a",
                occurrence_key="same",
                relation_support="contradicted",
                expression_status="negated",
            ),
        ],
        opportunity=1,
    )
    assert result.state == {}


def test_observation_semantic_matrix_rejects_invalid_learner_boundary() -> None:
    with pytest.raises(LearnerError, match="semantic disposition"):
        Observation(
            "edge-a",
            relation_support="contradicted",
            expression_status="affirmed",
        )


def test_induced_credit_requires_actual_exposure_but_retains_audit_contribution() -> None:
    result = apply_transition(
        LearnerState.empty(),
        TransitionInput(
            "not-supplied",
            observations=(
                Observation(
                    "edge-a",
                    source_role="model",
                    dependence="exposure_linked",
                    actual_exposure=False,
                    observation_id="memory-echo",
                ),
            ),
        ),
    )
    assert result.contributions[0].proposed == 8_000
    assert result.contributions[0].awarded == 0
    assert result.contributions[0].reason == "not_actually_exposed"
    assert result.state.edge("edge-a").accessibility == 0


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


def test_measured_absence_advances_retention_and_unsupported_streak() -> None:
    state = LearnerState(
        edge_states=(
            EdgeState(
                "edge-a",
                accessibility=800_000,
                support=800_000,
            ),
        )
    )
    result = apply_transition(
        state,
        TransitionInput(
            "absence-1",
            observations=(Observation("edge-a", status="absent", observation_id="a1"),),
        ),
    )
    edge = result.state.edge("edge-a")
    assert edge.accessibility == 700_000
    assert edge.support == 800_000
    assert edge.inactivity_ticks == 1
    assert edge.unsupported_streak == 1
    assert result.updates[0].retention == "observed_nonrecurrence"


def test_unknown_freezes_retention_state_and_presence_resets_it() -> None:
    state = LearnerState(
        edge_states=(
            EdgeState(
                "edge-a",
                accessibility=700_000,
                support=600_000,
                inactivity_ticks=3,
                unsupported_streak=3,
                relevant_opportunities=3,
            ),
        ),
        global_opportunity=3,
    )
    unknown = apply_transition(
        state,
        TransitionInput(
            "unknown-1",
            observations=(
                Observation(
                    "edge-a",
                    status="unknown",
                    covered=False,
                    observation_id="u1",
                ),
            ),
        ),
    )
    assert unknown.state.edge("edge-a") == state.edge("edge-a")
    present = apply_transition(
        unknown.state,
        TransitionInput(
            "present-1",
            observations=(
                Observation(
                    "edge-a",
                    status="present",
                    dependence="current_input_echo",
                    observation_id="p1",
                ),
            ),
        ),
    )
    edge = present.state.edge("edge-a")
    assert edge.inactivity_ticks == 0
    assert edge.unsupported_streak == 0


def test_modeled_advance_decays_without_claiming_observed_unsupported() -> None:
    state = LearnerState(
        edge_states=(
            EdgeState(
                "edge-a",
                accessibility=800_000,
                support=800_000,
                unsupported_streak=4,
            ),
        )
    )
    result = apply_transition(
        state,
        TransitionInput(
            "advance-8",
            modeled_advance_ticks=8,
            advance_targets=(("edge-a", "general"),),
        ),
    )
    edge = result.state.edge("edge-a")
    assert edge.accessibility < 800_000
    assert edge.inactivity_ticks == 8
    assert edge.unsupported_streak == 4
    assert edge.support < 800_000


def test_retention_support_decay_starts_at_eighth_measured_absence() -> None:
    state = LearnerState(
        edge_states=(EdgeState("edge-a", accessibility=FIXED_SCALE, support=800_000),)
    )
    for index in range(1, 9):
        state = apply_transition(
            state,
            TransitionInput(
                f"absence-{index}",
                observations=(
                    Observation("edge-a", status="absent", observation_id=f"a{index}"),
                ),
            ),
        ).state
    edge = state.edge("edge-a")
    assert edge.inactivity_ticks == 8
    assert edge.support == 796_875


def _consequence(
    operation_id: str,
    *,
    direction: int = -1,
    exposure_id: str | None = None,
    opportunity: int | None = None,
) -> ConsequenceAssessment:
    return ConsequenceAssessment(
        operation_id,
        "route-a",
        direction=direction,
        exposure_id=exposure_id or operation_id,
        opportunity=opportunity,
    )


def test_consequence_caps_do_not_cancel_by_opposite_awards() -> None:
    state = LearnerState.empty()
    negative = apply_consequence(state, _consequence("negative", exposure_id="same"))
    assert negative.awarded == -50_000
    positive = apply_consequence(
        negative.state,
        _consequence("positive", direction=1, exposure_id="same", opportunity=2),
    )
    assert positive.awarded == 50_000
    capped = apply_consequence(
        positive.state,
        _consequence("negative-2", exposure_id="same", opportunity=3),
    )
    assert capped.awarded == 0
    assert capped.reason == "consequence_cap_exhausted"
    assert capped.state.route("route-a").consequence == 0


def test_consequence_exposure_cap_is_shared_across_signs() -> None:
    state = LearnerState.empty()
    for index, direction in enumerate((-1, 1, -1), start=1):
        result = apply_consequence(
            state,
            _consequence(
                f"signed-{index}",
                direction=direction,
                exposure_id="same-origin",
                opportunity=index,
            ),
        )
        state = result.state
        if index < 3:
            assert result.awarded == direction * 50_000
    assert result.awarded == 0
    assert result.reason == "consequence_cap_exhausted"
    assert dict(state.route("route-a").by_exposure) == {"same-origin": 100_000}
    assert state.route("route-a").consequence == 0


def test_established_route_closes_after_spaced_negative_consequences_and_recovers() -> None:
    state = LearnerState(
        edge_states=(
            EdgeState("edge-a", accessibility=400_000, support=100_000),
        )
    )
    for index, opportunity in enumerate((1, 2, 9, 10, 17), start=1):
        result = apply_consequence(
            state,
            _consequence(f"negative-{index}", opportunity=opportunity),
        )
        assert result.awarded == -50_000
        state = result.state
    assert state.route("route-a").consequence == -250_000
    _base, _score, eligible = route_score(state, ("edge-a",), "route-a")
    assert not eligible
    assert state.route("route-a").to_dict()["consequence"] == -250_000
    recovered = apply_consequence(
        state,
        _consequence("recovery", direction=1, opportunity=25),
    )
    assert recovered.awarded == 50_000
    assert recovered.state.route("route-a").consequence == -200_000


def test_saturated_route_remains_closed_under_dependent_recurrence() -> None:
    state = LearnerState(
        edge_states=(EdgeState("edge-a", accessibility=FIXED_SCALE, support=FIXED_SCALE),)
    )
    for index, opportunity in enumerate((1, 2, 9, 10, 17)):
        state = apply_consequence(
            state,
            _consequence(f"negative-{index}", opportunity=opportunity),
        ).state
    assert state.route("route-a").consequence == -250_000
    recurrence = apply_transition(
        state,
        TransitionInput(
            "dependent-recurrence",
            observations=(
                Observation(
                    "edge-a",
                    dependence="exposure_linked",
                    group_key="replayed-route",
                    observation_id="recurrence",
                ),
            ),
        ),
    )
    assert recurrence.state.route("route-a").consequence == -250_000
    _base, _score, eligible = route_score(
        recurrence.state, ("edge-a",), "route-a"
    )
    assert not eligible
    recovered = apply_consequence(
        recurrence.state,
        _consequence("recovery", direction=1, opportunity=25),
    )
    assert recovered.state.route("route-a").consequence == -200_000


def test_multiple_provenance_roots_use_the_minimum_remaining_cap() -> None:
    state = LearnerState(
        edge_states=(
            EdgeState(
                "edge-a",
                lifetime_by_group=(
                    ("exposure:memory-1", LIFETIME_CAP - 10),
                    ("replay:root-1", LIFETIME_CAP),
                ),
            ),
        )
    )
    result = apply_transition(
        state,
        TransitionInput(
            "multi-root",
            observations=(
                Observation(
                    "edge-a",
                    source_role="model",
                    dependence="exposure_linked",
                    provenance_group_keys=("exposure:memory-1", "replay:root-1"),
                    actual_exposure=True,
                    observation_id="multi-root-observation",
                ),
            ),
        ),
    )
    assert result.contributions[0].awarded == 0
    assert result.contributions[0].reason == "cap_exhausted"
    assert dict(result.state.edge("edge-a").lifetime_by_group) == {
        "exposure:memory-1": LIFETIME_CAP - 10,
        "replay:root-1": LIFETIME_CAP,
    }


def test_competing_and_hard_gated_routes_remain_correct_under_restraint() -> None:
    state = LearnerState(
        edge_states=(
            EdgeState("edge-a", accessibility=400_000, support=100_000),
            EdgeState("edge-b", accessibility=400_000, support=100_000),
        )
    )
    for index, opportunity in enumerate((1, 2, 9, 10, 17)):
        state = apply_consequence(
            state,
            _consequence(f"negative-{index}", opportunity=opportunity),
        ).state
    routes = (
        RouteSpec(
            "route-a",
            ("edge-a",),
            query_coverage=2,
            hard_gates_pass=True,
        ),
        RouteSpec(
            "route-b",
            ("edge-b",),
            query_coverage=1,
            hard_gates_pass=False,
        ),
    )
    selected = select_routes(state, routes, opportunity=1)
    assert selected == ()
