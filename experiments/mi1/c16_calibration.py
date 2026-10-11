"""Frozen C16 diagnostic for assistant-authored MI1 memory encoding."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.mi1.c12_calibration import MODEL, SEEDS, SYSTEM_PLAIN

ASSISTANT_CUE = (
    "You have an additional internal note available to your attention, although its text is "
    "not printed in this conversation. Use the note's actual contents as evidence if they are "
    "available; do not invent or infer a value. If no usable note is available, answer unknown. "
    "Reply with exactly one candidate label or unknown."
)

CALIBRATION_FIXTURES = (
    {"fixture_id": "A41", "item": "canvas pouch", "target": "Mero", "decoy": "Tavi"},
    {"fixture_id": "A42", "item": "signal lamp", "target": "Peka", "decoy": "Doru"},
    {"fixture_id": "A43", "item": "water filter", "target": "Sumi", "decoy": "Garo"},
    {"fixture_id": "A44", "item": "survey case", "target": "Leki", "decoy": "Voma"},
)

HELDOUT_FIXTURES = (
    {"fixture_id": "A45", "item": "rope bag", "target": "Neri", "decoy": "Kavu"},
    {"fixture_id": "A46", "item": "repair kit", "target": "Besa", "decoy": "Yori"},
    {"fixture_id": "A47", "item": "food tin", "target": "Haku", "decoy": "Cemi"},
    {"fixture_id": "A48", "item": "map case", "target": "Feli", "decoy": "Ravo"},
)

CONDITIONS = (
    "no_bank",
    "cue_no_bank",
    "visible_A",
    "visible_B",
    "latent_assistant_turn_A",
    "latent_assistant_turn_B",
)


def fact_text(fixture: dict[str, str], side: str) -> str:
    value = fixture["target"] if side == "A" else fixture["decoy"]
    return f"The stored codeword for the {fixture['item']} is {value}."


def assistant_bank_text(fixture: dict[str, str], side: str) -> str:
    fact = fact_text(fixture, side)
    return f"<|turn>assistant\n{fact}<turn|>\n"


def _coordinate(fixture: dict[str, str], condition: str, seed: int, phase: str) -> dict[str, Any]:
    side = condition[-1] if condition.endswith(("_A", "_B")) else None
    latent = condition.startswith("latent_")
    source = (
        assistant_bank_text(fixture, side)
        if latent and side
        else (fact_text(fixture, side) if side else None)
    )
    if condition == "no_bank":
        system = SYSTEM_PLAIN
    elif condition == "cue_no_bank":
        system = "You are answering a small fictional stored-fact question. " + ASSISTANT_CUE
    else:
        system = (
            "You are solving a small fictional stored-fact question. A private side-memory "
            "note may be available to your attention even though it is not printed in the "
            "conversation. Treat an available note as evidence; do not reject it merely "
            "because it is hidden from the visible prompt. If no usable note is available, "
            "answer unknown. Reply with exactly one candidate label or unknown."
        )
    user = (
        f"Which label does the archived note associate with the {fixture['item']}: "
        f"{fixture['target']} or {fixture['decoy']}? If the note's value is unavailable, "
        "answer unknown."
    )
    if condition.startswith("visible_") and side:
        user = f"Visible record:\n- {fact_text(fixture, side)}\n\nQuestion:\n{user}"
    expected = "unknown" if side is None else fixture["target"] if side == "A" else fixture["decoy"]
    config = {
        "selector": "none" if not latent else f"selected_{side}",
        "gain": None if not latent else {"logit_bias": math.log(4.0), "relative_prior": 4.0},
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
        "coordinate_id": f"C16-{phase}-{fixture['fixture_id']}-{condition}-{seed}",
        "fixture_id": fixture["fixture_id"],
        "item": fixture["item"],
        "seed": seed,
        "condition": condition,
        "bank_action": "attach" if latent else "clear",
        "bank_source": source if latent else None,
        "bank_source_sha256": (
            hashlib.sha256(source.encode()).hexdigest() if latent and source is not None else None
        ),
        "bank_encoding": "assistant_turn" if latent else None,
        "bank_fact": fact_text(fixture, side) if latent and side else None,
        "tokenization_mode": "chat-special" if latent else "raw",
        "bank_config": config,
        "expected": {"answer": expected},
        "metadata": {
            "suite": "c16_assistant_authored_memory",
            "phase": phase,
            "fixture_id": fixture["fixture_id"],
            "seed": seed,
            "condition": condition,
            "encoding": "assistant_turn" if latent else None,
            "selector": config["selector"],
            "server_role": "mi1_server",
        },
        "request": request,
        "request_sha256": hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def build_c16_plan(*, c15b_readout_sha256: str, selector_map_sha256: str) -> dict[str, Any]:
    if any(len(value) != 64 for value in (c15b_readout_sha256, selector_map_sha256)):
        raise ValueError("C16 parent readout and selector map must be SHA-256 values")
    calibration = [
        _coordinate(fixture, condition, seed, "calibration")
        for fixture in CALIBRATION_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    confirmation = [
        _coordinate(fixture, condition, seed, "confirmation")
        for fixture in HELDOUT_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
        if condition != "cue_no_bank"
    ]
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C16 assistant-authored memory calibration",
        "revision": "C16",
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "parents": {
            "c15b_readout_sha256": c15b_readout_sha256,
            "selected_site_map_sha256": selector_map_sha256,
        },
        "model": {
            "name": MODEL,
            "gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03",
            "llama_cpp_commit": "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        },
        "hypothesis": (
            "C14-C15 bank K/V are attached and numerically attended, but raw, system-turn, and "
            "user-turn facts are not retrieved. C16 tests one remaining role-specific encoding: "
            "the same fact as a completed assistant-authored note. The fact sentence, task, "
            "selector, gain, and scoring thresholds remain otherwise fixed."
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
            "parallel_slots": 1,
        },
        "encoding": {
            "mode": "assistant_turn",
            "source_format": "<|turn>assistant\\n{fact}<turn|>\\n",
            "tokenization": "llama_tokenize(add_special=true,parse_special=true)",
        },
        "calibration_fixtures": list(CALIBRATION_FIXTURES),
        "heldout_fixtures": list(HELDOUT_FIXTURES),
        "conditions": list(CONDITIONS),
        "coordinates": calibration,
        "call_count": len(calibration),
        "confirmation_coordinates_frozen_not_authorized_until_gate": confirmation,
        "confirmation_call_count": len(confirmation),
        "criteria": {
            "latent_each_polarity_minimum": 6,
            "visible_each_polarity_minimum": 7,
            "unknown_control_minimum": 7,
            "denominator_per_condition": len(CALIBRATION_FIXTURES) * len(SEEDS),
            "confirmation_latent_each_polarity_minimum": 7,
            "confirmation_visible_each_polarity_minimum": 7,
            "confirmation_unknown_control_minimum": 7,
            "confirmation_denominator_per_condition": len(HELDOUT_FIXTURES) * len(SEEDS),
        },
        "selection_rule": (
            "Run held-out confirmation only if assistant-turn latent A and B each reach 6/8, "
            "visible A and B each reach 7/8, and both no-bank and cue-only controls reach 7/8. "
            "Confirmation requires at least 7/8 for each frozen condition."
        ),
    }


def _normalized(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.lower()).split())


def score_c16(
    plan_path: Path, evidence_root: Path, *, phase: str = "calibration"
) -> dict[str, Any]:
    if phase not in {"calibration", "confirmation"}:
        raise ValueError("phase must be calibration or confirmation")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    expected_rows = (
        plan["coordinates"]
        if phase == "calibration"
        else plan["confirmation_coordinates_frozen_not_authorized_until_gate"]
    )
    expected = {row["coordinate_id"]: row for row in expected_rows}
    index = json.loads((evidence_root / "index.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[str] = set()
    for attempt in index["attempts"]:
        key = attempt["attempt_id"]
        if key not in expected:
            continue
        if key in seen:
            raise ValueError(f"duplicate C16 attempt: {key}")
        seen.add(key)
        if attempt["status"] != "COMPLETE":
            missing.append(key)
            continue
        outcome = json.loads(
            (evidence_root / "attempts" / attempt["outcome_file"]).read_text(encoding="utf-8")
        )
        if outcome.get("attempt_id") != key or outcome.get("status") != "COMPLETE":
            raise ValueError(f"invalid C16 completion envelope: {key}")
        choices = outcome.get("payload", {}).get("choices", [])
        if len(choices) != 1:
            raise ValueError(f"C16 requires exactly one choice: {key}")
        message = choices[0].get("message", {})
        answer = str(message.get("content") or "").strip()
        row = expected[key]
        records.append(
            {
                "coordinate_id": key,
                "fixture_id": row["fixture_id"],
                "condition": row["condition"],
                "seed": row["seed"],
                "expected": row["expected"]["answer"],
                "answer": answer,
                "exact_label_hit": _normalized(answer) == _normalized(row["expected"]["answer"]),
                "finish_reason": choices[0].get("finish_reason"),
                "request_sha256": attempt["request_sha256"],
                "outcome_sha256": attempt["outcome_sha256"],
                "reasoning_bytes": len(str(message.get("reasoning_content") or "").encode()),
            }
        )
    missing.extend(sorted(set(expected) - seen))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        groups[row["condition"]].append(row)
    rates = {
        condition: {
            "n": len(rows),
            "hits": sum(row["exact_label_hit"] for row in rows),
            "rate": sum(row["exact_label_hit"] for row in rows) / len(rows),
        }
        for condition, rows in sorted(groups.items())
    }
    criteria = plan["criteria"]
    latent = "latent_assistant_turn_"
    if phase == "calibration":
        passed = (
            rates.get(f"{latent}A", {}).get("hits", 0) >= criteria["latent_each_polarity_minimum"]
            and rates.get(f"{latent}B", {}).get("hits", 0)
            >= criteria["latent_each_polarity_minimum"]
            and rates.get("visible_A", {}).get("hits", 0)
            >= criteria["visible_each_polarity_minimum"]
            and rates.get("visible_B", {}).get("hits", 0)
            >= criteria["visible_each_polarity_minimum"]
            and rates.get("no_bank", {}).get("hits", 0) >= criteria["unknown_control_minimum"]
            and rates.get("cue_no_bank", {}).get("hits", 0) >= criteria["unknown_control_minimum"]
        )
    else:
        passed = (
            rates.get(f"{latent}A", {}).get("hits", 0)
            >= criteria["confirmation_latent_each_polarity_minimum"]
            and rates.get(f"{latent}B", {}).get("hits", 0)
            >= criteria["confirmation_latent_each_polarity_minimum"]
            and rates.get("visible_A", {}).get("hits", 0)
            >= criteria["confirmation_visible_each_polarity_minimum"]
            and rates.get("visible_B", {}).get("hits", 0)
            >= criteria["confirmation_visible_each_polarity_minimum"]
            and rates.get("no_bank", {}).get("hits", 0)
            >= criteria["confirmation_unknown_control_minimum"]
        )
    return {
        "schema_version": 1,
        "experiment": plan["experiment"],
        "phase": phase,
        "scheduled_coordinates": len(expected),
        "complete_coordinates": len(records),
        "missing_or_uncertain_coordinates": sorted(missing),
        "condition_rates": rates,
        "calibration_gate_passed": passed if phase == "calibration" else None,
        "heldout_confirmation_authorized_by_gate": passed if phase == "calibration" else None,
        "confirmation_passed": passed if phase == "confirmation" else None,
        "coordinates": records,
    }
