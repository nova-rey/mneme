#!/usr/bin/env python3
"""Freeze the C12 cue/dose calibration plan before any generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c12_calibration import build_calibration_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection_bytes = args.site_selection.read_bytes()
    selection: dict[str, Any] = json.loads(selection_bytes)
    plan = build_calibration_plan(
        c11_selection=selection,
        c11_selection_sha256=hashlib.sha256(selection_bytes).hexdigest(),
    )
    plan["code_sha256"] = {
        "calibration_module": hashlib.sha256(
            Path("experiments/mi1/c12_calibration.py").read_bytes()
        ).hexdigest(),
        "site_selection": hashlib.sha256(
            Path("experiments/mi1/c11_site_selection.py").read_bytes()
        ).hexdigest(),
        "runner": hashlib.sha256(Path("experiments/mi1/runner.py").read_bytes()).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(
        json.dumps(
            {"output": str(args.output), "sha256": digest, "coordinates": plan["call_count"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
