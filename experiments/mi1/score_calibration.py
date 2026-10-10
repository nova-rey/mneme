"""Score frozen MI1 calibration outputs and select a pre-scored configuration."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

_CANDIDATES = (
    "latent_sparse_low",
    "latent_sparse_moderate",
    "latent_sparse_strong",
    "latent_broad_moderate",
)


def _answer_text(outcome: dict[str, Any]) -> str | None:
    if outcome.get("status") != "COMPLETE":
        return None
    choices = outcome.get("payload", {}).get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content")
    return content if isinstance(content, str) else None


def _ordered_labels(text: str, labels: list[str]) -> bool:
    folded = text.casefold()
    cursor = 0
    for label in labels:
        match = re.search(rf"(?<!\w){re.escape(label.casefold())}(?!\w)", folded[cursor:])
        if match is None:
            return False
        cursor += match.end()
    return True


def _is_correct(text: str | None, coordinate: dict[str, Any]) -> bool:
    if text is None:
        return False
    expected = coordinate["expected"]
    answer = expected["answer"]
    # C2 asks for an explicit two-line answer. Score that frozen schema
    # directly instead of applying the legacy bare-label parser to its tags.
    if re.search(r"(?im)^\s*ANSWER\s*:", text):
        answer_match = re.search(r"(?im)^\s*ANSWER\s*:\s*(.*?)\s*$", text)
        path_match = re.search(r"(?im)^\s*PATH\s*:\s*(.*?)\s*$", text)
        if answer_match is None or path_match is None:
            return False
        reported_answer = answer_match.group(1).strip().strip("`*_\"'").casefold()
        reported_path = path_match.group(1).strip()
        if answer == "unknown":
            no_path = re.match(r"^\s*none(?:\b|$)", reported_path, re.I) is not None
            return reported_answer in {"unknown", "unknown.", "unknown!"} and no_path
        if reported_answer != answer.casefold():
            return False
        reported_labels = re.findall(r"\b[A-Z][a-z]+\b", reported_path)
        return reported_labels == expected["path"]
    if answer == "unknown":
        return re.match(r"^\s*(?:\*\*)?unknown(?:\*\*)?(?:\b|\s|[.!,:;])", text, re.I) is not None
    labels = expected["path"]
    first_line = text.splitlines()[0] if text.splitlines() else text
    begins_with_answer = re.match(
        rf"^\s*(?:\*\*)?{re.escape(answer)}(?:\*\*)?(?:\b|\s|[.!,:;])",
        first_line,
        re.I,
    )
    return bool(labels) and begins_with_answer is not None and _ordered_labels(text, labels)


def _message_signature(outcome: dict[str, Any]) -> tuple[str, str, str] | None:
    if outcome.get("status") != "COMPLETE":
        return None
    choices = outcome.get("payload", {}).get("choices", [])
    if not choices:
        return None
    choice = choices[0]
    message = choice.get("message", {})
    return (
        str(message.get("reasoning_content", message.get("reasoning", ""))),
        str(message.get("content", "")),
        str(choice.get("finish_reason", "")),
    )


def _primary_negative_controls(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the 12 primary no-bank/irrelevant controls, excluding replay rows."""
    return [
        row
        for row in rows
        if row["condition"] in {"no_bank", "latent_irrelevant_sparse_moderate"}
        and row.get("duplicate_of") is None
    ]


def _determinism_ids(plan: dict[str, Any]) -> dict[str, str]:
    """Read replay IDs from current plans or a correction amendment."""
    ids = plan.get("determinism_coordinate_ids")
    if ids is None:
        correction = plan.get("correction", {})
        ids = correction.get("determinism_coordinate_ids", {})
    return ids


def score_calibration(plan_path: Path, journal_root: Path) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    index = json.loads((journal_root / "index.json").read_text(encoding="utf-8"))
    indexed = {row["attempt_id"]: row for row in index["attempts"]}
    scored_rows: list[dict[str, Any]] = []
    coordinates = {row["coordinate_id"]: row for row in plan["coordinates"]}
    for coordinate_id, coordinate in coordinates.items():
        record = indexed.get(coordinate_id)
        if record is None or record.get("outcome_file") is None:
            outcome: dict[str, Any] = {"status": "MISSING", "payload": {}}
        else:
            outcome = json.loads(
                (journal_root / "attempts" / record["outcome_file"]).read_text(encoding="utf-8")
            )
        text = _answer_text(outcome)
        scored_rows.append(
            {
                "coordinate_id": coordinate_id,
                "task_id": coordinate["metadata"]["task_id"],
                "condition": coordinate["metadata"]["condition"],
                "server_role": coordinate["metadata"]["server_role"],
                "seed": coordinate["metadata"]["seed"],
                "duplicate_of": coordinate["metadata"].get("duplicate_of"),
                "status": outcome.get("status"),
                "correct": _is_correct(text, coordinate),
                "answer": text,
            }
        )

    def rows_for(condition: str) -> list[dict[str, Any]]:
        return [row for row in scored_rows if row["condition"] == condition]

    visible = rows_for("visible_bank")
    negative = _primary_negative_controls(scored_rows)
    gates = {
        "visible_correct": sum(row["correct"] for row in visible),
        "visible_total": len(visible),
        "negative_unknown_correct": sum(row["correct"] for row in negative),
        "negative_total": len(negative),
    }
    candidates: list[dict[str, Any]] = []
    for condition in _CANDIDATES:
        positive = rows_for(condition)
        bank_config = next(
            row["bank_config"]
            for row in plan["coordinates"]
            if row["metadata"]["condition"] == condition
        )
        gains = [
            row["bank_config"]["gain"]["logit_bias"]
            for row in plan["coordinates"]
            if row["metadata"]["condition"] == condition
        ]
        bias = gains[0]
        site_count = 16 if bank_config["selector"] == "sparse" else 336
        false_positives = sum(not row["correct"] for row in negative)
        positive_correct = sum(row["correct"] for row in positive)
        passes = (
            gates["visible_correct"] >= 5
            and gates["negative_unknown_correct"] >= 11
            and positive_correct >= 5
            and false_positives <= 1
        )
        candidates.append(
            {
                "condition": condition,
                "positive_correct": positive_correct,
                "positive_total": len(positive),
                "negative_false_positive_count": false_positives,
                "negative_total": len(negative),
                "site_count": site_count,
                "logit_bias": bias,
                "exposure_index": site_count * math.exp(bias),
                "passes": passes,
            }
        )

    # Mechanical correction plans keep their new replay IDs under the explicit
    # correction object so the original frozen plan remains unchanged.
    deterministic_ids = _determinism_ids(plan)
    dup_id = deterministic_ids.get(
        "same_server_replay", "CAL-REL-01-no_bank-34111-duplicate"
    )
    base_id = deterministic_ids.get(
        "base_server_replay", "CAL-REL-01-no_bank-34111-base-server"
    )
    original_id = deterministic_ids.get("primary_no_bank", "CAL-REL-01-no_bank-34111")
    signatures = {
        key: _message_signature(
            json.loads(
                (journal_root / "attempts" / indexed[key]["outcome_file"]).read_text(
                    encoding="utf-8"
                )
            )
        )
        if key in indexed and indexed[key].get("outcome_file")
        else None
        for key in (original_id, dup_id, base_id)
    }
    duplicate_checks = {
        "base_server_coordinate_id": base_id,
        "mi1_replay_byte_identical": signatures[original_id] is not None
        and signatures[original_id] == signatures[dup_id],
        "base_server_byte_identical": signatures[original_id] is not None
        and signatures[original_id] == signatures[base_id],
        "signatures": signatures,
    }
    eligible = [row for row in candidates if row["passes"]]
    selected = None
    if eligible:
        selected = min(
            eligible,
            key=lambda row: (
                row["exposure_index"],
                row["site_count"],
                row["logit_bias"],
                _CANDIDATES.index(row["condition"]),
            ),
        )["condition"]
    deterministic = all(
        duplicate_checks[key]
        for key in ("mi1_replay_byte_identical", "base_server_byte_identical")
    )
    gates["determinism_pass"] = deterministic
    gates["calibration_pass"] = (
        selected is not None
        and gates["visible_correct"] >= 5
        and gates["negative_unknown_correct"] >= 11
        and deterministic
    )
    return {
        "schema_version": 1,
        "plan": str(plan_path),
        "journal": str(journal_root),
        "gates": gates,
        "candidates": candidates,
        "selected_condition": selected if gates["calibration_pass"] else None,
        "duplicate_checks": duplicate_checks,
        "rows": scored_rows,
        "prior_mechanical_failures": plan.get("prior_mechanical_failures", []),
        "note": (
            "No automatic retries. Missing or failed attempts score incorrect and remain counted."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("journal", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = score_calibration(args.plan, args.journal)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"calibration_pass={result['gates']['calibration_pass']} "
        f"selected={result['selected_condition']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
