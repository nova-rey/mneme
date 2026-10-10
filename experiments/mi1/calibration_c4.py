"""Frozen MI1 diagnostic separating a generic memory cue from bank content."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from experiments.mi1.calibration import canonical_bytes, source_hash
from experiments.mi1.calibration_c3 import CONFIGS, FIXTURES, SEEDS

SYSTEM_NO_CUE = (
    "You are solving a fictional directed-reachability task. Use only rules available in the "
    "current context. If no rules are supplied or no directed path exists, answer UNKNOWN. "
    "Return exactly two lines: ANSWER: <yes, no, or unknown>; PATH: <complete path separated "
    "by ->, or none>. Do not add an explanation."
)
SYSTEM_MEMORY_CUE = (
    "You are solving a fictional directed-reachability task. A separate private reference "
    "memory may contain directed rules relevant to the current task; use those rules if "
    "available, without inventing any. If no rules are available or no directed path exists, "
    "answer UNKNOWN. Return exactly two lines: ANSWER: <yes, no, or unknown>; PATH: "
    "<complete path separated by ->, or none>. Do not add an explanation."
)

CONDITIONS = (
    "no_bank",
    "no_bank_memory_cue",
    "visible",
    "latent_sparse_no_cue",
    "latent_broad_no_cue",
    "latent_sparse_memory_cue",
    "latent_broad_memory_cue",
)


def _messages(fixture: dict[str, Any], condition: str) -> list[dict[str, str]]:
    cue = condition.endswith("memory_cue")
    system = SYSTEM_MEMORY_CUE if cue else SYSTEM_NO_CUE
    question = (
        f"These are fictional labels. Initially only {fixture['initial']} is active. "
        f"Is {fixture['target']} reachable from {fixture['initial']}?"
    )
    if condition == "visible":
        user = f"{fixture['intro']}\n\nRules:\n{fixture['bank']}\n\nQuestion:\n{question}"
    else:
        user = f"{fixture['intro']}\n\n{question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_c4_plan() -> dict[str, Any]:
    """Build a 56-coordinate prompt-cue and bank-access diagnostic matrix."""
    coordinates: list[dict[str, Any]] = []
    configs = {
        "latent_sparse_no_cue": "sparse_moderate",
        "latent_broad_no_cue": "broad_moderate",
        "latent_sparse_memory_cue": "sparse_moderate",
        "latent_broad_memory_cue": "broad_moderate",
    }
    for fixture in FIXTURES:
        for condition in CONDITIONS:
            for seed in SEEDS:
                latent = condition.startswith("latent_")
                config = copy.deepcopy(CONFIGS[configs[condition]]) if latent else None
                messages = _messages(fixture, condition)
                request = {
                    "model": "google/gemma-4-E4B-it",
                    "messages": messages,
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
                    "answer": fixture["target"]
                    if condition in ("visible",) or latent
                    else "unknown",
                    "path": fixture["path"] if condition in ("visible",) or latent else [],
                }
                coordinate_id = f"C4-{fixture['fixture_id']}-{condition}-{seed}"
                bank_action = "attach" if latent else "clear"
                coordinates.append(
                    {
                        "coordinate_id": coordinate_id,
                        "suite": "calibration_c4",
                        "metadata": {
                            "fixture_id": fixture["fixture_id"],
                            "condition": condition,
                            "seed": seed,
                            "expected_answer": expected["answer"],
                            "expected_path": expected["path"],
                            "candidate_target": fixture["target"],
                            "server_role": "mi1_server",
                            "cue_is_generic": condition.endswith("memory_cue"),
                        },
                        "request": request,
                        "request_sha256": hashlib.sha256(canonical_bytes(request)).hexdigest(),
                        "bank_source": fixture["bank"] if latent else None,
                        "bank_source_sha256": source_hash(fixture["bank"]) if latent else None,
                        "bank_action": bank_action,
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
        "revision": "C4-explicit-completion-and-generic-memory-cue-diagnostic",
        "purpose": (
            "Resolve C3's missing final answers and isolate generic memory cueing from "
            "side-bank content; not scored Test A/B/C evidence."
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
        "fixture_source": "same four earlier successful simple-chain fixtures used in frozen C3",
        "c3_plan_sha256": "4412f28877996850339de441b2fb95536858af6686326ed3cfaaa0ea0dd4809f",
        "coordinates": coordinates,
    }
