"""Evidence audit for a completed Phase Two pilot.

The pilot counters describe what the scheduler says it did.  They are useful
progress information, but they are not sufficient engineering evidence by
themselves.  This module performs a small, filesystem-oriented audit against
the durable :class:`PilotRun` ledger and its published inventory.  It does not
inspect or alter developmental state and it does not make provider calls.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..development.recovery import verify_replay
from ..state.policy import PolicyError, PolicyService
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
    subjects: Mapping[int, Any] | None = None,
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

    def _coordinate(kind: str, slot: int, item: Any, attempt: int | None = None) -> dict[str, Any]:
        method = getattr(schedule, f"{kind}_coordinate", None)
        if callable(method):
            if kind == "extraction":
                return dict(method(slot, item, attempt=int(attempt or 0)))
            if kind == "evaluation":
                raise AssertionError("evaluation coordinates require a repetition")
            return dict(method(slot, item))
        if kind == "extraction":
            return {"subject": slot, "episode": int(item.ordinal), "attempt": int(attempt or 0)}
        return {"subject": slot, "episode": int(item.ordinal)}

    expected_coordinates: dict[tuple[str, str], set[str]] = {}

    def _encoded(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    for slot in schedule.subject_slots:
        for episode in schedule.episodes:
            development_id = f"development-s{slot}-e{episode.ordinal}"
            expected_coordinates[("development-response", development_id)] = {
                _encoded(_coordinate("development", slot, episode))
            }
            assessment_id = f"assessment-s{slot}-e{episode.ordinal}"
            expected_coordinates[("assessor", assessment_id)] = {
                _encoded(_coordinate("assessment", slot, episode))
            }
            extraction_id = f"extraction-s{slot}-e{episode.ordinal}"
            expected_coordinates[("development-extraction", extraction_id)] = {
                _encoded(_coordinate("extraction", slot, episode, attempt=0)),
                _encoded(_coordinate("extraction", slot, episode, attempt=1)),
            }
        for probe in schedule.probes:
            for repetition in range(schedule.evaluation_repetitions):
                evaluation_id = f"evaluation-s{slot}-p{probe.ordinal}-r{repetition}"
                method = getattr(schedule, "evaluation_coordinate", None)
                coordinate = (
                    dict(method(slot, probe, repetition))
                    if callable(method)
                    else {"subject": slot, "probe": int(probe.ordinal), "repetition": repetition}
                )
                expected_coordinates[("evaluation", evaluation_id)] = {_encoded(coordinate)}

    coordinate_failures: list[dict[str, Any]] = []
    known_extraction_ids = {
        call_id for role, call_id in expected_coordinates if role == "development-extraction"
    }

    def _is_extraction_coordinate(call_id: Any) -> bool:
        return isinstance(call_id, str) and any(
            call_id == expected_id
            or call_id.startswith(f"{expected_id}-repair")
            or call_id.startswith(f"{expected_id}-recovery-")
            for expected_id in known_extraction_ids
        )

    for item in calls:
        role = str(item.get("role"))
        call_id = str(item.get("call_id"))
        coordinate = item.get("coordinate")
        encoded = _encoded(coordinate) if isinstance(coordinate, Mapping) else None
        allowed: set[str] | None = expected_coordinates.get((role, call_id))
        if allowed is None and role == "development-extraction":
            # Recovery calls carry a fixed suffix but retain the same
            # schedule coordinate.  They are bounded alternatives to the
            # base attempt, never new schedule coordinates.
            base = next(
                (
                    expected_id
                    for expected_role, expected_id in expected_coordinates
                    if expected_role == role
                    and (
                        call_id == expected_id
                        or call_id.startswith(f"{expected_id}-repair")
                        or call_id.startswith(f"{expected_id}-recovery-")
                    )
                ),
                None,
            )
            if base is not None:
                allowed = expected_coordinates[(role, base)]
        if role == "assessor-qualification":
            allowed = {_encoded({"case": f"Q{ordinal}"}) for ordinal in range(1, 4)}
        elif role == "evidence-reviewer":
            extraction_call = (
                coordinate.get("extraction_call")
                if isinstance(coordinate, Mapping)
                else None
            )
            evidence_index = (
                coordinate.get("evidence_index")
                if isinstance(coordinate, Mapping)
                else None
            )
            allowed = None
            if (
                isinstance(coordinate, Mapping)
                and coordinate.get("kind") == "semantic-evidence-reconciliation"
                and isinstance(extraction_call, str)
                and _is_extraction_coordinate(extraction_call)
                and isinstance(evidence_index, int)
                and not isinstance(evidence_index, bool)
                and 0 <= evidence_index < 4
            ):
                allowed = {encoded or ""}
        if allowed is None or encoded not in allowed:
            coordinate_failures.append(
                {"call_id": call_id, "role": role, "coordinate": coordinate}
            )
    checks.append(
        _check(
            "call-coordinates",
            not coordinate_failures,
            unexpected=coordinate_failures,
        )
    )

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
            and all(item in development_ids for item in expected_development)
            and development_ids <= expected_development,
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
            expected_evaluation <= evaluation_ids and evaluation_ids <= expected_evaluation,
            expected=len(expected_evaluation),
            observed=len(expected_evaluation & evaluation_ids),
        )
    )

    host_failures: list[dict[str, Any]] = []
    envelope = status_value.get("envelope") if isinstance(status_value, Mapping) else None
    role_bindings = envelope.get("role_bindings") if isinstance(envelope, Mapping) else None

    def _binding_role(role: str) -> str:
        if role in {"development-response", "development-extraction"}:
            if isinstance(role_bindings, Mapping) and role in role_bindings:
                return role
            return "developing"
        if role in {"assessor", "assessor-qualification", "evaluation-assessor"}:
            return "assessor"
        return role

    for item in returned:
        expected = item.get("expected_host_fingerprint")
        actual = item.get("actual_host_fingerprint")
        configured = None
        binding = (
            role_bindings.get(_binding_role(str(item.get("role"))))
            if isinstance(role_bindings, Mapping)
            else None
        )
        if isinstance(binding, Mapping):
            configured = binding.get("fingerprint")
        if isinstance(role_bindings, Mapping) and (
            not isinstance(expected, Mapping) or not isinstance(actual, Mapping)
        ):
            host_failures.append(
                {"call_id": item.get("call_id"), "reason": "missing host fingerprint"}
            )
        elif (
            isinstance(expected, Mapping)
            and isinstance(actual, Mapping)
            and dict(expected) != dict(actual)
        ):
            host_failures.append(
                {
                    "call_id": item.get("call_id"),
                    "reason": "returned host differs from reserved host",
                }
            )
        elif (
            isinstance(configured, Mapping)
            and isinstance(actual, Mapping)
            and dict(configured) != dict(actual)
        ):
            host_failures.append(
                {
                    "call_id": item.get("call_id"),
                    "reason": "returned host differs from role binding",
                }
            )
    checks.append(
        _check(
            "host-provenance",
            not host_failures,
            failures=host_failures,
            returned=len(returned),
        )
    )

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

    replay_results: list[dict[str, Any]] = []
    replay_failures: list[str] = []
    subject_bindings = (
        status_value.get("subject_bindings")
        if isinstance(status_value, Mapping)
        else None
    )
    if not isinstance(subjects, Mapping) or not isinstance(subject_bindings, list):
        replay_failures.append("prepared subject/replay evidence is unavailable")
    else:
        snapshots = {
            item.get("slot"): item
            for item in subject_bindings
            if isinstance(item, Mapping) and isinstance(item.get("slot"), int)
        }
        prepared_subjects = pilot.bindings.get("subjects") if isinstance(
            getattr(pilot, "bindings", None), Mapping
        ) else None
        if (
            set(snapshots) != set(schedule.subject_slots)
            or set(subjects) != set(schedule.subject_slots)
            or not isinstance(prepared_subjects, list)
        ):
            replay_failures.append("subject slots do not match the prepared schedule")
        for slot in schedule.subject_slots:
            snapshot = snapshots.get(slot)
            subject = subjects.get(slot)
            if not isinstance(snapshot, Mapping) or subject is None:
                replay_failures.append(f"missing subject binding for slot {slot}")
                continue
            prepared_matches = [
                item
                for item in (prepared_subjects or [])
                if isinstance(item, Mapping) and item.get("slot") == slot
            ]
            if (
                len(prepared_matches) != 1
                or snapshot.get("prepared_binding") != dict(prepared_matches[0])
            ):
                replay_failures.append(f"prepared subject binding mismatch for slot {slot}")
            store = getattr(subject, "store", None)
            try:
                if store is not None and hasattr(store, "connection"):
                    replay_value = verify_replay(store)
                else:
                    replay_raw = getattr(subject, "replay_evidence", None)
                    if not isinstance(replay_raw, Mapping):
                        raise ValueError("replay evidence is unavailable")
                    replay_value = dict(replay_raw)
                replay_results.append({"slot": slot, **replay_value})
                if replay_value.get("matches_materialized") is not True:
                    replay_failures.append(
                        "learner replay does not match materialized state "
                        f"for slot {slot}"
                    )
                authority_evidence = getattr(subject, "authority_evidence", {})
                if store is not None and hasattr(store, "current"):
                    current = dict(store.current())
                    policy = PolicyService(
                        store, str(getattr(subject, "instance_id", ""))
                    ).current().to_dict()
                elif isinstance(authority_evidence, Mapping):
                    current = dict(authority_evidence.get("current", {}))
                    policy = dict(authority_evidence.get("permission", {}))
                else:
                    current, policy = {}, {}
                prepared_current = snapshot.get("current")
                prepared_policy = snapshot.get("permission")
                if not isinstance(prepared_current, Mapping) or not isinstance(
                    prepared_policy, Mapping
                ):
                    raise ValueError("prepared subject authority snapshot is incomplete")
                if str(current.get("active_instance_id")) != str(snapshot.get("instance_id")):
                    replay_failures.append(f"final subject identity differs for slot {slot}")
                if str(policy.get("policy_id")) != str(prepared_policy.get("policy_id")):
                    replay_failures.append(f"policy identity changed for slot {slot}")
                if str(policy.get("scope_id")) != str(prepared_policy.get("scope_id")):
                    replay_failures.append(f"policy scope changed for slot {slot}")
                if (
                    policy.get("authority_available") is not True
                    or prepared_policy.get("authority_available") is not True
                ):
                    replay_failures.append(f"permission authority unavailable for slot {slot}")
                for permission in ("storage", "interpret", "learn"):
                    if (
                        prepared_policy.get(permission) is True
                        and policy.get(permission) is not True
                    ):
                        replay_failures.append(
                            f"prepared {permission} permission was lost for slot {slot}"
                        )
            except (PolicyError, OSError, TypeError, ValueError, KeyError) as exc:
                replay_failures.append(f"slot {slot}: {type(exc).__name__}: {exc}")
    checks.append(
        _check(
            "subject-authority-and-replay",
            not replay_failures,
            failures=replay_failures,
            replay=replay_results,
        )
    )

    complete = status == "COMPLETE"
    all_passed = complete and all(bool(check.get("passed")) for check in checks)
    return EngineeringAudit("PASS" if all_passed else "FAIL", tuple(checks))


__all__ = ["EngineeringAudit", "audit_pilot_run"]
