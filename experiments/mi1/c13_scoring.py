"""Strictly score the frozen C13 calibration without regenerating responses."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def _normalized(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.lower()).split())


def score_c13(plan_path: Path, evidence_root: Path) -> dict[str, Any]:
    """Join all C13 frozen coordinates to their immutable result envelopes."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    index = json.loads((evidence_root / "index.json").read_text(encoding="utf-8"))
    expected = {row["coordinate_id"]: row for row in plan["coordinates"]}
    if len(expected) != plan["call_count"]:
        raise ValueError("C13 plan has duplicate or missing coordinate IDs")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    missing: list[str] = []
    for attempt in index["attempts"]:
        coordinate_id = attempt["attempt_id"]
        if coordinate_id not in expected:
            raise ValueError(f"unexpected C13 attempt: {coordinate_id}")
        if coordinate_id in seen:
            raise ValueError(f"duplicate C13 attempt: {coordinate_id}")
        seen.add(coordinate_id)
        if attempt["status"] != "COMPLETE":
            missing.append(coordinate_id)
            continue
        outcome = json.loads(
            (evidence_root / "attempts" / attempt["outcome_file"]).read_text(
                encoding="utf-8"
            )
        )
        if outcome.get("attempt_id") != coordinate_id or outcome.get("status") != "COMPLETE":
            raise ValueError(f"invalid C13 completion envelope: {coordinate_id}")
        choices = outcome.get("payload", {}).get("choices", [])
        if len(choices) != 1:
            raise ValueError(f"C13 result must have exactly one choice: {coordinate_id}")
        choice = choices[0]
        message = choice.get("message", {})
        source = expected[coordinate_id]
        answer = str(message.get("content") or "").strip()
        reasoning = str(message.get("reasoning_content") or "")
        wanted = str(source["expected"]["answer"])
        facts = [
            line.strip()
            for line in str(source.get("bank_source") or "").splitlines()
            if line.strip()
        ]
        normalized_reasoning = _normalized(reasoning)
        rows.append(
            {
                "coordinate_id": coordinate_id,
                "fixture_id": source["fixture_id"],
                "seed": source["seed"],
                "condition": source["condition"],
                "selector": source["bank_config"]["selector"],
                "expected": wanted,
                "answer": answer,
                "exact_label_hit": _normalized(answer) == _normalized(wanted),
                "finish_reason": choice.get("finish_reason"),
                "reasoning_bytes": len(reasoning.encode("utf-8")),
                "final_bytes": len(answer.encode("utf-8")),
                "source_fact_count": len(facts),
                "source_facts_mentioned_in_reasoning": sum(
                    _normalized(fact) in normalized_reasoning for fact in facts
                ),
                "request_sha256": attempt["request_sha256"],
                "outcome_sha256": attempt["outcome_sha256"],
            }
        )

    absent = sorted(set(expected) - seen)
    missing.extend(absent)
    if len(rows) + len(missing) != len(expected):
        raise ValueError("C13 evidence does not reconcile to the frozen coordinate count")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["condition"]].append(row)
    rates: dict[str, dict[str, Any]] = {}
    for condition, values in sorted(groups.items()):
        hits = sum(row["exact_label_hit"] for row in values)
        rates[condition] = {
            "n": len(values),
            "exact_label_hits": hits,
            "rate": hits / len(values),
            "finish_reasons": {
                str(reason): sum(row["finish_reason"] == reason for row in values)
                for reason in sorted({row["finish_reason"] for row in values}, key=str)
            },
            "source_fact_mention_coordinates": sum(
                row["source_facts_mentioned_in_reasoning"] == row["source_fact_count"]
                and row["source_fact_count"] > 0
                for row in values
            ),
        }

    def hits(condition: str) -> int:
        return int(rates.get(condition, {}).get("exact_label_hits", 0))

    threshold = int(plan["criteria"]["calibration_per_polarity_minimum"])
    visible_threshold = int(plan["criteria"]["visible_each_polarity_minimum"])
    control_threshold = int(plan["criteria"]["unknown_controls_minimum"])
    controls = ("no_bank", "cue_no_bank_assertive", "latent_irrelevant_broad_assertive_fourfold")

    def mode_passes(mode: str) -> bool:
        suffix = "selected_assertive_fourfold" if mode == "selected" else "broad_assertive_fourfold"
        return (
            hits(f"latent_A_{suffix}") >= threshold
            and hits(f"latent_B_{suffix}") >= threshold
            and hits("visible_A") >= visible_threshold
            and hits("visible_B") >= visible_threshold
            and all(hits(control) >= control_threshold for control in controls)
        )

    passing = [mode for mode in ("selected", "broad") if mode_passes(mode)]
    chosen = "selected" if "selected" in passing else "broad" if "broad" in passing else None
    return {
        "schema_version": 1,
        "experiment": plan["experiment"],
        "plan_sha256": plan.get("sha256"),
        "scheduled_coordinates": len(expected),
        "complete_coordinates": len(rows),
        "missing_or_uncertain_coordinates": sorted(missing),
        "condition_rates": rates,
        "routing_modes_passing_predeclared_gate": passing,
        "selected_confirmation_routing_mode": chosen,
        "calibration_gate_passed": chosen is not None,
        "heldout_generation_authorized_by_gate": chosen is not None,
        "coordinates": rows,
    }
