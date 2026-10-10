"""Deterministic scoring for MI1's fictional counterfactual rule suite."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.mi1.native.evidence import EvidenceJournal

_ANSWER_PREFIX = re.compile(
    r"^\s*(?:\*\*)?(?:answer\s*:\s*|answer\s+is\s+|the answer is\s+)?",
    re.IGNORECASE,
)


def _choice_at_start(text: str, choices: list[str]) -> str | None:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    candidate = _ANSWER_PREFIX.sub("", first_line, count=1).lstrip(" -*#`:")
    for choice in sorted(choices, key=len, reverse=True):
        if re.match(rf"(?i)^{re.escape(choice)}(?:\b|\s|[.,:;—-])", candidate):
            return choice
    return None


def _ordered_path(text: str, path: list[str]) -> bool:
    offset = 0
    for label in path:
        match = re.search(rf"(?i)\b{re.escape(label)}\b", text[offset:])
        if match is None:
            return False
        offset += match.end()
    return True


def load_journal_rows(root: Path, *, hard_call_limit: int = 800) -> list[dict[str, Any]]:
    """Read only hash-verified journal rows; never infer a missing outcome."""
    journal = EvidenceJournal(root, hard_call_limit=hard_call_limit)
    journal.verify()
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in index["attempts"]:
        request_envelope = json.loads(
            (root / "attempts" / item["request_file"]).read_text(encoding="utf-8")
        )
        outcome = None
        if item["outcome_file"] is not None:
            outcome = json.loads(
                (root / "attempts" / item["outcome_file"]).read_text(encoding="utf-8")
            )
        rows.append(
            {"attempt_id": item["attempt_id"], "request": request_envelope, "outcome": outcome}
        )
    return rows


def score_test_a(suite: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Score every scheduled A coordinate, counting missing/failed calls as wrong."""
    expected_coordinates: dict[str, dict[str, Any]] = {}
    for fixture in suite["test_a"]["fixtures"]:
        choices = fixture["nodes"]
        for condition, expected in fixture["expected_by_condition"].items():
            for seed in suite["test_a"]["seeds"]:
                key = f"A:{fixture['fixture_id']}:{condition}:{seed}"
                expected_coordinates[key] = {
                    "fixture_id": fixture["fixture_id"],
                    "condition": condition,
                    "seed": seed,
                    "choices": choices,
                    "expected": expected,
                    "path": fixture["checks"]["bank_A_path"]
                    if expected == fixture["bank_A"]["expected_answer"]
                    else fixture["checks"]["bank_B_path"]
                    if expected == fixture["bank_B"]["expected_answer"]
                    else [],
                }

    observed: dict[str, dict[str, Any]] = {}
    unexpected: list[str] = []
    for row in rows:
        metadata = row["request"].get("metadata", {})
        if metadata.get("suite") != "test_a":
            continue
        fixture_id = metadata.get("fixture_id")
        condition = metadata.get("condition")
        seed = metadata.get("seed")
        key = f"A:{fixture_id}:{condition}:{seed}"
        if key not in expected_coordinates or key in observed:
            unexpected.append(row["attempt_id"])
            continue
        coordinate = expected_coordinates[key]
        outcome = row["outcome"]
        status = outcome.get("status") if outcome else "MISSING_OUTCOME"
        payload = outcome.get("payload", {}) if outcome else {}
        final = payload.get("final", "") if status == "COMPLETE" else ""
        parsed = _choice_at_start(final, coordinate["choices"] + ["unknown"])
        path_ok = _ordered_path(final, coordinate["path"]) if coordinate["path"] else None
        expected = coordinate["expected"]
        observed[key] = {
            **coordinate,
            "attempt_id": row["attempt_id"],
            "status": status,
            "finish_reason": payload.get("finish_reason"),
            "parsed_answer": parsed,
            "answer_correct": parsed is not None and parsed.casefold() == expected.casefold(),
            "path_required": bool(coordinate["path"]),
            "path_supported": path_ok if coordinate["path"] else None,
            "correct": parsed is not None
            and parsed.casefold() == expected.casefold()
            and (not coordinate["path"] or path_ok),
        }

    scored = []
    for key, coordinate in expected_coordinates.items():
        scored.append(
            observed.get(
                key,
                {
                    **coordinate,
                    "coordinate_id": key,
                    "status": "NOT_RUN",
                    "correct": False,
                    "answer_correct": False,
                    "path_supported": None,
                },
            )
        )
    correct_by_condition: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "n": 0})
    pairs: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in scored:
        condition = result["condition"]
        correct_by_condition[condition]["n"] += 1
        correct_by_condition[condition]["correct"] += int(result["correct"])
        pairs[(result["fixture_id"], result["seed"])][condition] = result
    switch_rows = []
    for (fixture_id, seed), pair in sorted(pairs.items()):
        a = pair.get("latent_A", {})
        b = pair.get("latent_B", {})
        expected_switch = a.get("expected") != b.get("expected")
        observed_switch = (
            a.get("parsed_answer") is not None
            and b.get("parsed_answer") is not None
            and a.get("parsed_answer", "").casefold() != b.get("parsed_answer", "").casefold()
        )
        switch_rows.append(
            {
                "fixture_id": fixture_id,
                "seed": seed,
                "expected_switch": expected_switch,
                "observed_switch": observed_switch,
                "both_correct": bool(a.get("correct") and b.get("correct")),
            }
        )
    rates = {
        condition: {
            "correct": values["correct"],
            "n": values["n"],
            "rate": values["correct"] / values["n"] if values["n"] else None,
        }
        for condition, values in sorted(correct_by_condition.items())
    }
    return {
        "scheduled_coordinates": len(expected_coordinates),
        "observed_coordinates": len(observed),
        "missing_coordinates": len(expected_coordinates) - len(observed),
        "unexpected_or_duplicate_attempt_ids": unexpected,
        "condition_accuracy": rates,
        "latent_counterfactual": {
            "n": len(switch_rows),
            "observed_switches": sum(row["observed_switch"] for row in switch_rows),
            "both_correct_switches": sum(row["both_correct"] for row in switch_rows),
            "fixture_seed_results": switch_rows,
        },
        "coordinates": scored,
    }
