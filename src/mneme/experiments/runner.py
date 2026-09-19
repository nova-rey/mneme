"""P0.4's small integrated no-learning execution primitive.

The runner is deliberately an orchestrator, not a second state system.  P0.2
continues to own developmental operations and accepted revisions; P0.3 owns
prepared-run bindings, immutable plans, and evaluation receipts.  This module
only joins those boundaries for a finite schedule.

Every developmental request is constructed from the declared fixture record
alone.  Accepted operation IDs and execution evidence are administrative
coordinates and never enter :class:`~mneme.contracts.GenerationRequest`.
Evaluation receives a :class:`FrozenEvaluationView` and writes only through the
P0.3 artifact receipt API.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..contracts import GenerationRequest
from ..controller import ResponseController, TurnIntent
from ..host import Host
from ..state.reader import CheckpointReader
from ..state.service import (
    ContinuityError,
    ContinuityService,
)
from ..state.snapshots import SnapshotError, create_checkpoint, fork_from_checkpoint
from ..state.storage import SchemaError, SQLiteStore
from .artifacts import ArtifactError, ArtifactStore, content_digest, file_digest
from .evaluation import FrozenEvaluationView


class RunnerError(RuntimeError):
    """The prepared run cannot safely execute or resume."""


class RunnerUncertain(RunnerError):
    """An external operation has no terminal result and is never regenerated."""


@dataclass(frozen=True)
class SubjectExecution:
    """A writable P0.2 subject and the host pinned for this prepared run.

    The store is supplied explicitly because P0.3 intentionally does not put
    writable lineage locators into laboratory artifacts.  A caller may open a
    forked working store before constructing this object.
    """

    slot: int
    store: SQLiteStore
    host: Host


@dataclass(frozen=True)
class DevelopmentEvidence:
    subject_slot: int
    ordinal: int
    record_id: str
    operation_id: str
    status: str
    revision: int | None
    model_calls: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_slot": self.subject_slot,
            "ordinal": self.ordinal,
            "record_id": self.record_id,
            "operation_id": self.operation_id,
            "status": self.status,
            "revision": self.revision,
            "model_calls": self.model_calls,
        }


@dataclass(frozen=True)
class EvaluationEvidence:
    subject_slot: int
    probe_ordinal: int
    repetition: int
    check_id: str
    status: str
    output: str
    checkpoint_sha256: str
    state_digest_before: str
    state_digest_after: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_slot": self.subject_slot,
            "probe_ordinal": self.probe_ordinal,
            "repetition": self.repetition,
            "check_id": self.check_id,
            "status": self.status,
            "output": self.output,
            "checkpoint_sha256": self.checkpoint_sha256,
            "state_digest_before": self.state_digest_before,
            "state_digest_after": self.state_digest_after,
        }


def _uuid_coordinate(run_id: str, domain: str, *coordinates: object) -> str:
    """Create a stable administrative UUID for one execution coordinate."""

    material = ":".join(["mneme-p0.4", run_id, domain, *(str(item) for item in coordinates)])
    return str(uuid.uuid5(uuid.NAMESPACE_URL, material))


def _record_id(record: Mapping[str, Any], ordinal: int) -> str:
    value = record.get("record_id", record.get("id"))
    return str(value) if value is not None else f"record-{ordinal}"


def _messages(record: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    raw = record.get("messages")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise RunnerError("execution record must contain non-empty messages")
    messages: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise RunnerError("execution record messages must be objects")
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise RunnerError("execution record messages require string role/content")
        messages.append({"role": role, "content": content})
    return tuple(messages)


def _experiment_parameters(
    experiment: Mapping[str, Any],
) -> tuple[str | None, dict[str, Any], dict[str, Any] | None]:
    generation = experiment.get("generation", {})
    if not isinstance(generation, Mapping):
        raise RunnerError("generation must be an object")
    system = generation.get("system")
    if system is not None and not isinstance(system, str):
        raise RunnerError("generation.system must be a string")
    parameters = generation.get("parameters", {})
    if not isinstance(parameters, Mapping):
        raise RunnerError("generation.parameters must be an object")
    response_format = generation.get("response_format")
    if response_format is not None and not isinstance(response_format, Mapping):
        raise RunnerError("generation.response_format must be an object")
    return system, dict(parameters), dict(response_format) if response_format else None


def _host_digest(host: Host) -> str:
    value = json.dumps(
        host.fingerprint().to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _current_descriptor(store: SQLiteStore) -> tuple[str, int, str]:
    current = store.current()
    return (
        str(current["active_instance_id"]),
        int(current["current_revision"]),
        str(current["current_manifest_id"]),
    )


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _binding_for_slot(
    bindings: Mapping[str, Any], slot: int
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    subjects = bindings.get("subjects")
    checkpoints = bindings.get("checkpoints")
    if not isinstance(subjects, list) or not isinstance(checkpoints, Mapping):
        raise RunnerError("prepared run has no subject checkpoint bindings")
    selected = [item for item in subjects if isinstance(item, Mapping) and item.get("slot") == slot]
    if len(selected) != 1:
        raise RunnerError(f"subject slot is not uniquely bound: {slot}")
    start = selected[0].get("start")
    binding = checkpoints.get(start)
    if not isinstance(binding, Mapping):
        raise RunnerError(f"subject start checkpoint is not bound: {start!r}")
    return selected[0], binding


def _initial_revision(store: SQLiteStore, binding: Mapping[str, Any]) -> int:
    """Validate direct or forked checkpoint ancestry and return child head."""

    source_instance = binding.get("instance_id")
    source_revision = binding.get("revision")
    source_manifest = binding.get("manifest_id")
    checkpoint_id = binding.get("checkpoint_id")
    if not isinstance(source_instance, str) or not isinstance(source_revision, int):
        raise RunnerError("checkpoint binding lacks source lineage/revision")
    if not isinstance(source_manifest, str) or not isinstance(checkpoint_id, str):
        raise RunnerError("checkpoint binding lacks source manifest/checkpoint ID")
    active, revision, manifest = _current_descriptor(store)
    if active == source_instance:
        if revision < source_revision:
            raise RunnerError("subject writable store precedes its bound checkpoint")
        if revision == source_revision and manifest != source_manifest:
            raise RunnerError("subject writable store does not match its bound checkpoint")
        return source_revision
    row = store.connection.execute(
        "SELECT parent_instance_id,fork_checkpoint_id,fork_manifest_id "
        "FROM lineages WHERE instance_id=?",
        (active,),
    ).fetchone()
    if (
        row is None
        or row[0] != source_instance
        or row[1] != checkpoint_id
        or row[2] != source_manifest
    ):
        raise RunnerError("subject writable store is not forked from its bound checkpoint")
    if revision < 0:
        raise RunnerError("forked subject has an invalid revision")
    return 0


def _stream_seed(plan: Mapping[str, Any], domain: str, **coordinates: int) -> int:
    streams = plan.get("streams")
    if not isinstance(streams, list):
        raise RunnerError("prepared run has no resolved random streams")
    matches = [
        item
        for item in streams
        if isinstance(item, Mapping)
        and item.get("domain") == domain
        and all(item.get(key) == value for key, value in coordinates.items())
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("seed"), int):
        raise RunnerError(f"no unique prepared seed for {domain} {coordinates}")
    return int(matches[0]["seed"])


def _optional_stream_seed(plan: Mapping[str, Any], domain: str, **coordinates: int) -> int | None:
    """Use prepared seeds only when the bound host advertises seed control."""

    host = plan.get("host")
    if isinstance(host, Mapping) and host.get("sampling") == "provider_managed":
        return None
    return _stream_seed(plan, domain, **coordinates)


def _find_assignment(plan: Mapping[str, Any], slot: int) -> Mapping[str, Any]:
    assignments = plan.get("assignments")
    if not isinstance(assignments, list):
        raise RunnerError("prepared run has no assignments")
    matches = [
        item
        for item in assignments
        if isinstance(item, Mapping) and item.get("subject_slot") == slot
    ]
    if len(matches) != 1:
        raise RunnerError(f"subject slot is not uniquely assigned: {slot}")
    return matches[0]


def _validate_order(
    plan: Mapping[str, Any],
    slot: int,
    records: Sequence[Mapping[str, Any]],
    key: str,
) -> None:
    assignment = _find_assignment(plan, slot)
    expected = assignment.get(key)
    if not isinstance(expected, list):
        raise RunnerError(f"prepared plan has no {key} for subject {slot}")
    actual = [_record_id(record, ordinal) for ordinal, record in enumerate(records)]
    if actual != [str(item) for item in expected]:
        raise RunnerError(f"provided {key} does not match the prepared order for subject {slot}")


class IntegratedRunner:
    """Execute one prepared finite schedule while preserving P0.2/P0.3 boundaries."""

    def __init__(self, run_id: str, lab: str | Path, subjects: Mapping[int, SubjectExecution]):
        self.run_id = run_id
        self.artifacts = ArtifactStore(lab)
        self.run_path = self.artifacts.locate_run(run_id)
        if not self.artifacts.verify_run(self.run_path):
            raise RunnerError("prepared run failed artifact integrity verification")
        self.experiment = self.artifacts._read_json(self.run_path / "experiment.json")
        self.plan = self.artifacts._read_json(self.run_path / "study-plan.json")
        self.bindings = self.artifacts._read_json(self.run_path / "bindings.json")
        self.subjects = dict(subjects)
        # P0.3's immutable prepared-run tree is intentionally not rewritten by
        # execution.  The journal is therefore a sibling laboratory artifact;
        # publication remains atomic and restart state is durable without
        # weakening prepared-run verification.
        self.execution_dir = self.artifacts.root / "execution" / run_id
        self.execution_state_path = self.execution_dir / "state.json"
        self.execution_journal_path = self.execution_dir / "journal.jsonl"
        self._validate_host_bindings()

    def _read_execution_state(self) -> dict[str, Any]:
        if not self.execution_state_path.is_file():
            return {"status": "PREPARED", "run_id": self.run_id, "events": 0}
        try:
            value = json.loads(self.execution_state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RunnerError(f"execution state is unreadable: {exc}") from exc
        if not isinstance(value, dict) or value.get("run_id") != self.run_id:
            raise RunnerError("execution state has the wrong run identity")
        return value

    def _write_execution_state(self, status: str, **fields: Any) -> dict[str, Any]:
        self.execution_dir.mkdir(parents=True, exist_ok=True)
        value = self._read_execution_state()
        value.update(fields)
        value.update({"run_id": self.run_id, "status": status, "updated_at": _utc()})
        fd, temporary = tempfile.mkstemp(prefix=".state.", dir=self.execution_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.execution_state_path)
            with self.execution_state_path.open("rb") as handle:
                os.fsync(handle.fileno())
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return value

    def _append_execution_event(self, event: Mapping[str, Any]) -> None:
        self.execution_dir.mkdir(parents=True, exist_ok=True)
        record = {"run_id": self.run_id, "recorded_at": _utc(), **dict(event)}
        with self.execution_journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _journal_calls(self) -> int:
        return sum(
            int(item.get("model_calls", 0))
            for item in self._read_journal()
            if isinstance(item.get("model_calls", 0), int) and item.get("model_calls", 0) >= 0
        )

    def _read_journal(self) -> list[dict[str, Any]]:
        if not self.execution_journal_path.is_file():
            return []
        result: list[dict[str, Any]] = []
        for line in self.execution_journal_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RunnerError(f"execution journal is unreadable: {exc}") from exc
            if isinstance(record, Mapping):
                result.append(dict(record))
        return result

    def _assert_call_budget(self) -> None:
        budgets = self.plan.get("budgets", {})
        if not isinstance(budgets, Mapping):
            return
        declared_limits = budgets.get("hard_limits", budgets.get("limits", budgets))
        if not isinstance(declared_limits, Mapping):
            raise RunnerError("prepared plan has invalid hard budget limits")
        limit = declared_limits.get("max_model_calls")
        persisted = 0
        for subject in self.subjects.values():
            row = subject.store.connection.execute(
                "SELECT COUNT(*) FROM generation_records"
            ).fetchone()
            persisted += int(row[0]) if row is not None else 0
        consumed = max(self._journal_calls(), persisted)
        if isinstance(limit, int) and consumed + 1 > limit:
            self._write_execution_state("PAUSED", reason="max_model_calls")
            raise RunnerError("execution would exceed max_model_calls")

    def _validate_host_bindings(self) -> None:
        declared = self.plan.get("host")
        if not isinstance(declared, Mapping):
            raise RunnerError("prepared plan has no host binding")
        assignments = self.plan.get("assignments")
        planned_slots = {
            item.get("subject_slot")
            for item in assignments
            if isinstance(item, Mapping) and isinstance(item.get("subject_slot"), int)
        } if isinstance(assignments, list) else set()
        if planned_slots != set(self.subjects):
            raise RunnerError("subject mapping does not contain exactly the prepared subject slots")
        expected = declared.get("fingerprint_sha256")
        for slot, subject in self.subjects.items():
            if slot != subject.slot:
                raise RunnerError("subject mapping key does not match subject slot")
            actual = _host_digest(subject.host)
            if isinstance(expected, str) and actual != expected:
                raise RunnerError(f"subject host fingerprint drifted for slot {slot}")
            capabilities = declared.get("capabilities")
            if isinstance(capabilities, list):
                available = set(subject.host.capabilities().to_dict())
                missing = set(str(item) for item in capabilities) - available
                if missing:
                    raise RunnerError(
                        f"subject host lost capabilities: {', '.join(sorted(missing))}"
                    )

    def _subject_start(self, slot: int) -> int:
        subject = self.subjects.get(slot)
        if subject is None:
            raise RunnerError(f"no writable subject supplied for slot {slot}")
        _, binding = _binding_for_slot(self.bindings, slot)
        return _initial_revision(subject.store, binding)

    def execute_development(
        self,
        slot: int,
        records: Sequence[Mapping[str, Any]],
        *,
        stop_after: int | None = None,
    ) -> tuple[DevelopmentEvidence, ...]:
        """Execute records in prepared order, resuming accepted operations safely.

        ``stop_after`` is a test/control hook for a clean pause at an accepted
        episode boundary; it never interrupts a provider call.  An uncertain
        operation is terminal for this schedule and is never regenerated.
        """

        subject = self.subjects.get(slot)
        if subject is None:
            raise RunnerError(f"no writable subject supplied for slot {slot}")
        _validate_order(self.plan, slot, records, "development_order")
        start_revision = self._subject_start(slot)
        system, parameters, response_format = _experiment_parameters(self.experiment)
        controller_config = self.experiment.get("controller")
        if controller_config is not None and not isinstance(controller_config, Mapping):
            raise RunnerError("controller must be an object when provided")
        controller_mode = (
            str(controller_config.get("mode", "develop"))
            if isinstance(controller_config, Mapping)
            else "develop"
        )
        controller_memory = (
            str(controller_config.get("memory", "off"))
            if isinstance(controller_config, Mapping)
            else "off"
        )
        if controller_mode not in {"develop", "observe"}:
            raise RunnerError("runner development controller mode must be develop or observe")
        if controller_memory not in {"graph", "episodic", "off"}:
            raise RunnerError("runner controller memory must be graph, episodic, or off")
        evidence: list[DevelopmentEvidence] = []
        limit = len(records) if stop_after is None else max(0, min(stop_after, len(records)))
        accepted_count = 0
        for ordinal, record in enumerate(records[:limit]):
            record_messages = _messages(record)
            operation_id = _uuid_coordinate(
                self.run_id,
                "development",
                slot,
                ordinal,
                _record_id(record, ordinal),
            )
            if controller_config is not None:
                seed = _optional_stream_seed(
                    self.plan,
                    "development_generation",
                    subject_slot=slot,
                    episode=ordinal,
                )
                controller = ResponseController(
                    subject.store,
                    str(subject.store.current()["active_instance_id"]),
                    subject.host,
                )
                status_before = self._operation_status(subject.store, operation_id)
                try:
                    prepared_turn = controller.prepare(
                        TurnIntent(
                            current_input=record_messages[-1]["content"],
                            mode=controller_mode,
                            memory=controller_memory,
                            session_messages=tuple(record_messages[:-1]),
                            system=system,
                            parameters=parameters,
                            seed=seed,
                            response_format=response_format,
                            operation_id=operation_id,
                        )
                    )
                    if status_before in {None, "PREPARED"}:
                        self._assert_call_budget()
                    result = controller.execute(prepared_turn)
                except Exception as exc:
                    if self._operation_status(subject.store, operation_id) in {
                        "UNCERTAIN",
                        "STARTED",
                    }:
                        raise RunnerUncertain(
                            f"development controller operation is uncertain: {operation_id}"
                        ) from exc
                    raise RunnerError(
                        f"development controller operation failed: {operation_id}: {exc}"
                    ) from exc
                receipt = result.operation
                model_calls = int(status_before in {None, "PREPARED"})
            else:
                request = GenerationRequest(
                    record_messages,
                    system=system,
                    parameters=parameters,
                    seed=_optional_stream_seed(
                        self.plan,
                        "development_generation",
                        subject_slot=slot,
                        episode=ordinal,
                    ),
                    response_format=response_format,
                )
                try:
                    prepared = ContinuityService(
                        subject.store,
                        str(subject.store.current()["active_instance_id"]),
                        subject.host,
                    ).prepare_episode(request, operation_id=operation_id)
                except ContinuityError as exc:
                    raise RunnerError(
                        f"cannot prepare development operation {operation_id}: {exc}"
                    ) from exc
                if prepared.status == "UNCERTAIN" or prepared.status == "STARTED":
                    raise RunnerUncertain(
                        f"development operation is {prepared.status}: {operation_id}"
                    )
                model_calls = 0
                if prepared.status == "ACCEPTED":
                    # ``prepare_episode`` intentionally returns a compact accepted
                    # receipt.  Re-read the terminal operation through the
                    # idempotent accept path so the revision is available for
                    # restart validation.
                    receipt = ContinuityService(
                        subject.store,
                        str(subject.store.current()["active_instance_id"]),
                        subject.host,
                    ).accept_episode(operation_id)
                else:
                    service = ContinuityService(
                        subject.store,
                        str(subject.store.current()["active_instance_id"]),
                        subject.host,
                    )
                    if prepared.status == "PREPARED":
                        try:
                            self._assert_call_budget()
                            generated = service.generate_operation(operation_id)
                            model_calls = 1
                        except Exception as exc:
                            if self._operation_status(subject.store, operation_id) == "UNCERTAIN":
                                raise RunnerUncertain(
                                    f"development generation became UNCERTAIN: {operation_id}"
                                ) from exc
                            raise RunnerError(
                                f"development generation failed: {operation_id}: {exc}"
                            ) from exc
                    else:
                        generated = prepared
                    if generated.status == "UNCERTAIN" or generated.status == "STARTED":
                        raise RunnerUncertain(
                            f"development operation is {generated.status}: {operation_id}"
                        )
                    try:
                        receipt = service.accept_episode(operation_id)
                    except Exception as exc:
                        raise RunnerError(
                            f"development acceptance failed: {operation_id}: {exc}"
                        ) from exc
            if receipt.status == "ACCEPTED":
                expected_revision = start_revision + ordinal + 1
                if receipt.revision != expected_revision:
                    raise RunnerError(
                        f"development revision mismatch for {operation_id}: "
                        f"expected {expected_revision}, got {receipt.revision}"
                    )
                accepted_count += 1
            evidence.append(
                DevelopmentEvidence(
                    slot,
                    ordinal,
                    _record_id(record, ordinal),
                    operation_id,
                    receipt.status,
                    receipt.revision,
                    model_calls,
                )
            )
            self._append_execution_event(
                {
                    "kind": "development",
                    "subject_slot": slot,
                    "ordinal": ordinal,
                    "record_id": _record_id(record, ordinal),
                    "operation_id": operation_id,
                    "status": receipt.status,
                    "revision": receipt.revision,
                    "model_calls": model_calls,
                }
            )
        if stop_after is not None and limit < len(records):
            return tuple(evidence)
        # A resumed run must have exactly one accepted operation per record.
        if accepted_count != len(records):
            raise RunnerError("development schedule did not reach an accepted boundary")
        return tuple(evidence)

    @staticmethod
    def _operation_status(store: SQLiteStore, operation_id: str) -> str | None:
        row = store.connection.execute(
            "SELECT status FROM operations WHERE operation_id=?", (operation_id,)
        ).fetchone()
        return None if row is None else str(row[0])

    def create_boundary_checkpoint(
        self,
        slot: int,
        destination: str | Path,
        *,
        checkpoint_id: str | None = None,
    ) -> Path:
        """Publish a checkpoint of the subject's current accepted state."""

        subject = self.subjects.get(slot)
        if subject is None:
            raise RunnerError(f"no writable subject supplied for slot {slot}")
        destination = Path(destination)
        if destination.exists():
            if not destination.is_file() or destination.is_symlink():
                raise RunnerError("boundary checkpoint destination is not a regular file")
            try:
                with CheckpointReader(destination, checkpoint_id=checkpoint_id) as reader:
                    current = _current_descriptor(subject.store)
                    manifest = reader.manifest()
                    if (
                        manifest.get("source_instance_id") != current[0]
                        or manifest.get("source_revision") != current[1]
                        or manifest.get("manifest_id") != current[2]
                    ):
                        raise RunnerError("existing boundary checkpoint is stale")
            except RunnerError:
                raise
            except Exception as exc:
                raise RunnerError(f"existing boundary checkpoint is invalid: {exc}") from exc
            return destination
        checkpoint_id = checkpoint_id or _uuid_coordinate(
            self.run_id, "checkpoint", slot, destination.name
        )
        try:
            create_checkpoint(subject.store, destination, checkpoint_id)
        except (SnapshotError, OSError) as exc:
            raise RunnerError(f"boundary checkpoint publication failed: {exc}") from exc
        return destination

    def evaluate(
        self,
        slot: int,
        records: Sequence[Mapping[str, Any]],
        *,
        checkpoint: str | Path,
        repetition_count: int = 1,
        boundary: int = 0,
    ) -> tuple[EvaluationEvidence, ...]:
        """Evaluate fresh probes through a private read-only checkpoint view."""

        subject = self.subjects.get(slot)
        if subject is None:
            raise RunnerError(f"no writable subject supplied for slot {slot}")
        if repetition_count < 1:
            raise RunnerError("repetition_count must be positive")
        _validate_order(self.plan, slot, records, "evaluation_order")
        checkpoint_path = Path(checkpoint)
        if not checkpoint_path.is_file() or checkpoint_path.is_symlink():
            raise RunnerError("evaluation checkpoint must be a regular file")
        try:
            with CheckpointReader(checkpoint_path) as reader:
                manifest = reader.manifest()
                current = _current_descriptor(subject.store)
                if (
                    manifest.get("source_instance_id") != current[0]
                    or manifest.get("source_revision") != current[1]
                    or manifest.get("manifest_id") != current[2]
                ):
                    raise RunnerError("evaluation checkpoint is not the subject's current boundary")
        except RunnerError:
            raise
        except Exception as exc:
            raise RunnerError(f"evaluation checkpoint is invalid: {exc}") from exc
        system, parameters, response_format = _experiment_parameters(self.experiment)
        before_subject = _current_descriptor(subject.store)
        evidence: list[EvaluationEvidence] = []
        for probe, record in enumerate(records):
            for repetition in range(repetition_count):
                check_id = _uuid_coordinate(
                    self.run_id, "evaluation", slot, boundary, probe, repetition
                )
                seed = _optional_stream_seed(
                    self.plan,
                    "evaluation_generation",
                    subject_slot=slot,
                    probe=probe,
                    repetition=repetition,
                )
                with FrozenEvaluationView(checkpoint_path) as view:
                    request = {
                        "subject_slot": slot,
                        "probe_ordinal": probe,
                        "repetition": repetition,
                        "boundary": boundary,
                        "checkpoint_sha256": view.checkpoint_file_digest,
                        "seed": seed,
                        "messages_sha256": content_digest(list(_messages(record))),
                        "parameters_sha256": content_digest(parameters),
                        "system_sha256": content_digest(system) if system is not None else None,
                    }
                    started_or_result = self.artifacts.begin_check(self.run_id, check_id, request)
                    if started_or_result.get("status") == "RESULT":
                        output = started_or_result
                    elif started_or_result.get("status") != "STARTED":
                        raise RunnerUncertain(f"evaluation check is non-retryable: {check_id}")
                    else:
                        try:
                            self._assert_call_budget()
                            request_obj = GenerationRequest(
                                _messages(record),
                                system=system,
                                parameters=parameters,
                                seed=seed,
                                response_format=response_format,
                            )
                            # The host is intentionally called while the only
                            # state object in scope is the read-only view.  A
                            # provider-managed host receives no synthetic seed.
                            result = subject.host.generate(request_obj)
                            view.assert_unchanged()
                            output = self.artifacts.complete_check(
                                self.run_id,
                                check_id,
                                {
                                    "subject_slot": slot,
                                    "probe_ordinal": probe,
                                    "repetition": repetition,
                                    "boundary": boundary,
                                    "checkpoint_sha256": view.checkpoint_file_digest,
                                    "state_digest_before": view.state_digest,
                                    "state_digest_after": view.state_digest,
                                    "output": result.content,
                                    "model_id": result.model_id,
                                    "provider": result.provider,
                                    "seed": result.seed,
                                    "token_usage": (
                                        result.token_usage.__dict__ if result.token_usage else None
                                    ),
                                },
                            )
                            self._append_execution_event(
                                {
                                    "kind": "evaluation",
                                    "subject_slot": slot,
                                    "probe_ordinal": probe,
                                    "repetition": repetition,
                                    "check_id": check_id,
                                    "status": "RESULT",
                                    "model_calls": 1,
                                }
                            )
                        except Exception as exc:
                            try:
                                self.artifacts.mark_uncertain(
                                    self.run_id, check_id, type(exc).__name__
                                )
                            except ArtifactError:
                                pass
                            raise RunnerUncertain(
                                f"evaluation became UNCERTAIN: {check_id}"
                            ) from exc
                after_subject = _current_descriptor(subject.store)
                if after_subject != before_subject:
                    raise RunnerError("evaluation changed developmental lineage state")
                if not isinstance(output.get("output"), str):
                    raise RunnerError("evaluation receipt has no output")
                evidence.append(
                    EvaluationEvidence(
                        slot,
                        probe,
                        repetition,
                        check_id,
                        str(output.get("status")),
                        str(output["output"]),
                        str(output.get("checkpoint_sha256", "")),
                        str(output.get("state_digest_before", "")),
                        str(output.get("state_digest_after", "")),
                    )
                )
                if output.get("status") == "RESULT" and not any(
                    event.get("check_id") == check_id for event in self._read_journal()
                ):
                    self._append_execution_event(
                        {
                            "kind": "evaluation",
                            "subject_slot": slot,
                            "probe_ordinal": probe,
                            "repetition": repetition,
                            "check_id": check_id,
                            "status": "RESULT",
                            "model_calls": 0,
                        }
                    )
        return tuple(evidence)

    @staticmethod
    def _copy_private_snapshot(source: Path, destination: Path) -> Path:
        if destination.exists():
            if destination.is_symlink() or not destination.is_file():
                raise RunnerError("private evaluation snapshot is not a regular file")
            if file_digest(source) != file_digest(destination):
                raise RunnerError("private evaluation snapshot does not match boundary checkpoint")
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(source.read_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return destination

    def _checkpoint_artifact(
        self, subject: SubjectExecution, path: Path, label: str
    ) -> dict[str, Any]:
        """Validate and describe one terminal checkpoint artifact.

        A completed run records these descriptors in its execution state.  A
        later re-entry therefore checks the exact published files instead of
        merely checking that a path with a valid checkpoint happens to exist.
        """

        if not path.is_file() or path.is_symlink():
            raise RunnerError(f"terminal {label} checkpoint is missing or not a regular file")
        try:
            digest = file_digest(path)
            with CheckpointReader(path) as reader:
                manifest = reader.manifest()
            current = _current_descriptor(subject.store)
        except (
            ArtifactError,
            OSError,
            SchemaError,
            SnapshotError,
            ValueError,
            sqlite3.Error,
        ) as exc:
            raise RunnerError(f"terminal {label} checkpoint is invalid: {exc}") from exc
        if (
            manifest.get("source_instance_id") != current[0]
            or manifest.get("source_revision") != current[1]
            or manifest.get("manifest_id") != current[2]
        ):
            raise RunnerError(f"terminal {label} checkpoint is stale")
        checkpoint_id = manifest.get("checkpoint_id")
        if not isinstance(checkpoint_id, str):
            raise RunnerError(f"terminal {label} checkpoint has no checkpoint ID")
        return {
            "path": str(path.resolve()),
            "sha256": digest,
            "checkpoint_id": checkpoint_id,
            "source_instance_id": current[0],
            "source_revision": current[1],
            "manifest_id": current[2],
        }

    def _terminal_inventory_for_slot(
        self,
        slot: int,
        records: Sequence[Mapping[str, Any]],
        *,
        checkpoint: Path,
        private_snapshot: Path,
        repetition_count: int,
        boundary: int,
    ) -> dict[str, Any]:
        subject = self.subjects.get(slot)
        if subject is None:
            raise RunnerError(f"no writable subject supplied for slot {slot}")
        published = self._checkpoint_artifact(subject, checkpoint, "boundary")
        private = self._checkpoint_artifact(subject, private_snapshot, "private evaluation")
        if private["sha256"] != published["sha256"]:
            raise RunnerError("terminal private evaluation checkpoint differs from boundary")
        checks: list[dict[str, Any]] = []
        for probe, _record in enumerate(records):
            for repetition in range(repetition_count):
                check_id = _uuid_coordinate(
                    self.run_id, "evaluation", slot, boundary, probe, repetition
                )
                result_path = self.run_path / "evaluation" / check_id / "result.json"
                if not result_path.is_file() or result_path.is_symlink():
                    raise RunnerError(f"terminal evaluation result is missing: {check_id}")
                try:
                    result = self.artifacts._read_json(result_path)
                    if not ArtifactStore._verify_result(result, self.run_id, check_id):
                        raise RunnerError(f"terminal evaluation result is corrupt: {check_id}")
                except (ArtifactError, OSError, TypeError, ValueError) as exc:
                    raise RunnerError(f"terminal evaluation result is corrupt: {check_id}") from exc
                if (
                    result.get("subject_slot") != slot
                    or result.get("probe_ordinal") != probe
                    or result.get("repetition") != repetition
                    or result.get("boundary") != boundary
                    or result.get("checkpoint_sha256") != private["sha256"]
                    or not isinstance(result.get("output"), str)
                ):
                    raise RunnerError(f"terminal evaluation result has wrong binding: {check_id}")
                checks.append(
                    {
                        "check_id": check_id,
                        "path": str(result_path.resolve()),
                        "sha256": file_digest(result_path),
                    }
                )
        return {
            "subject_slot": slot,
            "boundary": boundary,
            "repetitions": repetition_count,
            "checkpoint": published,
            "private_snapshot": private,
            "checks": checks,
        }

    @staticmethod
    def _path_from_config(
        config: Mapping[str, Any], published: Path
    ) -> tuple[Path, Path]:
        checkpoint_value = config.get("checkpoint")
        if not isinstance(checkpoint_value, (str, Path)):
            raise RunnerError("evaluation checkpoint path is missing")
        checkpoint = Path(checkpoint_value)
        private_value = config.get("private_snapshot")
        private = (
            Path(private_value)
            if isinstance(private_value, (str, Path))
            else published.with_name(f"{published.stem}.evaluation.sqlite3")
        )
        return checkpoint, private

    def _validate_terminal_inventory(
        self,
        state: Mapping[str, Any],
        development: Mapping[int, Sequence[Mapping[str, Any]]],
        evaluations: Mapping[int, Mapping[str, Any]] | None,
    ) -> None:
        raw_inventory = state.get("terminal_artifacts")
        if not isinstance(raw_inventory, Mapping):
            raise RunnerError("completed execution has no terminal artifact inventory")
        raw_subjects = raw_inventory.get("subjects")
        if not isinstance(raw_subjects, list):
            raise RunnerError("completed execution has an invalid terminal artifact inventory")
        by_slot: dict[int, Mapping[str, Any]] = {}
        for item in raw_subjects:
            if not isinstance(item, Mapping) or isinstance(item.get("subject_slot"), bool):
                raise RunnerError("completed execution has an invalid terminal subject record")
            slot = item.get("subject_slot")
            if not isinstance(slot, int) or slot in by_slot:
                raise RunnerError("completed execution has duplicate terminal subject records")
            by_slot[slot] = item
        if set(by_slot) != set(self.subjects):
            raise RunnerError(
                "completed execution terminal subjects do not match supplied subjects"
            )

        for slot, item in by_slot.items():
            subject = self.subjects[slot]
            checkpoint_record = item.get("checkpoint")
            private_record = item.get("private_snapshot")
            if not isinstance(checkpoint_record, Mapping) or not isinstance(
                private_record, Mapping
            ):
                raise RunnerError(f"completed subject {slot} lacks terminal checkpoints")
            checkpoint_value = checkpoint_record.get("path")
            private_value = private_record.get("path")
            checkpoint_digest = checkpoint_record.get("sha256")
            private_digest = private_record.get("sha256")
            if not isinstance(checkpoint_value, str) or not isinstance(private_value, str):
                raise RunnerError(f"completed subject {slot} has invalid terminal checkpoint paths")
            if not isinstance(checkpoint_digest, str) or not isinstance(private_digest, str):
                raise RunnerError(
                    f"completed subject {slot} has invalid terminal checkpoint digests"
                )
            checkpoint = Path(checkpoint_value)
            private = Path(private_value)
            current_checkpoint = self._checkpoint_artifact(subject, checkpoint, "boundary")
            current_private = self._checkpoint_artifact(subject, private, "private evaluation")
            if current_checkpoint["sha256"] != checkpoint_digest:
                raise RunnerError(f"completed subject {slot} boundary checkpoint changed")
            if current_private["sha256"] != private_digest:
                raise RunnerError(f"completed subject {slot} private snapshot changed")
            for key in (
                "checkpoint_id",
                "source_instance_id",
                "source_revision",
                "manifest_id",
            ):
                if (
                    current_checkpoint.get(key) != checkpoint_record.get(key)
                    or current_private.get(key) != private_record.get(key)
                ):
                    raise RunnerError(f"completed subject {slot} checkpoint identity changed")
            if current_private["sha256"] != current_checkpoint["sha256"]:
                raise RunnerError(
                    f"completed subject {slot} private snapshot differs from boundary"
                )
            checks = item.get("checks")
            if not isinstance(checks, list):
                raise RunnerError(
                    f"completed subject {slot} has no terminal evaluation inventory"
                )
            for check in checks:
                if not isinstance(check, Mapping):
                    raise RunnerError(
                        f"completed subject {slot} has an invalid evaluation inventory"
                    )
                check_id = check.get("check_id")
                check_path = check.get("path")
                check_digest = check.get("sha256")
                if not isinstance(check_id, str) or not isinstance(check_path, str):
                    raise RunnerError(f"completed subject {slot} has an invalid evaluation record")
                if not isinstance(check_digest, str):
                    raise RunnerError(f"completed subject {slot} has an invalid evaluation digest")
                path = Path(check_path)
                expected_path = self.run_path / "evaluation" / check_id / "result.json"
                if path.resolve() != expected_path.resolve():
                    raise RunnerError(f"completed evaluation result path is not bound: {check_id}")
                if not path.is_file() or path.is_symlink():
                    raise RunnerError(f"terminal evaluation result is missing: {check_id}")
                try:
                    result = self.artifacts._read_json(path)
                    if not ArtifactStore._verify_result(result, self.run_id, check_id):
                        raise RunnerError(f"terminal evaluation result is corrupt: {check_id}")
                    digest = file_digest(path)
                except (ArtifactError, OSError, TypeError, ValueError) as exc:
                    raise RunnerError(f"terminal evaluation result is corrupt: {check_id}") from exc
                if digest != check_digest:
                    raise RunnerError(f"terminal evaluation result changed: {check_id}")

        if evaluations:
            for slot in sorted(set(development) | set(evaluations)):
                config = evaluations.get(slot)
                if not isinstance(config, Mapping):
                    raise RunnerError(
                        f"completed run has no evaluation schedule for subject {slot}"
                    )
                raw_records = config.get("records")
                if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
                    raise RunnerError(f"evaluation records are missing for subject {slot}")
                boundary_value = config.get("boundary", 0)
                if isinstance(boundary_value, bool) or not isinstance(boundary_value, int):
                    raise RunnerError("evaluation boundary must be an integer")
                repetitions = config.get("repetitions", 1)
                if isinstance(repetitions, bool) or not isinstance(repetitions, int):
                    raise RunnerError("evaluation repetitions must be an integer")
                checkpoint_value = config.get("checkpoint")
                if not isinstance(checkpoint_value, (str, Path)):
                    raise RunnerError("evaluation checkpoint path is missing")
                checkpoint, private = self._path_from_config(config, Path(checkpoint_value))
                item = by_slot.get(slot)
                if item is None:
                    raise RunnerError(f"completed run has no terminal artifacts for subject {slot}")
                recorded_checkpoint = item.get("checkpoint")
                recorded_private = item.get("private_snapshot")
                if not isinstance(recorded_checkpoint, Mapping) or not isinstance(
                    recorded_private, Mapping
                ):
                    raise RunnerError(f"completed subject {slot} lacks terminal checkpoints")
                if (
                    recorded_checkpoint.get("path") != str(checkpoint.resolve())
                    or recorded_private.get("path") != str(private.resolve())
                ):
                    raise RunnerError(f"completed subject {slot} terminal binding changed")
                expected_ids = {
                    _uuid_coordinate(
                        self.run_id,
                        "evaluation",
                        slot,
                        boundary_value,
                        probe,
                        repetition,
                    )
                    for probe, _record in enumerate(raw_records)
                    for repetition in range(repetitions)
                }
                recorded_checks = item.get("checks")
                actual_ids = {
                    check.get("check_id")
                    for check in recorded_checks
                    if isinstance(check, Mapping)
                } if isinstance(recorded_checks, list) else set()
                if actual_ids != expected_ids or item.get("boundary") != boundary_value:
                    raise RunnerError(f"completed subject {slot} evaluation schedule changed")
                if item.get("repetitions") != repetitions:
                    raise RunnerError(f"completed subject {slot} evaluation repetitions changed")

    def execute_run(
        self,
        development: Mapping[int, Sequence[Mapping[str, Any]]],
        evaluations: Mapping[int, Mapping[str, Any]] | None = None,
        *,
        pause_after: Mapping[int, int] | None = None,
    ) -> dict[str, Any]:
        """Execute or resume a finite prepared run.

        ``evaluations`` maps a subject slot to ``records``, ``checkpoint`` and
        optional ``private_snapshot``, ``repetitions``, and ``boundary``.  The
        boundary checkpoint and its private copy are created before probes and
        are then validated against the exact current subject descriptor.
        """

        state = self._read_execution_state()
        if state.get("status") == "COMPLETE":
            self._validate_terminal_inventory(state, development, evaluations)
            return state
        if set(development) != set(self.subjects):
            raise RunnerError(
                "development schedule does not contain exactly the prepared subject slots"
            )
        self._write_execution_state("EXECUTING", contract_sha256=self._run_contract_digest())
        evaluations = evaluations or {}
        try:
            terminal_subjects: list[dict[str, Any]] = []
            for slot in sorted(development):
                records = development[slot]
                stop = pause_after.get(slot) if pause_after is not None else None
                self.execute_development(slot, records, stop_after=stop)
                if stop is not None and stop < len(records):
                    return self._write_execution_state(
                        "PAUSED", paused_subject_slot=slot, paused_after=stop
                    )
                config = evaluations.get(slot)
                if config is None:
                    raise RunnerError(f"prepared run has no evaluation schedule for subject {slot}")
                raw_records = config.get("records")
                if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
                    raise RunnerError(f"evaluation records are missing for subject {slot}")
                boundary_value = config.get("boundary", 0)
                if isinstance(boundary_value, bool) or not isinstance(boundary_value, int):
                    raise RunnerError("evaluation boundary must be an integer")
                checkpoint_value = config.get("checkpoint")
                if not isinstance(checkpoint_value, (str, Path)):
                    raise RunnerError(f"evaluation checkpoint path is missing for subject {slot}")
                published = self.create_boundary_checkpoint(slot, checkpoint_value)
                _, private = self._path_from_config(config, published)
                private_path = self._copy_private_snapshot(published, private)
                self.evaluate(
                    slot,
                    [dict(item) for item in raw_records if isinstance(item, Mapping)],
                    checkpoint=private_path,
                    repetition_count=int(config.get("repetitions", 1)),
                    boundary=boundary_value,
                )
                terminal_inventory = self._terminal_inventory_for_slot(
                    slot,
                    [dict(item) for item in raw_records if isinstance(item, Mapping)],
                    checkpoint=published,
                    private_snapshot=private_path,
                    repetition_count=int(config.get("repetitions", 1)),
                    boundary=boundary_value,
                )
                terminal_subjects.append(terminal_inventory)
            final_inventory = {
                "schema_version": 1,
                "subjects": terminal_subjects,
            }
            final_state = dict(state)
            final_state["terminal_artifacts"] = final_inventory
            self._validate_terminal_inventory(final_state, development, evaluations)
            return self._write_execution_state(
                "COMPLETE",
                completed_at=_utc(),
                terminal_artifacts=final_inventory,
            )
        except RunnerUncertain as exc:
            self._write_execution_state("UNCERTAIN", reason=str(exc))
            raise
        except Exception as exc:
            self._write_execution_state("FAILED", reason=str(exc))
            raise

    def resume_run(
        self,
        development: Mapping[int, Sequence[Mapping[str, Any]]],
        evaluations: Mapping[int, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Resume from persisted P0.2/P0.3 operation and receipt state."""

        state = self._read_execution_state()
        if state.get("status") == "UNCERTAIN":
            raise RunnerUncertain(str(state.get("reason", "execution is UNCERTAIN")))
        return self.execute_run(development, evaluations)

    def _run_contract_digest(self) -> str:
        manifest = self.artifacts._read_json(self.run_path / "run-manifest.json")
        value = manifest.get("contract_sha256")
        if not isinstance(value, str):
            raise RunnerError("prepared run has no contract digest")
        return value


def execute_run(
    run_id: str,
    lab: str | Path,
    subjects: Mapping[int, SubjectExecution] | None = None,
    development: Mapping[int, Sequence[Mapping[str, Any]]] | None = None,
    evaluations: Mapping[int, Mapping[str, Any]] | None = None,
    *,
    host_name: str | None = None,
    pause_after: Mapping[int, int] | None = None,
) -> dict[str, Any]:
    """Public convenience wrapper for one integrated run."""
    if subjects is None or development is None:
        return _execute_prepared(run_id, lab, host_name=host_name, resume=False)
    return IntegratedRunner(run_id, lab, subjects).execute_run(
        development, evaluations, pause_after=pause_after
    )


def resume_run(
    run_id: str,
    lab: str | Path,
    subjects: Mapping[int, SubjectExecution] | None = None,
    development: Mapping[int, Sequence[Mapping[str, Any]]] | None = None,
    evaluations: Mapping[int, Mapping[str, Any]] | None = None,
    *,
    host_name: str | None = None,
) -> dict[str, Any]:
    """Public convenience wrapper for restart-safe continuation."""
    if subjects is None or development is None:
        return _execute_prepared(run_id, lab, host_name=host_name, resume=True)
    return IntegratedRunner(run_id, lab, subjects).resume_run(development, evaluations)


def _fixture_records(
    run_path: Path, experiment: Mapping[str, Any], plan: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    from .datasets import load_fixture_pack

    manifest = run_path / "inputs" / "fixture-pack" / "pack.json"
    reference = experiment.get("fixture_pack")
    expected = reference.get("sha256") if isinstance(reference, Mapping) else None
    if manifest.is_file():
        pack = load_fixture_pack(
            manifest, expected_manifest_digest=expected if isinstance(expected, str) else None
        )
        return {
            name: [
                {
                    "record_id": item.record_id,
                    "messages": [dict(message) for message in item.messages],
                    "scenario_family": item.scenario_family,
                    "max_output_tokens": item.max_output_tokens,
                }
                for item in records
            ]
            for name, records in pack.datasets.items()
        }
    datasets = experiment.get("datasets")
    if not isinstance(datasets, Mapping):
        raise RunnerError("prepared run has no embedded or copied fixture datasets")
    return {
        str(name): [dict(item) for item in records if isinstance(item, Mapping)]
        for name, records in datasets.items()
        if isinstance(records, list)
    }


def _execute_prepared(
    run_id: str, lab: str | Path, *, host_name: str | None, resume: bool
) -> dict[str, Any]:
    artifacts = ArtifactStore(lab)
    run_path = artifacts.locate_run(run_id)
    if not artifacts.verify_run(run_path):
        raise RunnerError("prepared run failed artifact integrity verification")
    experiment = artifacts._read_json(run_path / "experiment.json")
    plan = artifacts._read_json(run_path / "study-plan.json")
    bindings = artifacts._read_json(run_path / "bindings.json")
    from ..cli import _host

    declared_host = (
        experiment.get("host", {}).get("backend")
        if isinstance(experiment.get("host"), Mapping)
        else None
    )
    selected_host = host_name or (str(declared_host) if isinstance(declared_host, str) else "fake")
    host = _host(selected_host)
    records_by_name = _fixture_records(run_path, experiment, plan)
    execution_root = artifacts.root / "execution" / run_id
    subjects: dict[int, SubjectExecution] = {}
    opened: list[SQLiteStore] = []
    try:
        raw_subjects = bindings.get("subjects")
        if not isinstance(raw_subjects, list):
            raise RunnerError("prepared run has no subject bindings")
        for item in raw_subjects:
            if not isinstance(item, Mapping) or not isinstance(item.get("slot"), int):
                raise RunnerError("invalid subject binding")
            slot = int(item["slot"])
            _, binding = _binding_for_slot(bindings, slot)
            snapshot_name = binding.get("snapshot_path")
            if not isinstance(snapshot_name, str):
                raise RunnerError("subject checkpoint snapshot is missing")
            snapshot = run_path / "snapshots" / snapshot_name
            if not snapshot.is_file() or snapshot.is_symlink():
                raise RunnerError(f"subject checkpoint snapshot is missing: {snapshot}")
            destination = execution_root / "subjects" / f"slot-{slot}.sqlite3"
            if not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                child_id = _uuid_coordinate(run_id, "subject", slot)
                fork_from_checkpoint(snapshot, destination, child_id=child_id)
            store = SQLiteStore(destination)
            opened.append(store)
            subjects[slot] = SubjectExecution(slot, store, host)
        runner = IntegratedRunner(run_id, lab, subjects)
        development: dict[int, list[dict[str, Any]]] = {}
        evaluations: dict[int, dict[str, Any]] = {}
        evaluation_cfg = experiment.get("evaluation", {})
        repetitions = (
            int(evaluation_cfg.get("repetitions", 1)) if isinstance(evaluation_cfg, Mapping) else 1
        )
        for slot in sorted(subjects):
            assignment = _find_assignment(plan, slot)
            dev_name = assignment.get("development_dataset")
            eval_name = assignment.get("evaluation_dataset")
            if not isinstance(dev_name, str) or not isinstance(eval_name, str):
                raise RunnerError(f"subject {slot} has incomplete dataset assignment")
            development[slot] = records_by_name.get(dev_name, [])
            evaluations[slot] = {
                "records": records_by_name.get(eval_name, []),
                "checkpoint": execution_root / "boundaries" / f"slot-{slot}.sqlite3",
                "private_snapshot": execution_root / "evaluation" / f"slot-{slot}.sqlite3",
                "repetitions": repetitions,
            }
        if resume:
            for subject in subjects.values():
                ContinuityService(
                    subject.store,
                    str(subject.store.current()["active_instance_id"]),
                    subject.host,
                ).recover_orphaned_operations()
            return runner.resume_run(development, evaluations)
        return runner.execute_run(development, evaluations)
    finally:
        for store in opened:
            store.close()


__all__ = [
    "DevelopmentEvidence",
    "EvaluationEvidence",
    "IntegratedRunner",
    "execute_run",
    "resume_run",
    "RunnerError",
    "RunnerUncertain",
    "SubjectExecution",
]
