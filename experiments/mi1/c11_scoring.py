"""Score C11 held-out outputs without reconstructing missing responses."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.mi1.scoring import _final_response, load_journal_rows


def _parse_answer(text: str, labels: list[str]) -> str | None:
    normalized = text.replace("**", "")
    first_line = normalized.splitlines()[0] if normalized.splitlines() else ""
    if re.match(r"^\s*(?:\*\*)?(?:answer\s*:\s*)?unknown\b", first_line, re.I):
        return "unknown"
    ordered = sorted(labels, key=len, reverse=True)
    patterns = (
        (
            r"(?:\*{0,2})?(?:answer|label|active label|conclusion)"
            r"(?:\*{0,2})\s*(?:is\s+|:\s*)?\*{0,2}({label})\b"
        ),
        r"^\s*\*{0,2}({label})\*{0,2}(?:\b|\s|[.,:;—-])",
        r"\*{0,2}({label})\*{0,2}\s+can become active\b",
    )
    matches: list[tuple[int, int, str]] = []
    for label in ordered:
        for pattern_index, pattern in enumerate(patterns):
            match = re.search(
                pattern.replace("{label}", re.escape(label)),
                normalized,
                flags=re.IGNORECASE | re.MULTILINE,
            )
            if match is not None:
                matches.append((pattern_index, match.start(), label))
    if matches:
        return min(matches)[2]
    return None


def _path_supported(text: str, path: list[str]) -> bool:
    offset = 0
    for label in path:
        match = re.search(rf"\b{re.escape(label)}\b", text[offset:], re.I)
        if match is None:
            return False
        offset += match.end()
    return True


def score_c11(
    frozen_plan: dict[str, Any],
    design_plan: dict[str, Any],
    parent_root: Path,
    recovery_root: Path,
) -> dict[str, Any]:
    """Join 144 frozen coordinates to outputs from two immutable journals."""
    expected = {row["coordinate_id"]: row for row in frozen_plan["coordinates"]}
    if len(expected) != 144:
        raise ValueError("C11 scoring requires the frozen 144-coordinate matrix")
    outputs: dict[str, dict[str, Any]] = {}
    lost_parent_ids: list[str] = []
    for journal_root, journal_limit in ((parent_root, 144), (recovery_root, 120)):
        for row in load_journal_rows(journal_root, hard_call_limit=journal_limit):
            envelope = row["request"]
            metadata = envelope.get("metadata", {})
            coordinate = metadata.get("coordinate", {}) if isinstance(metadata, dict) else {}
            coordinate_metadata = coordinate.get("metadata", {})
            coordinate_id = coordinate.get("coordinate_id")
            if coordinate_id not in expected:
                parent_attempt = coordinate_metadata.get("recovery_parent_attempt")
                if parent_attempt not in expected:
                    if row["outcome"] is None:
                        lost_parent_ids.append(str(coordinate_id))
                        continue
                    raise ValueError(f"unexpected C11 attempt {row['attempt_id']}")
                coordinate_id = parent_attempt
            if row["outcome"] is None:
                lost_parent_ids.append(str(coordinate_id))
                continue
            if coordinate_id in outputs:
                raise ValueError(f"multiple complete outputs map to {coordinate_id}")
            outputs[coordinate_id] = row

    if set(outputs) != set(expected):
        missing = sorted(set(expected) - set(outputs))
        raise ValueError(f"C11 matrix lacks complete unique responses: {missing}")
    if len(lost_parent_ids) != 1:
        raise ValueError(
            f"expected exactly one preserved lost parent attempt, got {lost_parent_ids}"
        )

    scoring_coords = {row["coordinate_id"]: row for row in frozen_plan["coordinates"]}
    scored: list[dict[str, Any]] = []
    for coordinate_id, source in expected.items():
        row = outputs[coordinate_id]
        outcome = row["outcome"]
        final, finish_reason = _final_response(outcome)
        labels = sorted(
            {
                row["expected"]["answer"]
                for row in frozen_plan["coordinates"]
                if row["fixture_id"] == source["fixture_id"]
                and row["expected"]["answer"] != "unknown"
            }
        )
        answer = _parse_answer(final, labels)
        wanted = source["expected"]
        path_ok = _path_supported(final, wanted["path"]) if wanted["path"] else True
        condition = source["condition"]
        polarity = "A" if condition.endswith("_A") else "B" if condition.endswith("_B") else None
        scored.append(
            {
                "coordinate_id": coordinate_id,
                "fixture_id": source["fixture_id"],
                "seed": source["seed"],
                "condition": condition,
                "polarity": polarity,
                "selector": scoring_coords[coordinate_id]["metadata"]["selector"],
                "expected_answer": wanted["answer"],
                "parsed_answer": answer,
                "answer_correct": answer == wanted["answer"],
                "path_required": bool(wanted["path"]),
                "path_supported": path_ok if wanted["path"] else None,
                "correct": answer == wanted["answer"] and path_ok,
                "finish_reason": finish_reason,
                "final_bytes": len(final.encode("utf-8")),
                "attempt_id": row["attempt_id"],
            }
        )

    groups: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        groups[(row["condition"], row["polarity"])].append(row)
    rates = []
    for (condition, polarity), rows in sorted(groups.items()):
        hits = sum(bool(row["correct"]) for row in rows)
        rates.append(
            {
                "condition": condition,
                "polarity": polarity,
                "n": len(rows),
                "correct": hits,
                "rate": hits / len(rows),
            }
        )

    by_condition = {
        (row["condition"], row["polarity"]): row["rate"] for row in rates
    }
    thresholds = design_plan["criteria"]
    positive_rows = [row for row in rates if row["condition"].startswith("selected_")]
    visible_rows = [row for row in rates if row["condition"].startswith("visible_")]
    control_rows = [row for row in rates if row["condition"] == "no_bank"]
    selector_margins: dict[str, dict[str, float]] = {}
    for polarity in ("A", "B"):
        selected = by_condition[(f"selected_{polarity}", polarity)]
        selector_margins[polarity] = {
            control: selected - by_condition[(f"{control}_{polarity}", polarity)]
            for control in ("old_sparse", "random")
        }
    controls_adequate = all(row["rate"] >= 0.8 for row in visible_rows + control_rows)
    selected_adequate = all(row["rate"] >= 0.8 for row in positive_rows)
    margins_adequate = all(
        margin >= 0.2 for by_control in selector_margins.values() for margin in by_control.values()
    )
    return {
        "scheduled_coordinates": 144,
        "scored_coordinates": len(scored),
        "lost_parent_attempt_ids": lost_parent_ids,
        "condition_rates": rates,
        "selector_margins": selector_margins,
        "frozen_criteria": thresholds,
        "criteria_result": {
            "visible_and_no_bank_controls_at_least_80_percent": controls_adequate,
            "selected_A_and_B_at_least_80_percent": selected_adequate,
            "selected_exceeds_old_sparse_and_random_by_20pp_each_polarity": margins_adequate,
            "all_pass": controls_adequate and selected_adequate and margins_adequate,
        },
        "coordinates": scored,
    }
