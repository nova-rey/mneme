"""Frozen C17 maximum-access diagnostic for the isolated MI1 Gemma port.

C17 reuses C16's already-frozen fictional codeword fixtures and assistant-turn
banks. It changes only routing breadth: every Gemma query layer/head is eligible
to attend to the bank, with the same fourfold bank prior used in C16. This is a
calibration diagnostic, not held-out evidence; the disjoint C16 item set remains
gated on the predeclared calibration thresholds.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from experiments.mi1.c16_calibration import (
    CALIBRATION_FIXTURES,
    HELDOUT_FIXTURES,
    _coordinate,
)

SEEDS = (34211, 34219)
CONDITIONS = ("no_bank", "visible_A", "visible_B", "latent_all_A", "latent_all_B")
ALL_HEAD_CONFIG = {
    "selector": "all_heads_all_layers",
    "gain": {"logit_bias": math.log(4.0), "relative_prior": 4.0},
}


def _row(fixture: dict[str, str], condition: str, seed: int, phase: str) -> dict[str, Any]:
    base_condition = condition
    if condition.startswith("latent_all_"):
        side = condition[-1]
        base_condition = f"latent_assistant_turn_{side}"
    row = _coordinate(fixture, base_condition, seed, phase)
    row["coordinate_id"] = f"C17-{phase}-{fixture['fixture_id']}-{condition}-{seed}"
    row["condition"] = condition
    row["metadata"] = {
        **row["metadata"],
        "suite": "c17_allhead_maximum_access",
        "condition": condition,
        "routing": "all 42 query layers x 8 query heads; all 24 KV source layers",
    }
    if condition.startswith("latent_all_"):
        row["bank_config"] = ALL_HEAD_CONFIG
    return row


def build_plan(*, c16_plan_sha256: str, c16_readout_sha256: str) -> dict[str, Any]:
    for value in (c16_plan_sha256, c16_readout_sha256):
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("C17 parent references must be lowercase SHA-256 values")
    calibration = [
        _row(fixture, condition, seed, "calibration")
        for fixture in CALIBRATION_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    confirmation = [
        _row(fixture, condition, seed, "confirmation")
        for fixture in HELDOUT_FIXTURES
        for seed in SEEDS
        for condition in CONDITIONS
    ]
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C17 maximum-access calibration",
        "revision": "C17",
        "status": "FROZEN_BEFORE_GENERATION",
        "parents": {
            "c16_plan_sha256": c16_plan_sha256,
            "c16_readout_sha256": c16_readout_sha256,
        },
        "hypothesis": (
            "C14-C16 and Test A/B/C failed semantic retrieval under sparse selected-site routing. "
            "C17 tests whether restricting bank access to selected sites explains the failure by "
            "exposing all 24 KV-producing layers through all 42 query layers and all eight query "
            "heads, at the previously tested fourfold bank prior. No prompt, bank content, model, "
            "tokenization, or task wording is changed."
        ),
        "model": {
            "name": "google/gemma-4-E4B-it",
            "gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03",
            "llama_cpp_commit": "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        },
        "runtime": {
            "reasoning": "ON",
            "cache_prompt": False,
            "temperature": 0.35,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
            "max_tokens": 1024,
            "parallel_slots": 1,
            "seeds": list(SEEDS),
        },
        "encoding": {
            "reused_from": "C16 assistant-turn exact K/V captures",
            "source_format": "<|turn>assistant\\n{fact}<turn|>\\n",
            "tokenization": "llama_tokenize(add_special=true,parse_special=true)",
            "no_reencoding_or_source_changes": True,
        },
        "routing": {
            "query_layers": list(range(42)),
            "query_heads_per_layer": 8,
            "kv_source_layers": 24,
            "query_sites": [],
            "empty_query_site_list_means": "all query heads on every compatible query layer",
            "bank_logit_bias": math.log(4.0),
            "relative_prior": 4.0,
        },
        "calibration_fixtures": list(CALIBRATION_FIXTURES),
        "heldout_fixtures": list(HELDOUT_FIXTURES),
        "conditions": list(CONDITIONS),
        "calibration_coordinates": calibration,
        "confirmation_coordinates": confirmation,
        "call_count": {
            "calibration": len(calibration),
            "confirmation_if_gate_passes": len(confirmation),
            "maximum": len(calibration) + len(confirmation),
        },
        "gate": {
            "calibration_denominator_per_condition": len(CALIBRATION_FIXTURES) * len(SEEDS),
            "no_bank_minimum": 7,
            "visible_A_minimum": 7,
            "visible_B_minimum": 7,
            "latent_all_A_minimum": 6,
            "latent_all_B_minimum": 6,
            "confirmation_denominator_per_condition": len(HELDOUT_FIXTURES) * len(SEEDS),
            "confirmation_minimum_each_condition": 7,
            "confirmation_runs_only_if_all_calibration_thresholds_pass": True,
        },
        "interpretation": (
            "Passing C17 permits a new process-prior held-out experiment; it does not qualify "
            "MI1 or establish generalization. Failure leaves the bank contents and task form "
            "unchanged while removing sparse layer/head access as the remaining tested explanation."
        ),
    }


def write_plan(path: Path, *, c16_plan: Path, c16_readout: Path) -> str:
    def digest(item: Path) -> str:
        return hashlib.sha256(item.read_bytes()).hexdigest()

    value = build_plan(c16_plan_sha256=digest(c16_plan), c16_readout_sha256=digest(c16_readout))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return digest(path)
