#!/usr/bin/env python3
"""Apply C16's frozen exact-label calibration/confirmation gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c16_calibration import score_c16


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("calibration", "confirmation"), default="calibration")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, Any] = score_c16(args.plan, args.evidence_root, phase=args.phase)
    result["plan_sha256"] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "phase": args.phase,
                "complete": result["complete_coordinates"],
                "passed": result.get("calibration_gate_passed", result.get("confirmation_passed")),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
