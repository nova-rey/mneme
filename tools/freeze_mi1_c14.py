#!/usr/bin/env python3
"""Freeze C14 atomic-recall calibration and independent confirmation fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c14_calibration import build_c14_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c13-readout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent = args.c13_readout.read_bytes()
    plan: dict[str, Any] = build_c14_plan(c13_readout_sha256=hashlib.sha256(parent).hexdigest())
    plan["code_sha256"] = {
        "c14_calibration": hashlib.sha256(Path("experiments/mi1/c14_calibration.py").read_bytes()).hexdigest(),
        "runner": hashlib.sha256(Path("experiments/mi1/runner.py").read_bytes()).hexdigest(),
        "c14_freezer": hashlib.sha256(Path("tools/freeze_mi1_c14.py").read_bytes()).hexdigest(),
        "source_preparation": hashlib.sha256(Path("tools/prepare_mi1_c14_sources.py").read_bytes()).hexdigest(),
        "bank_preparation": hashlib.sha256(Path("tools/prepare_mi1_c14_banks.py").read_bytes()).hexdigest(),
        "generation_tool": hashlib.sha256(Path("tools/run_mi1_c14.py").read_bytes()).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"output": str(args.output), "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(), "coordinates": plan["call_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
