#!/usr/bin/env python3
"""Write the frozen C3 diagnostic calibration without invoking a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes
from experiments.mi1.calibration_c3 import build_c3_plan


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--c2-receipt", type=Path, required=True)
    parser.add_argument("--pretest-receipt", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = build_c3_plan()
    plan["diagnostic_parent_hashes"] = {
        "c2_plan": sha256(
            Path("docs/receipts/MNEME_Phase_4_MI1_Calibration_Framing_Revision_20261010.json")
        ),
        "c2_receipt": sha256(args.c2_receipt),
        "pretest_receipt": sha256(args.pretest_receipt),
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
