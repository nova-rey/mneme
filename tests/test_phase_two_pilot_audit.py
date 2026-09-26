from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from mneme.experiments.pilot_audit import audit_pilot_run


def _schedule() -> Any:
    return SimpleNamespace(
        subject_slots=(0,),
        episodes=(SimpleNamespace(ordinal=0),),
        probes=(SimpleNamespace(ordinal=0),),
        evaluation_repetitions=1,
    )


def test_durable_pilot_audit_requires_and_checks_published_evidence(tmp_path: Path) -> None:
    for category in ("development", "extraction", "assessment", "evaluation"):
        (tmp_path / category).mkdir()
    (tmp_path / "development" / "development-s0-e0.json").write_text("{}\n")
    (tmp_path / "extraction" / "extraction-s0-e0.json").write_text(
        json.dumps({"coordinate": {"subject": 0, "episode": 0}, "valid": True})
        + "\n"
    )
    (tmp_path / "assessment" / "assessment-s0-e0.json").write_text("{}\n")
    (tmp_path / "evaluation" / "evaluation-s0-p0-r0.json").write_text(
        json.dumps(
            {
                "developmental_state_before": ["instance", 0, "manifest"],
                "developmental_state_after": ["instance", 0, "manifest"],
                "developmental_state_digest_before": "digest",
                "developmental_state_digest_after": "digest",
            }
        )
        + "\n"
    )

    class _Artifacts:
        @staticmethod
        def verify_run(_path: Path) -> bool:
            return True

    calls = [
        {
            "call_id": "development-s0-e0",
            "role": "development-response",
            "status": "RETURNED",
            "actual_host_fingerprint": {"model_id": "fake"},
            "result": {},
        },
        {
            "call_id": "extraction-s0-e0",
            "role": "development-extraction",
            "status": "RETURNED",
            "actual_host_fingerprint": {"model_id": "fake"},
            "result": {},
        },
        {
            "call_id": "assessment-s0-e0",
            "role": "assessor",
            "status": "RETURNED",
            "actual_host_fingerprint": {"model_id": "fake"},
            "result": {},
        },
        {
            "call_id": "evaluation-s0-p0-r0",
            "role": "evaluation",
            "status": "RETURNED",
            "actual_host_fingerprint": {"model_id": "fake"},
            "result": {},
        },
    ]

    class _Pilot:
        run_path = tmp_path
        artifacts = _Artifacts()

        @staticmethod
        def status() -> dict[str, Any]:
            return {
                "status": "COMPLETE",
                "study_progress": {
                    "development_completed": 1,
                    "extractions_valid": 1,
                    "assessments_completed": 1,
                    "evaluations_completed": 1,
                    "accepted_development_ids": ["development-s0-e0"],
                    "completed_evaluations": ["evaluation-s0-p0-r0"],
                },
            }

        @staticmethod
        def reservations_report() -> dict[str, Any]:
            return {"calls": calls}

    audit = audit_pilot_run(
        _Pilot(),
        _schedule(),
        status="COMPLETE",
        development_completed=1,
        extractions_valid=1,
        assessments_completed=1,
        evaluations_completed=1,
    )

    assert audit.passed is True
    assert audit.status == "PASS"
    assert {check["name"] for check in audit.checks} >= {
        "durable-pilot-run",
        "assessment-reservations",
        "artifact-inventory",
        "evaluation-isolation-receipts",
    }
