#!/usr/bin/env python3
"""Run a frozen MI1 diagnostic plan with a durable, uncapped ledger."""

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
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--coordinate-id")
    parser.add_argument("--prior-calibration-calls", type=int, default=97)
    args = parser.parse_args()
    plan: dict[str, Any] = json.loads(args.plan.read_text(encoding="utf-8"))
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C3 plan must be frozen before inference")
    variant_map = json.loads(args.variant_map.read_text(encoding="utf-8"))
    plan_sha = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    if variant_map.get("plan_sha256") != plan_sha:
        raise ValueError("bank variants belong to another frozen C3 plan")
    variants = variant_map["variants"]

    def resolve(source: str, digest: str, config: dict[str, Any]) -> ResolvedBank:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != digest:
            raise ValueError("coordinate bank source hash mismatch")
        key = variant_key(digest, config)
        row = variants.get(key)
        if row is None or row.get("source_sha256") != digest or row.get("config") != config:
            raise ValueError("no exact frozen bank variant exists for this coordinate")
        return ResolvedBank(
            path=Path(row["remote_path"]),
            native_sha256=row["native_sha256"],
            bank_fingerprint=row["bank_fingerprint"],
            selector_sha256=row["selector_sha256"],
            selector=row["selector"],
        )

    journal = EvidenceJournal(args.evidence_root, hard_call_limit=None)
    budget = GenerationBudget(
        args.budget,
        prior_calibration_calls=args.prior_calibration_calls,
        calibration_limit=None,
        hard_limit=None,
    )
    runner = MI1CoordinateRunner(
        base_url=args.base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    index = json.loads((args.evidence_root / "index.json").read_text(encoding="utf-8"))
    completed = {row["attempt_id"] for row in index["attempts"] if row["status"] == "COMPLETE"}
    failed = {row["attempt_id"] for row in index["attempts"] if row["status"] != "COMPLETE"}
    reservations = json.loads(args.budget.read_text(encoding="utf-8"))["reservations"]
    reserved = {row["attempt_id"] for row in reservations}
    selected = 0
    for coordinate in plan["coordinates"]:
        if args.coordinate_id is not None and coordinate["coordinate_id"] != args.coordinate_id:
            continue
        selected += 1
        coordinate_id = coordinate["coordinate_id"]
        if coordinate_id in failed:
            raise RuntimeError(f"failed coordinate remains preserved; no retry: {coordinate_id}")
        if coordinate_id in completed:
            continue
        if coordinate_id in reserved:
            raise RuntimeError(f"reserved coordinate lacks a complete receipt: {coordinate_id}")
        runner.execute(coordinate, phase="calibration")
    if args.coordinate_id is not None and selected != 1:
        raise ValueError("requested coordinate ID is absent or ambiguous")
    print(json.dumps(budget.counts(), sort_keys=True))
    print(json.dumps(journal.verify(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
