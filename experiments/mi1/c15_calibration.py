"""Frozen calibration design for Gemma-role-aware MI1 bank encoding."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

from experiments.mi1.c12_calibration import MODEL, SEEDS, SYSTEM_PLAIN

ASSERTIVE_CUE = (
    "You have an additional internal record containing task facts available to you for this "
    "response. Its exact text is not printed in the conversation, but it is part of the "
    "information available to your attention. Treat the record's actual contents as evidence "
    "and use them to answer the question; do not infer missing details from this instruction. "
    "If no record is actually available, answer unknown. Reply with exactly one candidate "
    "label or unknown."
)

CALIBRATION_FIXTURES = (
    {"fixture_id": "A33", "item": "battery crate", "target": "Ruma", "decoy": "Kedo"},
    {"fixture_id": "A34", "item": "map tube", "target": "Pavi", "decoy": "Sero"},
    {"fixture_id": "A35", "item": "first-aid tin", "target": "Naku", "decoy": "Veli"},
    {"fixture_id": "A36", "item": "field notebook", "target": "Zori", "decoy": "Bemu"},
)

HELDOUT_FIXTURES = (
    {"fixture_id": "A37", "item": "spare key pouch", "target": "Davi", "decoy": "Yeno"},
    {"fixture_id": "A38", "item": "lamp box", "target": "Hesu", "decoy": "Qari"},
    {"fixture_id": "A39", "item": "repair roll", "target": "Luma", "decoy": "Feki"},
    {"fixture_id": "A40", "item": "seed envelope", "target": "Cavo", "decoy": "Jiri"},
)

ENCODINGS = ("raw", "system_turn", "user_turn")
CONDITIONS = (
    "no_bank",
    "cue_no_bank_assertive",
    "visible_A",
    "visible_B",
    "latent_raw_A",
    "latent_raw_B",
    "latent_system_turn_A",
    "latent_system_turn_B",
    "latent_user_turn_A",
    "latent_user_turn_B",
)


def fact_text(fixture: dict[str, str], side: str) -> str:
    value = fixture["target"] if side == "A" else fixture["decoy"]
    return f"The stored codeword for the {fixture['item']} is {value}."


def encoded_bank_text(fixture: dict[str, str], side: str, encoding: str) -> str:
    fact = fact_text(fixture, side)
    if encoding == "raw":
        return fact
    role = {"system_turn": "system", "user_turn": "user"}.get(encoding)
    if role is None:
        raise ValueError(f"unsupported C15 encoding: {encoding}")
    return f"<|turn>{role}\n{fact}<turn|>\n"


def _coordinate(
    fixture: dict[str, str], condition: str, seed: int, *, phase: str
) -> dict[str, Any]:
    side: str | None = None
    encoding: str | None = None
    if condition.startswith("visible_"):
        side = condition[-1]
    elif condition.startswith("latent_"):
        side = condition[-1]
        encoding = condition[len("latent_") : -2]
        if encoding not in ENCODINGS:
            raise ValueError(f"unsupported C15 latent condition: {condition}")
    source = (
        encoded_bank_text(fixture, side, encoding)
        if side and encoding
        else (fact_text(fixture, side) if side else None)
    )
    bank = condition.startswith("latent_")
    if condition == "no_bank":
        system = SYSTEM_PLAIN
    elif condition in {"visible_A", "visible_B"}:
        system = (
            "You are solving a small fictional stored-fact question. A private side-memory "
            "record may be available to your attention even though it is not printed in the "
            "conversation. Treat an available record as a source of facts; do not reject it "
            "merely because it is hidden from the visible prompt. If no usable record is "
            "available, answer unknown. Reply with exactly one candidate label or unknown."
        )
    else:
        system = "You are answering a small fictional stored-fact question. " + ASSERTIVE_CUE
    user = (
        f"Which label does the archived note associate with the {fixture['item']}: "
        f"{fixture['target']} or {fixture['decoy']}? If the note's value is unavailable, "
        "answer unknown."
    )
    if condition in {"visible_A", "visible_B"}:
        user = f"Visible record:\n- {source}\n\nQuestion:\n{user}"
    expected = "unknown" if side is None else fixture["target"] if side == "A" else fixture["decoy"]
    selector = "none" if not bank else f"selected_{side}"
    config = {
        "selector": selector,
        "gain": None if not bank else {"logit_bias": math.log(4.0), "relative_prior": 4.0},
    }
    request = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": True,
        "cache_prompt": False,
        "seed": seed,
        "max_tokens": 1024,
        "reasoning_format": "deepseek",
        "chat_template_kwargs": {"enable_thinking": True},
        "temperature": 0.35,
        "top_k": 40,
        "top_p": 0.9,
        "min_p": 0.05,
    }
    return {
        "coordinate_id": f"C15-{phase}-{fixture['fixture_id']}-{condition}-{seed}",
        "fixture_id": fixture["fixture_id"],
        "item": fixture["item"],
        "seed": seed,
        "condition": condition,
        "bank_action": "attach" if bank else "clear",
        "bank_source": source if bank else None,
        "bank_source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest() if bank else None,
        "bank_encoding": encoding if bank else None,
        "bank_fact": fact_text(fixture, side) if bank and side else None,
        "tokenization_mode": "chat-special" if encoding in {"system_turn", "user_turn"} else "raw",
        "bank_config": config,
        "expected": {"answer": expected},
        "metadata": {
            "suite": "c15_role_aware_bank_encoding",
            "phase": phase,
            "fixture_id": fixture["fixture_id"],
            "seed": seed,
            "condition": condition,
            "encoding": encoding,
            "selector": selector,
            "server_role": "mi1_server",
        },
        "request": request,
        "request_sha256": hashlib.sha256(
            json.dumps(
                request,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }


def build_c15_plan(*, c14_readout_sha256: str, selector_map_sha256: str) -> dict[str, Any]:
    """Freeze role-tokenization diagnostic plus independent confirmation set."""
    if any(len(value) != 64 for value in (c14_readout_sha256, selector_map_sha256)):
        raise ValueError("C15 parent and selector map must be SHA-256 values")
    calibration = [
        _coordinate(fixture, condition, seed, phase="calibration")
        for fixture in CALIBRATION_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    heldout = copy.deepcopy(list(HELDOUT_FIXTURES))
    confirmation_conditions = (
        "no_bank",
        "visible_A",
        "visible_B",
        *(condition for condition in CONDITIONS if condition.startswith("latent_")),
    )
    confirmation = [
        _coordinate(fixture, condition, seed, phase="confirmation")
        for fixture in heldout
        for seed in SEEDS
        for condition in confirmation_conditions
    ]
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C15 Gemma role-aware bank encoding diagnostic",
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "parents": {
            "c14_readout_sha256": c14_readout_sha256,
            "selected_site_map_sha256": selector_map_sha256,
        },
        "model": {
            "name": MODEL,
            "gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03",
            "llama_cpp_commit": "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        },
        "hypothesis": (
            "Plain C14 bank text is numerically attended but semantically unread. C15 tests "
            "whether the same fact encoded as an actual Gemma system/user chat turn gives the "
            "bank contextual role information. Prompt, selector, gain, facts, and controls "
            "are held fixed."
        ),
        "generation_config": {
            "cache_prompt": False,
            "reasoning": "ON",
            "temperature": 0.35,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
            "max_tokens": 1024,
            "seeds": list(SEEDS),
        },
        "encoding_modes": {
            "raw": {
                "cli_mode": "raw",
                "tokenization": "llama_tokenize(add_special=true,parse_special=false)",
            },
            "system_turn": {
                "cli_mode": "chat-special",
                "tokenization": "llama_tokenize(add_special=true,parse_special=true)",
                "role": "system",
            },
            "user_turn": {
                "cli_mode": "chat-special",
                "tokenization": "llama_tokenize(add_special=true,parse_special=true)",
                "role": "user",
            },
        },
        "calibration_fixture_ids": [row["fixture_id"] for row in CALIBRATION_FIXTURES],
        "heldout_fixture_ids": [row["fixture_id"] for row in heldout],
        "conditions": list(CONDITIONS),
        "call_count": len(calibration),
        "confirmation_coordinates_frozen_not_authorized_until_gate": confirmation,
        "confirmation_call_count": len(confirmation),
        "selection_rule": (
            "An encoding passes only if both latent polarities are >=6/8, both visible "
            "polarities >=7/8, and no-bank plus cue-only >=7/8. If multiple pass, choose "
            "the first in this predeclared order: system_turn, user_turn, raw. Only the "
            "chosen encoding's frozen held-out coordinates may then run."
        ),
        "criteria": {
            "latent_each_polarity_minimum": 6,
            "visible_each_polarity_minimum": 7,
            "unknown_control_minimum": 7,
            "denominator_per_condition": len(CALIBRATION_FIXTURES) * len(SEEDS),
            "confirmation_latent_each_polarity_minimum": 7,
            "confirmation_visible_each_polarity_minimum": 7,
            "confirmation_unknown_control_minimum": 7,
            "confirmation_denominator_per_condition": len(heldout) * len(SEEDS),
        },
        "calibration_fixtures": list(CALIBRATION_FIXTURES),
        "heldout_fixtures": heldout,
        "coordinates": calibration,
    }
