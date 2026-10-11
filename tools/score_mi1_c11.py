#!/usr/bin/env python3
"""Score frozen C11 criteria from the immutable original and recovery journals."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c11_scoring import score_c11
from experiments.mi1.native.evidence import atomic_json_write


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-plan", type=Path, required=True)
    parser.add_argument("--design-plan", type=Path, required=True)
    parser.add_argument("--parent-evidence", type=Path, required=True)
    parser.add_argument("--recovery-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execution_bytes = args.execution_plan.read_bytes()
    design_bytes = args.design_plan.read_bytes()
    execution: dict[str, Any] = json.loads(execution_bytes)
    design: dict[str, Any] = json.loads(design_bytes)
    if execution.get("design_plan_sha256") != hashlib.sha256(design_bytes).hexdigest():
        raise ValueError("C11 design and execution plan hashes do not match")
    scored = score_c11(execution, design, args.parent_evidence, args.recovery_evidence)
    scored["provenance"] = {
        "execution_plan_sha256": hashlib.sha256(execution_bytes).hexdigest(),
        "design_plan_sha256": hashlib.sha256(design_bytes).hexdigest(),
        "parent_index_sha256": _digest(args.parent_evidence / "index.json"),
        "recovery_index_sha256": _digest(args.recovery_evidence / "index.json"),
    }
    atomic_json_write(args.output, scored)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": _digest(args.output),
                "criteria_result": scored["criteria_result"],
                "condition_rates": scored["condition_rates"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
