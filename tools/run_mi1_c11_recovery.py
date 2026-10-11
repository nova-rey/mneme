#!/usr/bin/env python3
"""Run only the frozen C11 lost-coordinate replay and untouched coordinates."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.mi1.c11_recovery import recovery_coordinates
from experiments.mi1.calibration import variant_key
from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import GenerationBudget, MI1CoordinateRunner, ResolvedBank


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--recovery-plan", type=Path, required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()

    plan_bytes = args.plan.read_bytes()
    recovery_bytes = args.recovery_plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_bytes)
    recovery: dict[str, Any] = json.loads(recovery_bytes)
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    if recovery.get("status") != "FROZEN_BEFORE_RECOVERY_GENERATION":
        raise ValueError("C11 recovery plan is not frozen")
    if recovery.get("parent_execution_plan_sha256") != plan_sha:
        raise ValueError("recovery plan belongs to a different C11 execution plan")

    variant_map: dict[str, Any] = json.loads(args.variant_map.read_text(encoding="utf-8"))
    if variant_map.get("plan_sha256") != plan_sha:
        raise ValueError("C11 bank variants belong to another execution plan")
    variants = variant_map["variants"]

    def resolve(source: str, digest: str, config: dict[str, Any]) -> ResolvedBank:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != digest:
            raise ValueError("C11 bank source hash mismatch")
        row = variants.get(variant_key(digest, config))
        if row is None or row.get("source_sha256") != digest or row.get("config") != config:
            raise ValueError("no exact frozen C11 bank variant exists")
        return ResolvedBank(
            path=Path(row["remote_path"]),
            native_sha256=row["native_sha256"],
            bank_fingerprint=row["bank_fingerprint"],
            selector_sha256=row["selector_sha256"],
            selector=row["selector"],
        )

    coordinates = recovery_coordinates(plan, recovery)
    journal = EvidenceJournal(args.evidence_root, hard_call_limit=120)
    budget = GenerationBudget(
        args.budget,
        prior_calibration_calls=647,
        calibration_limit=None,
        hard_limit=800,
    )
    runner = MI1CoordinateRunner(
        base_url=args.base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    index = json.loads((args.evidence_root / "index.json").read_text(encoding="utf-8"))
    completed = {
        row["attempt_id"] for row in index["attempts"] if row["status"] == "COMPLETE"
    }
    incomplete = {
        row["attempt_id"] for row in index["attempts"] if row["status"] != "COMPLETE"
    }
    if incomplete:
        raise RuntimeError(f"recovery evidence has unresolved prior calls: {sorted(incomplete)}")
    recovery_sha = hashlib.sha256(recovery_bytes).hexdigest()
    metrics: dict[str, Any] = (
        json.loads(args.metrics.read_text(encoding="utf-8"))
        if args.metrics.exists()
        else {
            "schema_version": 1,
            "plan_sha256": plan_sha,
            "recovery_plan_sha256": recovery_sha,
            "attempts": {},
        }
    )
    if (
        metrics.get("plan_sha256") != plan_sha
        or metrics.get("recovery_plan_sha256") != recovery_sha
    ):
        raise ValueError("recovery timing metrics belong to another frozen plan")

    for coordinate in coordinates:
        coordinate_id = coordinate["coordinate_id"]
        if coordinate_id in completed:
            continue
        row: dict[str, Any] = {"started_at_utc": utc_now(), "status": "RUNNING"}
        metrics["attempts"][coordinate_id] = row
        atomic_json_write(args.metrics, metrics)
        started = time.monotonic()
        try:
            runner.execute(coordinate, phase="scored")
        except Exception as exc:
            row.update({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)})
            row["elapsed_seconds"] = time.monotonic() - started
            row["completed_at_utc"] = utc_now()
            atomic_json_write(args.metrics, metrics)
            raise
        row.update(
            {
                "status": "COMPLETE",
                "elapsed_seconds": time.monotonic() - started,
                "completed_at_utc": utc_now(),
            }
        )
        atomic_json_write(args.metrics, metrics)
        completed.add(coordinate_id)
        print(
            json.dumps(
                {
                    "completed": len(completed),
                    "coordinate_id": coordinate_id,
                    "budget": budget.counts(),
                },
                sort_keys=True,
            ),
            flush=True,
        )
    print(json.dumps({"budget": budget.counts(), "journal": journal.verify()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
