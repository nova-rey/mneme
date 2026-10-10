#!/usr/bin/env python3
"""Freeze C4 after inspecting, but without changing, the complete C3 results."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c4 import build_c4_plan


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c3-plan", type=Path, required=True)
    parser.add_argument("--c3-receipt", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = build_c4_plan()
    plan["diagnostic_parent_hashes"] = {
        "c3_plan": sha256(args.c3_plan),
        "c3_receipt": sha256(args.c3_receipt),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(plan) + b"\n")
    print(
        json.dumps(
            {
                "path": str(args.output),
                "sha256": sha256(args.output),
                "coordinates": len(plan["coordinates"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
