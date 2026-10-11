#!/usr/bin/env python3
"""Execute or score the frozen C17 all-head diagnostic with durable SSE evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.calibration import variant_key
from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.lower()).split())


def score_phase(plan: dict[str, Any], evidence_root: Path, phase: str) -> dict[str, Any]:
    rows = plan["calibration_coordinates" if phase == "calibration" else "confirmation_coordinates"]
    expected = {row["coordinate_id"]: row for row in rows}
    index = json.loads((evidence_root / "index.json").read_text(encoding="utf-8"))
    seen: set[str] = set()
    output_rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for item in index["attempts"]:
        key = item["attempt_id"]
        if key not in expected:
            continue
        if key in seen:
            raise ValueError(f"duplicate C17 attempt ID: {key}")
        seen.add(key)
        if item["status"] != "COMPLETE":
            missing.append(key)
            continue
        result = json.loads((evidence_root / "attempts" / item["outcome_file"]).read_text())
        choices = result.get("payload", {}).get("choices", [])
        if len(choices) != 1:
            missing.append(key)
            continue
        choice = choices[0]
        answer = str(choice.get("message", {}).get("content") or "").strip()
        row = expected[key]
        output_rows.append(
            {
                "coordinate_id": key,
                "fixture_id": row["fixture_id"],
                "condition": row["condition"],
                "seed": row["seed"],
                "expected": row["expected"]["answer"],
                "answer": answer,
                "exact_label_hit": normalize(answer) == normalize(row["expected"]["answer"]),
                "finish_reason": choice.get("finish_reason"),
                "request_sha256": item["request_sha256"],
                "outcome_sha256": item["outcome_sha256"],
                "reasoning_bytes": len(
                    str(choice.get("message", {}).get("reasoning_content") or "").encode()
                ),
            }
        )
    missing.extend(sorted(set(expected) - seen))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in output_rows:
        groups[row["condition"]].append(row)
    rates = {
        condition: {
            "n": len(values),
            "hits": sum(x["exact_label_hit"] for x in values),
            "rate": sum(x["exact_label_hit"] for x in values) / len(values),
        }
        for condition, values in sorted(groups.items())
    }
    gate = plan["gate"]
    complete = not missing and len(output_rows) == len(expected)
    passed: bool | None = None
    if complete:
        if phase == "calibration":
            passed = (
                rates["no_bank"]["hits"] >= gate["no_bank_minimum"]
                and rates["visible_A"]["hits"] >= gate["visible_A_minimum"]
                and rates["visible_B"]["hits"] >= gate["visible_B_minimum"]
                and rates["latent_all_A"]["hits"] >= gate["latent_all_A_minimum"]
                and rates["latent_all_B"]["hits"] >= gate["latent_all_B_minimum"]
            )
        else:
            passed = all(
                value["hits"] >= gate["confirmation_minimum_each_condition"]
                for value in rates.values()
            )
    return {
        "schema_version": 1,
        "experiment": plan["experiment"],
        "phase": phase,
        "scheduled_coordinates": len(expected),
        "complete_coordinates": len(output_rows),
        "missing_or_uncertain_coordinates": sorted(missing),
        "condition_rates": rates,
        "gate_passed": passed,
        "coordinates": output_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--phase", choices=("calibration", "confirmation"), required=True)
    parser.add_argument("--score-only", action="store_true")
    parser.add_argument("--max-new-calls", type=int)
    args = parser.parse_args()
    plan_bytes = args.plan.read_bytes()
    plan = json.loads(plan_bytes)
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    if plan.get("status") != "FROZEN_BEFORE_GENERATION":
        raise ValueError("C17 plan is not frozen")
    variant_map = json.loads(args.variant_map.read_text(encoding="utf-8"))
    if variant_map.get("plan_sha256") != plan_sha:
        raise ValueError("C17 variants belong to a different frozen plan")
    variants = variant_map["variants"]

    def resolve(source: str, digest: str, config: dict[str, Any]) -> ResolvedBank:
        if hashlib.sha256(source.encode()).hexdigest() != digest:
            raise ValueError("C17 coordinate source digest mismatch")
        row = variants.get(variant_key(digest, config))
        if row is None or row.get("source_sha256") != digest or row.get("config") != config:
            raise ValueError("no exact frozen C17 bank variant exists")
        return ResolvedBank(
            Path(row["remote_path"]),
            row["native_sha256"],
            row["bank_fingerprint"],
            row["selector_sha256"],
            row["selector"],
        )

    if not args.score_only:
        journal = EvidenceJournal(args.evidence_root, hard_call_limit=None)
        budget = GenerationBudget(
            args.budget, prior_calibration_calls=0, calibration_limit=None, hard_limit=None
        )
        runner = MI1CoordinateRunner(
            base_url=args.base_url, journal=journal, budget=budget, bank_resolver=resolve
        )
        index = json.loads((args.evidence_root / "index.json").read_text())
        completed = {x["attempt_id"] for x in index["attempts"] if x["status"] == "COMPLETE"}
        failed = {x["attempt_id"] for x in index["attempts"] if x["status"] != "COMPLETE"}
        if failed:
            raise RuntimeError(f"C17 failures preserved; no automatic retries: {sorted(failed)}")
        coordinates = plan[
            "calibration_coordinates" if args.phase == "calibration" else "confirmation_coordinates"
        ]
        if args.phase == "confirmation":
            gate_path = args.score.with_name("score-calibration.json")
            gate_result = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate_result.get("gate_passed") is not True:
                raise RuntimeError(
                    "held-out confirmation is not authorized by the frozen calibration gate"
                )
        if args.max_new_calls is not None and args.max_new_calls <= 0:
            raise ValueError("--max-new-calls must be positive")
        new_calls = 0
        for coordinate in coordinates:
            if coordinate["coordinate_id"] in completed:
                continue
            if args.max_new_calls is not None and new_calls >= args.max_new_calls:
                break
            runner.execute(coordinate, phase=args.phase)
            completed.add(coordinate["coordinate_id"])
            new_calls += 1
    result = score_phase(plan, args.evidence_root, args.phase)
    atomic_json_write(args.score, result)
    print(
        json.dumps(
            {
                "phase": args.phase,
                "complete": result["complete_coordinates"],
                "scheduled": result["scheduled_coordinates"],
                "gate_passed": result["gate_passed"],
                "rates": result["condition_rates"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
