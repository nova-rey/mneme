"""Evidence audit for a completed Phase Two pilot.

The pilot counters describe what the scheduler says it did.  They are useful
progress information, but they are not sufficient engineering evidence by
themselves.  This module performs a small, filesystem-oriented audit against
the durable :class:`PilotRun` ledger and its published inventory.  It does not
inspect or alter developmental state and it does not make provider calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pilot import CallStatus


@dataclass(frozen=True)
class EngineeringAudit:
    """Structured result of the P2.3 engineering-evidence audit."""

    status: str
    checks: tuple[dict[str, Any], ...]

    @property
    def passed(self) -> bool:
        return self.status == "PASS" and all(bool(check.get("passed")) for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.status,
            "passed": self.passed,
            "checks": [dict(check) for check in self.checks],
        }


def _check(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"name": name, "passed": passed, **details}


def _json_files(directory: Path) -> list[Path]:
    if not directory.is_dir() or directory.is_symlink():
        return []
    return sorted(
        candidate
        for candidate in directory.glob("*.json")
        if candidate.is_file() and not candidate.is_symlink()
    )


def _read_artifacts(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    result: list[tuple[Path, dict[str, Any]]] = []
    for path in _json_files(directory):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(value, dict):
            result.append((path, value))
    return result


def _int_field(value: Any, key: str) -> int | None:
    candidate = value.get(key) if isinstance(value, dict) else None
    if isinstance(candidate, bool) or not isinstance(candidate, int):
        return None
    return candidate


def audit_pilot_run(
    pilot: Any,
    schedule: Any,
    *,
    status: str,
    development_completed: int,
    extractions_valid: int,
    assessments_completed: int,
    evaluations_completed: int,
) -> EngineeringAudit:
    """Audit durable execution evidence for one pilot report.

    A test double or legacy caller without a real ``PilotRun`` is deliberately
    reported as ``UNAVAILABLE``.  Count-only reports therefore cannot satisfy
    ``engineering_adequate`` accidentally.
    """

    checks: list[dict[str, Any]] = []
    run_path = getattr(pilot, "run_path", None)
    reservations_reader = getattr(pilot, "reservations_report", None)
    status_reader = getattr(pilot, "status", None)
    if not isinstance(run_path, Path) or not callable(reservations_reader) or not callable(
        status_reader
    ):
        checks.append(
            _check(
                "durable-pilot-run",
                False,
                reason="PilotRun evidence is unavailable; counters alone are insufficient",
            )
        )
        return EngineeringAudit("UNAVAILABLE", tuple(checks))

    try:
        status_value = status_reader()
        reservation_report = reservations_reader()
        calls = list(reservation_report.get("calls", []))
        run_verified = bool(pilot.artifacts.verify_run(run_path))
    except Exception as exc:  # audit must report a structured failure
        checks.append(
            _check(
                "durable-pilot-run",
                False,
                reason=f"audit read failed: {type(exc).__name__}: {exc}",
            )
        )
        return EngineeringAudit("FAIL", tuple(checks))

    checks.append(
        _check(
            "durable-pilot-run",
            run_verified,
            reason=None if run_verified else "published run failed artifact/inventory verification",
        )
    )

    expected_development = {
        f"development-s{slot}-e{episode.ordinal}"
        for slot in schedule.subject_slots
        for episode in schedule.episodes
    }
    expected_assessment = {
        f"assessment-s{slot}-e{episode.ordinal}"
        for slot in schedule.subject_slots
        for episode in schedule.episodes
    }
    expected_evaluation = {
        f"evaluation-s{slot}-p{probe.ordinal}-r{repetition}"
        for slot in schedule.subject_slots
        for probe in schedule.probes
        for repetition in range(schedule.evaluation_repetitions)
    }

    returned = [item for item in calls if item.get("status") == CallStatus.RETURNED.value]
    pending = [
        item
        for item in calls
        if item.get("status") in {
            CallStatus.RESERVED.value,
            CallStatus.DISPATCHED.value,
            CallStatus.UNCERTAIN.value,
        }
    ]
    checks.append(
        _check(
            "terminal-reservations",
            not pending and all(item.get("status") == CallStatus.RETURNED.value for item in calls),
            pending_call_ids=[str(item.get("call_id")) for item in pending],
            non_returned_call_ids=[
                str(item.get("call_id"))
                for item in calls
                if item.get("status") != CallStatus.RETURNED.value
            ],
        )
    )
    call_ids = [str(item.get("call_id")) for item in calls]
    checks.append(
        _check(
            "unique-reservations",
            len(call_ids) == len(set(call_ids)) and all(call_id != "None" for call_id in call_ids),
            reservation_count=len(call_ids),
            unique_count=len(set(call_ids)),
        )
    )

    by_role: dict[str, list[dict[str, Any]]] = {}
    for item in calls:
        by_role.setdefault(str(item.get("role")), []).append(item)
    development_ids = {str(item.get("call_id")) for item in by_role.get("development-response", [])}
    extraction_ids = {
        str(item.get("call_id")) for item in by_role.get("development-extraction", [])
    }
    assessment_ids = {str(item.get("call_id")) for item in by_role.get("assessor", [])}
    evaluation_ids = {str(item.get("call_id")) for item in by_role.get("evaluation", [])}
    checks.append(
        _check(
            "development-coordinates",
            expected_development <= development_ids
            and all(item in development_ids for item in expected_development),
            expected=len(expected_development),
            observed=len(expected_development & development_ids),
        )
    )
    checks.append(
        _check(
            "extraction-coordinates",
            len(extraction_ids) >= extractions_valid,
            expected_valid=extractions_valid,
            observed=len(extraction_ids),
        )
    )
    checks.append(
        _check(
            "evaluation-coordinates",
            expected_evaluation <= evaluation_ids,
            expected=len(expected_evaluation),
            observed=len(expected_evaluation & evaluation_ids),
        )
    )

    host_complete = all(
        isinstance(item.get("actual_host_fingerprint"), dict)
        for item in returned
    )
    checks.append(_check("host-provenance", host_complete, returned=len(returned)))

    progress = status_value.get("study_progress") if isinstance(status_value, dict) else None
    progress_ok = (
        isinstance(progress, dict)
        and _int_field(progress, "development_completed") == development_completed
        and _int_field(progress, "extractions_valid") == extractions_valid
        and _int_field(progress, "assessments_completed") == assessments_completed
        and _int_field(progress, "evaluations_completed") == evaluations_completed
        and isinstance(progress.get("accepted_development_ids"), list)
        and len(progress["accepted_development_ids"]) == development_completed
        and isinstance(progress.get("completed_evaluations"), list)
        and len(progress["completed_evaluations"]) == evaluations_completed
    )
    checks.append(_check("study-progress-ledger", progress_ok))

    development_artifacts = {path.stem for path, _ in _read_artifacts(run_path / "development")}
    extraction_artifacts = _read_artifacts(run_path / "extraction")
    assessment_artifacts = {path.stem for path, _ in _read_artifacts(run_path / "assessment")}
    evaluation_artifacts = {path.stem for path, _ in _read_artifacts(run_path / "evaluation")}
    assessment_coordinates = {
        stem.removesuffix("-excluded").removesuffix("-resolution")
        for stem in assessment_artifacts
    }
    assessment_excluded = {
        stem.removesuffix("-excluded")
        for stem in assessment_artifacts
        if stem.endswith("-excluded")
    }
    missing_assessment_evidence = sorted(
        expected_assessment - assessment_ids - assessment_excluded
    )
    assessment_call_failures = sorted(
        str(item.get("call_id"))
        for item in by_role.get("assessor", [])
        if item.get("call_id") in expected_assessment
        and item.get("status") != CallStatus.RETURNED.value
    )
    checks.append(
        _check(
            "assessment-reservations",
            not missing_assessment_evidence and not assessment_call_failures,
            missing=missing_assessment_evidence,
            non_returned=assessment_call_failures,
            reserved=len(assessment_ids),
            excluded=len(assessment_excluded),
        )
    )
    extraction_coordinates = {
        (value.get("coordinate", {}).get("subject"), value.get("coordinate", {}).get("episode"))
        for _, value in extraction_artifacts
        if isinstance(value.get("coordinate"), dict)
        and value.get("valid") is True
    }
    expected_extraction_coordinates = {
        (slot, episode.ordinal)
        for slot in schedule.subject_slots
        for episode in schedule.episodes
    }
    checks.append(
        _check(
            "artifact-inventory",
            expected_development <= development_artifacts
            and expected_assessment <= assessment_coordinates
            and expected_evaluation <= evaluation_artifacts
            and expected_extraction_coordinates <= extraction_coordinates,
            missing_development=sorted(expected_development - development_artifacts),
            missing_assessment=sorted(expected_assessment - assessment_coordinates),
            missing_extraction=sorted(expected_extraction_coordinates - extraction_coordinates),
            missing_evaluation=sorted(expected_evaluation - evaluation_artifacts),
        )
    )

    evaluation_values = _read_artifacts(run_path / "evaluation")
    isolation_ok = True
    isolation_failures: list[str] = []
    for path, value in evaluation_values:
        before = value.get("developmental_state_before")
        after = value.get("developmental_state_after")
        digest_before = value.get("developmental_state_digest_before")
        digest_after = value.get("developmental_state_digest_after")
        if before != after or digest_before != digest_after:
            isolation_ok = False
            isolation_failures.append(path.name)
    checks.append(
        _check("evaluation-isolation-receipts", isolation_ok, failures=isolation_failures)
    )

    complete = status == "COMPLETE"
    all_passed = complete and all(bool(check.get("passed")) for check in checks)
    return EngineeringAudit("PASS" if all_passed else "FAIL", tuple(checks))


__all__ = ["EngineeringAudit", "audit_pilot_run"]
