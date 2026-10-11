"""C13 diagnostic separating stronger availability framing from site breadth."""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any

from experiments.mi1.c12_calibration import (
    CALIBRATION_FIXTURES,
    HELDOUT_FIXTURES,
    MODEL,
    SEEDS,
    SYSTEM_CUED,
    SYSTEM_PLAIN,
)

ASSERTIVE_CUE = (
    "You have an additional internal record containing task facts available to you for this "
    "response. Its exact text is not printed in the conversation, but it is part of the "
    "information available to your attention. Treat the record's actual contents as evidence "
    "and use them to answer the question; do not infer missing details from this instruction. "
    "If no record is actually available, answer unknown. Reply with exactly one candidate "
    "label or unknown."
)

CONDITIONS = (
    "no_bank",
    "cue_no_bank_assertive",
    "visible_A",
    "visible_B",
    "latent_A_selected_assertive_fourfold",
    "latent_B_selected_assertive_fourfold",
    "latent_A_broad_assertive_fourfold",
    "latent_B_broad_assertive_fourfold",
    "latent_irrelevant_broad_assertive_fourfold",
)
LOGIT_BIAS = math.log(4.0)


def _bank_text(fixture: dict[str, str], side: str) -> str:
    if side == "A":
        start, middle, terminal = fixture["start"], fixture["middle"], fixture["target"]
    elif side == "B":
        start, middle, terminal = fixture["start"], fixture["middle"], fixture["decoy"]
    elif side == "irrelevant":
        start, middle, terminal = fixture["other"], fixture["unused"], fixture["decoy"]
    else:
        raise ValueError(f"unknown C13 bank side: {side}")
    return f"- {start} activates {middle}.\n- {middle} activates {terminal}.\n"


def _condition(condition: str) -> tuple[str | None, str | None]:
    if condition in {"visible_A", "visible_B"}:
        side = condition[-1]
        return side, "visible"
    if condition.startswith("latent_A_"):
        return "A", "selected" if "selected" in condition else "broad"
    if condition.startswith("latent_B_"):
        return "B", "selected" if "selected" in condition else "broad"
    if condition == "latent_irrelevant_broad_assertive_fourfold":
        return "irrelevant", "broad"
    return None, None


def _make_coordinate(
    fixture: dict[str, str], condition: str, seed: int, *, heldout: bool = False
) -> dict[str, Any]:
    side, route = _condition(condition)
    source = _bank_text(fixture, side) if side else None
    if condition == "no_bank":
        system = SYSTEM_PLAIN
    elif condition == "cue_no_bank_assertive" or route == "broad" or route == "selected":
        system = "You are solving a small fictional directed-reachability task. " + ASSERTIVE_CUE
    else:
        system = SYSTEM_CUED

    visible_source = source if route == "visible" else None
    start = fixture["start"]
    first, second = fixture["target"], fixture["decoy"]
    prompt = (
        f"Begin at {start}. Follow only the stored directed links. Can {first} or {second} "
        "be reached?"
        if heldout
        else f"Starting only at {start}, which of {first} or {second} is reachable by following "
        "the directed links?"
    )
    user = f"Visible record:\n{visible_source}\n\nQuestion:\n{prompt}" if visible_source else prompt
    expected = "unknown"
    if side == "A":
        expected = fixture["target"]
    elif side == "B":
        expected = fixture["decoy"]
    bank_selector = "none"
    gain: dict[str, float] | None = None
    if route in {"selected", "broad"}:
        bank_selector = "selected_A" if route == "selected" else "all_heads"
        if side == "B" and route == "selected":
            bank_selector = "selected_B"
        gain = {"logit_bias": LOGIT_BIAS, "relative_prior": 4.0}

    fixture_id = fixture["fixture_id"]
    coordinate_id = f"C13-{fixture_id}-{condition}-{seed}"
    request = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
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
    expected_path = (
        [fixture["start"], fixture["middle"], fixture["target"]]
        if side == "A"
        else [fixture["start"], fixture["middle"], fixture["decoy"]]
        if side == "B"
        else []
    )
    return {
        "coordinate_id": coordinate_id,
        "fixture_id": fixture_id,
        "seed": seed,
        "condition": condition,
        "bank_action": "attach" if route in {"selected", "broad"} else "clear",
        "bank_source": source if route in {"selected", "broad"} else None,
        "bank_source_sha256": hashlib.sha256(source.encode()).hexdigest()
        if source and route in {"selected", "broad"}
        else None,
        "bank_config": {
            "selector": bank_selector,
            "gain": gain,
        },
        "expected": {"answer": expected, "path": expected_path},
        "metadata": {
            "suite": "c13_calibration",
            "fixture_id": fixture_id,
            "seed": seed,
            "condition": condition,
            "selector": bank_selector,
            "server_role": "mi1_server",
        },
        "request": request,
    }


def build_c13_plan(c12_plan: dict[str, Any], *, c12_plan_sha256: str) -> dict[str, Any]:
    """Freeze 72 calibration calls plus the already withheld C12 fixture bank."""
    if c12_plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C13 parent calibration must be frozen")
    coordinates = [
        _make_coordinate(fixture, condition, seed)
        for fixture in CALIBRATION_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    heldout = copy.deepcopy(list(HELDOUT_FIXTURES))
    confirmation_coordinates = [
        _make_coordinate(fixture, condition, seed, heldout=True)
        for fixture in heldout
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    selected_gate = {
        "minimum_per_polarity": 7,
        "denominator": len(heldout) * len(SEEDS),
        "visible_each_polarity_minimum": 7,
        "unknown_controls_minimum": 7,
        "requirement": "At least one of selected or broad must pass A and B; choose selected if both pass.",
    }
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C13 availability-cue and site-breadth diagnostic",
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "parent_c12_plan_sha256": c12_plan_sha256,
        "site_selection_sha256": c12_plan["site_selection_sha256"],
        "model": c12_plan["model"],
        "generation_config": c12_plan["generation_config"],
        "calibration_fixture_ids": [row["fixture_id"] for row in CALIBRATION_FIXTURES],
        "heldout_fixture_ids_frozen_but_not_run": [row["fixture_id"] for row in heldout],
        "heldout_fixtures": heldout,
        "confirmation_conditions_frozen_but_not_run": list(CONDITIONS),
        "confirmation_call_count_if_one_routing_mode_is_selected": len(heldout)
        * len(SEEDS)
        * (len(CONDITIONS) - 2),
        "confirmation_coordinates_frozen_but_not_run": confirmation_coordinates,
        "seeds": list(SEEDS),
        "conditions": list(CONDITIONS),
        "assertive_cue": ASSERTIVE_CUE,
        "design_rationale": (
            "C12's generic may-be-available cue was interpreted by reasoning as no record was "
            "provided, despite a matching attached bank and measured selected-site attention. "
            "C13 tests a non-content assertive availability cue and broad all-query-head routing, "
            "with a cue-only control and irrelevant-bank control. No bank fact is in latent prompt text."
        ),
        "criteria": {
            "calibration_per_polarity_minimum": 7,
            "calibration_denominator": len(CALIBRATION_FIXTURES) * len(SEEDS),
            "visible_each_polarity_minimum": 7,
            "unknown_controls_minimum": 7,
            "confirmation_per_polarity_minimum": 14,
            "confirmation_denominator": selected_gate["denominator"],
            "confirmation_controls_minimum": 14,
            "selection_rule": "Choose selected-site confirmation if selected A and B both pass; otherwise choose broad-site confirmation if broad A and B both pass; if both pass prefer selected sites.",
        },
        "call_count": len(coordinates),
        "coordinates": coordinates,
    }
