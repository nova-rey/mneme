#!/usr/bin/env python3
"""Run one frozen MI1 calibration server role with durable, no-retry evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import variant_key
from experiments.mi1.native.evidence import EvidenceJournal
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--base-server-url", required=True)
    parser.add_argument("--server-role", choices=("mi1_server", "base_server"), required=True)
    parser.add_argument("--coordinate-id")
    args = parser.parse_args()
    plan: dict[str, Any] = json.loads(args.plan.read_text(encoding="utf-8"))
    if plan.get("status") not in {
        "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "FROZEN_MECHANICAL_CORRECTION",
        "FROZEN_CALIBRATION_REVISION",
    }:
        raise ValueError("calibration plan is not frozen before generation")
    variant_manifest = json.loads(args.variant_map.read_text(encoding="utf-8"))
    expected_variant_plan = (
        plan.get("variant_source_plan_sha256")
        or plan.get("parent_plan_sha256")
        or hashlib.sha256(args.plan.read_bytes()).hexdigest()
    )
    if variant_manifest.get("plan_sha256") != expected_variant_plan:
        raise ValueError("variant map was prepared for another frozen plan")
    variants = variant_manifest["variants"]

    def resolve(source: str, source_sha: str, config: dict[str, Any]) -> ResolvedBank:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != source_sha:
            raise ValueError("runner received source text with a different frozen hash")
        key = variant_key(source_sha, config)
        row = variants.get(key)
        if row is None or row.get("source_sha256") != source_sha or row.get("config") != config:
            raise ValueError("no exact frozen host-local variant for requested bank/config")
        return ResolvedBank(
            path=Path(row["remote_path"]),
            native_sha256=row["native_sha256"],
            bank_fingerprint=row["bank_fingerprint"],
            selector_sha256=row["selector_sha256"],
            selector=row["selector"],
        )

    journal = EvidenceJournal(args.evidence_root, hard_call_limit=800)
    budget = GenerationBudget(args.budget)
    runner = MI1CoordinateRunner(
        base_url=args.base_url,
        base_server_url=args.base_server_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    index = json.loads((args.evidence_root / "index.json").read_text(encoding="utf-8"))
    completed = {row["attempt_id"] for row in index["attempts"] if row["status"] == "COMPLETE"}
    failed = {row["attempt_id"] for row in index["attempts"] if row["status"] != "COMPLETE"}
    reservations = json.loads(args.budget.read_text(encoding="utf-8"))["reservations"]
    reserved = {row["attempt_id"] for row in reservations}
    selected_count = 0
    for coordinate in plan["coordinates"]:
        if args.coordinate_id is not None and coordinate["coordinate_id"] != args.coordinate_id:
            continue
        if coordinate["metadata"]["server_role"] != args.server_role:
            continue
        selected_count += 1
        coordinate_id = coordinate["coordinate_id"]
        if coordinate_id in failed:
            raise RuntimeError(
                f"previous attempt is failed/uncertain; refusing retry: {coordinate_id}"
            )
        if coordinate_id in completed:
            continue
        if coordinate_id in reserved:
            raise RuntimeError(
                f"reserved call has no complete evidence; refusing retry: {coordinate_id}"
            )
        runner.execute(coordinate, phase="calibration")
    if args.coordinate_id is not None and selected_count != 1:
        raise ValueError("requested coordinate ID is absent or ambiguous in this plan")
    print(json.dumps(budget.counts(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
