"""Freeze a known-format MI1 control using the previously successful C2 contract."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from experiments.mi1.calibration import canonical_bytes, source_hash
from experiments.mi1.calibration_c3 import CONFIGS, FIXTURES, SEEDS

SYSTEM_CORE = (
    "You are solving a fictional directed-reachability task. The reference relationships are "
    "directed: follow them only from an initially active label, and a label is reachable only "
    "when a complete directed chain connects an initial label to it. A relationship whose "
    "source is not reachable cannot activate its destination. Use no unstated relationships."
)
OUTPUT_CONTRACT = (
    " Return exactly two lines: ANSWER: <reachable candidate label, or unknown> and PATH: "
    "<complete label chain separated by ->, or none if unknown>. Do not omit the path when a "
    "candidate is reachable."
)
MEMORY_CUE = (
    " A separate private reference memory may contain additional directed relationships "
    "relevant to the question; use only relationships actually available there."
)
SYSTEM = SYSTEM_CORE + OUTPUT_CONTRACT
CONDITIONS = (
    "no_bank",
    "no_bank_memory_cue",
    "visible",
    "latent_sparse_no_cue",
    "latent_sparse_memory_cue",
)


def _messages(fixture: dict[str, Any], condition: str) -> list[dict[str, str]]:
    has_cue = condition.endswith("memory_cue")
    system = SYSTEM_CORE + MEMORY_CUE + OUTPUT_CONTRACT if has_cue else SYSTEM
    decoy = "Qepo"
    question = (
        f"Initially only {fixture['initial']} is active. Which of {fixture['target']} or {decoy} "
        "can become active? Give the complete path or say unknown."
    )
    if condition == "visible":
        user = (
            f"Reference relationships:\n{fixture['bank']}\nOnly the stated direction applies."
            f"\n\nQuestion:\n{question}"
        )
    else:
        user = question
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_c5_plan() -> dict[str, Any]:
    """Build 40 matched coordinates with C2's proven answer contract."""
    coordinates: list[dict[str, Any]] = []
    for fixture in FIXTURES:
        for condition in CONDITIONS:
            for seed in SEEDS:
                latent = condition.startswith("latent_")
                config = copy.deepcopy(CONFIGS["sparse_moderate"]) if latent else None
                request = {
                    "model": "google/gemma-4-E4B-it",
                    "messages": _messages(fixture, condition),
                    "stream": True,
                    "cache_prompt": False,
                    "seed": seed,
                    "max_tokens": 2048,
                    "chat_template_kwargs": {"enable_thinking": True},
                    "temperature": 0.35,
                    "top_k": 40,
                    "top_p": 0.9,
                    "min_p": 0.05,
                }
                expected = {
                    "answer": fixture["target"] if condition == "visible" or latent else "unknown",
                    "path": fixture["path"] if condition == "visible" or latent else [],
                }
                coordinates.append(
                    {
                        "coordinate_id": f"C5-{fixture['fixture_id']}-{condition}-{seed}",
                        "suite": "calibration_c5",
                        "metadata": {
                            "fixture_id": fixture["fixture_id"],
                            "condition": condition,
                            "seed": seed,
                            "expected_answer": expected["answer"],
                            "expected_path": expected["path"],
                            "candidate_target": fixture["target"],
                            "decoy_candidate": "Qepo",
                            "cue_is_generic": has_cue(condition),
                            "server_role": "mi1_server",
                        },
                        "request": request,
                        "request_sha256": hashlib.sha256(canonical_bytes(request)).hexdigest(),
                        "bank_source": fixture["bank"] if latent else None,
                        "bank_source_sha256": source_hash(fixture["bank"]) if latent else None,
                        "bank_action": "attach" if latent else "clear",
                        "bank_config": (
                            {
                                "selector": config["selector"],
                                "gain": {"logit_bias": config["logit_bias"]},
                            }
                            if config is not None
                            else {"selector": "none", "gain": None}
                        ),
                        "expected": expected,
                    }
                )
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "revision": "C5-C2-answer-contract-simple-fixtures",
        "purpose": (
            "Test whether C2's previously successful directed-reachability answer contract "
            "resolves C4 control failures while preserving simple C3 tasks; diagnostic, not "
            "scored Test A/B/C."
        ),
        "host_model": "google/gemma-4-E4B-it",
        "model_gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03",
        "llama_cpp_commit": "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        "seeds": list(SEEDS),
        "generation": {
            "reasoning": "on",
            "cache_prompt": False,
            "temperature": 0.35,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
            "max_tokens": 2048,
        },
        "conditions": list(CONDITIONS),
        "coordinate_count": len(coordinates),
        "c3_plan_sha256": "4412f28877996850339de441b2fb95536858af6686326ed3cfaaa0ea0dd4809f",
        "c4_plan_sha256": "8ec9aea5eda3405593dbcd112ce08f6c89b28614df938efc06bd1267dd25514c",
        "coordinates": coordinates,
    }


def has_cue(condition: str) -> bool:
    return condition.endswith("memory_cue")
