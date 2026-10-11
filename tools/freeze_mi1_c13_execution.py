#!/usr/bin/env python3
"""Bind C13's exact plan, runner, banks and remote checksums before inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        pieces = line.split()
        if len(pieces) != 2:
            raise ValueError(f"invalid SHA-256 line in {path}")
        result[Path(pieces[1]).name] = pieces[0]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--c12-remote-sums", type=Path, required=True)
    parser.add_argument("--c13-remote-sums", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan_raw = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_raw)
    variant_map_raw = args.variant_map.read_bytes()
    variant_map: dict[str, Any] = json.loads(variant_map_raw)
    if variant_map.get("plan_sha256") != sha256(args.plan):
        raise ValueError("C13 variant map does not match frozen plan")

    c12_sums = read_sums(args.c12_remote_sums)
    c13_sums = read_sums(args.c13_remote_sums)
    verified: list[dict[str, str]] = []
    for row in variant_map["variants"].values():
        local_path = Path(row["local_path"])
        if sha256(local_path) != row["native_sha256"]:
            raise ValueError(f"local C13 bank checksum mismatch: {local_path.name}")
        remote_name = Path(row["remote_path"]).name
        selector = row["selector"]["selector"]
        remote_hash = (c13_sums if selector == "all_heads" else c12_sums).get(remote_name)
        if remote_hash != row["native_sha256"]:
            raise ValueError(f"remote bank checksum mismatch: {remote_name}")
        verified.append(
            {
                "name": remote_name,
                "selector": selector,
                "sha256": row["native_sha256"],
                "bank_fingerprint": row["bank_fingerprint"],
            }
        )
    if len(verified) != variant_map["variant_count"]:
        raise ValueError("not every frozen C13 variant was verified")

    execution = {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C13 execution binding",
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "design_plan_sha256": sha256(args.plan),
        "variant_map_sha256": hashlib.sha256(variant_map_raw).hexdigest(),
        "code_sha256": {
            "c13_calibration": sha256(Path("experiments/mi1/c13_calibration.py")),
            "mi1_runner": sha256(Path("experiments/mi1/runner.py")),
            "c13_generation_tool": sha256(Path("tools/run_mi1_c13.py")),
            "c13_bank_preparation_tool": sha256(Path("tools/prepare_mi1_c13_banks.py")),
        },
        "model": plan["model"],
        "generation_config": plan["generation_config"],
        "calibration_call_count": plan["call_count"],
        "prior_campaign_generations": 880,
        "projected_after_calibration": 880 + plan["call_count"],
        "remote_bank_variant_count": len(verified),
        "all_remote_bank_variants_hash_verified": True,
        "remote_bank_variants": sorted(verified, key=lambda row: row["name"]),
        "budget_contract": {
            "prior_calibration_calls": 880,
            "calibration_limit": None,
            "hard_limit": None,
            "implicit_retries": False,
        },
        "external_evidence_root": "/home/nyx/mneme-artifacts/phase4-mi1/c13-calibration/evidence",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output), "sha256": sha256(args.output), "variants": len(verified)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
