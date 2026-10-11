"""Frozen atomic-fact diagnostic separating bank access from graph reasoning."""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any

from experiments.mi1.c12_calibration import MODEL, SEEDS, SYSTEM_CUED, SYSTEM_PLAIN

ASSERTIVE_CUE = (
    "You have an additional internal record containing task facts available to you for this "
    "response. Its exact text is not printed in the conversation, but it is part of the "
    "information available to your attention. Treat the record's actual contents as evidence "
    "and use them to answer the question; do not infer missing details from this instruction. "
    "If no record is actually available, answer unknown. Reply with exactly one candidate "
    "label or unknown."
)

CALIBRATION_FIXTURES = (
    {"fixture_id": "A25", "item": "equipment locker", "target": "Tulo", "decoy": "Fera"},
    {"fixture_id": "A26", "item": "generator cabinet", "target": "Doru", "decoy": "Baki"},
    {"fixture_id": "A27", "item": "radio case", "target": "Nemi", "decoy": "Rava"},
    {"fixture_id": "A28", "item": "field kit", "target": "Sula", "decoy": "Tena"},
)

HELDOUT_FIXTURES = (
    {"fixture_id": "A29", "item": "supply cupboard", "target": "Veko", "decoy": "Miri"},
    {"fixture_id": "A30", "item": "service panel", "target": "Zanu", "decoy": "Lepo"},
    {"fixture_id": "A31", "item": "weather case", "target": "Kavi", "decoy": "Oren"},
    {"fixture_id": "A32", "item": "archive drawer", "target": "Pexa", "decoy": "Gumi"},
)

CONDITIONS = (
    "no_bank",
    "cue_no_bank_assertive",
    "visible_A",
    "visible_B",
    "latent_A_selected_twofold",
    "latent_B_selected_twofold",
    "latent_A_selected_fourfold",
    "latent_B_selected_fourfold",
)


def _source(fixture: dict[str, str], side: str) -> str:
    value = fixture["target"] if side == "A" else fixture["decoy"]
    return f"The stored codeword for the {fixture['item']} is {value}."


def _condition(condition: str) -> tuple[str | None, float | None]:
    if condition.startswith("visible_"):
        return condition[-1], None
    if condition.startswith("latent_A_"):
        return "A", 2.0 if "twofold" in condition else 4.0
    if condition.startswith("latent_B_"):
        return "B", 2.0 if "twofold" in condition else 4.0
    return None, None


def _coordinate(fixture: dict[str, str], condition: str, seed: int) -> dict[str, Any]:
    side, gain = _condition(condition)
    source = _source(fixture, side) if side else None
    if condition == "no_bank":
        system = SYSTEM_PLAIN
    elif condition == "visible_A" or condition == "visible_B":
        system = SYSTEM_CUED
    else:
        system = "You are answering a small fictional stored-fact question. " + ASSERTIVE_CUE
    first, second = fixture["target"], fixture["decoy"]
    question = (
        f"Which label does the archived note associate with the {fixture['item']}: "
        f"{first} or {second}? If the note's value is unavailable, answer unknown."
    )
    visible_source = source if condition in {"visible_A", "visible_B"} else None
    user = f"Visible record:\n- {visible_source}\n\nQuestion:\n{question}" if visible_source else question
    expected = "unknown" if side is None else fixture["target"] if side == "A" else fixture["decoy"]
    bank_selector = "none" if gain is None else "selected_A" if side == "A" else "selected_B"
    bank_config = {
        "selector": bank_selector,
        "gain": None
        if gain is None
        else {"logit_bias": math.log(gain), "relative_prior": gain},
    }
    return {
        "coordinate_id": f"C14-{fixture['fixture_id']}-{condition}-{seed}",
        "fixture_id": fixture["fixture_id"],
        "item": fixture["item"],
        "seed": seed,
        "condition": condition,
        "bank_action": "attach" if gain is not None else "clear",
        "bank_source": source if gain is not None else None,
        "bank_source_sha256": hashlib.sha256(source.encode()).hexdigest() if gain else None,
        "bank_config": bank_config,
        "expected": {"answer": expected},
        "metadata": {"suite": "c14_atomic_calibration", "fixture_id": fixture["fixture_id"], "seed": seed, "condition": condition, "selector": bank_selector, "server_role": "mi1_server"},
        "request": {
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
        },
    }


def build_c14_plan(*, c13_readout_sha256: str) -> dict[str, Any]:
    """Freeze independent atomic recall calibration and confirmation sets."""
    if len(c13_readout_sha256) != 64:
        raise ValueError("C14 must link the complete C13 readout by SHA-256")
    calibration = [
        _coordinate(fixture, condition, seed)
        for fixture in CALIBRATION_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    heldout_fixtures = copy.deepcopy(list(HELDOUT_FIXTURES))
    confirmation = [
        _coordinate(fixture, condition, seed)
        for fixture in heldout_fixtures
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C14 atomic-fact access calibration",
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "parent_c13_readout_sha256": c13_readout_sha256,
        "model": {"name": MODEL, "gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"},
        "generation_config": {"cache_prompt": False, "reasoning": "ON", "temperature": 0.35, "top_k": 40, "top_p": 0.9, "min_p": 0.05, "max_tokens": 1024},
        "seeds": list(SEEDS),
        "conditions": list(CONDITIONS),
        "calibration_fixture_ids": [row["fixture_id"] for row in CALIBRATION_FIXTURES],
        "heldout_fixture_ids_frozen_but_not_run": [row["fixture_id"] for row in heldout_fixtures],
        "heldout_fixtures": heldout_fixtures,
        "confirmation_coordinates_frozen_but_not_run": confirmation,
        "confirmation_selection_rule": "If a gain passes calibration, select the lower passing gain. Confirmation includes no-bank, cue-only, both visible polarities, and both latent polarities at the selected gain.",
        "criteria": {
            "latent_each_polarity_minimum": 6,
            "visible_each_polarity_minimum": 7,
            "unknown_control_minimum": 7,
            "calibration_denominator": 8,
            "confirmation_latent_each_polarity_minimum": 7,
            "confirmation_visible_each_polarity_minimum": 7,
            "confirmation_unknown_control_minimum": 7,
            "confirmation_denominator": 8,
        },
        "design_rationale": "C13 selected-site bank attention failed to surface two-hop directed facts, while broad routing was disruptive. C14 tests the simpler prerequisite of retrieving a single text-derived codeword fact with selected-site routing at two fixed strengths. Four calibration fixture pairs and four separate heldout pairs are frozen before generation; visible and no-bank/cue-only controls remain matched.",
        "call_count": len(calibration),
        "coordinates": calibration,
        "confirmation_call_count_per_gain": len(heldout_fixtures) * len(SEEDS) * 6,
    }
