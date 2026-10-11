from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from experiments.mi1.c11_recovery import build_recovery_plan, recovery_coordinates


def fixture_inputs(
    tmp_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    coordinates = [
        {
            "coordinate_id": f"C11-{index:03d}",
            "request": {"messages": [{"role": "user", "content": str(index)}]},
            "metadata": {"condition": "no_bank"},
        }
        for index in range(144)
    ]
    attempts = []
    attempts_root = tmp_path / "attempts"
    attempts_root.mkdir()
    for index, coordinate in enumerate(coordinates[:25]):
        attempt_id = coordinate["coordinate_id"]
        request = {
            "attempt_id": attempt_id,
            "metadata": {"coordinate": coordinate, "stream_file": f"{attempt_id}.stream.jsonl"},
            "request": coordinate["request"],
        }
        request_path = attempts_root / f"{attempt_id}.request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        attempts.append(
            {
                "attempt_id": attempt_id,
                "status": "REQUEST_DURABLE" if index == 24 else "COMPLETE",
                "request_file": request_path.name,
                "request_sha256": hashlib.sha256(request_path.read_bytes()).hexdigest(),
            }
        )
    lost_id = coordinates[24]["coordinate_id"]
    (attempts_root / f"{lost_id}.stream.jsonl").write_bytes(b"")
    plan = {"coordinates": coordinates}
    evidence = {"hard_call_limit": 144, "attempts": attempts}
    budget = {
        "hard_limit": 800,
        "reservations": [{"attempt_id": row["attempt_id"]} for row in attempts],
    }
    server = {
        "completion_logged": True,
        "task_id": 42,
        "completed_tokens": 50,
        "truncated": False,
        "log_excerpt_sha256": "a" * 64,
    }
    return plan, evidence, budget, server, tmp_path


def test_c11_recovery_freezes_only_lost_replay_and_unattempted_rows(tmp_path: Path) -> None:
    plan, evidence, budget, server, root = fixture_inputs(tmp_path)
    receipt = build_recovery_plan(
        plan,
        frozen_plan_sha256="b" * 64,
        evidence_index=evidence,
        evidence_index_sha256="c" * 64,
        evidence_root=root,
        generation_budget=budget,
        server_completion=server,
    )
    assert receipt["count"] == 120
    assert receipt["coordinate_ids"][0] == "C11-024-retry01"
    untouched = [row["coordinate_id"] for row in plan["coordinates"][25:]]
    assert receipt["coordinate_ids"][1:] == untouched
    assert receipt["accounting"]["projected_campaign_total"] == 792
    rows = recovery_coordinates(plan, receipt)
    assert rows[0]["coordinate_id"] == "C11-024-retry01"
    assert rows[0]["request"] == plan["coordinates"][24]["request"]
    assert rows[0]["metadata"]["recovery_parent_attempt"] == "C11-024"
    assert rows[1:] == plan["coordinates"][25:]


def test_c11_recovery_rejects_nonempty_lost_stream(tmp_path: Path) -> None:
    plan, evidence, budget, server, root = fixture_inputs(tmp_path)
    (root / "attempts" / "C11-024.stream.jsonl").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ValueError, match="empty persisted stream"):
        build_recovery_plan(
            plan,
            frozen_plan_sha256="b" * 64,
            evidence_index=evidence,
            evidence_index_sha256="c" * 64,
            evidence_root=root,
            generation_budget=budget,
            server_completion=server,
        )


def test_c11_recovery_rejects_anything_but_one_final_gap(tmp_path: Path) -> None:
    plan, evidence, budget, server, root = fixture_inputs(tmp_path)
    evidence["attempts"][0]["status"] = "REQUEST_DURABLE"
    with pytest.raises(ValueError, match="sequential prefix|exactly one unresolved"):
        build_recovery_plan(
            plan,
            frozen_plan_sha256="b" * 64,
            evidence_index=evidence,
            evidence_index_sha256="c" * 64,
            evidence_root=root,
            generation_budget=budget,
            server_completion=server,
        )
