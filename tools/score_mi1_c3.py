#!/usr/bin/env python3
"""Score frozen C3 task answers from its verified evidence journal."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write


def _normal(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _has_full_path(final: str, path: list[str]) -> bool:
    normalized_final = final.replace(r"$\rightarrow$", "->").replace(r"\rightarrow", "->")
    separator = r"(?:\s*(?:->|→|⟶|—|–|,|;|/)\s*|\s+)"
    pattern = separator.join(re.escape(label) for label in path)
    return re.search(rf"(?<!\w){pattern}(?!\w)", normalized_final, flags=re.IGNORECASE) is not None


def _score(final: str, expected: dict[str, Any]) -> dict[str, Any]:
    normalized = _normal(final)
    target = expected["answer"]
    if target == "unknown":
        unknown = any(
            marker in normalized
            for marker in (
                "unknown",
                "cannot determine",
                "not enough information",
                "no rules were provided",
                "no rule was provided",
                "not specified",
            )
        )
        return {"answer_correct": unknown, "path_correct": None, "correct": unknown}
    target_found = (
        re.search(rf"(?<!\w){re.escape(target.casefold())}(?!\w)", normalized) is not None
    )
    yes = re.search(r"\byes\b", normalized) is not None
    path_found = _has_full_path(final, expected["path"])
    return {
        "answer_correct": target_found and yes,
        "path_correct": path_found,
        "correct": target_found and yes and path_found,
    }


def _response_fields(payload: dict[str, Any]) -> tuple[str, str, str | None]:
    """Extract visible/reasoning text from the journal's raw completion envelope."""
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return "", "", None
    choice = choices[0]
    message = choice.get("message", {})
    if not isinstance(message, dict):
        return "", "", None
    final = message.get("content", "")
    reasoning = message.get("reasoning_content") or message.get("reasoning", "")
    finish_reason = choice.get("finish_reason")
    return (
        final if isinstance(final, str) else "",
        reasoning if isinstance(reasoning, str) else "",
        finish_reason if isinstance(finish_reason, str) else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    journal = EvidenceJournal(args.evidence_root, hard_call_limit=None)
    journal.verify()
    index = json.loads((args.evidence_root / "index.json").read_text(encoding="utf-8"))
    by_id: dict[str, tuple[dict[str, Any], dict[str, Any] | None]] = {}
    for row in index["attempts"]:
        request = json.loads((args.evidence_root / "attempts" / row["request_file"]).read_text())
        outcome = (
            json.loads((args.evidence_root / "attempts" / row["outcome_file"]).read_text())
            if row["outcome_file"]
            else None
        )
        by_id[row["attempt_id"]] = (request, outcome)

    coordinates: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "n": 0})
    pairs: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for expected in plan["coordinates"]:
        coordinate_id = expected["coordinate_id"]
        item = by_id.get(coordinate_id)
        if item is None:
            row = {
                "coordinate_id": coordinate_id,
                "condition": expected["metadata"]["condition"],
                "fixture_id": expected["metadata"]["fixture_id"],
                "seed": expected["metadata"]["seed"],
                "status": "NOT_RUN",
                "correct": False,
                "answer_correct": False,
                "path_correct": False,
            }
            coordinates.append(row)
            summaries[row["condition"]]["n"] += 1
            pairs[(row["fixture_id"], row["seed"])][row["condition"]] = row
            continue
        request, outcome = item
        status = outcome.get("status", "MISSING_OUTCOME") if outcome else "MISSING_OUTCOME"
        payload = outcome.get("payload", {}) if outcome and status == "COMPLETE" else {}
        final, reasoning, finish_reason = _response_fields(payload)
        result = (
            _score(final, expected["expected"])
            if status == "COMPLETE"
            else {"answer_correct": False, "path_correct": False, "correct": False}
        )
        row = {
            "coordinate_id": coordinate_id,
            "fixture_id": expected["metadata"]["fixture_id"],
            "condition": expected["metadata"]["condition"],
            "seed": expected["metadata"]["seed"],
            "status": status,
            "finish_reason": finish_reason,
            **result,
            "final": final,
            "reasoning": reasoning,
            "request_sha256": request.get("request", {}).get("request_sha256"),
            "loaded_bank_fingerprint": (
                request.get("metadata", {})
                .get("bank_state", {})
                .get("response", {})
                .get("bank_fingerprint")
            ),
        }
        coordinates.append(row)
        condition = row["condition"]
        summaries[condition]["n"] += 1
        summaries[condition]["correct"] += int(bool(row["correct"]))
        pairs[(row["fixture_id"], row["seed"])][condition] = row

    counterfactual = []
    for (fixture_id, seed), pair in sorted(pairs.items()):
        for latent in ("latent_sparse_moderate", "latent_broad_moderate", "latent_broad_strong"):
            row = pair.get(latent)
            if row is None:
                continue
            counterfactual.append(
                {
                    "fixture_id": fixture_id,
                    "seed": seed,
                    "condition": latent,
                    "visible_correct": bool(pair.get("visible", {}).get("correct")),
                    "baseline_unknown": bool(pair.get("no_bank", {}).get("correct")),
                    "latent_correct": bool(row.get("correct")),
                    "visible_and_latent_match_expected": bool(
                        pair.get("visible", {}).get("correct") and row.get("correct")
                    ),
                }
            )
    summary = {
        "schema_version": 1,
        "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
        "journal_status_counts": journal.verify(),
        "scheduled_coordinates": len(plan["coordinates"]),
        "coordinate_rows": len(coordinates),
        "condition_accuracy": {
            condition: {
                **values,
                "rate": values["correct"] / values["n"] if values["n"] else None,
            }
            for condition, values in sorted(summaries.items())
        },
        "paired_latent_results": counterfactual,
        "coordinates": coordinates,
    }
    atomic_json_write(args.output, summary)
    print(
        json.dumps(
            {"output": str(args.output), "condition_accuracy": summary["condition_accuracy"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
