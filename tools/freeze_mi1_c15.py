#!/usr/bin/env python3
"""Write the pre-generation C15 MI1 encoding diagnostic freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c15_calibration import build_c15_plan


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c14-readout", type=Path, required=True)
    parser.add_argument("--selector-map", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = build_c15_plan(
        c14_readout_sha256=_sha(args.c14_readout),
        selector_map_sha256=_sha(args.selector_map),
    )
    plan["source_sha256"] = {
        "calibration": _sha(Path("experiments/mi1/c15_calibration.py")),
        "scoring": _sha(Path("experiments/mi1/c15_scoring.py")),
        "native_encoder": _sha(Path("tools/mi1_native_encode.cpp")),
        "bank_model": _sha(Path("experiments/mi1/native/bank.py")),
        "source_preparation": _sha(Path("tools/prepare_mi1_c15_sources.py")),
        "bank_preparation": _sha(Path("tools/prepare_mi1_c15_banks.py")),
        "runner": _sha(Path("tools/run_mi1_c15.py")),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(
        json.dumps(
            {"output": str(args.output), "sha256": _sha(args.output), "calls": plan["call_count"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
