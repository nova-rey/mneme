#!/usr/bin/env python3
"""Freeze C8 and bind the original C3 and latest C7 diagnostic evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c8 import build_c8_plan


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c3-plan", type=Path, required=True)
    parser.add_argument("--c3-result", type=Path, required=True)
    parser.add_argument("--c7-plan", type=Path, required=True)
    parser.add_argument("--c7-result", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = build_c8_plan()
    plan.update(
        {
            "c3_plan_sha256": sha256(args.c3_plan),
            "c3_result_sha256": sha256(args.c3_result),
            "c7_plan_sha256": sha256(args.c7_plan),
            "c7_result_sha256": sha256(args.c7_result),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(plan) + b"\n")
    print(json.dumps({"path": str(args.output), "sha256": sha256(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
