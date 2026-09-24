"""Deliberate Phase One identity and self-view transitions.

Administrative lineage UUIDs never enter this module's model requests.  A
name exists only after an explicit adoption transition and is projected from
an immutable self-view record at cold start.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import GenerationRequest, GenerationResult
from .host import Host
from .state.policy import PolicyError, PolicyService
from .state.storage import SQLiteStore, _utc


class IdentityError(RuntimeError):
    """The requested deliberate identity transition is invalid."""


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not name or len(name) > 64:
        raise IdentityError("name must contain 1 to 64 characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise IdentityError("name contains a control character")
    if "\n" in name or "\r" in name or "\t" in name:
        raise IdentityError("name contains a control character")
    return name


@dataclass(frozen=True)
class SelfView:
    instance_id: str
    version: int
    name: str | None
    self_view_id: str
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "version": self.version,
            "name": self.name,
            "self_view_id": self.self_view_id,
            "content_digest": self.content_digest,
        }


class IdentityService:
    """Append-only identity transitions with manifest-bound self views."""

    def __init__(self, store: SQLiteStore, instance_id: str):
        self.store = store
        self.instance_id = instance_id

    def current(self) -> SelfView | None:
        row = self.store.connection.execute(
            "SELECT m.self_view_id,m.self_view_version,s.name,s.content_digest "
            "FROM current_state c JOIN manifests m ON m.manifest_id=c.current_manifest_id "
            "LEFT JOIN self_views s ON s.self_view_id=m.self_view_id "
            "AND s.instance_id=m.instance_id "
            "WHERE c.active_instance_id=?",
            (self.instance_id,),
        ).fetchone()
        if row is None:
            raise IdentityError("lineage has no current state")
        if row[0] is None:
            return None
        if row[2] is None or row[3] is None:
            raise IdentityError("current self-view binding is missing")
        return SelfView(self.instance_id, int(row[1]), row[2], str(row[0]), str(row[3]))

    def _start_naming_attempt(
        self,
        request: GenerationRequest,
        fingerprint: Mapping[str, Any],
    ) -> tuple[str, str]:
        """Charge and persist a naming request before dispatch.

        Identity adoption historically wrote its generation record only after
        the model result had passed local validation.  That lost malformed
        results from the durable call ledger.  The mutable attempt record is
        the naming equivalent of an interpretation attempt: it is created
        before dispatch and linked to the immutable identity generation record
        only after the adoption transition commits.
        """

        attempt_id = str(uuid.uuid4())
        host_ref = _digest(dict(fingerprint))
        now = _utc()
        with self.store.transaction() as db:
            db.execute(
                "INSERT OR IGNORE INTO host_records(host_ref,provider,model_id,"
                "model_revision,runtime,fingerprint_json,canonical_digest) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    host_ref,
                    fingerprint["provider"],
                    fingerprint["model_id"],
                    fingerprint.get("model_revision"),
                    fingerprint["runtime"],
                    json.dumps(dict(fingerprint), sort_keys=True),
                    host_ref,
                ),
            )
            db.execute(
                "INSERT INTO identity_generation_attempts "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    attempt_id,
                    self.instance_id,
                    host_ref,
                    json.dumps(request.to_dict(), sort_keys=True),
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "STARTED",
                    "[]",
                    None,
                    now,
                    now,
                ),
            )
        return attempt_id, host_ref

    def _persist_naming_result(
        self,
        attempt_id: str,
        result: GenerationResult,
        fingerprint: Mapping[str, Any],
    ) -> None:
        """Persist the complete provider result before any local validation."""

        usage = result.token_usage
        result_payload = {
            "content": result.content,
            "model_id": result.model_id,
            "provider": result.provider,
            "effective_parameters": result.effective_parameters,
            "seed": result.seed,
            "finish_reason": result.finish_reason,
        }
        provider_evidence = {
            "provenance": result.provenance,
            "host_fingerprint": dict(fingerprint),
            "provider": result.provider,
            "model_id": result.model_id,
            "finish_reason": result.finish_reason,
        }
        with self.store.transaction() as db:
            row = db.execute(
                "SELECT status FROM identity_generation_attempts WHERE attempt_id=? "
                "AND instance_id=?",
                (attempt_id, self.instance_id),
            ).fetchone()
            if row is None or str(row[0]) != "STARTED":
                raise IdentityError("naming attempt is not awaiting a provider result")
            db.execute(
                "UPDATE identity_generation_attempts SET result_json=?,returned_model=?,"
                "returned_provider=?,effective_parameters_json=?,usage_json=?,latency_ms=?,"
                "finish_reason=?,provider_evidence_json=?,status='RESULT_READY',updated_at=? "
                "WHERE attempt_id=? AND instance_id=?",
                (
                    json.dumps(result_payload, sort_keys=True),
                    result.model_id,
                    result.provider,
                    json.dumps(result.effective_parameters, sort_keys=True),
                    json.dumps(usage.__dict__, sort_keys=True) if usage is not None else None,
                    result.latency_ms,
                    result.finish_reason,
                    json.dumps(provider_evidence, sort_keys=True),
                    _utc(),
                    attempt_id,
                    self.instance_id,
                ),
            )

    def _finish_naming_attempt(
        self,
        attempt_id: str,
        *,
        status: str,
        errors: tuple[str, ...] = (),
    ) -> None:
        if status not in {"INVALID", "UNCERTAIN"}:
            raise IdentityError("invalid naming attempt disposition")
        with self.store.transaction() as db:
            db.execute(
                "UPDATE identity_generation_attempts SET status=?,validation_errors_json=?,"
                "updated_at=? WHERE attempt_id=? AND instance_id=?",
                (
                    status,
                    json.dumps(list(errors), sort_keys=True),
                    _utc(),
                    attempt_id,
                    self.instance_id,
                ),
            )

    def adopt_from_host(
        self,
        host: Host,
        *,
        source: Mapping[str, Any] | None = None,
    ) -> SelfView:
        """Make one bounded structured naming call, then adopt its result.

        The provider boundary does not advertise native structured output for
        all Phase One hosts, so the contract is a prompted JSON object and a
        strict local validator.  A malformed response is terminal: this
        method never resamples or silently falls back to an operator name.
        """

        current = self.store.current()
        manifest = self.store.connection.execute(
            "SELECT self_view_id,policy_id FROM manifests WHERE manifest_id=?",
            (current["current_manifest_id"],),
        ).fetchone()
        if manifest is None:
            raise IdentityError("current manifest is missing")
        if manifest["self_view_id"] is not None:
            raise IdentityError("identity is already adopted")
        fingerprint = host.fingerprint().to_dict()
        try:
            policy = PolicyService(self.store, self.instance_id).current()
            if not policy.recall_allowed or not policy.provider_reuse_allowed:
                raise PolicyError("identity adoption permission is denied")
            if policy.bound_host_ref is not None:
                PolicyService(self.store, self.instance_id).require_host(
                    policy, fingerprint
                )
        except PolicyError as exc:
            raise IdentityError(str(exc)) from exc
        request = GenerationRequest(
            messages=(
                {
                    "role": "user",
                    "content": (
                        "Choose one concise name for this model instance. "
                        'Return exactly one JSON object with one string field: {"name":"…"}. '
                        "Do not include markdown or any other fields."
                    ),
                },
            ),
            system=(
                "You are performing a deliberate naming operation. "
                "The result is an administrative self-view label, not a personality claim."
            ),
            parameters={"max_new_tokens": 64, "temperature": 0.0},
        )
        attempt_id, _host_ref = self._start_naming_attempt(request, fingerprint)
        try:
            result = host.generate(request)
        except Exception as exc:
            self._finish_naming_attempt(
                attempt_id,
                status="UNCERTAIN",
                errors=(type(exc).__name__,),
            )
            raise
        self._persist_naming_result(attempt_id, result, fingerprint)
        try:
            if (
                result.provider != fingerprint["provider"]
                or result.model_id != fingerprint["model_id"]
            ):
                raise IdentityError("naming response does not match host fingerprint")
            decoded = json.loads(result.content)
        except json.JSONDecodeError as exc:
            self._finish_naming_attempt(
                attempt_id, status="INVALID", errors=("invalid_json",)
            )
            raise IdentityError("naming response is not valid JSON") from exc
        except IdentityError as exc:
            self._finish_naming_attempt(
                attempt_id, status="INVALID", errors=(str(exc),)
            )
            raise
        if (
            not isinstance(decoded, dict)
            or set(decoded) != {"name"}
            or not isinstance(decoded.get("name"), str)
        ):
            self._finish_naming_attempt(
                attempt_id, status="INVALID", errors=("name_schema_failed",)
            )
            raise IdentityError("naming response must contain only a string name")
        try:
            name = validate_name(str(decoded["name"]))
        except IdentityError:
            self._finish_naming_attempt(
                attempt_id, status="INVALID", errors=("name_validation_failed",)
            )
            raise
        provenance = {
            "operation": "identity_adoption",
            "host": fingerprint,
            "model_id": result.model_id,
            "provider": result.provider,
            "response_digest": hashlib.sha256(result.content.encode()).hexdigest(),
        }
        if source:
            provenance["source"] = dict(source)
        return self._adopt(
            name,
            source=provenance,
            generation=(attempt_id, request, result, fingerprint),
        )

    def adopt(self, name: str, *, source: Mapping[str, Any] | None = None) -> SelfView:
        """Adopt one deliberate name; generic extraction cannot call this."""

        return self._adopt(name, source=source, generation=None)

    def _adopt(
        self,
        name: str,
        *,
        source: Mapping[str, Any] | None,
        generation: tuple[str, GenerationRequest, GenerationResult, Mapping[str, Any]] | None,
    ) -> SelfView:
        """Commit an identity transition and, when applicable, its host call."""

        name = validate_name(name)
        with self.store.transaction() as db:
            current = db.execute(
                "SELECT * FROM current_state WHERE active_instance_id=?", (self.instance_id,)
            ).fetchone()
            if current is None:
                raise IdentityError("lineage has no current state")
            manifest = db.execute(
                "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
            ).fetchone()
            if manifest is None:
                raise IdentityError("current manifest is missing")
            try:
                policy = PolicyService(self.store, self.instance_id).current()
                if not policy.recall_allowed or not policy.provider_reuse_allowed:
                    raise PolicyError("identity adoption permission is denied")
            except PolicyError as exc:
                raise IdentityError(str(exc)) from exc
            if manifest["self_view_id"] is not None:
                raise IdentityError("identity is already adopted")
            version = int(manifest["self_view_version"]) + 1
            event_id = str(uuid.uuid4())
            view_id = str(uuid.uuid4())
            now = _utc()
            content = {"name": name}
            content_json = json.dumps(content, sort_keys=True, separators=(",", ":"))
            content_digest = _digest(content)
            db.execute(
                "INSERT INTO identity_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    self.instance_id,
                    "adopt",
                    name,
                    None,
                    json.dumps(dict(source or {}), sort_keys=True),
                    int(current["current_revision"]) + 1,
                    version,
                    None,
                    now,
                ),
            )
            if generation is not None:
                attempt_id, request, result, fingerprint = generation
                host_ref = _digest(fingerprint)
                db.execute(
                    "INSERT OR IGNORE INTO host_records(host_ref,provider,model_id,"
                    "model_revision,runtime,fingerprint_json,canonical_digest) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (
                        host_ref,
                        fingerprint["provider"],
                        fingerprint["model_id"],
                        fingerprint.get("model_revision"),
                        fingerprint["runtime"],
                        json.dumps(dict(fingerprint), sort_keys=True),
                        host_ref,
                    ),
                )
                generation_id = str(uuid.uuid4())
                usage = result.token_usage
                result_payload = {
                    "content": result.content,
                    "model_id": result.model_id,
                    "provider": result.provider,
                    "effective_parameters": result.effective_parameters,
                    "seed": result.seed,
                    "finish_reason": result.finish_reason,
                }
                provider_evidence = {
                    "provenance": result.provenance,
                    "host_fingerprint": dict(fingerprint),
                    "provider": result.provider,
                    "model_id": result.model_id,
                    "finish_reason": result.finish_reason,
                }
                db.execute(
                    "INSERT INTO identity_generation_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        generation_id,
                        event_id,
                        host_ref,
                        json.dumps(request.to_dict(), sort_keys=True),
                        json.dumps(result_payload, sort_keys=True),
                        result.model_id,
                        result.provider,
                        json.dumps(result.effective_parameters, sort_keys=True),
                        json.dumps(usage.__dict__) if usage is not None else None,
                        result.latency_ms,
                        result.finish_reason,
                        json.dumps(provider_evidence, sort_keys=True),
                        now,
                    ),
                )
                updated = db.execute(
                    "UPDATE identity_generation_attempts SET status='ACCEPTED',"
                    "identity_event_id=?,updated_at=? WHERE attempt_id=? AND instance_id=? "
                    "AND status='RESULT_READY'",
                    (event_id, now, attempt_id, self.instance_id),
                ).rowcount
                if updated != 1:
                    raise IdentityError("naming attempt is not ready for adoption")
            db.execute(
                "INSERT INTO self_views VALUES(?,?,?,?,?,?,?,?)",
                (
                    view_id,
                    self.instance_id,
                    version,
                    name,
                    event_id,
                    content_json,
                    content_digest,
                    now,
                ),
            )
            revision = int(current["current_revision"]) + 1
            manifest_id = str(uuid.uuid4())
            integrity = _digest(
                {
                    "instance_id": self.instance_id,
                    "revision": revision,
                    "self_view_id": view_id,
                    "self_view_version": version,
                }
            )
            db.execute(
                "INSERT INTO manifests(manifest_id,instance_id,revision,parent_manifest_id,"
                "inherited_base_manifest_id,policy_id,self_ref_id,format_version,"
                "controller_version,integrity_digest,accepted_history_digest,graph_snapshot_id,"
                "graph_revision,accepted_episode_count,self_view_id,self_view_version) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id,
                    self.instance_id,
                    revision,
                    manifest["manifest_id"],
                    manifest["inherited_base_manifest_id"],
                    manifest["policy_id"],
                    manifest["self_ref_id"],
                    manifest["format_version"],
                    "mneme-p1.2",
                    integrity,
                    manifest["accepted_history_digest"],
                    manifest["graph_snapshot_id"],
                    manifest["graph_revision"],
                    manifest["accepted_episode_count"],
                    view_id,
                    version,
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.instance_id,
                    revision,
                    current["current_revision"],
                    event_id,
                    "identity_adopted",
                    None,
                    manifest_id,
                    now,
                ),
            )
            db.execute(
                "UPDATE current_state SET current_revision=?,current_manifest_id=? "
                "WHERE singleton=1",
                (revision, manifest_id),
            )
            return SelfView(self.instance_id, version, name, view_id, content_digest)

    def add_alias(self, alias: str, *, source: Mapping[str, Any] | None = None) -> str:
        alias = validate_name(alias)
        with self.store.transaction() as db:
            current = db.execute(
                "SELECT * FROM current_state WHERE active_instance_id=?", (self.instance_id,)
            ).fetchone()
            if current is None:
                raise IdentityError("lineage has no current state")
            manifest = db.execute(
                "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
            ).fetchone()
            if manifest is None or manifest["self_view_id"] is None:
                raise IdentityError("adopt a name before adding an alias")
            event_id, now = str(uuid.uuid4()), _utc()
            revision = int(current["current_revision"]) + 1
            db.execute(
                "INSERT INTO identity_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    self.instance_id,
                    "alias",
                    None,
                    alias,
                    json.dumps(dict(source or {}), sort_keys=True),
                    revision,
                    manifest["self_view_version"],
                    None,
                    now,
                ),
            )
            new_manifest = str(uuid.uuid4())
            db.execute(
                "INSERT INTO manifests(manifest_id,instance_id,revision,parent_manifest_id,"
                "inherited_base_manifest_id,policy_id,self_ref_id,format_version,"
                "controller_version,integrity_digest,accepted_history_digest,graph_snapshot_id,"
                "graph_revision,accepted_episode_count,self_view_id,self_view_version) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    new_manifest,
                    self.instance_id,
                    revision,
                    manifest["manifest_id"],
                    manifest["inherited_base_manifest_id"],
                    manifest["policy_id"],
                    manifest["self_ref_id"],
                    manifest["format_version"],
                    "mneme-p1.2",
                    _digest(
                        {
                            "instance_id": self.instance_id,
                            "revision": revision,
                            "self_view_id": manifest["self_view_id"],
                            "alias": alias,
                        }
                    ),
                    manifest["accepted_history_digest"],
                    manifest["graph_snapshot_id"],
                    manifest["graph_revision"],
                    manifest["accepted_episode_count"],
                    manifest["self_view_id"],
                    manifest["self_view_version"],
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.instance_id,
                    revision,
                    current["current_revision"],
                    event_id,
                    "identity_alias_added",
                    None,
                    new_manifest,
                    now,
                ),
            )
            db.execute(
                "UPDATE current_state SET current_revision=?,current_manifest_id=? "
                "WHERE singleton=1",
                (revision, new_manifest),
            )
            return event_id


__all__ = ["IdentityError", "IdentityService", "SelfView", "validate_name"]
