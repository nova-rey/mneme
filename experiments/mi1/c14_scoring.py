"""Strictly score the frozen C14 atomic-recall calibration."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def _normalized(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.lower()).split())


def score_c14(plan_path: Path, evidence_root: Path) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    index = json.loads((evidence_root / "index.json").read_text(encoding="utf-8"))
    expected = {row["coordinate_id"]: row for row in plan["coordinates"]}
    if len(expected) != plan["call_count"]:
        raise ValueError("C14 plan has duplicate or missing coordinate IDs")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    missing: list[str] = []
    for attempt in index["attempts"]:
        coordinate_id = attempt["attempt_id"]
        if coordinate_id not in expected:
            raise ValueError(f"unexpected C14 attempt: {coordinate_id}")
        if coordinate_id in seen:
            raise ValueError(f"duplicate C14 attempt: {coordinate_id}")
        seen.add(coordinate_id)
        if attempt["status"] != "COMPLETE":
            missing.append(coordinate_id)
            continue
        outcome = json.loads((evidence_root / "attempts" / attempt["outcome_file"]).read_text(encoding="utf-8"))
        if outcome.get("attempt_id") != coordinate_id or outcome.get("status") != "COMPLETE":
            raise ValueError(f"invalid C14 completion envelope: {coordinate_id}")
        choices = outcome.get("payload", {}).get("choices", [])
        if len(choices) != 1:
            raise ValueError(f"C14 result must have exactly one choice: {coordinate_id}")
        choice = choices[0]
        message = choice.get("message", {})
        source = expected[coordinate_id]
        answer = str(message.get("content") or "").strip()
        reasoning = str(message.get("reasoning_content") or "")
        wanted = str(source["expected"]["answer"])
        bank_source = str(source.get("bank_source") or "")
        fact = _normalized(bank_source)
        normalized_reasoning = _normalized(reasoning)
        records.append(
            {
                "coordinate_id": coordinate_id,
                "fixture_id": source["fixture_id"],
                "item": source["item"],
                "seed": source["seed"],
                "condition": source["condition"],
                "selector": source["bank_config"]["selector"],
                "expected": wanted,
                "answer": answer,
                "exact_label_hit": _normalized(answer) == _normalized(wanted),
                "finish_reason": choice.get("finish_reason"),
                "reasoning_bytes": len(reasoning.encode("utf-8")),
                "final_bytes": len(answer.encode("utf-8")),
                "bank_sentence_in_reasoning": bool(fact) and fact in normalized_reasoning,
                "request_sha256": attempt["request_sha256"],
                "outcome_sha256": attempt["outcome_sha256"],
            }
        )
    missing.extend(sorted(set(expected) - seen))
    if len(records) + len(missing) != len(expected):
        raise ValueError("C14 evidence does not reconcile to the frozen coordinate count")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["condition"]].append(record)
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
            "reasoning_mentions_of_exact_bank_sentence": sum(
                row["bank_sentence_in_reasoning"] for row in values
            ),
        }

    def hits(condition: str) -> int:
        return int(rates.get(condition, {}).get("exact_label_hits", 0))

    criteria = plan["criteria"]
    gates: dict[str, bool] = {}
    for gain in (2, 4):
        gain_word = "two" if gain == 2 else "four"
        gates[str(gain)] = (
            hits(f"latent_A_selected_{gain_word}fold") >= criteria["latent_each_polarity_minimum"]
            and hits(f"latent_B_selected_{gain_word}fold") >= criteria["latent_each_polarity_minimum"]
            and hits("visible_A") >= criteria["visible_each_polarity_minimum"]
            and hits("visible_B") >= criteria["visible_each_polarity_minimum"]
            and hits("no_bank") >= criteria["unknown_control_minimum"]
            and hits("cue_no_bank_assertive") >= criteria["unknown_control_minimum"]
        )
    passing = [gain for gain in (2, 4) if gates[str(gain)]]
    chosen = passing[0] if passing else None
    return {
        "schema_version": 1,
        "experiment": plan["experiment"],
        "scheduled_coordinates": len(expected),
        "complete_coordinates": len(records),
        "missing_or_uncertain_coordinates": sorted(missing),
        "condition_rates": rates,
        "gain_gate_results": gates,
        "passing_gains_in_low_to_high_order": passing,
        "selected_confirmation_gain": chosen,
        "calibration_gate_passed": chosen is not None,
        "heldout_confirmation_authorized_by_gate": chosen is not None,
        "coordinates": records,
    }
