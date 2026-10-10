#!/usr/bin/env python3
"""Freeze C7 and bind its C5/C6 diagnostic parents."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c7 import build_c7_plan


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c5-plan", type=Path, required=True)
    parser.add_argument("--c6-plan", type=Path, required=True)
    parser.add_argument("--c6-receipt", type=Path, required=True)
    parser.add_argument("--c6-result", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = build_c7_plan()
    plan.update(
        {
            "c5_plan_sha256": sha256(args.c5_plan),
            "c6_plan_sha256": sha256(args.c6_plan),
            "c6_receipt_sha256": sha256(args.c6_receipt),
            "c6_result_sha256": sha256(args.c6_result),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(plan) + b"\n")
    print(json.dumps({"path": str(args.output), "sha256": sha256(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
