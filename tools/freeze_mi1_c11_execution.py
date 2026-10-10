#!/usr/bin/env python3
"""Materialize the frozen C11 conditions as exact durable runner coordinates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c11_execution import build_execution_plan


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    design_bytes = args.design.read_bytes()
    selection_bytes = args.selection.read_bytes()
    output: dict[str, Any] = build_execution_plan(
        json.loads(design_bytes),
        frozen_plan_sha256=hashlib.sha256(design_bytes).hexdigest(),
        site_selection=json.loads(selection_bytes),
        site_selection_sha256=hashlib.sha256(selection_bytes).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                "coordinates": output["coordinate_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
