#!/usr/bin/env python3
"""Freeze C17's all-head diagnostic plan before any new generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.c17_allhead_calibration import write_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c16-plan", type=Path, required=True)
    parser.add_argument("--c16-readout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    digest = write_plan(args.output, c16_plan=args.c16_plan, c16_readout=args.c16_readout)
    print(f"plan={args.output} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
