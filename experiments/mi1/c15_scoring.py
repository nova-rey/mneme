"""Strict C15 scoring for atomic recall with alternate bank encodings."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


def _normalized(value: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", value.lower()).split())


def score_c15(
    plan_path: Path,
    evidence_root: Path,
    *,
    phase: str = "calibration",
    encoding: str | None = None,
) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if phase not in {"calibration", "confirmation"}:
        raise ValueError("phase must be calibration or confirmation")
    if phase == "calibration":
        expected_rows = plan["coordinates"]
    else:
        if encoding not in {"system_turn", "user_turn", "raw"}:
            raise ValueError("confirmation scoring requires the frozen selected encoding")
        allowed = {
            "no_bank",
            "visible_A",
            "visible_B",
            f"latent_{encoding}_A",
            f"latent_{encoding}_B",
        }
        expected_rows = plan["confirmation_coordinates_frozen_not_authorized_until_gate"]
        expected_rows = [row for row in expected_rows if row["condition"] in allowed]
    expected = {row["coordinate_id"]: row for row in expected_rows}
    index = json.loads((evidence_root / "index.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    missing: list[str] = []
    for attempt in index["attempts"]:
        coordinate_id = attempt["attempt_id"]
        if coordinate_id not in expected:
            continue
        if coordinate_id in seen:
            raise ValueError(f"duplicate C15 attempt: {coordinate_id}")
        seen.add(coordinate_id)
        if attempt["status"] != "COMPLETE":
            missing.append(coordinate_id)
            continue
        outcome = json.loads(
            (evidence_root / "attempts" / attempt["outcome_file"]).read_text(encoding="utf-8")
        )
        if outcome.get("attempt_id") != coordinate_id or outcome.get("status") != "COMPLETE":
            raise ValueError(f"invalid C15 completion envelope: {coordinate_id}")
        choices = outcome.get("payload", {}).get("choices", [])
        if len(choices) != 1:
            raise ValueError(f"C15 requires exactly one model choice: {coordinate_id}")
        choice = choices[0]
        message = choice.get("message", {})
        source = expected[coordinate_id]
        answer = str(message.get("content") or "").strip()
        reasoning = str(message.get("reasoning_content") or "")
        records.append(
            {
                "coordinate_id": coordinate_id,
                "fixture_id": source["fixture_id"],
                "item": source["item"],
                "condition": source["condition"],
                "encoding": source.get("bank_encoding"),
                "seed": source["seed"],
                "expected": source["expected"]["answer"],
                "answer": answer,
                "exact_label_hit": _normalized(answer) == _normalized(source["expected"]["answer"]),
                "finish_reason": choice.get("finish_reason"),
                "reasoning_bytes": len(reasoning.encode("utf-8")),
                "final_bytes": len(answer.encode("utf-8")),
                "reasoning_excerpt": reasoning[:500],
                "request_sha256": attempt["request_sha256"],
                "outcome_sha256": attempt["outcome_sha256"],
            }
        )
    missing.extend(sorted(set(expected) - seen))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        groups[row["condition"]].append(row)
    rates = {
        condition: {
            "n": len(rows),
            "hits": sum(row["exact_label_hit"] for row in rows),
            "rate": sum(row["exact_label_hit"] for row in rows) / len(rows),
        }
        for condition, rows in sorted(groups.items())
    }
    criteria = plan["criteria"]
    encodings = ("raw", "system_turn", "user_turn")
    gates = {}
    for encoding in encodings:
        gates[encoding] = (
            rates.get(f"latent_{encoding}_A", {}).get("hits", 0)
            >= criteria["latent_each_polarity_minimum"]
            and rates.get(f"latent_{encoding}_B", {}).get("hits", 0)
            >= criteria["latent_each_polarity_minimum"]
            and rates.get("visible_A", {}).get("hits", 0)
            >= criteria["visible_each_polarity_minimum"]
            and rates.get("visible_B", {}).get("hits", 0)
            >= criteria["visible_each_polarity_minimum"]
            and rates.get("no_bank", {}).get("hits", 0) >= criteria["unknown_control_minimum"]
            and rates.get("cue_no_bank_assertive", {}).get("hits", 0)
            >= criteria["unknown_control_minimum"]
        )
    order = ("system_turn", "user_turn", "raw")
    selected = next((encoding for encoding in order if gates[encoding]), None)
    return {
        "schema_version": 1,
        "experiment": plan["experiment"],
        "phase": phase,
        "scheduled_coordinates": len(expected),
        "complete_coordinates": len(records),
        "missing_or_uncertain_coordinates": sorted(missing),
        "condition_rates": rates,
        "encoding_gate_results": gates,
        "selected_encoding": selected if phase == "calibration" else encoding,
        "calibration_gate_passed": selected is not None if phase == "calibration" else None,
        "heldout_confirmation_authorized_by_gate": selected is not None
        if phase == "calibration"
        else None,
        "confirmation_passed": (
            rates.get(f"latent_{encoding}_A", {}).get("hits", 0)
            >= criteria["confirmation_latent_each_polarity_minimum"]
            and rates.get(f"latent_{encoding}_B", {}).get("hits", 0)
            >= criteria["confirmation_latent_each_polarity_minimum"]
            and rates.get("visible_A", {}).get("hits", 0)
            >= criteria["confirmation_visible_each_polarity_minimum"]
            and rates.get("visible_B", {}).get("hits", 0)
            >= criteria["confirmation_visible_each_polarity_minimum"]
            and rates.get("no_bank", {}).get("hits", 0)
            >= criteria["confirmation_unknown_control_minimum"]
        )
        if phase == "confirmation"
        else None,
        "coordinates": records,
    }
