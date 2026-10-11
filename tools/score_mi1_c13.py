#!/usr/bin/env python3
"""Score a completed, frozen C13 evidence journal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c13_scoring import score_c13


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, Any] = score_c13(args.plan, args.evidence_root)
    result["plan_sha256"] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "complete_coordinates": result["complete_coordinates"],
                "calibration_gate_passed": result["calibration_gate_passed"],
                "passing_modes": result["routing_modes_passing_predeclared_gate"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
