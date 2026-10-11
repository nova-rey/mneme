"""Build an auditable continuation after an MI1 C11 response-capture loss."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_recovery_plan(
    frozen_plan: dict[str, Any],
    *,
    frozen_plan_sha256: str,
    evidence_index: dict[str, Any],
    evidence_index_sha256: str,
    evidence_root: Path,
    generation_budget: dict[str, Any],
    server_completion: dict[str, Any],
) -> dict[str, Any]:
    """Preserve prior calls and schedule only one explicit replay plus untouched IDs."""
    coordinates = frozen_plan.get("coordinates")
    attempts = evidence_index.get("attempts")
    if not isinstance(coordinates, list) or len(coordinates) != 144:
        raise ValueError("recovery requires the frozen 144-coordinate C11 plan")
    if not isinstance(attempts, list) or not attempts:
        raise ValueError("C11 evidence journal has no durable attempts")
    if evidence_index.get("hard_call_limit") != 144:
        raise ValueError("parent C11 evidence journal has a different call contract")
    coordinate_ids = [row["coordinate_id"] for row in coordinates]
    attempt_ids = [row["attempt_id"] for row in attempts]
    if attempt_ids != coordinate_ids[: len(attempt_ids)]:
        raise ValueError("parent attempts are not a sequential prefix of the frozen plan")
    completed = [row for row in attempts if row.get("status") == "COMPLETE"]
    unresolved = [row for row in attempts if row.get("status") != "COMPLETE"]
    if len(unresolved) != 1 or unresolved[0] is not attempts[-1]:
        raise ValueError("recovery requires exactly one unresolved final parent attempt")
    interrupted = unresolved[0]
    interrupted_id = interrupted["attempt_id"]
    request_path = evidence_root / "attempts" / interrupted["request_file"]
    request_bytes = request_path.read_bytes()
    if sha256(request_bytes) != interrupted["request_sha256"]:
        raise ValueError("interrupted request failed its journal digest")
    request = json.loads(request_bytes)
    coordinate = request.get("metadata", {}).get("coordinate", {})
    if coordinate.get("coordinate_id") != interrupted_id:
        raise ValueError("interrupted request and C11 coordinate identity differ")
    stream_path = evidence_root / "attempts" / f"{interrupted_id}.stream.jsonl"
    if not stream_path.exists() or stream_path.stat().st_size != 0:
        raise ValueError("automatic recovery is limited to an empty persisted stream")
    if (evidence_root / "attempts" / f"{interrupted_id}.complete.json").exists():
        raise ValueError("interrupted coordinate already has a complete result")
    if (evidence_root / "attempts" / f"{interrupted_id}.failed.json").exists():
        raise ValueError("interrupted coordinate already has a failed result")
    if len(generation_budget.get("reservations", [])) != len(attempts):
        raise ValueError("C11 generation-budget reservations do not reconcile with attempts")
    if not server_completion.get("completion_logged"):
        raise ValueError("server evidence must establish the interrupted request completed")

    retry_id = f"{interrupted_id}-retry01"
    pending_ids = [retry_id, *coordinate_ids[len(attempts) :]]
    if len(pending_ids) != 120 or len(set(pending_ids)) != len(pending_ids):
        raise ValueError("recovery must contain one explicit replay plus 119 untouched calls")
    return {
        "schema_version": 1,
        "experiment": "MNEME Phase 4 MI1 C11 evidence-loss recovery",
        "status": "FROZEN_BEFORE_RECOVERY_GENERATION",
        "created_date": "2026-10-11",
        "parent_execution_plan_sha256": frozen_plan_sha256,
        "parent_evidence_index_sha256": evidence_index_sha256,
        "parent_attempt_count": len(attempts),
        "parent_complete_count": len(completed),
        "interruption": {
            "attempt_id": interrupted_id,
            "request_sha256": interrupted["request_sha256"],
            "empty_stream_sha256": sha256(stream_path.read_bytes()),
            "empty_stream_bytes": stream_path.stat().st_size,
            "status": interrupted["status"],
            "server_task_id": server_completion.get("task_id"),
            "server_completed_tokens": server_completion.get("completed_tokens"),
            "server_truncated": server_completion.get("truncated"),
            "server_completion_evidence_sha256": server_completion.get("log_excerpt_sha256"),
            "interpretation": (
                "The dedicated llama-server log reports completion for the 25th serialized "
                "request, but the client stream file is empty and no response artifact exists. "
                "The answer is unrecoverable and excluded; it is not reconstructed from logs."
            ),
        },
        "replay": {
            "coordinate_id": interrupted_id,
            "new_attempt_id": retry_id,
            "reason": (
                "recover the frozen coordinate whose completed response was not durably captured"
            ),
            "prompt_seed_sampler_bank_and_expected_result": (
                "identical to the parent frozen coordinate"
            ),
            "original_attempt_preserved_and_scored": False,
        },
        "unattempted_coordinate_ids": coordinate_ids[len(attempts) :],
        "coordinate_ids": pending_ids,
        "count": len(pending_ids),
        "accounting": {
            "prior_call_total": 647,
            "parent_attempts_charged": len(attempts),
            "recovery_calls": len(pending_ids),
            "projected_campaign_total": 647 + len(attempts) + len(pending_ids),
            "hard_ceiling": generation_budget.get("hard_limit"),
        },
        "server_completion_evidence": server_completion,
    }


def recovery_coordinates(
    frozen_plan: dict[str, Any], recovery_plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return frozen coordinates plus one explicitly named retry without prompt changes."""
    by_id = {row["coordinate_id"]: row for row in frozen_plan.get("coordinates", [])}
    if len(by_id) != 144:
        raise ValueError("recovery requires exactly 144 source coordinates")
    retry = recovery_plan.get("replay", {})
    original_id = retry.get("coordinate_id")
    retry_id = retry.get("new_attempt_id")
    if original_id not in by_id or not isinstance(retry_id, str):
        raise ValueError("recovery replay does not identify a frozen source coordinate")
    expected_ids = [retry_id, *recovery_plan.get("unattempted_coordinate_ids", [])]
    if expected_ids != recovery_plan.get("coordinate_ids") or len(expected_ids) != 120:
        raise ValueError("recovery coordinate list does not match its frozen accounting")
    import copy

    replay_coordinate = copy.deepcopy(by_id[original_id])
    replay_coordinate["coordinate_id"] = retry_id
    replay_coordinate.setdefault("metadata", {})["recovery_parent_attempt"] = original_id
    by_id[retry_id] = replay_coordinate
    try:
        return [by_id[coordinate_id] for coordinate_id in expected_ids]
    except KeyError as exc:
        raise ValueError(f"recovery references an unknown frozen coordinate: {exc}") from exc
