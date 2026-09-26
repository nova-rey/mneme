from mneme.experiments.shared_interloper import (
    ThreadSpec,
    build_shared_interloper_request,
    build_subject_request,
    shared_interloper_history,
    subject_history,
    treatment_exposure_gate,
)


def test_subject_history_is_gemma_perspective() -> None:
    messages = subject_history(
        [("participant one", "assistant one"), ("participant two", "assistant two")],
        current="latest participant",
    )
    assert list(messages) == [
        {"role": "user", "content": "participant one"},
        {"role": "assistant", "content": "assistant one"},
        {"role": "user", "content": "participant two"},
        {"role": "assistant", "content": "assistant two"},
        {"role": "user", "content": "latest participant"},
    ]


def test_interloper_history_is_reversed_and_contains_both_responses() -> None:
    messages = shared_interloper_history(
        "prior participant", {"A": "layered with smoked", "B": "other branch"}
    )
    assert messages[0] == {"role": "assistant", "content": "prior participant"}
    assert messages[1]["role"] == "user"
    assert '"assistant_A": "layered with smoked"' in messages[1]["content"]
    assert '"assistant_B": "other branch"' in messages[1]["content"]
    assert all(
        item["role"] != "assistant" or item["content"] != "layered with smoked"
        for item in messages
    )


def test_exact_request_builders_preserve_perspective_and_seed() -> None:
    thread = ThreadSpec("A", "opening", ("practical concern",))
    qwen = build_shared_interloper_request(
        thread=thread,
        prior_participant="previous participant",
        responses={"A": "response A", "B": "response B"},
        turn=2,
    )
    gemma = build_subject_request(
        pairs=[("participant", "Gemma response")],
        participant_message="new participant",
        seed=1001,
        memory_system=None,
        turn=2,
    )
    assert qwen.messages[0]["role"] == "assistant"
    assert qwen.messages[-1]["role"] == "user"
    assert gemma.messages[-2] == {"role": "assistant", "content": "Gemma response"}
    assert gemma.messages[-1] == {"role": "user", "content": "new participant"}
    assert gemma.seed == 1001


def test_treatment_gate_requires_actual_nonzero_mneme_application() -> None:
    assert not treatment_exposure_gate(
        [{"eligible_state": True, "selected_count": 0, "applied_count": 0, "control_influence": 0}]
    )["valid"]
    result = treatment_exposure_gate(
        [
            {
                "coordinate": "A:1",
                "eligible_state": True,
                "selected_count": 1,
                "applied_count": 1,
                "control_influence": 0,
            }
        ]
    )
    assert result["valid"] is True
    assert result["first_applied_coordinate"] == "A:1"
