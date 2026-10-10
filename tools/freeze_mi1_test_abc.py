#!/usr/bin/env python3
"""Freeze the original MI1 Test A/B/C prompts with the calibrated selector."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.coordinates import build_scored_coordinates


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def build_plan(
    suite: dict[str, Any],
    *,
    suite_sha256: str,
    site: dict[str, Any],
    site_sha256: str,
    calibration_sha256: str,
    c8_sha256: str,
) -> dict[str, Any]:
    coordinates = build_scored_coordinates(suite)
    if len(coordinates) != 268:
        raise ValueError(f"frozen Test A/B/C requires 268 coordinates, got {len(coordinates)}")
    site_selection = site.get("site_selection", site)
    sparse_sites = site_selection.get("sparse_query_sites")
    if not isinstance(sparse_sites, list) or len(sparse_sites) != 16:
        raise ValueError("MI1 scored exposure requires the previously qualified 16 sparse sites")
    counts = {
        "test_a": 0,
        "test_b": 0,
        "test_c_fresh": 0,
        "test_c_ongoing": 0,
        "test_c_new_bank": 0,
    }
    seen: set[str] = set()
    for coordinate in coordinates:
        coordinate_id = coordinate["coordinate_id"]
        if coordinate_id in seen:
            raise ValueError(f"duplicate frozen coordinate {coordinate_id}")
        seen.add(coordinate_id)
        suite_name = coordinate["suite"]
        counts[suite_name] += 1
        has_bank = coordinate.get("bank_source") is not None
        coordinate["metadata"]["server_role"] = "mi1_server"
        coordinate["bank_config"] = (
            {"selector": "sparse", "gain": {"logit_bias": 0.0}}
            if has_bank
            else {"selector": "none", "gain": None}
        )
        coordinate["request_sha256"] = (
            sha256(canonical(coordinate["request"]))
            if coordinate["request"].get("messages") is not None
            else None
        )
    expected_counts = {
        "test_a": 144,
        "test_b": 108,
        "test_c_fresh": 12,
        "test_c_ongoing": 2,
        "test_c_new_bank": 2,
    }
    if counts != expected_counts:
        raise ValueError(f"frozen coordinate count mismatch: {counts}")
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4-MI1 local Memory Inception synthetic test",
        "status": "FROZEN_BEFORE_SCORED_GENERATION",
        "revision": "test-abc-sparse-moderate-context-8192",
        "purpose": (
            "Execute the original Test A/B/C without changing prompts, facts, conditions, "
            "seeds, or rubric."
        ),
        "source_suite_sha256": suite_sha256,
        "site_calibration_receipt_sha256": site_sha256,
        "original_calibration_freeze_sha256": calibration_sha256,
        "c8_diagnostic_result_sha256": c8_sha256,
        "model": {
            "name": suite["host_model"],
            "gguf_sha256": suite["gguf_sha256"],
            "llama_cpp_commit": suite["llama_cpp_commit"],
            "cache_prompt": False,
            "reasoning": "ON",
            "server_context_size": 8192,
            "generation_config": suite["generation_config"],
        },
        "side_memory_exposure": {
            "selector": "sparse",
            "query_sites": sparse_sites,
            "site_count": len(sparse_sites),
            "bank_logit_bias": 0.0,
            "relative_per_slot_prior": 1.0,
            "rationale": (
                "Use the selector and neutral prior already frozen after site calibration; "
                "C8 did not change the selection or gain."
            ),
        },
        "coordinate_counts": counts,
        "coordinate_count": len(coordinates),
        "generation_budget": {
            "test_a": 144,
            "test_b": 108,
            "test_c": 16,
            "scored_total": 268,
            "prior_calibration_calls_before_c8": 317,
            "c8_calls": 44,
            "total_after_scored_suite": 629,
            "untouched_confirmation_reserve": 48,
            "projected_total_after_confirmation": 677,
            "authorized_hard_max": 800,
        },
        "dynamic_request_contract": {
            "coordinate_id": "C-ONGOING-A02-turn-2",
            "depends_on_attempt": "C-ONGOING-A02-turn-1",
            "construction": (
                "Use the frozen turn-1 user prompt, the durable assistant final answer from "
                "its complete receipt, then the frozen turn-2 user prompt. Do not include "
                "hidden reasoning in conversational history."
            ),
        },
        "coordinates": coordinates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite", type=Path, default=Path("experiments/mi1/fixtures/mi1_frozen_suite.json")
    )
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--calibration-freeze", type=Path, required=True)
    parser.add_argument("--c8-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    suite_bytes = args.suite.read_bytes()
    site_bytes = args.site.read_bytes()
    site_document = json.loads(site_bytes)
    site_digest = site_document.get("site_selection_sha256", sha256(site_bytes))
    plan = build_plan(
        json.loads(suite_bytes),
        suite_sha256=sha256(suite_bytes),
        site=site_document,
        site_sha256=site_digest,
        calibration_sha256=sha256(args.calibration_freeze.read_bytes()),
        c8_sha256=sha256(args.c8_result.read_bytes()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(plan) + b"\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": sha256(args.output.read_bytes()),
                "coordinates": len(plan["coordinates"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
