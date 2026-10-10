#!/usr/bin/env python3
"""Run the frozen MI1 Test A/B/C suite with durable per-coordinate evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import variant_key
from experiments.mi1.coordinates import build_ongoing_turn_two_messages
from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
    load_completed_response,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def ongoing_messages(
    coordinate: dict[str, Any], suite: dict[str, Any], evidence_root: Path
) -> list[dict[str, str]]:
    dependency = coordinate.get("depends_on_attempt")
    if dependency != "C-ONGOING-A02-turn-1":
        raise ValueError("unexpected dynamic Test-C dependency")
    response = load_completed_response(evidence_root, dependency)
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("durable turn-1 response has no assistant choice")
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content:
        raise ValueError("durable turn-1 assistant final answer is empty")
    if suite["test_c"]["ongoing_exchange"]["fixture_id"] != coordinate["metadata"]["fixture_id"]:
        raise ValueError("ongoing Test-C dependency belongs to another fixture")
    return build_ongoing_turn_two_messages(suite, content)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--suite", type=Path, default=Path("experiments/mi1/fixtures/mi1_frozen_suite.json")
    )
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--coordinate-id")
    parser.add_argument("--prior-calibration-calls", type=int, default=361)
    parser.add_argument("--hard-limit", type=int, default=800)
    args = parser.parse_args()
    plan: dict[str, Any] = json.loads(args.plan.read_text(encoding="utf-8"))
    if plan.get("status") != "FROZEN_BEFORE_SCORED_GENERATION":
        raise ValueError("Test A/B/C plan must be frozen before scored inference")
    suite_bytes = args.suite.read_bytes()
    if hashlib.sha256(suite_bytes).hexdigest() != plan["source_suite_sha256"]:
        raise ValueError("frozen source suite digest changed")
    suite: dict[str, Any] = json.loads(suite_bytes)
    variant_map = json.loads(args.variant_map.read_text(encoding="utf-8"))
    if variant_map.get("plan_sha256") != hashlib.sha256(args.plan.read_bytes()).hexdigest():
        raise ValueError("bank variants belong to another frozen Test A/B/C plan")
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

    journal = EvidenceJournal(args.evidence_root, hard_call_limit=args.hard_limit)
    budget = GenerationBudget(
        args.budget,
        prior_calibration_calls=args.prior_calibration_calls,
        calibration_limit=None,
        hard_limit=args.hard_limit,
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
    metrics: dict[str, Any] = (
        json.loads(args.metrics.read_text(encoding="utf-8"))
        if args.metrics.exists()
        else {
            "schema_version": 1,
            "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
            "attempts": {},
        }
    )
    if metrics.get("plan_sha256") != hashlib.sha256(args.plan.read_bytes()).hexdigest():
        raise ValueError("latency metrics belong to another frozen plan")

    selected = 0
    for coordinate in plan["coordinates"]:
        coordinate_id = coordinate["coordinate_id"]
        if args.coordinate_id is not None and coordinate_id != args.coordinate_id:
            continue
        selected += 1
        if coordinate_id in failed:
            raise RuntimeError(f"failed coordinate remains preserved; no retry: {coordinate_id}")
        if coordinate_id in completed:
            continue
        if coordinate_id in reserved:
            raise RuntimeError(f"reserved coordinate lacks a complete receipt: {coordinate_id}")
        messages = None
        if coordinate.get("depends_on_attempt") is not None:
            messages = ongoing_messages(coordinate, suite, args.evidence_root)
        row: dict[str, Any] = {"started_at_utc": utc_now(), "status": "RUNNING"}
        metrics["attempts"][coordinate_id] = row
        atomic_json_write(args.metrics, metrics)
        start = time.monotonic()
        try:
            runner.execute(coordinate, phase="scored", messages=messages)
        except Exception as exc:
            row.update({"status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)})
            row["elapsed_seconds"] = time.monotonic() - start
            row["completed_at_utc"] = utc_now()
            atomic_json_write(args.metrics, metrics)
            raise
        row.update(
            {
                "status": "COMPLETE",
                "elapsed_seconds": time.monotonic() - start,
                "completed_at_utc": utc_now(),
            }
        )
        atomic_json_write(args.metrics, metrics)
        completed.add(coordinate_id)

    if args.coordinate_id is not None and selected != 1:
        raise ValueError("requested coordinate ID is absent or ambiguous")
    print(json.dumps(budget.counts(), sort_keys=True))
    print(json.dumps(journal.verify(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
