#!/usr/bin/env python3
"""Run or resume one frozen C12 phase with durable no-retry evidence."""

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
    parser.add_argument("--phase", choices=("calibration", "confirmation"), default="calibration")
    args = parser.parse_args()
    plan_bytes = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_bytes)
    if plan.get("status") not in {
        "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "FROZEN_BEFORE_HELDOUT_GENERATION",
    }:
        raise ValueError("C12 phase is not frozen before generation")
    variants: dict[str, Any] = json.loads(args.variant_map.read_text(encoding="utf-8"))
    if variants.get("plan_sha256") != hashlib.sha256(plan_bytes).hexdigest():
        raise ValueError("C12 variants were prepared for a different frozen plan")

    def resolve(source: str, digest: str, config: dict[str, Any]) -> ResolvedBank:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != digest:
            raise ValueError("C12 request bank source hash mismatch")
        row = variants["variants"].get(variant_key(digest, config))
        if row is None or row.get("source_sha256") != digest or row.get("config") != config:
            raise ValueError("C12 bank variant is missing or has the wrong frozen config")
        return ResolvedBank(
            path=Path(row["remote_path"]),
            native_sha256=row["native_sha256"],
            bank_fingerprint=row["bank_fingerprint"],
            selector_sha256=row["selector_sha256"],
            selector=row["selector"],
        )

    evidence = EvidenceJournal(args.evidence_root, hard_call_limit=int(plan["call_count"]))
    budget = GenerationBudget(
        args.budget,
        prior_calibration_calls=792,
        calibration_limit=None,
        hard_limit=None,
    )
    runner = MI1CoordinateRunner(
        base_url=args.base_url,
        journal=evidence,
        budget=budget,
        bank_resolver=resolve,
    )
    index = json.loads((args.evidence_root / "index.json").read_text(encoding="utf-8"))
    completed = {row["attempt_id"] for row in index["attempts"] if row["status"] == "COMPLETE"}
    uncertain = {row["attempt_id"] for row in index["attempts"] if row["status"] != "COMPLETE"}
    if uncertain:
        raise RuntimeError(
            f"C12 contains uncertain prior calls; refusing implicit retry: {sorted(uncertain)}"
        )
    reserved = {
        row["attempt_id"]
        for row in json.loads(args.budget.read_text(encoding="utf-8"))["reservations"]
    }
    for coordinate in plan["coordinates"]:
        attempt = coordinate["coordinate_id"]
        if attempt in completed:
            continue
        if attempt in reserved:
            raise RuntimeError(f"C12 call was charged without complete evidence: {attempt}")
        runner.execute(coordinate, phase=args.phase)
        completed.add(attempt)
        print(
            json.dumps({"complete": len(completed), "total": plan["call_count"], "id": attempt}),
            flush=True,
        )
    print(json.dumps({"budget": budget.counts(), "journal": evidence.verify()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
