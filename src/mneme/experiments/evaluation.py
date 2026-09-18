"""The bounded P0.3 frozen-checkpoint evaluation primitive.

Evaluation uses a checkpoint reader and writes only laboratory artifacts.  It
does not expose a lineage store, continuity service, or acceptance operation.
The primitive intentionally supports the built-in FakeHost only; complete
development/evaluation execution is a P0.4 concern.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..contracts import GenerationRequest, GenerationResult
from ..hosts.fake import FakeHost
from ..state.reader import CheckpointReader
from .artifacts import ArtifactError, ArtifactStore, content_digest, file_digest


class EvaluationError(RuntimeError):
    """The frozen evaluation boundary cannot safely execute a probe."""


class FrozenEvaluationView:
    """Read-only checkpoint view used by the P0.3 isolation check."""

    def __init__(self, checkpoint: str | Path, checkpoint_id: str | None = None) -> None:
        self.path = Path(checkpoint)
        self._reader = CheckpointReader(self.path, checkpoint_id)
        self._before_file_digest = file_digest(self.path)
        self._before_state_digest = self._reader.state_digest()

    def close(self) -> None:
        self._reader.close()

    def __enter__(self) -> FrozenEvaluationView:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def checkpoint_file_digest(self) -> str:
        return self._before_file_digest

    @property
    def state_digest(self) -> str:
        return self._before_state_digest

    def manifest(self) -> dict[str, Any]:
        return copy.deepcopy(self._reader.manifest())

    def episodes(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._reader.episodes())

    def history(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._reader.history())

    def generate(
        self,
        host: FakeHost,
        messages: Sequence[Mapping[str, str]],
        *,
        seed: int | None,
        parameters: Mapping[str, Any] | None = None,
        system: str | None = None,
    ) -> GenerationResult:
        """Generate one fresh probe without any developmental write path."""

        if not isinstance(host, FakeHost):
            raise EvaluationError("P0.3 frozen evaluation supports FakeHost only")
        normalized = tuple(
            {"role": str(item["role"]), "content": str(item["content"])}
            for item in messages
        )
        request = GenerationRequest(
            normalized,
            system=system,
            parameters=dict(parameters or {}),
            seed=seed,
        )
        result = host.generate(request)
        self.assert_unchanged()
        return result

    def assert_unchanged(self) -> None:
        after_file = file_digest(self.path)
        after_state = self._reader.state_digest()
        if after_file != self._before_file_digest or after_state != self._before_state_digest:
            raise EvaluationError("evaluation changed the frozen checkpoint")


def run_isolation_check(
    *,
    run_id: str,
    lab: str | Path,
    check_id: str,
    checkpoint: str | Path,
    host: FakeHost,
    messages: Sequence[Mapping[str, str]],
    seed: int | None,
    subject_slot: int,
    probe_ordinal: int,
    repetition: int,
    parameters: Mapping[str, Any] | None = None,
    system: str | None = None,
) -> dict[str, Any]:
    """Run one idempotent FakeHost probe and publish a separate receipt."""

    artifact_store = ArtifactStore(lab)
    run_path = artifact_store.locate_run(run_id)
    bindings = artifact_store._read_json(run_path / "bindings.json")
    expected_checkpoint_id: str | None = None
    expected_snapshot: Path | None = None
    if isinstance(bindings.get("checkpoint_id"), str):
        expected_checkpoint_id = bindings["checkpoint_id"]
    checkpoint_bindings = bindings.get("checkpoints", {})
    if isinstance(checkpoint_bindings, Mapping):
        subjects = bindings.get("subjects")
        if isinstance(subjects, list):
            selected = [
                subject
                for subject in subjects
                if isinstance(subject, Mapping) and subject.get("slot") == subject_slot
            ]
            if len(selected) != 1:
                raise EvaluationError(f"subject slot is not uniquely bound: {subject_slot}")
            start = selected[0].get("start")
            selected_binding = checkpoint_bindings.get(start)
            if not isinstance(selected_binding, Mapping):
                raise EvaluationError(f"subject start checkpoint is not bound: {start!r}")
            checkpoint_id = selected_binding.get("checkpoint_id")
            if not isinstance(checkpoint_id, str):
                raise EvaluationError("subject checkpoint binding has no checkpoint_id")
            expected_checkpoint_id = checkpoint_id
            snapshot_name = selected_binding.get("snapshot_path")
            if isinstance(snapshot_name, str):
                expected_snapshot = run_path / "snapshots" / snapshot_name
        elif expected_checkpoint_id is None:
            ids = {
                binding.get("checkpoint_id")
                for binding in checkpoint_bindings.values()
                if isinstance(binding, Mapping) and isinstance(binding.get("checkpoint_id"), str)
            }
            if len(ids) == 1:
                expected_checkpoint_id = next(iter(ids))
    if expected_snapshot is not None:
        if not expected_snapshot.is_file() or expected_snapshot.is_symlink():
            raise EvaluationError("bound evaluation snapshot is missing")
        if Path(checkpoint).resolve() != expected_snapshot.resolve():
            raise EvaluationError("evaluation checkpoint is not the subject's private snapshot")
    if not artifact_store.verify_run(run_path):
        raise EvaluationError("prepared run failed artifact integrity verification")
    check_path = run_path / "evaluation" / check_id
    normalized_messages = [
        {"role": str(item["role"]), "content": str(item["content"])} for item in messages
    ]
    request = {
        "subject_slot": subject_slot,
        "probe_ordinal": probe_ordinal,
        "repetition": repetition,
        "checkpoint_sha256": file_digest(Path(checkpoint)),
        "seed": seed,
        "messages_sha256": content_digest(normalized_messages),
        "parameters_sha256": content_digest(dict(parameters or {})),
        "system_sha256": content_digest(system) if system is not None else None,
    }
    if (check_path / "started.json").exists():
        started = ArtifactStore._read_json(check_path / "started.json")
        if started.get("request_sha256") != content_digest(request):
            raise EvaluationError("check ID already exists with conflicting intent")
        if (check_path / "result.json").exists():
            completed = ArtifactStore._read_json(check_path / "result.json")
            if not ArtifactStore._verify_result(completed):
                raise EvaluationError("completed check receipt is malformed")
            return completed
        if (check_path / "uncertain.json").exists():
            raise EvaluationError("existing check is UNCERTAIN; use a new check ID")
        artifact_store.mark_uncertain(run_id, check_id, "recovery requires a new check ID")
        raise EvaluationError("existing non-terminal check is UNCERTAIN; use a new check ID")

    artifact_store.begin_check(run_id, check_id, request)
    try:
        with FrozenEvaluationView(checkpoint) as view:
            checkpoint_identity = str(view.manifest()["checkpoint_id"])
            if expected_checkpoint_id is not None and checkpoint_identity != expected_checkpoint_id:
                raise EvaluationError("evaluation checkpoint is not bound to the prepared run")
            before_file = view.checkpoint_file_digest
            before_state = view.state_digest
            result = view.generate(
                host,
                messages,
                seed=seed,
                parameters=parameters,
                system=system,
            )
            view.assert_unchanged()
            output = {
                "subject_slot": subject_slot,
                "probe_ordinal": probe_ordinal,
                "repetition": repetition,
                "checkpoint_sha256": before_file,
                "state_digest_before": before_state,
                "state_digest_after": view.state_digest,
                "output": result.content,
                "model_id": result.model_id,
                "provider": result.provider,
                "seed": result.seed,
                "token_usage": (
                    result.token_usage.__dict__ if result.token_usage is not None else None
                ),
            }
        completed_result = artifact_store.complete_check(run_id, check_id, output)
        return {str(key): value for key, value in completed_result.items()}
    except Exception as exc:
        try:
            artifact_store.mark_uncertain(run_id, check_id, type(exc).__name__)
        except ArtifactError:
            pass
        raise
