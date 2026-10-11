#!/usr/bin/env python3
"""Score C15 calibration or held-out confirmation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c15_scoring import score_c15


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("calibration", "confirmation"), default="calibration")
    parser.add_argument("--encoding", choices=("system_turn", "user_turn", "raw"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, Any] = score_c15(
        args.plan, args.evidence_root, phase=args.phase, encoding=args.encoding
    )
    result["plan_sha256"] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "phase": args.phase,
                "output": str(args.output),
                "complete": result["complete_coordinates"],
                "selected_encoding": result.get("selected_encoding"),
                "passed": result.get("calibration_gate_passed", result.get("confirmation_passed")),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
