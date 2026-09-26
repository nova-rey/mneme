from mneme.development import (
    ConsequenceAssessment,
    EdgeState,
    LearnerState,
    Observation,
    RouteSpec,
    TransitionInput,
    apply_transition,
    select_routes,
)


def _observation(
    *, arc: str, role: str = "external", dependence: str = "external_supported", **kwargs: object
) -> Observation:
    observation_id = str(kwargs.pop("observation_id", f"{arc}-{role}"))
    return Observation(
        "wick-maintains-moisture",
        source_role=role,
        dependence=dependence,
        conversation_arc_id=arc,
        observation_id=observation_id,
        **kwargs,
    )


def test_repeated_observations_within_one_arc_receive_one_credit() -> None:
    first = apply_transition(
        apply_transition(
            LearnerState.empty(),
            TransitionInput("op-1", observations=(_observation(arc="arc-a"),)),
        ).state,
        TransitionInput("op-2", observations=(_observation(arc="arc-a"),)),
    )
    assert first.updates[0].credited == 0
    assert first.updates[0].reason == "same_conversation_episode"
    assert first.state.edge("wick-maintains-moisture").relevant_opportunities == 1


def test_external_reentry_gets_a_new_opportunity() -> None:
    first = apply_transition(
        LearnerState.empty(),
        TransitionInput("op-1", observations=(_observation(arc="arc-a"),)),
    )
    second = apply_transition(
        first.state,
        TransitionInput("op-2", observations=(_observation(arc="arc-b"),)),
    )
    assert second.updates[0].credited > 0
    assert second.state.edge("wick-maintains-moisture").relevant_opportunities == 2
    assert set(second.state.edge("wick-maintains-moisture").episode_keys) == {"arc-a", "arc-b"}


def test_model_reentry_inside_refractory_window_is_recorded_without_credit() -> None:
    first = apply_transition(
        LearnerState.empty(),
        TransitionInput("op-1", observations=(_observation(arc="arc-a"),)),
    )
    second = apply_transition(
        first.state,
        TransitionInput(
            "op-2",
            observations=(
                _observation(
                    arc="arc-b",
                    role="model_output",
                    dependence="no_identified_link",
                    reentry_initiator="model",
                    arc_reentry=True,
                    refractory_active=True,
                ),
            ),
        ),
    )
    assert second.updates[0].credited == 0
    assert second.updates[0].reason == "model_reentry_refractory"
    assert "arc-b" in second.state.edge("wick-maintains-moisture").episode_keys


def test_model_reentry_after_refractory_window_uses_bounded_model_credit() -> None:
    first = apply_transition(
        LearnerState.empty(),
        TransitionInput("op-1", observations=(_observation(arc="arc-a"),)),
    )
    second = apply_transition(
        first.state,
        TransitionInput(
            "op-2",
            observations=(
                _observation(
                    arc="arc-c",
                    role="model_output",
                    dependence="no_identified_link",
                    reentry_initiator="model",
                    arc_reentry=True,
                    refractory_active=False,
                ),
            ),
        ),
    )
    assert second.updates[0].credited > 0


def test_qwen_reply_to_model_callback_keeps_model_reentry_ancestry() -> None:
    result = apply_transition(
        LearnerState.empty(),
        TransitionInput(
            "op-1",
            observations=(
                _observation(
                    arc="arc-b",
                    role="external",
                    dependence="external_supported",
                    reentry_initiator="model",
                    arc_reentry=True,
                    refractory_active=True,
                ),
            ),
        ),
    )
    assert result.updates[0].credited == 0
    assert result.updates[0].reason == "model_reentry_refractory"


def test_external_negative_outcome_is_preserved_as_consequence_not_absence() -> None:
    first = apply_transition(
        LearnerState.empty(),
        TransitionInput("op-1", observations=(_observation(arc="arc-a"),)),
    )
    result = apply_transition(
        first.state,
        TransitionInput(
            "op-2",
            observations=(
                _observation(
                    arc="arc-b",
                    relation_support="contradicted",
                    expression_status="negated",
                    observation_id="negative-outcome",
                ),
            ),
            consequences=(
                ConsequenceAssessment(
                    operation_id="op-2",
                    route_key="wick-route",
                    direction=-1,
                ),
            ),
        ),
    )
    assert result.updates[-1].reason == "contradicted_no_positive_credit"
    assert result.state.edge("wick-maintains-moisture").support == first.state.edge(
        "wick-maintains-moisture"
    ).support
    assert result.state.route("wick-route").consequence < 0


def test_mneme_injected_reentry_retains_exposure_dependence() -> None:
    result = apply_transition(
        LearnerState.empty(),
        TransitionInput(
            "op-1",
            observations=(
                _observation(
                    arc="arc-mneme",
                    role="model_output",
                    dependence="exposure_linked",
                    actual_exposure=True,
                    reentry_initiator="mneme",
                    arc_reentry=True,
                ),
            ),
        ),
    )
    contribution = result.contributions[0]
    assert contribution.dependence == "exposure_linked"
    assert contribution.awarded <= 100_000
    assert contribution.dependence != "external_supported"


def test_arc_ids_do_not_change_route_selection() -> None:
    base = EdgeState(
        target_key="edge",
        context="general",
        accessibility=100_000,
        support=100_000,
        episode_keys=("arc-a",),
    )
    alternate = EdgeState(
        target_key="edge",
        context="general",
        accessibility=100_000,
        support=100_000,
        episode_keys=("arc-z",),
    )
    routes = (RouteSpec("route", ("edge",), query_coverage=1, directness=1),)
    assert select_routes(LearnerState(edge_states=(base,)), routes) == select_routes(
        LearnerState(edge_states=(alternate,)), routes
    )
