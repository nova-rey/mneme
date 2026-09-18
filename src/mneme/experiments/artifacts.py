"""Durable, filesystem-only records for prepared P0.3 experiment runs.

The lineage databases remain the authority for developmental state.  This module
only publishes immutable laboratory records and evaluation receipts outside those
databases.  It deliberately does not execute a developmental schedule.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ArtifactError(RuntimeError):
    """Raised when a laboratory artifact cannot be safely read or published."""


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def canonical_json(value: Any) -> bytes:
    """Return the canonical bytes used for manifests and intent comparisons."""

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ArtifactError(f"value is not canonical JSON: {exc}") from exc


def content_digest(value: Any) -> str:
    """Hash canonical JSON content and return a lowercase SHA-256 digest."""

    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ArtifactError(f"cannot hash artifact {path}: {exc}") from exc
    return digest.hexdigest()


def _component(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_COMPONENT.fullmatch(value):
        raise ArtifactError(f"invalid {label}: {value!r}")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_json(value) + b"\n")


@dataclass(frozen=True)
class PublishedRun:
    """The immutable identity of a prepared run."""

    path: Path
    experiment_name: str
    contract_revision: int
    contract_sha256: str
    run_id: str


class ArtifactStore:
    """Publish and inspect P0.3 runs under one local laboratory root.

    All publication is same-filesystem and uses a temporary sibling directory
    followed by an atomic directory rename.  A lock serializes writers within a
    process and, on POSIX hosts, across processes.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.experiments = self.root / "experiments"
        self._lock_path = self.root / ".artifact-writer.lock"

    @contextmanager
    def _writer(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        handle = self._lock_path.open("a+b")
        try:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except ImportError:
                # Windows has no fcntl; the atomic rename still prevents a
                # partially published directory, while callers should retain
                # the one-writer contract.
                pass
            yield
        finally:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass
            handle.close()

    def run_path(self, experiment_name: str, contract_revision: int, run_id: str) -> Path:
        name = _component(experiment_name, "experiment name")
        run = _component(run_id, "run ID")
        if isinstance(contract_revision, bool) or not isinstance(contract_revision, int):
            raise ArtifactError("contract revision must be an integer")
        if contract_revision < 0:
            raise ArtifactError("contract revision must be nonnegative")
        return self.experiments / name / "revisions" / str(contract_revision) / "runs" / run

    def locate_run(self, run_id: str) -> Path:
        _component(run_id, "run ID")
        matches = list(self.experiments.glob(f"*/revisions/*/runs/{run_id}"))
        if len(matches) != 1:
            if not matches:
                raise ArtifactError(f"unknown experiment run: {run_id}")
            raise ArtifactError(f"run ID is ambiguous across experiment series: {run_id}")
        return matches[0]

    def publish_run(
        self,
        *,
        experiment: Mapping[str, Any],
        preflight: Mapping[str, Any],
        study_plan: Mapping[str, Any],
        bindings: Mapping[str, Any],
        run_id: str,
        inputs: Mapping[str, bytes] | None = None,
        snapshots: Mapping[str, bytes] | None = None,
    ) -> PublishedRun:
        """Atomically publish a prepared run, idempotently by run intent.

        ``experiment`` must carry ``name`` and ``contract_revision``.  Its
        canonical content digest is calculated from the supplied contract; any
        supplied ``contract_sha256`` must match it.  Payload files are bytes so
        callers cannot accidentally copy a mutable source after publication.
        """

        name = experiment.get("name")
        revision = experiment.get("contract_revision")
        if not isinstance(name, str) or not name:
            raise ArtifactError("experiment requires a non-empty name")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ArtifactError("experiment contract_revision must be a nonnegative integer")
        supplied_digest = experiment.get("contract_sha256")
        contract = {key: value for key, value in experiment.items() if key != "contract_sha256"}
        digest = content_digest(contract)
        if supplied_digest is not None and supplied_digest != digest:
            raise ArtifactError("experiment contract_sha256 does not match canonical contents")
        target = self.run_path(name, revision, run_id)
        payloads = {
            "inputs": self._payload_digests(inputs),
            "snapshots": self._payload_digests(snapshots),
        }
        manifest = {
            "schema_version": 1,
            "status": "PREPARED",
            "experiment_name": name,
            "contract_revision": revision,
            "contract_sha256": digest,
            "run_id": run_id,
            "experiment": contract,
            "preflight_sha256": content_digest(preflight),
            "study_plan_sha256": content_digest(study_plan),
            "bindings_sha256": content_digest(bindings),
            "payloads": payloads,
        }
        intent = content_digest(manifest)
        manifest["publication_intent_sha256"] = intent
        with self._writer():
            if target.exists():
                existing = self._read_json(target / "run-manifest.json")
                expected_intent = intent
                # A retry from an older caller may omit payload arguments.  In
                # that case preserve the already-published payload binding;
                # explicitly supplied empty mappings still mean "no payload".
                if inputs is None and snapshots is None and isinstance(
                    existing.get("payloads"), Mapping
                ):
                    retry_manifest = dict(manifest)
                    retry_manifest.pop("publication_intent_sha256", None)
                    retry_manifest["payloads"] = existing["payloads"]
                    expected_intent = content_digest(retry_manifest)
                if existing.get("publication_intent_sha256") != expected_intent:
                    raise ArtifactError(f"run ID already exists with conflicting intent: {run_id}")
                if not self.verify_run(target):
                    raise ArtifactError(f"existing run failed integrity verification: {run_id}")
                return PublishedRun(target, name, revision, digest, run_id)
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=target.parent))
            try:
                _write_json(stage / "experiment.json", contract)
                _write_json(stage / "preflight.json", preflight)
                _write_json(stage / "study-plan.json", study_plan)
                _write_json(stage / "bindings.json", bindings)
                _write_json(stage / "run-manifest.json", manifest)
                if inputs:
                    self._write_bytes(stage / "inputs", inputs)
                if snapshots:
                    self._write_bytes(stage / "snapshots", snapshots)
                self._sync_tree(stage)
                os.replace(stage, target)
                self._sync_directory(target.parent)
            except Exception:
                self._remove_tree(stage)
                raise
        return PublishedRun(target, name, revision, digest, run_id)

    def begin_check(
        self, run_id: str, check_id: str, request: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        run = self.locate_run(run_id)
        check = _component(check_id, "check ID")
        directory = run / "evaluation" / check
        started = {
            "schema_version": 1,
            "status": "STARTED",
            "run_id": run_id,
            "check_id": check,
            "request": dict(request),
            "request_sha256": content_digest(request),
        }
        with self._writer():
            result = directory / "result.json"
            if result.exists():
                started_path = directory / "started.json"
                if not started_path.exists():
                    raise ArtifactError(f"check result has no STARTED record: {check_id}")
                prior_started = self._read_json(started_path)
                if not self._verify_started(prior_started):
                    raise ArtifactError(
                        f"check STARTED record failed integrity verification: {check_id}"
                    )
                if prior_started.get("request_sha256") != started["request_sha256"]:
                    raise ArtifactError(
                        f"check ID already exists with conflicting intent: {check_id}"
                    )
                prior_result = self._read_json(result)
                if not self._verify_result(prior_result):
                    raise ArtifactError(
                        f"check RESULT record failed integrity verification: {check_id}"
                    )
                return prior_result
            if (directory / "uncertain.json").exists():
                raise ArtifactError(f"check is UNCERTAIN and requires a new check ID: {check_id}")
            directory.mkdir(parents=True, exist_ok=True)
            if (directory / "started.json").exists():
                prior = self._read_json(directory / "started.json")
                if not self._verify_started(prior):
                    raise ArtifactError(
                        f"check STARTED record failed integrity verification: {check_id}"
                    )
                if prior.get("request_sha256") != started["request_sha256"]:
                    raise ArtifactError(
                        f"check ID already exists with conflicting intent: {check_id}"
                    )
                return prior
            _write_json(directory / "started.json", started)
            self._sync_file(directory / "started.json")
        return started

    def complete_check(
        self, run_id: str, check_id: str, result: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        run = self.locate_run(run_id)
        directory = run / "evaluation" / _component(check_id, "check ID")
        with self._writer():
            started_path = directory / "started.json"
            if not started_path.exists():
                raise ArtifactError("cannot complete a check that was not started")
            if (directory / "uncertain.json").exists():
                raise ArtifactError("cannot complete an uncertain check")
            output = dict(result)
            output.update(
                {"schema_version": 1, "status": "RESULT", "run_id": run_id, "check_id": check_id}
            )
            result_path = directory / "result.json"
            if result_path.exists():
                prior = self._read_json(result_path)
                if not self._verify_result(prior):
                    raise ArtifactError("existing check result conflicts with retry")
                return prior
            output["result_sha256"] = content_digest(output)
            _write_json(result_path, output)
            self._sync_file(result_path)
            return output

    def mark_uncertain(self, run_id: str, check_id: str, reason: str) -> Mapping[str, Any]:
        run = self.locate_run(run_id)
        directory = run / "evaluation" / _component(check_id, "check ID")
        with self._writer():
            if (directory / "result.json").exists():
                return self._read_json(directory / "result.json")
            if not (directory / "started.json").exists():
                raise ArtifactError("cannot mark an unstarted check uncertain")
            output = {
                "schema_version": 1,
                "status": "UNCERTAIN",
                "run_id": run_id,
                "check_id": check_id,
                "reason": reason,
            }
            path = directory / "uncertain.json"
            if path.exists():
                prior = self._read_json(path)
                if not self._verify_uncertain(prior):
                    raise ArtifactError(
                        "existing uncertain check receipt failed integrity verification"
                    )
                return prior
            output["receipt_sha256"] = content_digest(output)
            _write_json(path, output)
            self._sync_file(path)
            return output

    def inspect_run(self, run_id: str, verify: bool = False) -> dict[str, Any]:
        path = self.locate_run(run_id)
        manifest = self._read_json(path / "run-manifest.json")
        checks: list[dict[str, Any]] = []
        evaluation = path / "evaluation"
        if evaluation.is_dir():
            for check_dir in sorted(p for p in evaluation.iterdir() if p.is_dir()):
                for filename in ("result.json", "uncertain.json", "started.json"):
                    candidate = check_dir / filename
                    if candidate.exists():
                        checks.append(self._read_json(candidate))
                        break
        output: dict[str, Any] = {"path": str(path), "manifest": manifest, "checks": checks}
        if verify:
            output["verified"] = self.verify_run(path)
        return output

    def verify_run(self, path: Path) -> bool:
        """Verify the complete published run tree and receipt integrity hashes."""
        try:
            manifest = self._read_json(path / "run-manifest.json")
            intent = manifest.get("publication_intent_sha256")
            if not isinstance(intent, str) or intent != content_digest(
                {
                    key: value
                    for key, value in manifest.items()
                    if key != "publication_intent_sha256"
                }
            ):
                return False
            required = {
                "experiment.json": manifest["contract_sha256"],
                "preflight.json": manifest["preflight_sha256"],
                "study-plan.json": manifest["study_plan_sha256"],
                "bindings.json": manifest["bindings_sha256"],
            }
            for filename, digest in required.items():
                if not isinstance(digest, str):
                    return False
                if content_digest(self._read_json(path / filename)) != digest:
                    return False

            payloads = manifest.get("payloads")
            if not isinstance(payloads, Mapping) or set(payloads) != {"inputs", "snapshots"}:
                return False
            for category in ("inputs", "snapshots"):
                expected = payloads[category]
                if not isinstance(expected, Mapping):
                    return False
                root = path / category
                actual: dict[str, str] = {}
                if root.exists():
                    if not root.is_dir() or root.is_symlink():
                        return False
                    for candidate in root.rglob("*"):
                        if candidate.is_symlink():
                            return False
                        if candidate.is_file():
                            actual[str(candidate.relative_to(root))] = file_digest(candidate)
                if dict(expected) != actual:
                    return False

            evaluation = path / "evaluation"
            if evaluation.exists():
                if not evaluation.is_dir() or evaluation.is_symlink():
                    return False
                for check_dir in evaluation.iterdir():
                    if not check_dir.is_dir() or check_dir.is_symlink():
                        return False
                    names = {item.name for item in check_dir.iterdir()}
                    if not names <= {"started.json", "result.json", "uncertain.json"}:
                        return False
                    started_path = check_dir / "started.json"
                    result_path = check_dir / "result.json"
                    uncertain_path = check_dir / "uncertain.json"
                    if started_path.exists() and not self._verify_started(
                        self._read_json(started_path)
                    ):
                        return False
                    if result_path.exists():
                        if not started_path.exists() or not self._verify_result(
                            self._read_json(result_path)
                        ):
                            return False
                    if uncertain_path.exists():
                        if (
                            result_path.exists()
                            or not started_path.exists()
                            or not self._verify_uncertain(self._read_json(uncertain_path))
                        ):
                            return False

            allowed = {
                "experiment.json",
                "preflight.json",
                "study-plan.json",
                "bindings.json",
                "run-manifest.json",
                "inputs",
                "snapshots",
                "evaluation",
            }
            if {item.name for item in path.iterdir()} - allowed:
                return False
            return True
        except (ArtifactError, KeyError, OSError, TypeError, ValueError):
            return False

    @staticmethod
    def _verify_started(value: Mapping[str, Any]) -> bool:
        request = value.get("request")
        return (
            value.get("schema_version") == 1
            and value.get("status") == "STARTED"
            and isinstance(request, Mapping)
            and value.get("request_sha256") == content_digest(request)
        )

    @staticmethod
    def _verify_result(value: Mapping[str, Any]) -> bool:
        return (
            value.get("schema_version") == 1
            and value.get("status") == "RESULT"
            and isinstance(value.get("result_sha256"), str)
            and value.get("result_sha256")
            == content_digest(
                {key: item for key, item in value.items() if key != "result_sha256"}
            )
        )

    @staticmethod
    def _verify_uncertain(value: Mapping[str, Any]) -> bool:
        return (
            value.get("schema_version") == 1
            and value.get("status") == "UNCERTAIN"
            and isinstance(value.get("receipt_sha256"), str)
            and value.get("receipt_sha256")
            == content_digest(
                {key: item for key, item in value.items() if key != "receipt_sha256"}
            )
        )

    @staticmethod
    def _payload_digests(files: Mapping[str, bytes] | None) -> dict[str, str]:
        if not files:
            return {}
        result: dict[str, str] = {}
        for relative, content in files.items():
            if not isinstance(content, bytes):
                raise ArtifactError(f"artifact payload must be bytes: {relative}")
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ArtifactError(f"artifact path escapes its directory: {relative}")
            result[str(relative_path)] = hashlib.sha256(content).hexdigest()
        return result

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid artifact JSON {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise ArtifactError(f"artifact must contain a JSON object: {path}")
        return value

    @staticmethod
    def _write_bytes(root: Path, files: Mapping[str, bytes]) -> None:
        for relative, content in files.items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ArtifactError(f"artifact path escapes its directory: {relative}")
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    @staticmethod
    def _sync_file(path: Path) -> None:
        with path.open("rb") as handle:
            os.fsync(handle.fileno())
        ArtifactStore._sync_directory(path.parent)

    @staticmethod
    def _sync_tree(root: Path) -> None:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                ArtifactStore._sync_file(path)
        ArtifactStore._sync_directory(root)

    @staticmethod
    def _sync_directory(path: Path) -> None:
        try:
            fd = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _remove_tree(path: Path) -> None:
        import shutil

        shutil.rmtree(path, ignore_errors=True)
