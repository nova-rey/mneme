#!/usr/bin/env python3
"""Freeze C6, a byte-matched C5 replay with a larger context window."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c6 import build_c6_plan


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c5-plan", type=Path, required=True)
    parser.add_argument("--c5-receipt", type=Path, required=True)
    parser.add_argument("--c5-result", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = build_c6_plan()
    parent_hashes = {
        "c5_plan_sha256": sha256(args.c5_plan),
        "c5_receipt_sha256": sha256(args.c5_receipt),
        "c5_result_sha256": sha256(args.c5_result),
    }
    for key, value in parent_hashes.items():
        plan[key] = value
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(plan) + b"\n")
    print(json.dumps({"path": str(args.output), "sha256": sha256(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
