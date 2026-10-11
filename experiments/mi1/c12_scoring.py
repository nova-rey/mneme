"""Strictly score the frozen C12 calibration without regenerating responses."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def _normalized_answer(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.lower()).split())


def score_c12(plan_path: Path, evidence_root: Path) -> dict[str, Any]:
    """Join the exact frozen C12 coordinates to their immutable local outcomes."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    index = json.loads((evidence_root / "index.json").read_text(encoding="utf-8"))
    expected = {row["coordinate_id"]: row for row in plan["coordinates"]}
    if len(expected) != plan["call_count"]:
        raise ValueError("C12 plan has duplicate or missing coordinate IDs")

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    missing: list[str] = []
    for attempt in index["attempts"]:
        coordinate_id = attempt["attempt_id"]
        if coordinate_id not in expected:
            raise ValueError(f"unexpected C12 attempt: {coordinate_id}")
        if coordinate_id in seen:
            raise ValueError(f"duplicate C12 attempt: {coordinate_id}")
        seen.add(coordinate_id)
        if attempt["status"] != "COMPLETE":
            missing.append(coordinate_id)
            continue
        outcome_path = evidence_root / "attempts" / attempt["outcome_file"]
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        if outcome.get("attempt_id") != coordinate_id or outcome.get("status") != "COMPLETE":
            raise ValueError(f"invalid C12 completion envelope: {coordinate_id}")
        choices = outcome.get("payload", {}).get("choices", [])
        if len(choices) != 1:
            raise ValueError(f"C12 result must have exactly one choice: {coordinate_id}")
        choice = choices[0]
        message = choice.get("message", {})
        source = expected[coordinate_id]
        answer = str(message.get("content") or "").strip()
        reasoning = str(message.get("reasoning_content") or "")
        source_facts = [
            line.strip()
            for line in str(source.get("bank_source") or "").splitlines()
            if line.strip()
        ]
        normalized_reasoning = _normalized_answer(reasoning)
        fact_mentions = [
            _normalized_answer(fact) in normalized_reasoning for fact in source_facts
        ]
        records.append(
            {
                "coordinate_id": coordinate_id,
                "fixture_id": source["metadata"]["fixture_id"],
                "seed": source["metadata"]["seed"],
                "condition": source["metadata"]["condition"],
                "expected": source["expected"]["answer"],
                "answer": answer,
                "answer_correct": _normalized_answer(answer)
                == _normalized_answer(source["expected"]["answer"]),
                "finish_reason": choice.get("finish_reason"),
                "reasoning_bytes": len(reasoning.encode("utf-8")),
                "final_bytes": len(answer.encode("utf-8")),
                "source_fact_count": len(source_facts),
                "source_facts_mentioned": sum(fact_mentions),
                "all_source_facts_mentioned": bool(source_facts) and all(fact_mentions),
                "request_sha256": attempt["request_sha256"],
                "outcome_sha256": attempt["outcome_sha256"],
            }
        )

    absent = sorted(set(expected) - seen)
    if absent:
        missing.extend(absent)
    if len(records) + len(missing) != len(expected):
        raise ValueError("C12 evidence does not reconcile to the frozen coordinate count")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["condition"]].append(record)
    rates = {
        condition: {
            "n": len(rows),
            "correct": sum(row["answer_correct"] for row in rows),
            "rate": sum(row["answer_correct"] for row in rows) / len(rows),
            "finish_reasons": {
                reason: sum(row["finish_reason"] == reason for row in rows)
                for reason in sorted({row["finish_reason"] for row in rows}, key=str)
            },
            "complete_source_fact_mentions": sum(
                row["all_source_facts_mentioned"] for row in rows
            ),
        }
        for condition, rows in sorted(groups.items())
    }

    def rate(condition: str) -> int:
        return int(rates.get(condition, {}).get("correct", 0))

    criteria = plan["criteria"]
    passing_biases = []
    for bias in ("zero", "twofold", "fourfold"):
        latent_a = rate(f"latent_A_{bias}")
        latent_b = rate(f"latent_B_{bias}")
        visible_a = rate("visible_A")
        visible_b = rate("visible_B")
        controls = [
            rate("no_bank"),
            rate("cue_no_bank"),
            rate("latent_irrelevant_fourfold"),
        ]
        if (
            latent_a >= criteria["latent_each_polarity_minimum"]
            and latent_b >= criteria["latent_each_polarity_minimum"]
            and visible_a >= criteria["visible_each_polarity_minimum"]
            and visible_b >= criteria["visible_each_polarity_minimum"]
            and min(controls) >= criteria["unknown_control_minimum"]
        ):
            passing_biases.append(bias)

    return {
        "schema_version": 1,
        "experiment": plan["experiment"],
        "plan_sha256": plan.get("sha256"),
        "scheduled_coordinates": len(expected),
        "complete_coordinates": len(records),
        "missing_or_uncertain_coordinates": sorted(missing),
        "condition_rates": rates,
        "passing_biases_in_predeclared_order": passing_biases,
        "calibration_gate_passed": bool(passing_biases),
        "heldout_generation_authorized_by_gate": bool(passing_biases),
        "coordinates": records,
    }
