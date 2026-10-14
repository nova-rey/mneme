"""Frozen MI4 Qwen coordinate construction (no inference or mutable state)."""

from __future__ import annotations

import hashlib
import random
import re
from typing import Any


def _messages(
    system: str,
    user: str,
    *,
    visible: str | None,
    neighborhoods: dict[str, Any],
    wrapper: dict[str, str],
) -> list[dict[str, str]]:
    if visible is not None:
        descriptor = neighborhoods[visible]["descriptor_text"]
        user = wrapper["prefix"] + descriptor + wrapper["suffix"] + user
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _request(
    protocol: dict[str, Any], *, seed: int, thinking: bool, messages: list[dict[str, str]]
) -> dict[str, Any]:
    generation = protocol["generation"]
    sampler = generation["sampler"]
    return {
        "messages": messages,
        "seed": seed,
        "temperature": sampler["temperature"],
        "top_k": sampler["top_k"],
        "top_p": sampler["top_p"],
        "min_p": sampler["min_p"],
        "max_tokens": sampler["max_tokens"],
        "cache_prompt": False,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }


def build_heldout_coordinates(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand the frozen prompt × seed × condition × thinking matrix."""
    heldout = protocol["heldout"]
    neighborhoods = protocol["neighborhoods"]
    wrapper = protocol["calibration"]["visible_prompt_wrapper"]
    system = protocol["generation"]["system"]
    output: list[dict[str, Any]] = []
    for prompt_index, prompt in enumerate(heldout["prompts"]):
        for seed_index, seed in enumerate(heldout["seeds"]):
            conditions = list(heldout["conditions"])
            order_seed = 2026101407 + 100 * prompt_index + seed_index
            random.Random(order_seed).shuffle(conditions)
            for thinking in (False, True):
                for order_index, condition in enumerate(conditions):
                    visible = {
                        "visible_A_resilience": "A_resilience",
                        "visible_B_simplicity": "B_simplicity",
                    }.get(condition)
                    bank = {
                        "latent_A_resilience": "A_resilience",
                        "latent_B_simplicity": "B_simplicity",
                        "latent_irrelevant_visual_composition": "irrelevant_visual_composition",
                    }.get(condition)
                    identity = (
                        f"{prompt['id']}__s{seed}__{'on' if thinking else 'off'}__{condition}"
                    )
                    messages = _messages(
                        system,
                        prompt["user"],
                        visible=visible,
                        neighborhoods=neighborhoods,
                        wrapper=wrapper,
                    )
                    output.append(
                        {
                            "coordinate_id": identity,
                            "fixture_id": prompt["id"],
                            "seed": seed,
                            "thinking": thinking,
                            "condition": condition,
                            "bank": bank,
                            "order_seed": order_seed,
                            "order_index": order_index,
                            "request": _request(
                                protocol, seed=seed, thinking=thinking, messages=messages
                            ),
                            "expected": {"not_in_prompt": [] if bank is not None else None},
                        }
                    )
    if len(output) != int(heldout["coordinates_per_mode"]) * len(heldout["mode_matrix"]):
        raise ValueError("frozen MI4 heldout matrix cardinality mismatch")
    return output


def validate_heldout_coordinate(protocol: dict[str, Any], coordinate: dict[str, Any]) -> None:
    """Fail closed on latent prompt contamination or a changed control."""
    request = coordinate["request"]
    if request.get("cache_prompt") is not False or request.get("stream") is not True:
        raise ValueError("sensitive MI4 requests require streaming and cache_prompt=false")
    messages = request["messages"]
    if len(messages) != 2 or messages[0] != {
        "role": "system",
        "content": protocol["generation"]["system"],
    }:
        raise ValueError("MI4 system or message structure changed")
    if coordinate["bank"] is not None:
        text = "\n".join(message["content"] for message in messages).casefold()
        pattern = re.compile(r"\b(?:harbor|tides?|docks?|port|maritime)\b", re.IGNORECASE)
        found = sorted({match.group(0).casefold() for match in pattern.finditer(text)})
        if found:
            raise ValueError(f"latent prompt contains forbidden target material: {found}")


def protocol_sha256(protocol_bytes: bytes) -> str:
    return hashlib.sha256(protocol_bytes).hexdigest()
