#!/usr/bin/env python3
"""Emit the exact pre-generation MI1 calibration request manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import build_calibration_coordinates, canonical_bytes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite", type=Path, default=Path("experiments/mi1/fixtures/mi1_frozen_suite.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--native-receipt", type=Path, required=True)
    parser.add_argument("--base-server-sha256", required=True)
    parser.add_argument("--site-selection", type=Path, required=True)
    parser.add_argument("--site-receipt", type=Path, required=True)
    args = parser.parse_args()
    suite: dict[str, Any] = json.loads(args.suite.read_text(encoding="utf-8"))
    native: dict[str, Any] = json.loads(args.native_receipt.read_text(encoding="utf-8"))
    site_selection: dict[str, Any] = json.loads(
        args.site_selection.read_text(encoding="utf-8")
    )
    coordinates = build_calibration_coordinates(suite)
    payload = {
        "schema_version": 1,
        "experiment": "MNEME Phase 4-MI1 local Memory Inception synthetic test",
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "scope": suite["scope"],
        "frozen_suite_sha256": sha256(args.suite),
        "calibration_code_sha256": sha256(Path("experiments/mi1/calibration.py")),
        "site_calibration_code_sha256": sha256(Path("experiments/mi1/site_calibration.py")),
        "site_selector_code_sha256": sha256(Path("experiments/mi1/native/selector.py")),
        "bank_code_sha256": sha256(Path("experiments/mi1/native/bank.py")),
        "query_capture_reader_code_sha256": sha256(
            Path("experiments/mi1/native/query_capture.py")
        ),
        "query_capture_tool_code_sha256": sha256(Path("tools/mi1_native_query_capture.cpp")),
        "site_selection_tool_code_sha256": sha256(Path("tools/mi1_select_sites.py")),
        "runner_code_sha256": sha256(Path("experiments/mi1/runner.py")),
        "evidence_journal_code_sha256": sha256(Path("experiments/mi1/native/evidence.py")),
        "coordinate_builder_code_sha256": sha256(Path("experiments/mi1/coordinates.py")),
        "calibration_scorer_code_sha256": sha256(Path("experiments/mi1/score_calibration.py")),
        "native_validation_receipt": {
            "locator": (
                "local-canonical:phase4-mi1/native/mi1-native-server-lifecycle/"
                "final-content-replacement/validation-receipt.json"
            ),
            "sha256": sha256(args.native_receipt),
        },
        "model": {
            "name": suite["host_model"],
            "gguf_sha256": suite["gguf_sha256"],
            "llama_cpp_commit": suite["llama_cpp_commit"],
            "reasoning": suite["reasoning"],
            "cache_prompt": False,
            "generation_config": suite["generation_config"],
        },
        "runtime": {
            "host": "brokeass-msi",
            "gpu": "NVIDIA GeForce RTX 3060 Laptop GPU, 6144 MiB",
            "system_ram": "14 GiB observed; available at preflight was approximately 13 GiB",
            "base_llama_cpp_commit": suite["llama_cpp_commit"],
            "base_server_sha256": args.base_server_sha256,
            "mi1_server_sha256": native.get("native_build", {}).get("binaries", {}).get(
                "llama-server"
            ),
            "cmake_build_type": "Release",
            "cmake_ggml_cuda": True,
            "cmake_cuda_architecture": "sm_86",
            "cmake_flash_attention_quants": [
                "q4_0-q4_0",
                "q8_0-q8_0",
                "f16-f16",
                "bf16-bf16",
            ],
            "server_command": [
                "<binary>",
                "-m",
                "/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf",
                "-ngl",
                "99",
                "-c",
                "8192",
                "-t",
                "8",
                "-tb",
                "8",
                "--parallel",
                "1",
                "--host",
                "127.0.0.1",
                "--port",
                "<assigned-loopback-port>",
                "--reasoning-format",
                "deepseek",
                "--no-warmup",
                "--no-webui",
            ],
            "cache_policy": (
                "Requests set cache_prompt=false; isolated server rejects missing or true values."
            ),
        },
        "generation_budget": {
            "prior_calibration_calls": 8,
            "new_calibration_calls": len(coordinates),
            "actual_planned_calibration_total": 8 + len(coordinates),
            "calibration_ceiling": 120,
            "test_a": 144,
            "test_b": 108,
            "test_c": 16,
            "untouched_confirmation_reserve": 48,
            "hard_total_ceiling": 800,
            "currently_planned_total_including_reserve": (
                8 + len(coordinates) + 144 + 108 + 16 + 48
            ),
            "retry_policy": (
                "No automatic retry. Failed or uncertain calls remain charged and reported."
            ),
        },
        "site_selection_sha256": sha256(args.site_selection),
        "site_selection": site_selection,
        "site_calibration_receipt": {
            "path": "docs/receipts/MNEME_Phase_4_MI1_Site_Calibration_20261010.json",
            "sha256": sha256(args.site_receipt),
        },
        "site_calibration": {
            "query_prompts": (
                "Three frozen calibration requests, rendered by the pinned chat template."
            ),
            "target_banks": (
                "Encode each task's four directed rules with the pinned Q2 model; no generation."
            ),
            "reference_bank": (
                "Use the fixed four-rule irrelevant bank in calibration.py; no generation."
            ),
            "capture": (
                "One prefill-only Q/attention capture per task with its bank visible to all heads. "
                "Use only the final user-query row."
            ),
            "score": (
                "Average the per-layer/KV-group Eq.3 margin (max target minus max reference "
                "normalized-key alignment) across tasks. Retain bank attention mass as a tie-break."
            ),
            "sparse": (
                "Appendix-C stable selection: top one KV group per layer, then top four layers; "
                "expand each group to its four query heads."
            ),
            "broad": "All 42 query layers and both KV groups (all 336 query heads).",
            "no_scored_prompt_used_for_selection": True,
        },
        "gain_calibration": {
            "meaning": (
                "Add additive logit bias c to each bank slot; the relative per-slot prior is "
                "exp(c). This is not a residual-vector gain."
            ),
            "levels": {
                "low": {"relative_prior": 0.5, "logit_bias": -0.6931471805599453},
                "moderate": {"relative_prior": 1.0, "logit_bias": 0.0},
                "strong": {"relative_prior": 2.0, "logit_bias": 0.6931471805599453},
            },
            "candidate_order": [
                "latent_sparse_low",
                "latent_sparse_moderate",
                "latent_sparse_strong",
                "latent_broad_moderate",
            ],
        },
        "scoring_and_freeze_rule": {
            "known_answer": (
                "Final output must contain the expected label and all path labels in order, "
                "using case-insensitive token-boundary matching."
            ),
            "unknown": (
                "Final output must answer unknown. No target/path credit is awarded."
            ),
            "visible_control_gate": (
                "At least 5/6 visible-bank calls must give the correct label and full path."
            ),
            "negative_control_gate": (
                "At least 11/12 no-bank and irrelevant-bank calls must answer unknown."
            ),
            "candidate_gate": (
                "Require at least 5/6 correct relevant latent calls and at most one false "
                "positive among the 12 no-bank/irrelevant controls."
            ),
            "candidate_choice": (
                "Among passing candidates, minimize site_count * exp(logit_bias); tie-break "
                "by site count, lower bias, then candidate_order. If none passes, stop before "
                "scored Test A/B/C."
            ),
            "determinism_gate": (
                "The repeated MI1 no-bank request and exact base-server replay must each be "
                "byte-identical to the original. Otherwise stop before scored calls."
            ),
            "failure_denominator": (
                "Every attempted call, including failed, malformed, or uncertain calls, "
                "remains in the denominator and call budget."
            ),
        },
        "coordinates": coordinates,
        "native_validation_summary": {
            "receipt_sha256": sha256(args.native_receipt),
            "scope": native.get("scope"),
            "generation_calls_in_native_smoke": native.get("generation_guard", {}).get(
                "valid_generation_requests_sent"
            ),
            "sampled_tokens_in_native_smoke": native.get("generation_guard", {}).get(
                "sampled_tokens"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(payload) + b"\n")
    print(f"wrote {args.output} sha256={sha256(args.output)} coordinates={len(coordinates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
