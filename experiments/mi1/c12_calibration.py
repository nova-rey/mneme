"""C12 readout-cue and bounded bank-prior calibration for MI1."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

SEEDS = (34201, 34219)
MODEL = "google/gemma-4-E4B-it"
GGUF_SHA256 = "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"
LLAMA_COMMIT = "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0"

SYSTEM_PLAIN = (
    "You are solving a small fictional directed-reachability task. Use only the facts "
    "available in this request. If no usable directed facts are available, answer unknown. "
    "Reply with exactly one candidate label or unknown."
)
SYSTEM_CUED = (
    "You are solving a small fictional directed-reachability task. A private side-memory "
    "record may be available to your attention even though it is not printed in the "
    "conversation. Treat an available record as a source of directed facts; do not reject "
    "it merely because it is hidden from the visible prompt. If no usable record is "
    "available, answer unknown. Reply with exactly one candidate label or unknown."
)

CALIBRATION_FIXTURES: tuple[dict[str, str], ...] = (
    {
        "fixture_id": "A13",
        "start": "Rava",
        "middle": "Nemi",
        "target": "Tulo",
        "decoy": "Fera",
        "other": "Savo",
        "unused": "Kiri",
    },
    {
        "fixture_id": "A14",
        "start": "Dema",
        "middle": "Vori",
        "target": "Leka",
        "decoy": "Panu",
        "other": "Gesi",
        "unused": "Mota",
    },
    {
        "fixture_id": "A15",
        "start": "Bero",
        "middle": "Cavi",
        "target": "Zuna",
        "decoy": "Hedo",
        "other": "Javi",
        "unused": "Weno",
    },
    {
        "fixture_id": "A16",
        "start": "Sula",
        "middle": "Riko",
        "target": "Mavi",
        "decoy": "Tena",
        "other": "Gora",
        "unused": "Peli",
    },
)

HELDOUT_FIXTURES: tuple[dict[str, str], ...] = (
    {
        "fixture_id": "A17",
        "start": "Filo",
        "middle": "Qena",
        "target": "Doru",
        "decoy": "Baki",
        "other": "Lumi",
        "unused": "Seki",
    },
    {
        "fixture_id": "A18",
        "start": "Wera",
        "middle": "Juno",
        "target": "Pexa",
        "decoy": "Celo",
        "other": "Rudi",
        "unused": "Navo",
    },
    {
        "fixture_id": "A19",
        "start": "Kavo",
        "middle": "Meri",
        "target": "Sadi",
        "decoy": "Vulo",
        "other": "Teki",
        "unused": "Bena",
    },
    {
        "fixture_id": "A20",
        "start": "Yeno",
        "middle": "Zavi",
        "target": "Lumo",
        "decoy": "Feki",
        "other": "Dasi",
        "unused": "Ravo",
    },
    {
        "fixture_id": "A21",
        "start": "Cira",
        "middle": "Huno",
        "target": "Gavi",
        "decoy": "Neri",
        "other": "Pavo",
        "unused": "Tumo",
    },
    {
        "fixture_id": "A22",
        "start": "Vesa",
        "middle": "Bulo",
        "target": "Reni",
        "decoy": "Meko",
        "other": "Jaso",
        "unused": "Fanu",
    },
    {
        "fixture_id": "A23",
        "start": "Ledo",
        "middle": "Tavi",
        "target": "Wemi",
        "decoy": "Qori",
        "other": "Suna",
        "unused": "Davi",
    },
    {
        "fixture_id": "A24",
        "start": "Navo",
        "middle": "Fela",
        "target": "Kesi",
        "decoy": "Yaro",
        "other": "Cumi",
        "unused": "Vena",
    },
)

BIAS = {"zero": 0.0, "twofold": math.log(2.0), "fourfold": math.log(4.0)}
CONDITIONS = (
    "no_bank",
    "cue_no_bank",
    "visible_A",
    "visible_B",
    "latent_A_zero",
    "latent_A_twofold",
    "latent_A_fourfold",
    "latent_B_zero",
    "latent_B_twofold",
    "latent_B_fourfold",
    "latent_irrelevant_fourfold",
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def bank_text(fixture: dict[str, str], side: str) -> str:
    start, middle = fixture["start"], fixture["middle"]
    if side == "A":
        terminal = fixture["target"]
    elif side == "B":
        terminal = fixture["decoy"]
    elif side == "irrelevant":
        start, middle = fixture["other"], fixture["unused"]
        terminal = fixture["decoy"]
    else:
        raise ValueError(f"unknown C12 bank side: {side}")
    return f"- {start} activates {middle}.\n- {middle} activates {terminal}.\n"


def user_text(fixture: dict[str, str], *, heldout: bool, visible: str | None) -> str:
    start = fixture["start"]
    first, second = fixture["target"], fixture["decoy"]
    if heldout:
        question = (
            f"Begin at {start}. Follow only the stored directed links. "
            f"Can {first} or {second} be reached?"
        )
    else:
        question = (
            f"Starting only at {start}, which of {first} or {second} is reachable "
            "by following the directed links?"
        )
    if visible is not None:
        return f"Visible record:\n{visible}\n\nQuestion:\n{question}"
    return question


def _coordinate(
    fixture: dict[str, str],
    *,
    condition: str,
    seed: int,
    heldout: bool = False,
) -> dict[str, Any]:
    bank_side: str | None = None
    bias_name: str | None = None
    if condition.startswith("visible_") or condition.startswith("latent_"):
        pieces = condition.split("_")
        if pieces[0] in {"visible", "latent"} and pieces[1] in {"A", "B"}:
            bank_side = pieces[1]
            bias_name = pieces[2] if pieces[0] == "latent" else None
        elif condition == "latent_irrelevant_fourfold":
            bank_side, bias_name = "irrelevant", "fourfold"
    source = bank_text(fixture, bank_side) if bank_side else None
    has_cue = condition != "no_bank"
    system = SYSTEM_CUED if has_cue else SYSTEM_PLAIN
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": user_text(
                fixture,
                heldout=heldout,
                visible=source if condition.startswith("visible_") else None,
            ),
        },
    ]
    bias = BIAS[bias_name] if bias_name else 0.0
    bank_config: dict[str, Any] = (
        {
            "selector": f"selected_{bank_side}" if bank_side in {"A", "B"} else "selected_A",
            "gain": {"logit_bias": bias, "relative_prior": math.exp(bias)},
        }
        if source is not None and condition.startswith("latent_")
        else {"selector": "none", "gain": None}
    )
    if condition == "latent_irrelevant_fourfold":
        bank_config = {
            "selector": "selected_A",
            "gain": {"logit_bias": bias, "relative_prior": math.exp(bias)},
        }
    expected = "unknown"
    if bank_side == "A":
        expected = fixture["target"]
    elif bank_side == "B":
        expected = fixture["decoy"]
    coordinate_id = f"C12-{fixture['fixture_id']}-{condition}-{seed}"
    request = {
        "model": MODEL,
        "messages": messages,
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
        "coordinate_id": coordinate_id,
        "suite": "c12_holdout" if heldout else "c12_calibration",
        "metadata": {
            "suite": "c12_holdout" if heldout else "c12_calibration",
            "fixture_id": fixture["fixture_id"],
            "condition": condition,
            "seed": seed,
            "selector": bank_config["selector"],
            "logit_bias": bank_config["gain"]["logit_bias"] if bank_config["gain"] else None,
            "expected_answer": expected,
            "server_role": "mi1_server",
        },
        "request": request,
        "request_sha256": sha256(canonical_bytes(request)),
        "bank_source": source,
        "bank_source_sha256": sha256(source.encode("utf-8")) if source else None,
        "bank_action": "attach" if source and condition.startswith("latent_") else "clear",
        "bank_config": bank_config,
        "expected": {"answer": expected, "path": []},
    }


def build_calibration_plan(
    *, c11_selection: dict[str, Any], c11_selection_sha256: str
) -> dict[str, Any]:
    """Build the 88-call cue/dose matrix; no generation is performed here."""
    if c11_selection.get("model", {}).get("gguf_sha256") not in (None, GGUF_SHA256):
        raise ValueError("C12 selector belongs to another model")
    if len(CALIBRATION_FIXTURES) != 4:
        raise ValueError("C12 calibration fixture count changed")
    coordinates = [
        _coordinate(fixture, condition=condition, seed=seed)
        for fixture in CALIBRATION_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C12 memory-readout cue and bank-prior calibration",
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "parent_c11_readout_sha256": (
            "b11f9dd67a5adc21acfeaf31affbf664f28795251f4134be1580f73550fc927a"
        ),
        "site_selection_sha256": c11_selection_sha256,
        "model": {"name": MODEL, "gguf_sha256": GGUF_SHA256, "llama_cpp_commit": LLAMA_COMMIT},
        "conditions": list(CONDITIONS),
        "bank_prior_multipliers": {key: math.exp(value) for key, value in BIAS.items()},
        "seeds": list(SEEDS),
        "calibration_fixture_ids": [row["fixture_id"] for row in CALIBRATION_FIXTURES],
        "heldout_fixture_ids_frozen_but_not_run": [row["fixture_id"] for row in HELDOUT_FIXTURES],
        "heldout_rule": (
            "For each polarity, choose the smallest bank prior with at least 7/8 correct "
            "on latent_A and latent_B; require visible_A and visible_B at least 7/8 and "
            "no_bank, cue_no_bank, and irrelevant_fourfold each at least 7/8 unknown. "
            "If no level passes, no holdout generation occurs."
        ),
        "criteria": {
            "latent_each_polarity_minimum": 7,
            "visible_each_polarity_minimum": 7,
            "unknown_control_minimum": 7,
            "per_condition_denominator": 8,
            "heldout_confirmation": "Required before any WORKS disposition.",
        },
        "cue": SYSTEM_CUED,
        "cue_contents_rule": (
            "Cue may identify that a side-memory mechanism exists; "
            "it contains none of the bank facts."
        ),
        "generation_config": {
            "reasoning": "ON",
            "cache_prompt": False,
            "max_tokens": 1024,
            "temperature": 0.35,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
        },
        "call_count": len(coordinates),
        "coordinates": coordinates,
        "fixtures": [copy.deepcopy(row) for row in (*CALIBRATION_FIXTURES, *HELDOUT_FIXTURES)],
    }


def build_holdout_plan(
    *,
    calibration_plan_sha256: str,
    selected_bias_name: str,
) -> dict[str, Any]:
    """Freeze new held-out prompts after a calibration candidate passes."""
    if selected_bias_name not in BIAS:
        raise ValueError("heldout plan requires a calibration-passing bias level")
    conditions = (
        "no_bank",
        "cue_no_bank",
        "visible_A",
        "visible_B",
        f"latent_A_{selected_bias_name}",
        f"latent_B_{selected_bias_name}",
        "latent_irrelevant_fourfold",
    )
    coordinates = [
        _coordinate(fixture, condition=condition, seed=seed, heldout=True)
        for fixture in HELDOUT_FIXTURES
        for seed in SEEDS
        for condition in conditions
    ]
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C12 independent held-out confirmation",
        "status": "FROZEN_BEFORE_HELDOUT_GENERATION",
        "calibration_plan_sha256": calibration_plan_sha256,
        "selected_bias_name": selected_bias_name,
        "conditions": list(conditions),
        "fixture_ids": [row["fixture_id"] for row in HELDOUT_FIXTURES],
        "generation_config": {
            "reasoning": "ON",
            "cache_prompt": False,
            "max_tokens": 1024,
            "temperature": 0.35,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
        },
        "call_count": len(coordinates),
        "coordinates": coordinates,
        "fixtures": [copy.deepcopy(row) for row in HELDOUT_FIXTURES],
    }
