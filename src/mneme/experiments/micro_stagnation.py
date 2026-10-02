"""Isolated experimental semantic readings; never part of conversation generation.

This module only selects recorded prefixes, serializes exact source text and
parses a classification. It has no host, persistence or developmental imports.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from mneme.experiments.pressure_meters import INPUT_KEYS

VERSION = "micro-stagnation-v1"


def checkpoint_windows(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Select the last five accepted exchanges at observed arc ages 5, 10, ...

    Input must start at each conversation's first accepted turn, as do the
    passive meter inputs. Gaps in global ordinals do not advance accepted age.
    Arc identities come from the existing tracker; this does not detect pivots.
    Missing text leaves the checkpoint unavailable rather than shortening it.
    """
    states: dict[str, dict[str, Any]] = {}
    output: list[dict[str, Any]] = []
    for record in records:
        if set(record) - INPUT_KEYS:
            raise ValueError("unexpected meter input keys")
        cid, arc, ordinal = (record.get(k) for k in ("conversation", "arc_id", "ordinal"))
        if (not isinstance(cid, str) or not cid or not isinstance(arc, str) or not arc
                or not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0):
            raise ValueError("invalid conversation, arc or ordinal")
        state = states.setdefault(cid, {"ordinal": -1, "arc": None, "arcs": set(),
                                        "turn_ids": set(), "history": []})
        turn_id = record.get("accepted_turn_id", f"{cid}:turn:{ordinal}")
        if (ordinal <= state["ordinal"] or not isinstance(turn_id, str) or not turn_id
                or turn_id in state["turn_ids"]):
            raise ValueError("ordinals and accepted turn identities must advance")
        if arc != state["arc"]:
            if arc in state["arcs"]:
                raise ValueError("an arc cannot recur")
            state.update(arc=arc, history=[])
            state["arcs"].add(arc)
        exchange = {}
        for source in ("participant", "gemma"):
            value = record.get(source + "_text")
            if value is not None and not isinstance(value, str):
                raise ValueError("text must be a string or unavailable")
            exchange[source] = value
        state["history"].append({"turn_id": turn_id, "exchange": exchange})
        state["turn_ids"].add(turn_id)
        state["ordinal"] = ordinal
        age = len(state["history"])
        if age % 5 == 0:
            recent = state["history"][-5:]
            available = all(isinstance(v, str) and v.strip()
                            for row in recent for v in row["exchange"].values())
            output.append({
                "measurement_version": VERSION, "conversation": cid, "arc_id": arc,
                "arc_age": age, "ordinal": ordinal, "turn": record.get("turn"),
                "accepted_turn_id": turn_id, "window_turn_ids": [x["turn_id"] for x in recent],
                "available": available,
                "unavailable_reason": None if available else "missing recent source text",
                "exchanges": [dict(x["exchange"]) for x in recent],
            })
    return output


def build_payload(exchanges: Sequence[Mapping[str, str]], system: str,
                  config: Mapping[str, Any]) -> dict[str, Any]:
    """No metadata, SAA, earlier assessments or private condition labels enter here."""
    if len(exchanges) != 5:
        raise ValueError("exactly five complete recent exchanges are required")
    if not isinstance(system, str) or not system.strip():
        raise ValueError("a frozen system prompt is required")
    safe = []
    for exchange in exchanges:
        if set(exchange) != {"participant", "gemma"} or any(
            not isinstance(value, str) or not value.strip() for value in exchange.values()
        ):
            raise ValueError("exchange requires only exact participant and gemma text")
        safe.append({"participant": exchange["participant"], "gemma": exchange["gemma"]})
    if config.get("reasoning_effort") != "none" or config.get("max_tokens") != 8:
        raise ValueError("micro configuration requires reasoning none and eight output tokens")
    model, seed = config["model"], config["seed"]
    temperature, top_p = config["temperature"], config["top_p"]
    if not isinstance(model, str) or not model or not isinstance(seed, int) \
            or isinstance(seed, bool):
        raise ValueError("explicit model and integer seed required")
    if (isinstance(temperature, bool) or not isinstance(temperature, (int, float))
            or not 0 <= temperature <= 2 or isinstance(top_p, bool)
            or not isinstance(top_p, (int, float)) or not 0 < top_p <= 1):
        raise ValueError("invalid explicit decoding settings")
    if (type(config.get("top_k")) is not int or config["top_k"] < 1
            or isinstance(config.get("min_p"), bool)
            or not isinstance(config.get("min_p"), (float, int))
            or not 0 <= config["min_p"] <= 1 or config.get("cache_prompt") is not False):
        raise ValueError("explicit top_k/min_p and cache_prompt false required")
    return {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(
                         {"recent_conversation": safe}, ensure_ascii=False)}],
        "temperature": temperature, "top_p": top_p, "seed": seed,
        "max_tokens": 8, "reasoning_effort": "none", "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "top_k": config["top_k"], "min_p": config["min_p"],
        "cache_prompt": config["cache_prompt"],
    }


def parse_classification(content: Any, finish_reason: Any,
                         allowed_values: Sequence[int]) -> dict[str, Any]:
    """Fail closed: no searching prose for digits or accepting truncated output."""
    if tuple(allowed_values) not in ((0, 1), (0, 1, 2)) or any(
        type(value) is not int for value in allowed_values
    ):
        raise ValueError("allowed values must declare binary or ternary format")
    reason = None
    if finish_reason != "stop":
        reason = "completion did not stop normally"
    elif not isinstance(content, str) or content.strip() not in {str(x) for x in allowed_values}:
        reason = "not exactly one permitted digit"
    return {"value": int(content.strip()) if reason is None else None,
            "available": reason is None, "unavailable_reason": reason}
