#!/usr/bin/env python3
"""Freeze a fresh C15 calibration identity after the server multi-slot crash."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rename(rows: list[dict[str, Any]], phase: str) -> None:
    for row in rows:
        row["coordinate_id"] = row["coordinate_id"].replace("C15-", "C15B-", 1)
        row["metadata"]["suite"] = "c15b_single_slot_replication"
        row["metadata"]["revision"] = "C15B"
        row["metadata"]["phase"] = phase


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-plan", type=Path, required=True)
    parser.add_argument("--parent-execution", type=Path, required=True)
    parser.add_argument("--failed-receipt", type=Path, required=True)
    parser.add_argument("--crash-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent = json.loads(args.parent_plan.read_text(encoding="utf-8"))
    execution = json.loads(args.parent_execution.read_text(encoding="utf-8"))
    failure = json.loads(args.failed_receipt.read_text(encoding="utf-8"))
    if parent.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("parent plan is not frozen")
    if (
        failure.get("status") != "FAILED"
        or failure.get("metadata", {}).get("stream", {}).get("stream_event_count") != 0
    ):
        raise ValueError("C15B requires the preserved zero-event C15 failed attempt")
    if execution.get("generation_issued") is not False:
        raise ValueError("C15 execution binding should remain pre-generation")
    plan = copy.deepcopy(parent)
    plan["experiment"] = "MNEME Phase 4 MI1 C15B single-slot bank-encoding calibration"
    plan["status"] = "FROZEN_BEFORE_CALIBRATION_GENERATION"
    plan["revision"] = "C15B"
    plan["parents"].update(
        {
            "c15_plan_sha256": _sha(args.parent_plan),
            "c15_execution_freeze_sha256": _sha(args.parent_execution),
            "failed_attempt_receipt_sha256": _sha(args.failed_receipt),
            "crash_log_sha256": _sha(args.crash_log),
        }
    )
    _rename(plan["coordinates"], "calibration")
    _rename(plan["confirmation_coordinates_frozen_not_authorized_until_gate"], "confirmation")
    plan["server_runtime"] = {
        "parallel_slots": 1,
        "reason": (
            "C15's first selected-bank request caused the pinned Gemma attention path to "
            "assert ubatch->n_seqs == 1 && n_seqs_unq == 1 with four server slots. The failed "
            "call yielded zero SSE events. C15B reruns all calibration coordinates with one "
            "slot; criteria, prompts, source strings, bank K/V, selector, gain, seeds, and "
            "sampler are unchanged."
        ),
        "only_server_command_delta": ["--parallel", "1"],
        "crash_site": "src/llama-graph.cpp:662 in llm_graph_input_attn_kv_iswa::set_input",
    }
    plan["prior_attempt_policy"] = {
        "C15_completed_controls": 4,
        "C15_failed_coordinates": [failure["attempt_id"]],
        "reuse_prior_outputs": False,
        "reason": (
            "All conditions are rerun so controls and latent banks share the corrected "
            "single-slot runtime; C15 outputs remain historical and are excluded from C15B "
            "scoring."
        ),
    }
    plan["generation_issued"] = False
    plan["freeze_tool_sha256"] = _sha(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": _sha(args.output),
                "calibration_calls": plan["call_count"],
                "confirmation_max": plan["confirmation_call_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
