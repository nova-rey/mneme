"""Frozen diagnostic calibration isolating MI1 fixture difficulty and exposure."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

from experiments.mi1.calibration import canonical_bytes, source_hash

SEEDS = (34031, 34037)
SYSTEM = (
    "You are solving a fictional rule task. Use only the supplied rules. "
    "Give the answer and the complete rule path. Do not infer unstated rules."
)
MEMORY_CUE = (
    "A separate private reference memory may contain rules relevant to this question. "
    "Use only rules that are available to you; do not assume missing content."
)

FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "fixture_id": "C3-SIMPLE-01",
        "intro": (
            "These are fictional labels and rules. An active label activates the target of each "
            "rule that starts with it. Initially only Zepi is active."
        ),
        "bank": (
            "Zepi activates Moru.\nMoru activates Kadi.\nKadi activates Velo.\nVelo activates Runi."
        ),
        "initial": "Zepi",
        "target": "Runi",
        "path": ["Zepi", "Moru", "Kadi", "Velo", "Runi"],
        "decoy": None,
    },
    {
        "fixture_id": "C3-INACTIVE-INCOMING-03",
        "intro": (
            "These are fictional labels and rules. An active label activates the target of each "
            "rule that starts with it. Initially only Heku is active."
        ),
        "bank": (
            "Heku activates Pali.\nPali activates Dovo.\nDovo activates Senu.\nXari activates Heku."
        ),
        "initial": "Heku",
        "target": "Senu",
        "path": ["Heku", "Pali", "Dovo", "Senu"],
        "decoy": "Xari",
    },
    {
        "fixture_id": "C3-INACTIVE-INCOMING-05",
        "intro": (
            "These are fictional labels and rules. An active label activates the target of each "
            "rule that starts with it. Initially only Bemi is active."
        ),
        "bank": (
            "Bemi activates Tavo.\nTavo activates Neki.\nNeki activates Lusa.\nGori activates Bemi."
        ),
        "initial": "Bemi",
        "target": "Lusa",
        "path": ["Bemi", "Tavo", "Neki", "Lusa"],
        "decoy": "Gori",
    },
    {
        "fixture_id": "C3-INACTIVE-INCOMING-04",
        "intro": (
            "These are fictional labels and rules. An active label activates the target of each "
            "rule that starts with it. Initially only Fenu is active."
        ),
        "bank": (
            "Fenu activates Rako.\nRako activates Wimi.\nWimi activates Jesa.\nCupo activates Fenu."
        ),
        "initial": "Fenu",
        "target": "Jesa",
        "path": ["Fenu", "Rako", "Wimi", "Jesa"],
        "decoy": "Cupo",
    },
)

CONFIGS: dict[str, dict[str, Any]] = {
    "sparse_moderate": {"selector": "sparse", "logit_bias": 0.0},
    "broad_moderate": {"selector": "broad", "logit_bias": 0.0},
    "broad_strong": {"selector": "broad", "logit_bias": 0.6931471805599453},
}


def _messages(fixture: dict[str, Any], condition: str) -> list[dict[str, str]]:
    system = SYSTEM
    if condition.startswith("cue_"):
        system = f"{SYSTEM} {MEMORY_CUE}"
    question = (
        f"Can {fixture['target']} become active? Give YES or NO and show the complete directed "
        f"path from {fixture['initial']}."
    )
    if condition in {"visible", "cue_visible"}:
        listed_bank = "\n".join(f"- {line}" for line in fixture["bank"].splitlines())
        user = f"{fixture['intro']}\n\nRules:\n{listed_bank}\n\n{question}"
    else:
        user = f"{fixture['intro']}\n\n{question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_c3_plan() -> dict[str, Any]:
    """Build the complete pre-inference 44-coordinate diagnostic matrix."""
    coordinates: list[dict[str, Any]] = []
    conditions = (
        "no_bank",
        "visible",
        "latent_sparse_moderate",
        "latent_broad_moderate",
        "latent_broad_strong",
    )
    for fixture in FIXTURES:
        for condition in conditions:
            selector_config = None
            if condition.startswith("latent_"):
                selector_config = copy.deepcopy(CONFIGS[condition.removeprefix("latent_")])
            for seed in SEEDS:
                messages = _messages(fixture, condition)
                bank_action = "attach" if selector_config is not None else "clear"
                coordinate_id = f"C3-{fixture['fixture_id']}-{condition}-{seed}"
                expected = {
                    "answer": fixture["target"] if condition != "no_bank" else "unknown",
                    "path": fixture["path"] if condition != "no_bank" else [],
                }
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
                config: dict[str, Any] = (
                    {
                        "selector": selector_config["selector"],
                        "gain": {"logit_bias": selector_config["logit_bias"]},
                    }
                    if selector_config is not None
                    else {"selector": "none", "gain": None}
                )
                coordinates.append(
                    {
                        "coordinate_id": coordinate_id,
                        "suite": "calibration_c3",
                        "metadata": {
                            "fixture_id": fixture["fixture_id"],
                            "condition": condition,
                            "seed": seed,
                            "expected_answer": expected["answer"],
                            "expected_path": expected["path"],
                            "candidate_target": fixture["target"],
                            "decoy_source": fixture["decoy"],
                            "server_role": "mi1_server",
                        },
                        "request": request,
                        "request_sha256": hashlib.sha256(canonical_bytes(request)).hexdigest(),
                        "bank_source": fixture["bank"] if bank_action == "attach" else None,
                        "bank_source_sha256": source_hash(fixture["bank"])
                        if bank_action == "attach"
                        else None,
                        "bank_action": bank_action,
                        "bank_config": config,
                        "expected": expected,
                    }
                )
        # The generic memory cue is a diagnostic factor only; the primary MI1
        # conditions above keep the recipient request free of a memory cue.
        if fixture["fixture_id"] == "C3-SIMPLE-01":
            for condition in ("cue_no_bank", "cue_latent_broad_strong"):
                for seed in SEEDS:
                    is_latent = condition == "cue_latent_broad_strong"
                    config = (
                        {
                            "selector": "broad",
                            "gain": {"logit_bias": CONFIGS["broad_strong"]["logit_bias"]},
                        }
                        if is_latent
                        else {"selector": "none", "gain": None}
                    )
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
                    coordinates.append(
                        {
                            "coordinate_id": f"C3-{fixture['fixture_id']}-{condition}-{seed}",
                            "suite": "calibration_c3",
                            "metadata": {
                                "fixture_id": fixture["fixture_id"],
                                "condition": condition,
                                "seed": seed,
                                "expected_answer": fixture["target"] if is_latent else "unknown",
                                "expected_path": fixture["path"] if is_latent else [],
                                "candidate_target": fixture["target"],
                                "decoy_source": fixture["decoy"],
                                "server_role": "mi1_server",
                                "diagnostic_only": True,
                            },
                            "request": request,
                            "request_sha256": hashlib.sha256(canonical_bytes(request)).hexdigest(),
                            "bank_source": fixture["bank"] if is_latent else None,
                            "bank_source_sha256": (
                                source_hash(fixture["bank"]) if is_latent else None
                            ),
                            "bank_action": "attach" if is_latent else "clear",
                            "bank_config": config,
                            "expected": {
                                "answer": fixture["target"] if is_latent else "unknown",
                                "path": fixture["path"] if is_latent else [],
                            },
                        }
                    )
    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "revision": "C3-complexity-and-exposure-diagnostic",
        "purpose": (
            "Separate fixture difficulty, bank cueing, and bank exposure strength; "
            "not scored A/B/C evidence."
        ),
        "host_model": "google/gemma-4-E4B-it",
        "model_gguf_sha256": "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03",
        "llama_cpp_commit": "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        "system_prompt": SYSTEM,
        "memory_cue_diagnostic_only": MEMORY_CUE,
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
        "calibration_interpretation": {
            "visible_controls_required": 8,
            "visible_controls_total": 8,
            "primary_latent_conditions": [
                "latent_sparse_moderate",
                "latent_broad_moderate",
                "latent_broad_strong",
            ],
            "cue_conditions_are_not_primary_efficacy_evidence": True,
            "score": (
                "exact target plus complete labeled directed path; no added reachable target claim"
            ),
            "no_bank_expected": "unknown because the query alone supplies no rule edges",
        },
        "fixture_source": (
            "all four earlier 8/8 visible-calibration fixtures reused only as task-form "
            "diagnostic controls; all earlier outputs remain immutable"
        ),
        "fixture_hashes": {
            fixture["fixture_id"]: source_hash(fixture["bank"]) for fixture in FIXTURES
        },
        "coordinate_count": len(coordinates),
        "coordinates": coordinates,
    }
