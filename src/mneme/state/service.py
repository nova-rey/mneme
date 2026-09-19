"""Atomic P0.2 episode lifecycle around the existing Host contract."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from ..contracts import GenerationRequest, GenerationResult
from ..host import Host
from .storage import SQLiteStore, _utc


class ContinuityError(RuntimeError):
    pass


class IdempotencyConflict(ContinuityError):
    pass


class StaleRevision(ContinuityError):
    pass


class OperationNotReady(ContinuityError):
    pass


@dataclass(frozen=True)
class OperationReceipt:
    operation_id: str
    episode_id: str
    status: str
    revision: int | None = None
    manifest_id: str | None = None


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class ContinuityService:
    """Prepare, execute, persist, and accept one operation at a time."""

    def __init__(self, store: SQLiteStore, instance_id: str, host: Host):
        self.store, self.db, self.instance_id, self.host = (
            store,
            store.connection,
            instance_id,
            host,
        )

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        with self.store.transaction() as db:
            yield db

    def _head(self) -> tuple[int, str]:
        row = self.db.execute(
            "SELECT current_revision,current_manifest_id FROM current_state WHERE active_instance_id=?",
            (self.instance_id,),
        ).fetchone()
        if row is None:
            raise ContinuityError(f"unknown active lineage: {self.instance_id}")
        return int(row[0]), str(row[1])

    def _assert_host_binding(self, run_id: str) -> None:
        """Reject host drift before a prepared operation reaches the provider."""
        row = self.db.execute(
            "SELECT host_ref FROM run_manifests WHERE run_id=? AND instance_id=?",
            (run_id, self.instance_id),
        ).fetchone()
        if row is None:
            raise ContinuityError("operation has no host binding")
        expected = str(row[0])
        actual = _digest(self.host.fingerprint().to_dict())
        if actual != expected:
            raise ContinuityError("host fingerprint drifted from prepared operation")

    def recover_orphaned_operations(
        self,
        *,
        operation_id: str | None = None,
        reason: str = "process_interrupted",
    ) -> tuple[OperationReceipt, ...]:
        """Mark provider calls left in ``STARTED`` as permanently uncertain.

        A process can disappear after the STARTED transaction commits and
        before the provider result is durably recorded.  There is no safe way
        to infer whether that remote call completed, so recovery must make the
        ambiguity explicit rather than retrying it.  This transition is
        idempotent: already-uncertain operations are left untouched and a
        later retry cannot regenerate them.

        ``operation_id`` narrows recovery to one known coordinate; omitting it
        recovers every orphaned STARTED operation for this lineage.  PREPARED
        operations remain retryable because no provider call has started.
        """

        if operation_id is not None and not isinstance(operation_id, str):
            raise ContinuityError("operation_id must be a string")
        if not isinstance(reason, str) or not reason:
            raise ContinuityError("recovery reason must be non-empty")
        with self._write() as db:
            if operation_id is None:
                rows = db.execute(
                    "SELECT operation_id,episode_id,status FROM operations "
                    "WHERE instance_id=? AND status='STARTED' ORDER BY created_at,operation_id",
                    (self.instance_id,),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT operation_id,episode_id,status FROM operations "
                    "WHERE instance_id=? AND operation_id=? AND status='STARTED'",
                    (self.instance_id, operation_id),
                ).fetchall()
            if not rows:
                return ()
            now = _utc()
            receipts: list[OperationReceipt] = []
            for row in rows:
                db.execute(
                    "UPDATE operations SET status='UNCERTAIN',failure_code=?,updated_at=? "
                    "WHERE operation_id=? AND instance_id=? AND status='STARTED'",
                    (reason, now, str(row[0]), self.instance_id),
                )
                receipts.append(
                    OperationReceipt(str(row[0]), str(row[1]), "UNCERTAIN")
                )
            return tuple(receipts)

    def recover_started_operations(
        self,
        *,
        operation_id: str | None = None,
        reason: str = "process_interrupted",
    ) -> tuple[OperationReceipt, ...]:
        """Compatibility spelling for the explicit STARTED recovery boundary."""

        return self.recover_orphaned_operations(
            operation_id=operation_id,
            reason=reason,
        )

    def prepare_episode(
        self,
        request: GenerationRequest,
        *,
        operation_id: str | None = None,
        supersedes_operation_id: str | None = None,
    ) -> OperationReceipt:
        operation_id = operation_id or str(uuid.uuid4())
        data = request.to_dict()
        intent = _digest({"instance_id": self.instance_id, "request": data})
        with self._write() as db:
            old = db.execute(
                "SELECT episode_id,status,intent_digest FROM operations WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if old:
                if old[2] != intent:
                    raise IdempotencyConflict(operation_id)
                return OperationReceipt(operation_id, str(old[0]), str(old[1]))
            unresolved = db.execute(
                "SELECT operation_id FROM operations WHERE instance_id=? AND status IN ('PREPARED','STARTED','RESULT_READY')",
                (self.instance_id,),
            ).fetchone()
            if unresolved is not None:
                raise OperationNotReady("another operation is unresolved")
            head, manifest_id = self._head()
            policy = db.execute(
                "SELECT p.policy_id,p.storage_allowed FROM policies p JOIN lineages l ON l.scope_id=p.scope_id WHERE l.instance_id=?",
                (self.instance_id,),
            ).fetchone()
            if policy and not bool(policy[1]):
                raise ContinuityError("storage permission denied")
            fp = self.host.fingerprint().to_dict()
            host_ref = _digest(fp)
            db.execute(
                "INSERT OR IGNORE INTO host_records(host_ref,provider,model_id,model_revision,runtime,fingerprint_json,canonical_digest) VALUES(?,?,?,?,?,?,?)",
                (
                    host_ref,
                    fp["provider"],
                    fp["model_id"],
                    fp.get("model_revision"),
                    fp["runtime"],
                    json.dumps(fp, sort_keys=True),
                    host_ref,
                ),
            )
            run_id, episode_id, now = str(uuid.uuid4()), str(uuid.uuid4()), _utc()
            db.execute(
                "INSERT INTO run_manifests(run_id,instance_id,pinned_manifest_id,host_ref,policy_id,controller_version,context_mode,seed,rng_plan_version,request_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    self.instance_id,
                    manifest_id,
                    host_ref,
                    policy[0] if policy else "",
                    "mneme-p0.2",
                    "develop",
                    request.seed,
                    "p0.2",
                    json.dumps(data, sort_keys=True),
                ),
            )
            db.execute(
                "INSERT INTO operations(operation_id,episode_id,instance_id,base_revision,run_id,intent_digest,status,created_at,updated_at,supersedes_operation_id) VALUES(?,?,?,?,?,?, 'PREPARED',?,?,?)",
                (
                    operation_id,
                    episode_id,
                    self.instance_id,
                    head,
                    run_id,
                    intent,
                    now,
                    now,
                    supersedes_operation_id,
                ),
            )
            replayed_ordinals_raw = request.run_metadata.get("replayed_message_ordinals", ())
            if not isinstance(replayed_ordinals_raw, (list, tuple, set, frozenset)):
                replayed_ordinals_raw = ()
            replayed_ordinals = {
                int(value)
                for value in replayed_ordinals_raw
                if isinstance(value, int) and value >= 0
            }
            for ordinal, message in enumerate(request.messages):
                content = str(message.get("content", ""))
                source_id = str(uuid.uuid4())
                role = str(message.get("role", "user"))
                db.execute(
                    "INSERT INTO sources VALUES(?,?,?,?,?,?,?)",
                    (
                        source_id,
                        operation_id,
                        ordinal,
                        role,
                        "external",
                        content,
                        hashlib.sha256(content.encode()).hexdigest(),
                    ),
                )
                purpose = (
                    "replayed_context"
                    if ordinal in replayed_ordinals
                    else {
                    "user": "external_evidence",
                    "assistant": "replayed_context",
                    "system": "controller_dependency",
                    }.get(role, "controller_dependency")
                )
                db.execute(
                    "INSERT INTO source_bindings VALUES(?,?,?,?,?,?)",
                    (
                        source_id,
                        purpose,
                        None,
                        None,
                        int(purpose == "external_evidence"),
                        now,
                    ),
                )
        return OperationReceipt(operation_id, episode_id, "PREPARED")

    def generate_operation(self, operation_id: str) -> OperationReceipt:
        with self._write() as db:
            row = db.execute(
                "SELECT episode_id,status,run_id FROM operations WHERE operation_id=? AND instance_id=?",
                (operation_id, self.instance_id),
            ).fetchone()
            if row is None:
                raise ContinuityError("unknown operation")
            episode_id, status, run_id = str(row[0]), str(row[1]), str(row[2])
            if status == "ACCEPTED":
                e = db.execute(
                    "SELECT e.accepted_revision,r.manifest_id FROM episodes e JOIN revisions r ON r.episode_id=e.episode_id WHERE e.episode_id=?",
                    (episode_id,),
                ).fetchone()
                return OperationReceipt(operation_id, episode_id, status, int(e[0]), str(e[1]))
            if status == "RESULT_READY":
                return OperationReceipt(operation_id, episode_id, status)
            if status != "PREPARED":
                raise OperationNotReady(status)
            # This check must precede STARTED publication.  A drifted host is
            # a rejected prepared operation, not an uncertain provider call.
            self._assert_host_binding(run_id)
            db.execute(
                "UPDATE operations SET status='STARTED',updated_at=? WHERE operation_id=?",
                (_utc(), operation_id),
            )
            request_json = db.execute(
                "SELECT request_json FROM run_manifests WHERE run_id=?", (run_id,)
            ).fetchone()[0]
        data = json.loads(request_json)
        request = GenerationRequest(
            tuple(dict(m) for m in data["messages"]),
            data.get("system"),
            dict(data.get("parameters", {})),
            data.get("seed"),
            data.get("response_format"),
            {},
        )
        try:
            result = self.host.generate(request)
        except Exception as exc:
            with self._write() as db:
                db.execute(
                    "UPDATE operations SET status='UNCERTAIN',failure_code=?,updated_at=? WHERE operation_id=?",
                    (type(exc).__name__, _utc(), operation_id),
                )
            raise
        self.persist_generation_result(operation_id, result)
        return OperationReceipt(operation_id, episode_id, "RESULT_READY")

    def persist_generation_result(
        self, operation_id: str, result: GenerationResult
    ) -> OperationReceipt:
        with self._write() as db:
            row = db.execute(
                "SELECT episode_id,status,run_id FROM operations WHERE operation_id=? AND instance_id=?",
                (operation_id, self.instance_id),
            ).fetchone()
            if row is None:
                raise ContinuityError("unknown operation")
            episode_id, status, run_id = str(row[0]), str(row[1]), str(row[2])
            if status == "RESULT_READY":
                return OperationReceipt(operation_id, episode_id, status)
            if status != "STARTED":
                raise OperationNotReady(status)
            generation_id, output_id = str(uuid.uuid4()), str(uuid.uuid4())
            host_ref = str(
                db.execute(
                    "SELECT host_ref FROM run_manifests WHERE run_id=?", (run_id,)
                ).fetchone()[0]
            )
            host_record = db.execute(
                "SELECT provider,model_id FROM host_records WHERE host_ref=?", (host_ref,)
            ).fetchone()
            if host_record is None:
                raise ContinuityError("operation host record is missing")
            if result.provider != str(host_record[0]) or result.model_id != str(host_record[1]):
                db.execute(
                    "UPDATE operations SET status='UNCERTAIN',failure_code=?,updated_at=? "
                    "WHERE operation_id=?",
                    ("result_host_mismatch", _utc(), operation_id),
                )
                raise ContinuityError("generation result does not match prepared host")
            content = result.content
            output_purpose = "model_output"
            db.execute(
                "INSERT INTO sources VALUES(?,?,?,?,?,?,?)",
                (
                    output_id,
                    operation_id,
                    1000000,
                    "model_output",
                    "model",
                    content,
                    hashlib.sha256(content.encode()).hexdigest(),
                ),
            )
            db.execute(
                "INSERT INTO source_bindings VALUES(?,?,?,?,?,?)",
                (output_id, output_purpose, None, None, 0, _utc()),
            )
            usage = result.token_usage
            db.execute(
                "INSERT INTO generation_records VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    generation_id,
                    operation_id,
                    host_ref,
                    output_id,
                    result.model_id,
                    result.provider,
                    json.dumps(result.effective_parameters, sort_keys=True),
                    json.dumps(usage.__dict__ if usage else None),
                    result.latency_ms,
                    result.finish_reason,
                    json.dumps(
                        {
                            "provenance": result.provenance,
                            "provider": result.provider,
                            "model_id": result.model_id,
                            "finish_reason": result.finish_reason,
                        },
                        sort_keys=True,
                    ),
                ),
            )
            db.execute(
                "UPDATE operations SET status='RESULT_READY',generation_id=?,updated_at=? WHERE operation_id=?",
                (generation_id, _utc(), operation_id),
            )
        return OperationReceipt(operation_id, episode_id, "RESULT_READY")

    def accept_episode(self, operation_id: str) -> OperationReceipt:
        with self._write() as db:
            row = db.execute(
                "SELECT episode_id,base_revision,status,generation_id FROM operations WHERE operation_id=? AND instance_id=?",
                (operation_id, self.instance_id),
            ).fetchone()
            if row is None:
                raise ContinuityError("unknown operation")
            episode_id, base, status, generation_id = str(row[0]), int(row[1]), str(row[2]), row[3]
            if status == "ACCEPTED":
                e = db.execute(
                    "SELECT e.accepted_revision,r.manifest_id FROM episodes e JOIN revisions r ON r.episode_id=e.episode_id WHERE e.episode_id=?",
                    (episode_id,),
                ).fetchone()
                return OperationReceipt(operation_id, episode_id, status, int(e[0]), str(e[1]))
            if status != "RESULT_READY":
                raise OperationNotReady(status)
            current, previous_manifest = self._head()
            if base != current:
                raise StaleRevision(f"prepared at {base}, current head is {current}")
            revision, now, manifest_id = current + 1, _utc(), str(uuid.uuid4())
            integrity = _digest(
                {
                    "instance_id": self.instance_id,
                    "revision": revision,
                    "episode_id": episode_id,
                    "manifest": manifest_id,
                }
            )
            db.execute(
                "INSERT INTO episodes(episode_id,operation_id,origin_instance_id,accepted_revision,generation_id,occurred_at,accepted_at) VALUES(?,?,?,?,?,?,?)",
                (episode_id, operation_id, self.instance_id, revision, generation_id, now, now),
            )
            # The revision row is inserted below, so include this accepted
            # content explicitly while the enclosing transaction protects the
            # complete transition.
            input_sources = [
                {"role": str(source[0]), "supplier": str(source[1]), "content": str(source[2])}
                for source in db.execute(
                    "SELECT role,supplier,content FROM sources WHERE operation_id=? ORDER BY ordinal",
                    (operation_id,),
                )
            ]
            output_source = db.execute(
                "SELECT output_source_id FROM generation_records WHERE generation_id=?",
                (generation_id,),
            ).fetchone()[0]
            output_content = db.execute(
                "SELECT content FROM sources WHERE source_id=?", (output_source,)
            ).fetchone()[0]
            history_digest = self.store.accepted_history_digest(
                self.instance_id,
                extra_records=[
                    {
                        "event_kind": "episode_accepted",
                        "sources": input_sources,
                        "generation": {"content": output_content},
                    }
                ],
            )
            base_manifest = db.execute(
                "SELECT * FROM manifests WHERE manifest_id=?", (previous_manifest,)
            ).fetchone()
            db.execute(
                "INSERT INTO manifests("
                "manifest_id,instance_id,revision,parent_manifest_id,inherited_base_manifest_id,"
                "policy_id,self_ref_id,format_version,controller_version,integrity_digest,"
                "accepted_history_digest,graph_snapshot_id,graph_revision,accepted_episode_count,"
                "self_view_id,self_view_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id,
                    self.instance_id,
                    revision,
                    previous_manifest,
                    base_manifest["inherited_base_manifest_id"],
                    base_manifest["policy_id"],
                    base_manifest["self_ref_id"],
                    1,
                    "mneme-p0.2",
                    integrity,
                    history_digest,
                    base_manifest["graph_snapshot_id"],
                    base_manifest["graph_revision"],
                    int(base_manifest["accepted_episode_count"]) + 1,
                    base_manifest["self_view_id"],
                    base_manifest["self_view_version"],
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.instance_id,
                    revision,
                    current,
                    operation_id,
                    "episode_accepted",
                    episode_id,
                    manifest_id,
                    now,
                ),
            )
            db.execute(
                "UPDATE operations SET status='ACCEPTED',updated_at=? WHERE operation_id=?",
                (now, operation_id),
            )
            db.execute(
                "UPDATE current_state SET current_revision=?,current_manifest_id=? WHERE singleton=1",
                (revision, manifest_id),
            )
        return OperationReceipt(operation_id, episode_id, "ACCEPTED", revision, manifest_id)

    def abandon_operation(self, operation_id: str) -> None:
        with self._write() as db:
            db.execute(
                "UPDATE operations SET status='ABANDONED',updated_at=? WHERE operation_id=? AND instance_id=? AND status IN ('PREPARED','UNCERTAIN','RESULT_READY')",
                (_utc(), operation_id, self.instance_id),
            )
