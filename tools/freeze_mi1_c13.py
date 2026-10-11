#!/usr/bin/env python3
"""Freeze the C13 cue/site-breadth matrix before any generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c13_calibration import build_c13_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c12-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.c12_plan.read_bytes()
    parent: dict[str, Any] = json.loads(raw)
    plan = build_c13_plan(parent, c12_plan_sha256=hashlib.sha256(raw).hexdigest())
    plan["code_sha256"] = {
        "c13_calibration": hashlib.sha256(
            Path("experiments/mi1/c13_calibration.py").read_bytes()
        ).hexdigest(),
        "c12_calibration": hashlib.sha256(
            Path("experiments/mi1/c12_calibration.py").read_bytes()
        ).hexdigest(),
        "runner": hashlib.sha256(Path("experiments/mi1/runner.py").read_bytes()).hexdigest(),
        "generation_tool": hashlib.sha256(Path("tools/run_mi1_c13.py").read_bytes()).hexdigest(),
        "bank_preparation_tool": hashlib.sha256(
            Path("tools/prepare_mi1_c13_banks.py").read_bytes()
        ).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                "coordinates": plan["call_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
