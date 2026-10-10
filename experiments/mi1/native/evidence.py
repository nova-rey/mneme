"""Atomic, append-only per-call evidence for isolated MI1 runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, cast

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        try:
            temp.unlink(missing_ok=True)
        finally:
            raise


def atomic_json_write(path: Path, value: Any) -> None:
    """Publish compact derived JSON with the same fsync-and-replace contract."""
    _atomic_write(path, _canonical(value))


class EvidenceJournal:
    """Persist each attempt before inference and each result before proceeding.

    An attempt is a single model call. Failed calls remain counted and stored.
    Request and outcome artifacts are immutable; only the small index is replaced.
    """

    def __init__(self, root: Path, *, hard_call_limit: int = 800):
        if hard_call_limit <= 0:
            raise ValueError("hard_call_limit must be positive")
        self.root = root
        self.attempts = root / "attempts"
        self.hard_call_limit = hard_call_limit
        self.attempts.mkdir(parents=True, exist_ok=True)
        self._index_path = root / "index.json"
        if not self._index_path.exists():
            _atomic_write(
                self._index_path,
                _canonical(
                    {"schema_version": 1, "hard_call_limit": hard_call_limit, "attempts": []}
                ),
            )
        self._recover_staged_attempt_files()
        self._recover_unindexed_files(self._check_index())

    def _recover_staged_attempt_files(self) -> None:
        """Promote a complete fsynced attempt temp left before atomic rename."""
        endings = (".request.json.", ".complete.json.", ".failed.json.")
        for staged in self.attempts.glob(".*.tmp"):
            stem = staged.name[1 : -len(".tmp")]
            marker = next((ending for ending in endings if ending in stem), None)
            if marker is None:
                raise ValueError(f"unrecognized staged evidence file: {staged.name}")
            attempt_id = stem.split(marker, 1)[0]
            if not _SAFE_ID.fullmatch(attempt_id):
                raise ValueError(f"invalid staged attempt ID: {staged.name}")
            suffix = marker[:-1]
            target = self.attempts / f"{attempt_id}{suffix}"
            value = json.loads(staged.read_text(encoding="utf-8"))
            if value.get("attempt_id") != attempt_id:
                raise ValueError(f"staged evidence identity mismatch: {staged.name}")
            if suffix != ".request.json":
                expected_status = "COMPLETE" if suffix == ".complete.json" else "FAILED"
                if value.get("status") != expected_status:
                    raise ValueError(f"staged evidence status mismatch: {staged.name}")
                request_path = self.attempts / f"{attempt_id}.request.json"
                if not request_path.exists():
                    raise ValueError(f"staged outcome has no request: {staged.name}")
            if target.exists():
                if target.read_bytes() != staged.read_bytes():
                    raise ValueError(
                        f"staged evidence conflicts with published file: {target.name}"
                    )
                staged.unlink()
                continue
            os.replace(staged, target)
            directory = os.open(self.attempts, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)

    def _check_index(self) -> dict[str, Any]:
        index = json.loads(self._index_path.read_text(encoding="utf-8"))
        if index.get("schema_version") != 1 or index.get("hard_call_limit") != self.hard_call_limit:
            raise ValueError("evidence journal index contract mismatch")
        seen: set[str] = set()
        for row in index.get("attempts", []):
            attempt_id = row.get("attempt_id")
            if (
                not isinstance(attempt_id, str)
                or not _SAFE_ID.fullmatch(attempt_id)
                or attempt_id in seen
            ):
                raise ValueError("invalid or duplicate attempt ID in evidence index")
            seen.add(attempt_id)
            for field in ("request_file", "outcome_file"):
                file_name = row.get(field)
                digest_field = "request_sha256" if field == "request_file" else "outcome_sha256"
                if file_name is None:
                    continue
                expected_suffix = (
                    ".request.json"
                    if field == "request_file"
                    else f".{str(row.get('status', '')).lower()}.json"
                )
                if file_name != f"{attempt_id}{expected_suffix}":
                    raise ValueError(f"invalid evidence filename for {attempt_id}: {file_name!r}")
                path = self.attempts / file_name
                payload = path.read_bytes()
                if _sha256_bytes(payload) != row[digest_field]:
                    raise ValueError(f"evidence hash mismatch: {path.name}")
                json.loads(payload)
        return cast(dict[str, Any], index)

    def _recover_unindexed_files(self, index: dict[str, Any]) -> dict[str, Any]:
        """Reconcile complete, hashable files left by a crash before index replace.

        A request written before a call remains charged to the call ceiling after
        recovery, even when its outcome is unknown. This prevents accidental
        retries from exceeding the authorization.
        """
        rows = {row["attempt_id"]: row for row in index["attempts"]}
        candidates: dict[str, dict[str, Path | None]] = {}
        for path in self.attempts.glob("*.json"):
            if path.name.endswith(".request.json"):
                attempt_id = path.name[: -len(".request.json")]
                kind = "request"
            elif path.name.endswith(".complete.json"):
                attempt_id = path.name[: -len(".complete.json")]
                kind = "complete"
            elif path.name.endswith(".failed.json"):
                attempt_id = path.name[: -len(".failed.json")]
                kind = "failed"
            else:
                raise ValueError(f"unrecognized evidence file: {path.name}")
            if not _SAFE_ID.fullmatch(attempt_id):
                raise ValueError(f"invalid attempt ID in evidence filename: {path.name}")
            candidates.setdefault(attempt_id, {"request": None, "complete": None, "failed": None})[
                kind
            ] = path

        changed = False
        for attempt_id, files in candidates.items():
            request = files["request"]
            complete = files["complete"]
            failed = files["failed"]
            if request is None or (complete is not None and failed is not None):
                raise ValueError(f"incomplete or conflicting evidence set for {attempt_id}")
            request_payload = json.loads(request.read_text(encoding="utf-8"))
            if request_payload.get("attempt_id") != attempt_id:
                raise ValueError(f"request identity mismatch: {request.name}")
            row = rows.get(attempt_id)
            if row is None:
                request_bytes = request.read_bytes()
                row = {
                    "attempt_id": attempt_id,
                    "status": "REQUEST_DURABLE",
                    "request_file": request.name,
                    "request_sha256": _sha256_bytes(request_bytes),
                    "outcome_file": None,
                    "outcome_sha256": None,
                }
                index["attempts"].append(row)
                rows[attempt_id] = row
                changed = True
            if complete is not None or failed is not None:
                outcome = complete if complete is not None else failed
                assert outcome is not None
                outcome_payload = json.loads(outcome.read_text(encoding="utf-8"))
                expected_status = "COMPLETE" if complete is not None else "FAILED"
                if (
                    outcome_payload.get("attempt_id") != attempt_id
                    or outcome_payload.get("status") != expected_status
                ):
                    raise ValueError(f"outcome identity/status mismatch: {outcome.name}")
                if row["status"] == "REQUEST_DURABLE":
                    outcome_bytes = outcome.read_bytes()
                    row["status"] = expected_status
                    row["outcome_file"] = outcome.name
                    row["outcome_sha256"] = _sha256_bytes(outcome_bytes)
                    changed = True
                elif row.get("outcome_file") != outcome.name:
                    raise ValueError(f"conflicting indexed outcome for {attempt_id}")
        if len(index["attempts"]) > self.hard_call_limit:
            raise RuntimeError("recovered evidence exceeds authorized MI1 model-call limit")
        if changed:
            index["attempts"].sort(key=lambda row: row["attempt_id"])
            self._write_index(index)
        return index

    def _write_index(self, index: dict[str, Any]) -> None:
        _atomic_write(self._index_path, _canonical(index))

    def begin(self, attempt_id: str, request: dict[str, Any], metadata: dict[str, Any]) -> Path:
        if not _SAFE_ID.fullmatch(attempt_id):
            raise ValueError("attempt_id contains unsupported characters")
        index = self._recover_unindexed_files(self._check_index())
        if any(row["attempt_id"] == attempt_id for row in index["attempts"]):
            raise FileExistsError(f"attempt already exists: {attempt_id}")
        if len(index["attempts"]) >= self.hard_call_limit:
            raise RuntimeError("authorized MI1 model-call limit reached")
        payload = _canonical({"attempt_id": attempt_id, "metadata": metadata, "request": request})
        file_name = f"{attempt_id}.request.json"
        path = self.attempts / file_name
        _atomic_write(path, payload)
        index["attempts"].append(
            {
                "attempt_id": attempt_id,
                "status": "REQUEST_DURABLE",
                "request_file": file_name,
                "request_sha256": _sha256_bytes(payload),
                "outcome_file": None,
                "outcome_sha256": None,
            }
        )
        self._write_index(index)
        return path

    def complete(
        self, attempt_id: str, response: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> Path:
        return self._finish(attempt_id, "COMPLETE", response, metadata or {})

    def fail(
        self, attempt_id: str, failure: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> Path:
        return self._finish(attempt_id, "FAILED", failure, metadata or {})

    def _finish(
        self, attempt_id: str, status: str, payload_value: dict[str, Any], metadata: dict[str, Any]
    ) -> Path:
        index = self._recover_unindexed_files(self._check_index())
        row = next((item for item in index["attempts"] if item["attempt_id"] == attempt_id), None)
        if row is None:
            raise KeyError(f"request was not durably begun: {attempt_id}")
        if row["status"] != "REQUEST_DURABLE":
            raise FileExistsError(f"attempt already has an outcome: {attempt_id}")
        payload = _canonical(
            {
                "attempt_id": attempt_id,
                "status": status,
                "metadata": metadata,
                "payload": payload_value,
            }
        )
        file_name = f"{attempt_id}.{status.lower()}.json"
        path = self.attempts / file_name
        _atomic_write(path, payload)
        row["status"] = status
        row["outcome_file"] = file_name
        row["outcome_sha256"] = _sha256_bytes(payload)
        self._write_index(index)
        return path

    def verify(self) -> dict[str, int]:
        index = self._recover_unindexed_files(self._check_index())
        statuses: dict[str, int] = {}
        for row in index["attempts"]:
            statuses[row["status"]] = statuses.get(row["status"], 0) + 1
        on_disk = {path.name for path in self.attempts.glob("*.json")}
        indexed = {
            name
            for row in index["attempts"]
            for name in (row["request_file"], row["outcome_file"])
            if name is not None
        }
        if on_disk != indexed:
            raise ValueError(f"unindexed or missing evidence files: {sorted(on_disk ^ indexed)}")
        return statuses
