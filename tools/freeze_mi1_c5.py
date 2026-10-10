#!/usr/bin/env python3
"""Freeze C5 with immutable C4 and original C2 provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c5 import build_c5_plan


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c4-plan", type=Path, required=True)
    parser.add_argument("--c4-receipt", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = build_c5_plan()
    plan["diagnostic_parent_hashes"] = {
        "c4_plan": sha256(args.c4_plan),
        "c4_receipt": sha256(args.c4_receipt),
        "c2_plan": sha256(
            Path("docs/receipts/MNEME_Phase_4_MI1_Calibration_Framing_Revision_20261010.json")
        ),
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
