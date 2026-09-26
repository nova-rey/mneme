# ruff: noqa: E501
"""Small, explicit contracts for the paired shared-Interloper experiment.

The experiment has two independent assistant histories and one participant
history.  Keeping the renderers here makes the provider-visible role mapping
reviewable and prevents a branch response from leaking into its sibling.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..contracts import GenerationRequest

SHARED_INTERLOPER_SYSTEM_PROMPT = """You are simulating one ordinary human conversational partner in two parallel conversations with closely matched assistants.

After each turn you may privately receive both assistant responses, labeled A and B. Write exactly one natural next human message that would make conversational sense if either assistant received it independently. Both assistants receive that exact same message.

Do not mention that there are two assistants, compare their answers, tell either assistant what the other said, merge unique content from one response into the other assistant's environment, or reveal the experimental setup. Maintain the current subject and advance the declared conversational arc. A brief tangent is fine, but return to the practical situation when the schedule calls for it.

This is a participant conversation, not an evaluation or research task. Do not test memory, request callbacks, teach target associations, or invent an outcome to validate either assistant. Keep your own concerns and voice. You may disagree, interrupt, become bored, leave a thread unfinished, say "anyway," or change subjects naturally.

When responses are supplied, find a continuation that is independently appropriate after either response. Do not average them or import a unique recommendation from one branch into the other. If no honest shared continuation exists, return the exact signal SHARED_ENVIRONMENT_DIVERGENCE and nothing else.

Write only the participant's next message."""

GEMMA_SYSTEM_PROMPT = "You are a helpful AI assistant in an ordinary conversation. Respond naturally to the participant's message."


@dataclass(frozen=True)
class ThreadSpec:
    """Frozen public setup and private participant circumstances for one thread."""

    thread_id: str
    opening: str
    concerns: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "opening": self.opening,
            "concerns": list(self.concerns),
        }


def subject_history(
    pairs: Sequence[tuple[str, str]], *, current: str, limit: int = 2
) -> tuple[dict[str, str], ...]:
    """Render a Gemma request from its own perspective."""

    messages: list[dict[str, str]] = []
    for participant, assistant in pairs[-limit:]:
        messages.extend(
            (
                {"role": "user", "content": participant},
                {"role": "assistant", "content": assistant},
            )
        )
    messages.append({"role": "user", "content": current})
    return tuple(messages)


def shared_interloper_history(
    prior_participant: str | None,
    responses: Mapping[str, str],
) -> tuple[dict[str, str], ...]:
    """Render Qwen's private history with both sibling responses as input."""

    payload = json.dumps(
        {"assistant_A": responses["A"], "assistant_B": responses["B"]},
        ensure_ascii=False,
        sort_keys=True,
    )
    messages: list[dict[str, str]] = []
    if prior_participant is not None:
        messages.append({"role": "assistant", "content": prior_participant})
    messages.append(
        {
            "role": "user",
            "content": "The assistants' latest replies are private inputs to you.\n" + payload,
        }
    )
    return tuple(messages)


def build_shared_interloper_request(
    *,
    thread: ThreadSpec,
    prior_participant: str | None,
    responses: Mapping[str, str],
    turn: int,
) -> GenerationRequest:
    """Create one shared Qwen request without sibling-response leakage."""

    private_state = (
        f"Current environment window: thread {thread.thread_id}; turn {turn}.\n"
        "Private practical concerns:\n- " + "\n- ".join(thread.concerns)
    )
    return GenerationRequest(
        shared_interloper_history(prior_participant, responses),
        system=SHARED_INTERLOPER_SYSTEM_PROMPT + "\n\n" + private_state,
        parameters={"temperature": 0.7, "top_p": 0.9, "max_new_tokens": 192},
    )


def build_subject_request(
    *,
    pairs: Sequence[tuple[str, str]],
    participant_message: str,
    seed: int,
    memory_system: str | None,
    turn: int,
) -> GenerationRequest:
    """Create one branch request from only that branch's history."""

    return GenerationRequest(
        subject_history(pairs, current=participant_message),
        system=memory_system or GEMMA_SYSTEM_PROMPT,
        parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
        seed=seed,
        run_metadata={"role_perspective": "gemma-branch", "turn": turn},
    )


def require_nonempty_message(content: str, *, role: str) -> str:
    """Fail closed for null/blank conversational content."""

    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"{role} returned an empty conversational message")
    return content.strip()


def treatment_exposure_gate(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize the mandatory MNEME-vs-control exposure validity gate."""

    selected = [item for item in records if int(item.get("selected_count", 0)) > 0]
    applied = [item for item in records if int(item.get("applied_count", 0)) > 0]
    eligible = any(bool(item.get("eligible_state")) for item in records)
    control_zero = all(int(item.get("control_influence", 0)) == 0 for item in records)
    return {
        "eligible_state": eligible,
        "selected_influence": bool(selected),
        "applied_influence": bool(applied),
        "control_influence_zero": control_zero,
        "valid": eligible and bool(selected) and bool(applied) and control_zero,
        "first_applied_coordinate": applied[0].get("coordinate") if applied else None,
    }


__all__ = [
    "GEMMA_SYSTEM_PROMPT",
    "SHARED_INTERLOPER_SYSTEM_PROMPT",
    "ThreadSpec",
    "build_shared_interloper_request",
    "build_subject_request",
    "require_nonempty_message",
    "shared_interloper_history",
    "subject_history",
    "treatment_exposure_gate",
]
