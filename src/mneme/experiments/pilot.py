"""Durable offline lifecycle and call accounting for the Phase Two pilot.

The pilot ledger is deliberately outside a lineage SQLite store.  It records
scientific execution coordinates and provider-call accounting beside the
immutable P0.3 run.  It never constructs a prompt, invokes a host, or accepts
developmental state; those operations remain owned by the existing runner and
memory services.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..host import Host
from ..state.policy import PolicyError, PolicyService, host_ref
from .artifacts import ArtifactError, ArtifactStore, _write_json, content_digest


class PilotError(ArtifactError):
    """The pilot ledger cannot safely advance or record a call."""


class PilotStatus(StrEnum):
    PREPARED = "PREPARED"
    QUALIFYING = "QUALIFYING"
    QUALIFIED = "QUALIFIED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"


class CallStatus(StrEnum):
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    RETURNED = "RETURNED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"


_SECRET_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "bearer",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
}
_USAGE_KEYS = {
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "max_input_tokens",
    "max_output_tokens",
}


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _safe_value(value: Any, *, key: str | None = None, depth: int = 0) -> Any:
    """Copy JSON data while redacting secret-bearing provider metadata."""

    if depth > 8:
        return "[TRUNCATED]"
    lowered = key.casefold() if key is not None else ""
    sensitive_fragment = any(
        lowered.startswith(f"{part}_")
        or lowered.endswith(f"_{part}")
        or f"_{part}_" in lowered
        for part in _SECRET_KEYS
    )
    if lowered in _SECRET_KEYS or (sensitive_fragment and lowered not in _USAGE_KEYS):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(child_key): _safe_value(child, key=str(child_key), depth=depth + 1)
            for child_key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_value(child, depth=depth + 1) for child in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _component(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or "/" in value or "\\" in value:
        raise PilotError(f"invalid {label}: {value!r}")
    return value


@dataclass(frozen=True)
class CallReservation:
    """One durable call coordinate and its terminal disposition."""

    call_id: str
    role: str
    coordinate: Mapping[str, Any]
    max_output_tokens: int
    status: CallStatus
    output_tokens: int | None = None
    usage: Mapping[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "call_id": self.call_id,
            "role": self.role,
            "coordinate": dict(self.coordinate),
            "max_output_tokens": self.max_output_tokens,
            "status": self.status.value,
            "output_tokens": self.output_tokens,
            "usage": None if self.usage is None else dict(self.usage),
            "error": self.error,
        }


def host_role_binding(role: str, host: Host) -> dict[str, Any]:
    """Return the immutable, sanitized host binding for one execution role."""

    if not isinstance(role, str) or not role:
        raise PilotError("host role must be non-empty")
    fingerprint = host.fingerprint().to_dict()
    return {
        "role": role,
        "fingerprint": fingerprint,
        "fingerprint_sha256": content_digest(fingerprint),
        "provider": fingerprint.get("provider"),
        "model_id": fingerprint.get("model_id"),
    }


class PilotRun:
    """A restart-safe P2.3 lifecycle bound to one prepared P0.3 run."""

    def __init__(self, artifacts: ArtifactStore, run_id: str) -> None:
        self.artifacts = artifacts
        self.run_id = _component(run_id, "run ID")
        self.run_path = artifacts.locate_run(self.run_id)
        if not artifacts.verify_run(self.run_path):
            raise PilotError("prepared run failed artifact integrity verification")
        self.root = self.run_path / "pilot"
        self.state_path = self.root / "state.json"
        self.reservations = self.root / "reservations"
        manifest = artifacts._read_json(self.run_path / "run-manifest.json")
        digest = manifest.get("contract_sha256")
        if not isinstance(digest, str):
            raise PilotError("prepared run has no contract digest")
        self.contract_digest = digest
        bindings_path = self.run_path / "bindings.json"
        self.bindings = artifacts._read_json(bindings_path)

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {
                "schema_version": 1,
                "run_id": self.run_id,
                "status": PilotStatus.PREPARED.value,
                "contract_sha256": self.contract_digest,
                "updated_at": _utc(),
            }
        value = self.artifacts._read_json(self.state_path)
        if (
            value.get("run_id") != self.run_id
            or value.get("contract_sha256") != self.contract_digest
        ):
            raise PilotError("pilot state is bound to a different run or contract")
        if value.get("schema_version") != 1:
            raise PilotError("unsupported pilot state schema")
        return value

    def _write_state(self, status: PilotStatus, **fields: Any) -> dict[str, Any]:
        value = self._read_state()
        value.update(_safe_value(fields))
        value.update(
            {
                "schema_version": 1,
                "run_id": self.run_id,
                "contract_sha256": self.contract_digest,
                "status": status.value,
                "updated_at": _utc(),
            }
        )
        if status in {
            PilotStatus.QUALIFYING,
            PilotStatus.QUALIFIED,
            PilotStatus.RUNNING,
            PilotStatus.PAUSED,
            PilotStatus.COMPLETE,
            PilotStatus.FAILED,
            PilotStatus.UNCERTAIN,
        }:
            pilot = dict(value.get("pilot", {}))
            pilot["status"] = status.value
            value["pilot"] = pilot
        value["state_sha256"] = content_digest(
            {key: item for key, item in value.items() if key != "state_sha256"}
        )
        self.root.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".state.", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
            self.artifacts._sync_file(self.state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.artifacts.update_run_status(self.run_id, status.value)
        return value

    @staticmethod
    def _verify_state(value: Mapping[str, Any]) -> bool:
        digest = value.get("state_sha256")
        return isinstance(digest, str) and digest == content_digest(
            {key: item for key, item in value.items() if key != "state_sha256"}
        )

    def status(self) -> dict[str, Any]:
        value = self._read_state()
        if "state_sha256" in value and not self._verify_state(value):
            raise PilotError("pilot state integrity check failed")
        return value

    def study_progress(self) -> dict[str, Any]:
        """Return the durable P2.3 coordinate ledger, if one exists."""

        value = self.status().get("study_progress")
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise PilotError("pilot study progress is not an object")
        return dict(value)

    def record_study_progress(self, **fields: Any) -> dict[str, Any]:
        """Atomically persist completed study coordinates and counters."""

        state = self.status()
        try:
            status = PilotStatus(str(state["status"]))
        except (KeyError, ValueError) as exc:
            raise PilotError("pilot state has an invalid lifecycle status") from exc
        current = self.study_progress()
        current.update(_safe_value(fields))
        return self._write_state(status, study_progress=current)

    def prepare(
        self,
        *,
        planned_calls: int,
        max_output_tokens: int,
        qualification_calls: int = 3,
        pilot_calls: int = 0,
        metadata: Mapping[str, Any] | None = None,
        role_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create or idempotently verify the immutable pilot execution envelope."""

        if (
            isinstance(planned_calls, bool)
            or not isinstance(planned_calls, int)
            or planned_calls <= 0
        ):
            raise PilotError("planned_calls must be a positive integer")
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens <= 0
        ):
            raise PilotError("max_output_tokens must be a positive integer")
        if (
            qualification_calls != 3
            or pilot_calls < 0
            or qualification_calls + pilot_calls > planned_calls
        ):
            raise PilotError("pilot call envelope is inconsistent with qualification/pilot counts")
        state = self._read_state()
        envelope = {
            "planned_calls": planned_calls,
            "max_output_tokens": max_output_tokens,
            "qualification_calls": qualification_calls,
            "pilot_calls": pilot_calls,
            "metadata": _safe_value(metadata or {}),
        }
        if role_bindings is not None:
            if not isinstance(role_bindings, Mapping):
                raise PilotError("role_bindings must be an object")
            normalized_roles = _safe_value(dict(role_bindings))
            if not isinstance(normalized_roles, dict):
                raise PilotError("role_bindings could not be serialized")
            for required in ("developing", "assessor"):
                if not isinstance(normalized_roles.get(required), Mapping):
                    raise PilotError(f"role_bindings requires {required!r}")
            envelope["role_bindings"] = normalized_roles
        if state.get("envelope") is not None and state.get("envelope") != envelope:
            raise PilotError("pilot envelope is immutable and conflicts with the existing state")
        return self._write_state(PilotStatus.PREPARED, envelope=envelope)

    def require_role_host(self, role: str, host: Host) -> Mapping[str, Any]:
        """Fail closed when a configured role is bound to another host."""

        state = self.status()
        envelope = state.get("envelope")
        configured = envelope.get("role_bindings") if isinstance(envelope, Mapping) else None
        if configured is None:
            # Existing single-host fixtures remain explicitly legacy. New
            # mixed-role runs always publish role_bindings and cannot use this
            # compatibility path accidentally.
            if role == "assessor" and self.bindings.get("roles") is None:
                return {"legacy_single_host": True}
            raise PilotError(f"missing configured host binding for role {role}")
        expected = configured.get(role) if isinstance(configured, Mapping) else None
        if not isinstance(expected, Mapping):
            raise PilotError(f"missing configured host binding for role {role}")
        actual = host_role_binding(role, host)
        if expected.get("fingerprint_sha256") != actual["fingerprint_sha256"]:
            raise PilotError(f"host fingerprint does not match configured {role} binding")
        if expected.get("fingerprint") != actual["fingerprint"]:
            raise PilotError(f"host fingerprint contents do not match configured {role} binding")
        return expected

    def capture_subject_bindings(self, subjects: Mapping[int, Any]) -> dict[str, Any]:
        """Persist the prepared subject/authority boundary before pilot work.

        The pilot ledger is outside the lineage stores, so the prepared
        subject identity and effective permission authority must be copied
        into it before the first developmental transition.  The snapshot is
        idempotent and immutable for a run; a restart that observes different
        bindings fails closed.
        """

        state = self.status()
        snapshots: list[dict[str, Any]] = []
        for slot in sorted(subjects):
            subject = subjects[slot]
            if getattr(subject, "slot", None) != slot:
                raise PilotError(f"subject mapping key does not match slot {slot}")
            store = getattr(subject, "store", None)
            instance_id = str(getattr(subject, "instance_id", ""))
            if store is None or not instance_id:
                raise PilotError(f"subject {slot} lacks a writable lineage binding")
            try:
                current = dict(store.current())
                policy = PolicyService(store, instance_id).current().to_dict()
            except (KeyError, PolicyError, TypeError, ValueError) as exc:
                raise PilotError(f"subject {slot} authority snapshot failed") from exc
            fingerprint = getattr(subject, "host", None)
            if fingerprint is None or not hasattr(fingerprint, "fingerprint"):
                raise PilotError(f"subject {slot} lacks a host binding")
            host_fingerprint = fingerprint.fingerprint().to_dict()
            prepared_binding: Mapping[str, Any] | None = None
            raw_subjects = self.bindings.get("subjects")
            if isinstance(raw_subjects, list):
                matches = [
                    item for item in raw_subjects
                    if isinstance(item, Mapping) and item.get("slot") == slot
                ]
                if len(matches) == 1:
                    prepared_binding = dict(matches[0])
            snapshots.append(
                {
                    "slot": slot,
                    "instance_id": instance_id,
                    "prepared_binding": prepared_binding,
                    "current": {
                        "active_instance_id": str(current["active_instance_id"]),
                        "current_revision": int(current["current_revision"]),
                        "current_manifest_id": str(current["current_manifest_id"]),
                    },
                    "permission": policy,
                    "host_fingerprint": host_fingerprint,
                    "host_ref": host_ref(host_fingerprint),
                }
            )
        existing = state.get("subject_bindings")
        if existing is not None and existing != snapshots:
            raise PilotError("prepared subject authority bindings are immutable")
        if existing is not None:
            return state
        try:
            status = PilotStatus(str(state["status"]))
        except (KeyError, ValueError) as exc:
            raise PilotError("pilot state has an invalid lifecycle status") from exc
        return self._write_state(status, subject_bindings=snapshots)

    def begin_qualification(self) -> dict[str, Any]:
        state = self.status()
        if state["status"] == PilotStatus.QUALIFYING.value:
            return state
        if state["status"] != PilotStatus.PREPARED.value:
            raise PilotError("qualification can begin only from PREPARED")
        return self._write_state(PilotStatus.QUALIFYING, qualification={"status": "RUNNING"})

    def _reservation_path(self, call_id: str) -> Path:
        return self.reservations / f"{_component(call_id, 'call ID')}.json"

    def _all_reservations(self) -> list[dict[str, Any]]:
        if not self.reservations.is_dir():
            return []
        values: list[dict[str, Any]] = []
        for path in sorted(self.reservations.glob("*.json")):
            value = self.artifacts._read_json(path)
            if value.get("run_id") != self.run_id:
                raise PilotError("reservation belongs to a different run")
            receipt = value.get("receipt_sha256")
            if not isinstance(receipt, str) or receipt != content_digest(
                {key: item for key, item in value.items() if key != "receipt_sha256"}
            ):
                raise PilotError(f"reservation integrity check failed: {path.name}")
            values.append(value)
        return values

    def reserve_call(
        self,
        *,
        call_id: str,
        role: str,
        coordinate: Mapping[str, Any],
        max_output_tokens: int,
    ) -> Mapping[str, Any]:
        """Reserve exactly one coordinate before dispatch; retries are idempotent."""

        call_id = _component(call_id, "call ID")
        role = _component(role, "call role")
        if not isinstance(coordinate, Mapping) or not coordinate:
            raise PilotError("call coordinate must be a non-empty object")
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens <= 0
        ):
            raise PilotError("max_output_tokens must be a positive integer")
        state = self.status()
        if state["status"] not in {
            PilotStatus.QUALIFYING.value,
            PilotStatus.QUALIFIED.value,
            PilotStatus.RUNNING.value,
        }:
            raise PilotError("calls can be reserved only while qualification or pilot is active")
        envelope = state.get("envelope")
        if not isinstance(envelope, Mapping):
            raise PilotError("pilot envelope has not been prepared")
        intent = {
            "run_id": self.run_id,
            "call_id": call_id,
            "role": role,
            "coordinate": _safe_value(dict(coordinate)),
            "max_output_tokens": max_output_tokens,
        }
        path = self._reservation_path(call_id)
        with self.artifacts._writer():
            if path.exists():
                existing = self.artifacts._read_json(path)
                if existing.get("intent_sha256") != content_digest(intent):
                    raise PilotError(f"call ID already has conflicting intent: {call_id}")
                return existing
            current = self._all_reservations()
            max_calls = envelope.get("planned_calls")
            if isinstance(max_calls, int) and len(current) >= max_calls:
                raise PilotError("pilot call ceiling would be exceeded")
            output_ceiling = envelope.get("max_output_tokens")
            already_reserved = sum(
                int(item.get("max_output_tokens", 0)) for item in current
            )
            if (
                isinstance(output_ceiling, int)
                and already_reserved + max_output_tokens > output_ceiling
            ):
                raise PilotError("pilot output-token ceiling would be exceeded")
            output = {
                **intent,
                "schema_version": 1,
                "status": CallStatus.RESERVED.value,
                "reserved_at": _utc(),
                "intent_sha256": content_digest(intent),
            }
            output["receipt_sha256"] = content_digest(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(path, output)
            self.artifacts._sync_file(path)
            return output

    def _transition_call(
        self, call_id: str, expected: CallStatus, status: CallStatus, **fields: Any
    ) -> Mapping[str, Any]:
        path = self._reservation_path(call_id)
        with self.artifacts._writer():
            if not path.is_file():
                raise PilotError(f"unknown call reservation: {call_id}")
            value = self.artifacts._read_json(path)
            if value.get("status") != expected.value:
                if value.get("status") == status.value:
                    normalized = _safe_value(fields)
                    for key, expected_value in normalized.items():
                        if key in value and value.get(key) != expected_value:
                            raise PilotError(
                                f"call {call_id} already has conflicting {key}"
                            )
                    return value
                raise PilotError(
                    f"call {call_id} is {value.get('status')}, expected {expected.value}"
                )
            value.update(_safe_value(fields))
            value["status"] = status.value
            value["updated_at"] = _utc()
            value.pop("receipt_sha256", None)
            value["receipt_sha256"] = content_digest(value)
            _write_json(path, value)
            self.artifacts._sync_file(path)
            return value

    def dispatch_call(
        self,
        call_id: str,
        *,
        expected_host_fingerprint: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        return self._transition_call(
            call_id,
            CallStatus.RESERVED,
            CallStatus.DISPATCHED,
            expected_host_fingerprint=dict(expected_host_fingerprint)
            if expected_host_fingerprint is not None
            else None,
        )

    def return_call(
        self,
        call_id: str,
        *,
        result: Mapping[str, Any] | None = None,
        usage: Mapping[str, Any] | None = None,
        output_tokens: int | None = None,
        actual_host_fingerprint: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if output_tokens is not None and (
            isinstance(output_tokens, bool)
            or not isinstance(output_tokens, int)
            or output_tokens < 0
        ):
            raise PilotError("output_tokens must be a non-negative integer or null")
        path = self._reservation_path(call_id)
        if path.is_file():
            existing = self.artifacts._read_json(path)
            expected = existing.get("expected_host_fingerprint")
            if expected is not None:
                if not isinstance(expected, Mapping) or not isinstance(
                    actual_host_fingerprint, Mapping
                ):
                    raise PilotError(f"call {call_id} has incomplete host provenance")
                if dict(expected) != dict(actual_host_fingerprint):
                    raise PilotError(f"call {call_id} returned from a different host binding")
        return self._transition_call(
            call_id,
            CallStatus.DISPATCHED,
            CallStatus.RETURNED,
            result=_safe_value(result or {}),
            usage=_safe_value(usage) if usage is not None else None,
            output_tokens=output_tokens,
            actual_host_fingerprint=dict(actual_host_fingerprint)
            if actual_host_fingerprint is not None
            else None,
            returned_at=_utc(),
        )

    def assert_returned_host(self, call_id: str) -> None:
        """Verify a returned result stayed on its reserved host binding."""

        value = self.artifacts._read_json(self._reservation_path(call_id))
        expected = value.get("expected_host_fingerprint")
        actual = value.get("actual_host_fingerprint")
        if expected is None:
            return
        if not isinstance(expected, Mapping) or not isinstance(actual, Mapping):
            raise PilotError(f"call {call_id} has incomplete host provenance")
        if dict(expected) != dict(actual):
            raise PilotError(f"call {call_id} returned from a different host binding")

    def fail_call(self, call_id: str, reason: str) -> Mapping[str, Any]:
        return self._transition_call(
            call_id, CallStatus.DISPATCHED, CallStatus.FAILED, error=str(reason)
        )

    def mark_uncertain(self, call_id: str, reason: str) -> Mapping[str, Any]:
        return self._transition_call(
            call_id, CallStatus.DISPATCHED, CallStatus.UNCERTAIN, error=str(reason)
        )

    def complete_qualification(
        self, *, passed: bool, details: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        state = self.status()
        if state["status"] != PilotStatus.QUALIFYING.value:
            raise PilotError("qualification is not active")
        calls = self._all_reservations()
        expected = int(state.get("envelope", {}).get("qualification_calls", 3))
        qualification = [item for item in calls if item.get("role") == "assessor-qualification"]
        if not qualification or any(
            item.get("status") != CallStatus.RETURNED.value for item in qualification
        ):
            raise PilotError("qualification cannot finish before all calls return")
        if passed and len(qualification) != expected:
            raise PilotError("qualification cannot pass before all calls return")
        next_status = PilotStatus.QUALIFIED if passed else PilotStatus.FAILED
        return self._write_state(
            next_status,
            qualification={
                "status": "PASS" if passed else "FAIL",
                "details": _safe_value(details or {}),
            },
        )

    def fail(self, reason: str, *, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Record a terminal failure without inventing missing call results."""

        state = self.status()
        if state["status"] not in {
            PilotStatus.QUALIFYING.value,
            PilotStatus.RUNNING.value,
            PilotStatus.PAUSED.value,
        }:
            raise PilotError("pilot is not active")
        return self._write_state(
            PilotStatus.FAILED,
            failure={"reason": str(reason), "details": _safe_value(details or {})},
        )

    def begin_pilot(self) -> dict[str, Any]:
        state = self.status()
        if state["status"] != PilotStatus.QUALIFIED.value:
            raise PilotError("pilot can begin only after qualification passes")
        return self._write_state(PilotStatus.RUNNING, pilot={"status": "RUNNING"})

    def pause(self, reason: str) -> dict[str, Any]:
        state = self.status()
        if state["status"] not in {PilotStatus.QUALIFYING.value, PilotStatus.RUNNING.value}:
            raise PilotError("only active pilot work can be paused")
        return self._write_state(PilotStatus.PAUSED, pause_reason=str(reason))

    def resume(self) -> dict[str, Any]:
        state = self.status()
        if state["status"] != PilotStatus.PAUSED.value:
            raise PilotError("pilot is not paused")
        target = (
            PilotStatus.RUNNING
            if state.get("qualification", {}).get("status") == "PASS"
            else PilotStatus.QUALIFYING
        )
        return self._write_state(target, resumed_at=_utc())

    def finish(self, *, summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
        state = self.status()
        if state["status"] not in {PilotStatus.RUNNING.value, PilotStatus.QUALIFIED.value}:
            raise PilotError("pilot is not in a finishable state")
        calls = self._all_reservations()
        if any(
            item.get("status") in {CallStatus.RESERVED.value, CallStatus.DISPATCHED.value}
            for item in calls
        ):
            raise PilotError("pilot has non-terminal call reservations")
        return self._write_state(PilotStatus.COMPLETE, summary=_safe_value(summary or {}))

    def reservations_report(self) -> dict[str, Any]:
        calls = self._all_reservations()
        return {
            "run_id": self.run_id,
            "contract_sha256": self.contract_digest,
            "status": self.status(),
            "calls": calls,
            "counts": {
                status.value: sum(item.get("status") == status.value for item in calls)
                for status in CallStatus
            },
            "actual_output_tokens": sum(
                int(item["output_tokens"])
                for item in calls
                if isinstance(item.get("output_tokens"), int)
            ),
            "unknown_output_token_calls": sum(item.get("output_tokens") is None for item in calls),
        }

    def publish_artifact(self, category: str, name: str, value: Mapping[str, Any]) -> Path:
        """Publish a sanitized JSON artifact under the run's P2.3 inventory."""

        category = _component(category, "artifact category")
        name = _component(name, "artifact name")
        if not isinstance(value, Mapping):
            raise PilotError("artifact value must be an object")
        payload = _safe_value(dict(value))
        if not isinstance(payload, dict):
            raise PilotError("artifact value could not be serialized")
        try:
            return self.artifacts.publish_json_artifact(self.run_path, category, name, payload)
        except ArtifactError as exc:
            raise PilotError(str(exc)) from exc


__all__ = [
    "CallReservation",
    "CallStatus",
    "PilotError",
    "PilotRun",
    "PilotStatus",
    "host_role_binding",
]
