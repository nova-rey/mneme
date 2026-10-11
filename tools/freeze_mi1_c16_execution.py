#!/usr/bin/env python3
"""Bind C16's uploaded K/V variants and host/runtime before generation."""

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
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--capture-manifest", type=Path, required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--remote-bank-manifest", type=Path, required=True)
    parser.add_argument("--parent-execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    source_manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    variants = json.loads(args.variant_map.read_text(encoding="utf-8"))
    parent = json.loads(args.parent_execution.read_text(encoding="utf-8"))
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C16 design is not frozen")
    plan_sha = _sha(args.plan)
    if source_manifest.get("plan_sha256") != plan_sha or variants.get("plan_sha256") != plan_sha:
        raise ValueError("C16 source or bank artifacts do not bind to the frozen plan")
    if source_manifest.get("source_count") != 16 or len(variants.get("variants", {})) != 16:
        raise ValueError("C16 requires 16 encoded sources and 16 selected variants")
    if plan.get("call_count") != 48 or plan.get("confirmation_call_count") != 40:
        raise ValueError("unexpected C16 call matrix")
    result: dict[str, Any] = {
        "schema_version": 1,
        "experiment": plan["experiment"],
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "generation_issued": False,
        "plan_sha256": plan_sha,
        "parent_c15b_execution_sha256": _sha(args.parent_execution),
        "model": parent["model"],
        "llama_cpp": parent["llama_cpp"],
        "runtime": parent["runtime"],
        "server_command": parent["server_command"],
        "encoding_binary_sha256": parent["encoder"]["binary_sha256"],
        "generation_config": plan["generation_config"],
        "sources": {
            "manifest_path": str(args.source_manifest),
            "manifest_sha256": _sha(args.source_manifest),
            "source_count": source_manifest["source_count"],
            "capture_manifest_path": str(args.capture_manifest),
            "capture_manifest_sha256": _sha(args.capture_manifest),
        },
        "banks": {
            "variant_map_path": str(args.variant_map),
            "variant_map_sha256": _sha(args.variant_map),
            "selected_variant_count": len(variants["variants"]),
            "remote_manifest_path": str(args.remote_bank_manifest),
            "remote_manifest_sha256": _sha(args.remote_bank_manifest),
            "remote_manifest_file_count": len(args.remote_bank_manifest.read_text().splitlines()),
            "verified_selected_variant_count": len(variants["variants"]),
        },
        "evidence_root": "/home/nyx/mneme-artifacts/phase4-mi1/c16-assistant/evidence",
        "budget_path": "/home/nyx/mneme-artifacts/phase4-mi1/c16-assistant/budget.json",
        "calibration_calls": plan["call_count"],
        "confirmation_max_calls": plan["confirmation_call_count"],
        "hard_call_limit": plan["call_count"] + plan["confirmation_call_count"],
        "source_sha256": {
            "calibration_and_scoring": _sha(Path("experiments/mi1/c16_calibration.py")),
            "runner": _sha(Path("tools/run_mi1_c15.py")),
            "bank_preparation": _sha(Path("tools/prepare_mi1_c15_banks.py")),
            "execution_freezer": _sha(Path(__file__)),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output), "sha256": _sha(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
