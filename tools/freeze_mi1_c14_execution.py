#!/usr/bin/env python3
"""Bind C14's frozen plan and exact-Q2 bank variants before generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--remote-sha256", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan_raw = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_raw)
    plan_sha = hashlib.sha256(plan_raw).hexdigest()
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C14 plan must be frozen before execution binding")
    map_raw = args.variant_map.read_bytes()
    variant_map: dict[str, Any] = json.loads(map_raw)
    if variant_map.get("plan_sha256") != plan_sha or variant_map.get("variant_count") != 16:
        raise ValueError("C14 variant map is stale or incomplete")
    remote_hashes: dict[str, str] = {}
    for line in args.remote_sha256.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        remote_hashes[Path(name.strip().lstrip("* ")).name] = digest
    variants = list(variant_map["variants"].values())
    if len(variants) != 16:
        raise ValueError("C14 requires exactly 16 (8 source x 2 gain) variants")
    bound = []
    for row in variants:
        path = Path(row["local_path"])
        name = Path(row["remote_path"]).name
        local_sha = _sha(path)
        if local_sha != row["native_sha256"] or remote_hashes.get(name) != local_sha:
            raise ValueError(f"C14 local/remote bank hash mismatch: {name}")
        bound.append(
            {
                "name": name,
                "sha256": local_sha,
                "fingerprint": row["bank_fingerprint"],
                "selector": row["selector"],
            }
        )
    code_paths = (
        "experiments/mi1/c14_calibration.py",
        "experiments/mi1/c13_scoring.py",
        "experiments/mi1/runner.py",
        "tools/run_mi1_c14.py",
        "tools/prepare_mi1_c14_banks.py",
        "tools/prepare_mi1_c14_sources.py",
    )
    output: dict[str, Any] = {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C14 exact-Q2 execution binding",
        "status": "FROZEN_BEFORE_GENERATION",
        "plan_sha256": plan_sha,
        "variant_map_sha256": hashlib.sha256(map_raw).hexdigest(),
        "remote_sha256_manifest_sha256": _sha(args.remote_sha256),
        "model": plan["model"],
        "generation_config": plan["generation_config"],
        "calibration_call_count": plan["call_count"],
        "prior_campaign_generations": 952,
        "projected_after_calibration": 952 + int(plan["call_count"]),
        "budget_contract": {
            "prior_calibration_calls": 952,
            "calibration_limit": None,
            "hard_limit": None,
            "implicit_retries": False,
        },
        "evidence_root": "/home/nyx/mneme-artifacts/phase4-mi1/c14-calibration/evidence",
        "code_sha256": {name: _sha(Path(name)) for name in code_paths},
        "remote_bank_variants": sorted(bound, key=lambda value: value["name"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": _sha(args.output),
                "variants": len(bound),
                "calls": plan["call_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
