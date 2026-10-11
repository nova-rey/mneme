#!/usr/bin/env python3
"""Freeze a no-tuning recovery after C11's final response was not captured."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.c11_recovery import build_recovery_plan


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--server-completion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan_bytes = args.plan.read_bytes()
    index_bytes = (args.evidence_root / "index.json").read_bytes()
    budget = json.loads(args.budget.read_text(encoding="utf-8"))
    output: dict[str, Any] = build_recovery_plan(
        json.loads(plan_bytes),
        frozen_plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
        evidence_index=json.loads(index_bytes),
        evidence_index_sha256=hashlib.sha256(index_bytes).hexdigest(),
        evidence_root=args.evidence_root,
        generation_budget=budget,
        server_completion=json.loads(args.server_completion.read_text(encoding="utf-8")),
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
                "calls": output["count"],
                "projected_campaign_total": output["accounting"]["projected_campaign_total"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
