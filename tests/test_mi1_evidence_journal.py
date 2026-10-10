from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.mi1.native.evidence import EvidenceJournal


def test_attempt_is_durable_before_inference_and_survives_reopen(tmp_path: Path) -> None:
    journal = EvidenceJournal(tmp_path, hard_call_limit=3)
    request = {"messages": [{"role": "user", "content": "exact prompt"}], "seed": 5}
    request_path = journal.begin("a01", request, {"condition": "latent"})
    assert json.loads(request_path.read_text(encoding="utf-8"))["request"] == request
    reopened = EvidenceJournal(tmp_path, hard_call_limit=3)
    assert reopened.verify() == {"REQUEST_DURABLE": 1}


def test_complete_and_failed_outcomes_are_immutable_and_counted(tmp_path: Path) -> None:
    journal = EvidenceJournal(tmp_path, hard_call_limit=2)
    journal.begin("a01", {"prompt": "p1"}, {})
    response_path = journal.complete("a01", {"reasoning": "think", "final": "answer"})
    assert json.loads(response_path.read_text(encoding="utf-8"))["payload"]["final"] == "answer"
    with pytest.raises(FileExistsError, match="outcome"):
        journal.complete("a01", {"final": "replacement"})
    journal.begin("a02", {"prompt": "p2"}, {})
    journal.fail("a02", {"exception": "timeout"})
    assert EvidenceJournal(tmp_path, hard_call_limit=2).verify() == {"COMPLETE": 1, "FAILED": 1}


def test_call_budget_and_attempt_identity_fail_closed(tmp_path: Path) -> None:
    journal = EvidenceJournal(tmp_path, hard_call_limit=1)
    journal.begin("only", {"prompt": "p"}, {})
    with pytest.raises(RuntimeError, match="limit reached"):
        journal.begin("second", {"prompt": "p2"}, {})
    with pytest.raises(FileExistsError, match="already exists"):
        journal.begin("only", {"prompt": "changed"}, {})


def test_hash_mismatch_and_unindexed_files_are_reported(tmp_path: Path) -> None:
    journal = EvidenceJournal(tmp_path, hard_call_limit=2)
    request_path = journal.begin("a01", {"prompt": "p"}, {})
    request_path.write_text('{"prompt":"tampered"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        journal.verify()


def test_reopen_recovers_request_committed_before_index_replace(tmp_path: Path) -> None:
    EvidenceJournal(tmp_path, hard_call_limit=2)
    request = {"attempt_id": "lost-index", "metadata": {}, "request": {"prompt": "exact"}}
    (tmp_path / "attempts" / "lost-index.request.json").write_text(
        json.dumps(request, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    reopened = EvidenceJournal(tmp_path, hard_call_limit=2)
    assert reopened.verify() == {"REQUEST_DURABLE": 1}
    with pytest.raises(FileExistsError, match="already exists"):
        reopened.begin("lost-index", {"prompt": "different"}, {})
    reopened.begin("second", {"prompt": "p2"}, {})


def test_reopen_recovers_result_committed_before_index_replace(tmp_path: Path) -> None:
    journal = EvidenceJournal(tmp_path, hard_call_limit=2)
    journal.begin("call-1", {"prompt": "exact"}, {})
    outcome = {
        "attempt_id": "call-1",
        "status": "COMPLETE",
        "metadata": {},
        "payload": {"answer": "ok"},
    }
    (tmp_path / "attempts" / "call-1.complete.json").write_text(
        json.dumps(outcome, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    reopened = EvidenceJournal(tmp_path, hard_call_limit=2)
    assert reopened.verify() == {"COMPLETE": 1}


def test_reopen_rejects_conflicting_unindexed_outcomes(tmp_path: Path) -> None:
    EvidenceJournal(tmp_path, hard_call_limit=2)
    request = {"attempt_id": "call-1", "metadata": {}, "request": {"prompt": "exact"}}
    attempt_dir = tmp_path / "attempts"
    (attempt_dir / "call-1.request.json").write_text(
        json.dumps(request, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    for status in ("COMPLETE", "FAILED"):
        (attempt_dir / f"call-1.{status.lower()}.json").write_text(
            json.dumps(
                {"attempt_id": "call-1", "status": status, "metadata": {}, "payload": {}},
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    with pytest.raises(ValueError, match="conflicting evidence set"):
        EvidenceJournal(tmp_path, hard_call_limit=2)
