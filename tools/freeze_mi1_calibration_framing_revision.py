#!/usr/bin/env python3
"""Freeze the second, generic MI1 calibration framing revision."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import build_calibration_framing_revision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent_bytes = args.parent_plan.read_bytes()
    parent: dict[str, Any] = json.loads(parent_bytes)
    plan = build_calibration_framing_revision(
        parent, parent_sha256=hashlib.sha256(parent_bytes).hexdigest()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"coordinates={len(plan['coordinates'])} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
