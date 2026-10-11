#!/usr/bin/env python3
"""Run or resume frozen C13 calibration with no implicit retries."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import variant_key
from experiments.mi1.native.evidence import EvidenceJournal
from experiments.mi1.runner import GenerationBudget, MI1CoordinateRunner, ResolvedBank


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18472")
    args = parser.parse_args()
    plan_raw = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_raw)
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C13 plan is not frozen")
    variants: dict[str, Any] = json.loads(args.variant_map.read_text(encoding="utf-8"))
    if variants.get("plan_sha256") != hashlib.sha256(plan_raw).hexdigest():
        raise ValueError("C13 bank map was prepared for a different plan")

    def resolve(source: str, digest: str, config: dict[str, Any]) -> ResolvedBank:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != digest:
            raise ValueError("C13 bank source hash mismatch")
        row = variants["variants"].get(variant_key(digest, config))
        if row is None or row.get("source_sha256") != digest or row.get("config") != config:
            raise ValueError("missing or mismatched C13 bank variant")
        return ResolvedBank(
            path=Path(row["remote_path"]),
            native_sha256=row["native_sha256"],
            bank_fingerprint=row["bank_fingerprint"],
            selector_sha256=row["selector_sha256"],
            selector=row["selector"],
        )

    journal = EvidenceJournal(args.evidence_root, hard_call_limit=int(plan["call_count"]))
    budget = GenerationBudget(args.budget, prior_calibration_calls=880)
    runner = MI1CoordinateRunner(
        base_url=args.base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    index = json.loads((args.evidence_root / "index.json").read_text(encoding="utf-8"))
    complete = {
        row["attempt_id"] for row in index["attempts"] if row["status"] == "COMPLETE"
    }
    uncertain = [row["attempt_id"] for row in index["attempts"] if row["status"] != "COMPLETE"]
    if uncertain:
        raise RuntimeError(f"C13 has uncertain calls; refusing implicit retry: {sorted(uncertain)}")
    reserved = {
        row["attempt_id"]
        for row in json.loads(args.budget.read_text(encoding="utf-8"))["reservations"]
    }
    for coordinate in plan["coordinates"]:
        attempt = coordinate["coordinate_id"]
        if attempt in complete:
            continue
        if attempt in reserved:
            raise RuntimeError(f"C13 call was reserved without complete evidence: {attempt}")
        runner.execute(coordinate, phase="calibration")
        complete.add(attempt)
        print(
            json.dumps({"complete": len(complete), "total": plan["call_count"], "id": attempt}),
            flush=True,
        )
    print(json.dumps({"budget": budget.counts(), "journal": journal.verify()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
