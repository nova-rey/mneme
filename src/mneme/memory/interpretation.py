"""Durable Phase One interpretation lifecycle.

Interpretation is deliberately a separate lifecycle from accepted episodes.
The host call happens outside a SQLite write transaction; the returned result
is persisted before residue validation, and only a validated residue can be
published through :class:`InterpretationPublisher`.

This module does not retrieve or inject memory.  It only turns one accepted
episode into an auditable, source-bound interpretation and (after explicit
validation) an immutable graph publication.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..contracts import GenerationRequest, GenerationResult
from ..host import Host
from ..state.policy import PolicyError, PolicyService
from ..state.storage import SQLiteStore, _utc
from .publication import (
    InterpretationPublisher,
    PublicationError,
    PublicationReceipt,
    StalePublication,
)
from .residue import (
    SUPPORTED_CONCEPT_KINDS,
    SUPPORTED_RELATIONSHIP_KINDS,
    Residue,
    ResidueValidationError,
    validate_residue,
)
from .resolution import ResolutionDecision


class InterpretationError(RuntimeError):
    """The interpretation operation cannot make the requested transition."""


class InterpretationIdempotencyConflict(InterpretationError):
    """An operation coordinate was reused for different input/configuration."""


class InterpretationNotReady(InterpretationError):
    """The operation is in a state that cannot perform the requested action."""


class InterpretationUncertain(InterpretationNotReady):
    """A provider call has an unknown outcome and must not be retried."""


class InterpretationValidationError(InterpretationError):
    """The persisted provider result is not a valid residue."""


# The residue schema remains v1. This version identifies the stricter
# provider-facing extraction contract used for new calls after the pilot
# quotation failure; historical v1 operations remain readable and immutable.
EXTRACTOR_VERSION = "residue-v4"


@dataclass(frozen=True)
class InterpretationReceipt:
    """Small durable-operation receipt returned by lifecycle methods."""

    operation_id: str
    episode_id: str
    status: str
    attempt: int = 0
    host_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "episode_id": self.episode_id,
            "status": self.status,
            "attempt": self.attempt,
            "host_ref": self.host_ref,
        }


def _json(value: Any) -> str:
    """Serialize mappings and tuples deterministically for operation records."""

    def convert(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(key): convert(val) for key, val in item.items()}
        if isinstance(item, (tuple, list)):
            return [convert(entry) for entry in item]
        return item

    return json.dumps(convert(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _as_operation_id(value: str | InterpretationReceipt) -> str:
    if isinstance(value, InterpretationReceipt):
        return value.operation_id
    if not isinstance(value, str) or not value:
        raise InterpretationError("operation_id must be a non-empty string")
    return value


def _result_payload(result: GenerationResult | Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(result, GenerationResult):
        return result.to_dict()
    if isinstance(result, str):
        return {"content": result}
    if isinstance(result, Mapping):
        return dict(result)
    raise InterpretationError("result must be GenerationResult, mapping, or string")


class InterpretationService:
    """Prepare, execute, validate, and publish one episode interpretation."""

    _ALLOWED_PURPOSES = frozenset({"external_evidence", "model_output", "tool_result"})

    def __init__(
        self,
        store: SQLiteStore,
        instance_id: str,
        host: Host,
        *,
        extractor_version: str = EXTRACTOR_VERSION,
        resolver_version: str = "explicit-v1",
        source_purposes: tuple[str, ...] | None = None,
    ) -> None:
        self.store = store
        self.instance_id = instance_id
        self.host = host
        self.extractor_version = extractor_version
        self.resolver_version = resolver_version
        if source_purposes is not None and not set(source_purposes) <= self._ALLOWED_PURPOSES:
            raise InterpretationError("source_purposes contains an unsupported purpose")
        self.source_purposes = source_purposes

    def _policy_allows_interpretation(self, db: Any) -> None:
        """Require the explicit Phase One interpretation opt-in.

        A v1/legacy policy has no interpretation grant and must fail closed.
        The v2 column is the only permission used here; recall and provider
        reuse remain outside this service until their implementing phases.
        """

        try:
            state = PolicyService(self.store, self.instance_id).require("interpret")
            if not state.storage_allowed:
                raise PolicyError("storage permission denied")
        except PolicyError as exc:
            raise InterpretationError(str(exc)) from exc

    def _policy_allows_selected_host(self) -> None:
        try:
            state = PolicyService(self.store, self.instance_id).current()
            if state.bound_host_ref is not None:
                PolicyService(self.store, self.instance_id).require_host(
                    state, self.host.fingerprint().to_dict()
                )
        except PolicyError as exc:
            raise InterpretationError(str(exc)) from exc

    def _policy_allows_provider_reuse(self) -> None:
        """Require current reuse authority when the lineage selected a host."""

        try:
            state = PolicyService(self.store, self.instance_id).current()
            if state.bound_host_ref is not None:
                PolicyService(self.store, self.instance_id).require("provider_reuse")
                PolicyService(self.store, self.instance_id).require_host(
                    state, self.host.fingerprint().to_dict()
                )
        except PolicyError as exc:
            raise InterpretationError(str(exc)) from exc

    def _source_bundle(self, db: Any, episode_id: str) -> dict[str, Any]:
        operation = db.execute(
            "SELECT operation_id FROM episodes WHERE episode_id=? AND origin_instance_id=?",
            (episode_id, self.instance_id),
        ).fetchone()
        if operation is None:
            raise InterpretationError("episode is not accepted by this lineage")
        rows = db.execute(
            "SELECT s.source_id,s.ordinal,s.role,s.supplier,s.content,s.content_digest,"
            "b.purpose,b.independent_evidence "
            "FROM sources s JOIN source_bindings b ON b.source_id=s.source_id "
            "WHERE s.operation_id=? ORDER BY s.ordinal,s.source_id",
            (operation[0],),
        ).fetchall()
        if not rows:
            raise InterpretationError("accepted episode has no bound source records")
        source_rows = [
            {
                "slot": f"s{index}",
                "source_id": str(row[0]),
                "ordinal": int(row[1]),
                "role": str(row[2]),
                "supplier": str(row[3]),
                "content": str(row[4]),
                "content_digest": str(row[5]),
                "purpose": str(row[6]),
                "independent_evidence": bool(row[7]),
            }
            for index, row in enumerate(rows)
        ]
        allowed = (
            self.source_purposes
            if self.source_purposes is not None
            else tuple(self._ALLOWED_PURPOSES)
        )
        eligible = [source for source in source_rows if source["purpose"] in allowed]
        if not eligible:
            raise InterpretationError("accepted episode has no interpretation-eligible sources")
        return {"episode_id": episode_id, "sources": source_rows, "eligible": eligible}

    def _host_ref(self) -> str:
        return _digest(self.host.fingerprint().to_dict())

    def _record_host(self, db: Any, host_ref: str) -> None:
        fingerprint = self.host.fingerprint().to_dict()
        db.execute(
            "INSERT OR IGNORE INTO host_records(host_ref,provider,model_id,model_revision,"
            "runtime,fingerprint_json,canonical_digest) VALUES(?,?,?,?,?,?,?)",
            (
                host_ref,
                fingerprint["provider"],
                fingerprint["model_id"],
                fingerprint.get("model_revision"),
                fingerprint["runtime"],
                _json(fingerprint),
                host_ref,
            ),
        )

    def _episode_host_ref(self, db: Any, episode_id: str) -> str | None:
        row = db.execute(
            "SELECT g.host_ref FROM episodes e "
            "JOIN generation_records g ON g.generation_id=e.generation_id "
            "WHERE e.episode_id=? AND e.origin_instance_id=?",
            (episode_id, self.instance_id),
        ).fetchone()
        return str(row[0]) if row is not None else None

    def _request(
        self,
        source_bundle: Mapping[str, Any],
        *,
        errors: list[str] | None = None,
    ) -> GenerationRequest:
        eligible = source_bundle["eligible"]
        source_text = {
            str(source["slot"]): str(source["content"])
            for source in eligible
        }
        concept_kinds = ", ".join(sorted(SUPPORTED_CONCEPT_KINDS))
        relationship_kinds = ", ".join(sorted(SUPPORTED_RELATIONSHIP_KINDS))
        instruction = (
            f"Extract residue v1 under extractor contract {self.extractor_version} "
            "as one JSON object. Use only the supplied source "
            "slots. For every supported assertion, provide evidence as an array "
            "of objects with exactly {source, evidence}, where source is the "
            "source slot and evidence is a short, exact, non-empty quotation "
            "copied verbatim from that source. Do not calculate or provide "
            "numeric offsets; MNEME resolves quotations to canonical Unicode "
            "code-point spans. If no supported candidate exists, return {}. Return raw "
            "JSON only: no Markdown fences, no introductory or concluding prose, "
            "and no comments. Never invent enum values or labels for constrained "
            "fields. Before returning each concept or relationship, check that "
            "every evidence quotation is one contiguous substring of the referenced "
            "source slot. If an assertion has no exact source substring, omit that "
            "assertion instead of paraphrasing, shortening, combining, or explaining "
            "the source in new words. This rule applies equally to model-output "
            "sources and to repair attempts. Formatting is part of the immutable "
            "source: preserve every Markdown marker, asterisk, underscore, backtick, "
            "punctuation mark, and whitespace character inside a quotation; do not "
            "quote rendered text after stripping formatting. For example, when the "
            "source contains **consistent, focused effort**, the valid quotation "
            "must include both asterisks exactly as **consistent, focused effort**; "
            "the unmarked text consistent, focused effort is invalid and must be "
            "omitted. For a Markdown list source such as `* **Reduces Evaporation:** "
            "water evaporates.`, the quotation must include the leading `* ` and "
            "both pairs of `**`; never return the rendered words without those "
            "markers. If exact character-for-character copying is uncertain, omit "
            "the assertion rather than guessing. "
            "The validator accepts exactly these top-level fields: store, "
            "episode_id, core_concepts, salient_phrases, observed_patterns, "
            "edge_candidates, route_candidates, declared_memories, "
            "earned_candidates, identity_candidates, "
            "developmental_observation_refs, evidence_refs, "
            "extraction_confidence, intrusion_risk_estimate. Use only the "
            "canonical record fields described below. The complete allowed "
            f"concept kind vocabulary is: {concept_kinds}. The complete allowed "
            f"relationship kind vocabulary is: {relationship_kinds}. There are "
            "no other concept or relationship enum values. "
            "core_concepts records require key, label, kind, evidence, and "
            "confidence; edge_candidates records require key, from, to, "
            "relationship, evidence, and confidence, with from/to equal to "
            "concept keys; route_candidates records require key, edge_keys, "
            "evidence, and confidence. Every evidence object must contain only "
            "source and evidence; do not return source_spans, start, or end. "
            "Confidence is mandatory on every graph record and must be a number "
            "from 0.0 through 1.0; never omit it. For example, a minimally "
            "valid graph record is {\"key\":\"c1\",\"label\":\"mulch\","
            "\"kind\":\"object\",\"confidence\":0.90,\"evidence\":["
            "{\"source\":\"s0\",\"evidence\":\"Mulch kept the soil damp.\"}]}. "
            "route_candidates are optional source-backed groupings. MNEME derives "
            "bounded directed routes from accepted graph edges, so do not invent "
            "a route solely to restate an edge. "
            "Use at most two concepts, one edge, "
            "and one route. Use only supported kinds from the vocabularies above, "
            "keep labels short, and return only the JSON object."
        )
        if self.extractor_version != "residue-v1":
            instruction += (
                " This is a corrected extraction contract. Prefer the complete "
                "external source evidence when it supports an assertion; do not "
                "add model-output concepts merely because they are plausible. "
                "Honor the at-most-two-concepts and one-edge limits exactly, "
                "and omit any assertion whose quotation cannot be copied byte "
                "for byte from its source slot."
            )
        if errors:
            instruction += " Correct these validation errors: " + _json(errors)
        prompt = _json({"source_slots": source_text})
        return GenerationRequest(
            messages=({"role": "user", "content": prompt},),
            system=instruction,
            parameters={"temperature": 0, "max_new_tokens": 1536},
            seed=None,
        )

    def _config_digest(
        self,
        source_bundle: Mapping[str, Any],
        *,
        configuration: Mapping[str, Any] | None,
    ) -> str:
        config: dict[str, Any] = {
            "schema_version": 1,
            "extractor_version": self.extractor_version,
            "resolver_version": self.resolver_version,
            "source_digests": [
                source["content_digest"] for source in source_bundle["eligible"]
            ],
            "host_fingerprint": self.host.fingerprint().to_dict(),
        }
        if configuration:
            config["configuration"] = dict(configuration)
        return _digest(config)

    def prepare(
        self,
        episode_id: str,
        *,
        operation_id: str | None = None,
        configuration: Mapping[str, Any] | None = None,
        configuration_digest: str | None = None,
        recovery_of: str | None = None,
        recovery_version: str | None = None,
    ) -> InterpretationReceipt:
        """Create an idempotent prepared operation without calling the host."""

        supplied_operation_id = operation_id is not None
        operation_id = operation_id or str(uuid.uuid4())
        with self.store.transaction() as db:
            self._policy_allows_interpretation(db)
            source_bundle = self._source_bundle(db, episode_id)
            if (recovery_of is None) != (recovery_version is None):
                raise InterpretationError(
                    "recovery_of and recovery_version must be supplied together"
                )
            if recovery_of is not None:
                if not supplied_operation_id:
                    raise InterpretationError(
                        "recovery requires an explicit new operation_id"
                    )
                if not recovery_of or not recovery_version:
                    raise InterpretationError("recovery marker is incomplete")
                recovery = db.execute(
                    "SELECT episode_id,status FROM interpretation_operations "
                    "WHERE operation_id=? AND instance_id=?",
                    (recovery_of, self.instance_id),
                ).fetchone()
                if recovery is None or str(recovery[0]) != episode_id:
                    raise InterpretationError("recovery source operation is not this episode")
                if str(recovery[1]) != "FAILED":
                    raise InterpretationError(
                        "only a FAILED interpretation can be explicitly recovered"
                    )
            effective_configuration = dict(configuration or {})
            if recovery_of is not None:
                effective_configuration.update(
                    {"recovery_of": recovery_of, "recovery_version": recovery_version}
                )
            digest = configuration_digest or self._config_digest(
                source_bundle, configuration=effective_configuration
            )
            old = db.execute(
                "SELECT episode_id,configuration_digest,status,current_attempt "
                "FROM interpretation_operations WHERE operation_id=? AND instance_id=?",
                (operation_id, self.instance_id),
            ).fetchone()
            if old is not None:
                if str(old[0]) != episode_id or str(old[1]) != digest:
                    raise InterpretationIdempotencyConflict(operation_id)
                return InterpretationReceipt(
                    operation_id, episode_id, str(old[2]), int(old[3])
                )
            duplicate = db.execute(
                "SELECT operation_id,configuration_digest,status,current_attempt "
                "FROM interpretation_operations WHERE episode_id=? AND instance_id=? "
                "ORDER BY updated_at DESC, operation_id DESC LIMIT 1",
                (episode_id, self.instance_id),
            ).fetchone()
            if duplicate is not None:
                if recovery_of is not None:
                    if str(duplicate[0]) != recovery_of or str(duplicate[2]) != "FAILED":
                        raise InterpretationIdempotencyConflict(episode_id)
                    # A distinct recovery operation is allowed only when it
                    # points at the latest failed operation and has a new
                    # configuration digest. The old row remains untouched.
                    if str(duplicate[1]) == digest:
                        raise InterpretationIdempotencyConflict(
                            "recovery configuration must be distinct"
                        )
                else:
                    if str(duplicate[1]) != digest:
                        raise InterpretationIdempotencyConflict(episode_id)
                    return InterpretationReceipt(
                        str(duplicate[0]), episode_id, str(duplicate[2]), int(duplicate[3])
                    )
            current = db.execute(
                "SELECT current_manifest_id FROM current_state "
                "WHERE active_instance_id=?",
                (self.instance_id,),
            ).fetchone()
            if current is None:
                raise InterpretationError("lineage has no current state")
            now = _utc()
            db.execute(
                "INSERT INTO interpretation_operations VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    episode_id,
                    self.instance_id,
                    str(current[0]),
                    "PREPARED",
                    0,
                    digest,
                    None
                    if recovery_of is None
                    else f"RECOVERY_OF:{recovery_of}",
                    now,
                    now,
                ),
            )
        return InterpretationReceipt(operation_id, episode_id, "PREPARED")

    def _operation(self, db: Any, value: str | InterpretationReceipt) -> Any:
        operation_id = _as_operation_id(value)
        row = db.execute(
            "SELECT * FROM interpretation_operations "
            "WHERE operation_id=? AND instance_id=?",
            (operation_id, self.instance_id),
        ).fetchone()
        if row is None:
            raise InterpretationError("unknown interpretation operation")
        return row

    def _start(self, operation_id: str, *, repair: bool) -> tuple[int, str, GenerationRequest]:
        with self.store.transaction() as db:
            op = self._operation(db, operation_id)
            status = str(op["status"])
            if status == "ACCEPTED":
                raise InterpretationNotReady("interpretation is already accepted")
            if status == "UNCERTAIN":
                raise InterpretationUncertain(
                    "provider outcome is uncertain; abandon or inspect it before retrying"
                )
            if status == "FAILED" and not repair:
                raise InterpretationNotReady("interpretation requires an explicit repair")
            if status not in {"PREPARED", "FAILED", "RESULT_READY"}:
                raise InterpretationNotReady(status)
            latest = db.execute(
                "SELECT attempt,status,validation_errors_json FROM interpretation_attempts "
                "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
                (operation_id,),
            ).fetchone()
            if status == "RESULT_READY":
                if latest is not None and str(latest[1]) == "RESULT_READY":
                    raise InterpretationNotReady("interpretation result is already ready")
                if not repair:
                    raise InterpretationNotReady("interpretation requires an explicit repair")
            if repair:
                if latest is None or str(latest[1]) != "INVALID":
                    raise InterpretationNotReady("repair requires one invalid validated attempt")
                attempt = int(latest[0]) + 1
                if attempt > 1:
                    raise InterpretationNotReady("only one extraction repair is permitted")
                errors = json.loads(str(latest[2] or "[]"))
                if not isinstance(errors, list):
                    errors = [str(errors)]
            else:
                attempt = 0
                errors = None
            source_bundle = self._source_bundle(db, str(op["episode_id"]))
            self._policy_allows_selected_host()
            self._policy_allows_provider_reuse()
            expected_host = self._episode_host_ref(db, str(op["episode_id"]))
            host_ref = self._host_ref()
            if expected_host is not None and expected_host != host_ref:
                raise InterpretationError("host fingerprint drifted from accepted episode")
            self._record_host(db, host_ref)
            request = self._request(source_bundle, errors=errors)
            request_json = _json(
                {
                    "request": request.to_dict(),
                    "source_bundle": source_bundle,
                    "host_ref": host_ref,
                }
            )
            now = _utc()
            db.execute(
                "INSERT INTO interpretation_attempts VALUES(?,?,?,?,?,?,?,?)",
                (operation_id, attempt, host_ref, request_json, None, "STARTED", None, now),
            )
            db.execute(
                "UPDATE interpretation_operations SET current_attempt=?,status='STARTED',"
                "failure_code=NULL,updated_at=? WHERE operation_id=?",
                (attempt, now, operation_id),
            )
        return attempt, host_ref, request

    def execute(
        self,
        operation: str | InterpretationReceipt,
        *,
        repair: bool = False,
    ) -> InterpretationReceipt:
        """Run one provider call, or explicitly run the sole repair call."""

        operation_id = _as_operation_id(operation)
        attempt, host_ref, request = self._start(operation_id, repair=repair)
        try:
            result = self.host.generate(request)
        except Exception as exc:
            with self.store.transaction() as db:
                now = _utc()
                db.execute(
                    "UPDATE interpretation_attempts SET status='UNCERTAIN',"
                    "validation_errors_json=? WHERE operation_id=? AND attempt=?",
                    (_json([type(exc).__name__]), operation_id, attempt),
                )
                db.execute(
                    "UPDATE interpretation_operations SET status='UNCERTAIN',"
                    "failure_code=?,updated_at=? WHERE operation_id=?",
                    (type(exc).__name__, now, operation_id),
                )
            raise
        self.persist_result(operation_id, result)
        return InterpretationReceipt(
            operation_id,
            self._episode_id(operation_id),
            "RESULT_READY",
            attempt,
            host_ref,
        )

    def _episode_id(self, operation_id: str) -> str:
        row = self.store.connection.execute(
            "SELECT episode_id FROM interpretation_operations WHERE operation_id=?",
            (operation_id,),
        ).fetchone()
        if row is None:
            raise InterpretationError("unknown interpretation operation")
        return str(row[0])

    def persist_result(
        self,
        operation: str | InterpretationReceipt,
        result: GenerationResult | Mapping[str, Any] | str,
    ) -> InterpretationReceipt:
        """Durably store a provider result before any residue validation."""

        operation_id = _as_operation_id(operation)
        payload = _result_payload(result)
        result_json = _json(payload)
        with self.store.transaction() as db:
            op = self._operation(db, operation_id)
            status = str(op["status"])
            attempt_row = db.execute(
                "SELECT attempt,host_ref,status,result_json FROM interpretation_attempts "
                "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
                (operation_id,),
            ).fetchone()
            if attempt_row is None:
                raise InterpretationNotReady("interpretation has not started")
            if status == "RESULT_READY":
                if str(attempt_row[3] or "") == result_json:
                    return InterpretationReceipt(
                        operation_id,
                        str(op["episode_id"]),
                        status,
                        int(attempt_row[0]),
                        str(attempt_row[1]) if attempt_row[1] else None,
                    )
                raise InterpretationIdempotencyConflict(operation_id)
            if status != "STARTED" or str(attempt_row[2]) != "STARTED":
                raise InterpretationNotReady(status)
            host_ref = str(attempt_row[1]) if attempt_row[1] else None
            if isinstance(result, GenerationResult) and host_ref is not None:
                host = db.execute(
                    "SELECT provider,model_id FROM host_records WHERE host_ref=?", (host_ref,)
                ).fetchone()
                if (
                    host is None
                    or result.provider != str(host[0])
                    or result.model_id != str(host[1])
                ):
                    db.execute(
                        "UPDATE interpretation_attempts SET status='UNCERTAIN' "
                        "WHERE operation_id=? AND attempt=?",
                        (operation_id, int(attempt_row[0])),
                    )
                    db.execute(
                        "UPDATE interpretation_operations SET status='UNCERTAIN',"
                        "failure_code=?,updated_at=? WHERE operation_id=?",
                        ("result_host_mismatch", _utc(), operation_id),
                    )
                    raise InterpretationError("generation result does not match prepared host")
            now = _utc()
            db.execute(
                "UPDATE interpretation_attempts SET result_json=?,status='RESULT_READY' "
                "WHERE operation_id=? AND attempt=?",
                (result_json, operation_id, int(attempt_row[0])),
            )
            db.execute(
                "UPDATE interpretation_operations SET status='RESULT_READY',updated_at=? "
                "WHERE operation_id=?",
                (now, operation_id),
            )
            return InterpretationReceipt(
                operation_id,
                str(op["episode_id"]),
                "RESULT_READY",
                int(attempt_row[0]),
                host_ref,
            )

    def _residue_from_attempt(
        self, result_json: str, sources: Mapping[str, str]
    ) -> tuple[Residue, dict[str, Any]]:
        try:
            payload: Any = json.loads(result_json)
        except json.JSONDecodeError as exc:
            raise InterpretationValidationError("provider result is not JSON") from exc
        if isinstance(payload, Mapping) and isinstance(payload.get("content"), str):
            try:
                payload = json.loads(str(payload["content"]))
            except json.JSONDecodeError as exc:
                raise InterpretationValidationError("provider content is not JSON") from exc
        if isinstance(payload, Mapping) and isinstance(payload.get("residue"), Mapping):
            payload = payload["residue"]
        if not isinstance(payload, Mapping):
            raise InterpretationValidationError("provider result must be a JSON object")
        return validate_residue(payload, sources, require_evidence_quotes=True), dict(payload)

    def validate(self, operation: str | InterpretationReceipt) -> Residue:
        """Validate the already persisted result and mark its attempt VALID."""

        operation_id = _as_operation_id(operation)
        invalid_error: str | None = None
        valid_residue: Residue | None = None
        with self.store.transaction() as db:
            op = self._operation(db, operation_id)
            latest = db.execute(
                "SELECT attempt,result_json,status,request_json FROM interpretation_attempts "
                "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
                (operation_id,),
            ).fetchone()
            if latest is None or latest[1] is None:
                raise InterpretationNotReady("interpretation result is not ready")
            request_record = json.loads(str(latest[3]))
            sources = {
                str(source["slot"]): str(source["content"])
                for source in request_record["source_bundle"]["eligible"]
            }
            if str(latest[2]) == "VALID":
                valid_residue, _ = self._residue_from_attempt(str(latest[1]), sources)
            elif str(latest[2]) in {"INVALID", "UNCERTAIN"}:
                invalid_error = "interpretation attempt is not valid"
            else:
                try:
                    payload: Any = json.loads(str(latest[1]))
                    if isinstance(payload, Mapping) and isinstance(payload.get("content"), str):
                        payload = json.loads(str(payload["content"]))
                    if isinstance(payload, Mapping) and isinstance(payload.get("residue"), Mapping):
                        payload = payload["residue"]
                    if not isinstance(payload, Mapping):
                        raise ResidueValidationError("provider result must be a JSON object")
                    valid_residue = validate_residue(
                        payload, sources, require_evidence_quotes=True
                    )
                    if (
                        valid_residue.episode_id is not None
                        and valid_residue.episode_id != str(op["episode_id"])
                    ):
                        raise ResidueValidationError("residue episode_id does not match operation")
                except (
                    ResidueValidationError,
                    ValueError,
                    KeyError,
                    TypeError,
                    json.JSONDecodeError,
                ) as exc:
                    invalid_error = str(exc)
            if invalid_error is not None:
                db.execute(
                    "UPDATE interpretation_attempts SET status='INVALID',"
                    "validation_errors_json=? WHERE operation_id=? AND attempt=?",
                    (_json([invalid_error]), operation_id, int(latest[0])),
                )
                db.execute(
                    "UPDATE interpretation_operations SET status='FAILED',failure_code=?,"
                    "updated_at=? WHERE operation_id=?",
                    ("validation_failed", _utc(), operation_id),
                )
            elif str(latest[2]) != "VALID":
                db.execute(
                    "UPDATE interpretation_attempts SET status='VALID',validation_errors_json='[]' "
                    "WHERE operation_id=? AND attempt=?",
                    (operation_id, int(latest[0])),
                )
        if invalid_error is not None:
            raise InterpretationValidationError(invalid_error)
        if valid_residue is None:
            raise InterpretationValidationError("validation did not produce a residue")
        return valid_residue

    def record_reviewed_result(
        self,
        operation: str | InterpretationReceipt,
        payload: Mapping[str, Any],
    ) -> InterpretationReceipt:
        """Persist a separately reviewed result without rewriting extraction evidence.

        This is temporary Phase Two acquisition scaffolding.  The original
        invalid extractor attempt remains immutable; a new recovery operation
        may record the reviewer-grounded payload as its own result-ready
        attempt.  The normal ``validate`` and publication revalidation paths
        still decide whether the payload is publishable.
        """

        operation_id = _as_operation_id(operation)
        with self.store.transaction() as db:
            op = self._operation(db, operation_id)
            latest = db.execute(
                "SELECT attempt,status,request_json,host_ref FROM interpretation_attempts "
                "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
                (operation_id,),
            ).fetchone()
            if str(op["status"]) != "PREPARED" or latest is not None:
                raise InterpretationNotReady("reviewed result operation is not prepared")
            if not isinstance(payload, Mapping):
                raise InterpretationError("reviewed payload must be an object")
            now = _utc()
            host_ref = self._host_ref()
            self._record_host(db, host_ref)
            db.execute(
                "INSERT INTO interpretation_attempts VALUES(?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    0,
                    host_ref,
                    self._request_json_for_episode(db, str(op["episode_id"])),
                    _json(payload),
                    "RESULT_READY",
                    "[]",
                    now,
                ),
            )
            db.execute(
                "UPDATE interpretation_operations SET current_attempt=0,status='RESULT_READY',"
                "failure_code='evidence_reconciled',updated_at=? WHERE operation_id=?",
                (now, operation_id),
            )
        return InterpretationReceipt(operation_id, str(op["episode_id"]), "RESULT_READY", 0)

    @staticmethod
    def _request_json_for_episode(db: Any, episode_id: str) -> str:
        row = db.execute(
            "SELECT request_json FROM interpretation_attempts ia "
            "JOIN interpretation_operations io ON io.operation_id=ia.operation_id "
            "WHERE io.episode_id=? ORDER BY io.updated_at DESC, ia.attempt DESC LIMIT 1",
            (episode_id,),
        ).fetchone()
        if row is None:
            raise InterpretationError("source-bound extraction request is missing")
        return str(row[0])

    def publish(
        self,
        operation: str | InterpretationReceipt,
        residue: Residue | None = None,
        *,
        expected_manifest_id: str | None = None,
        resolution_decisions: Mapping[str, ResolutionDecision] | None = None,
    ) -> PublicationReceipt:
        """Publish a validated residue through the atomic graph boundary."""

        operation_id = _as_operation_id(operation)
        if residue is None:
            residue = self.validate(operation_id)
        elif not isinstance(residue, Residue):
            raise InterpretationError("publish requires a validated Residue")
        return InterpretationPublisher(self.store, self.instance_id).publish(
            operation_id,
            residue,
            expected_manifest_id=expected_manifest_id,
            extractor_version=self.extractor_version,
            resolver_version=self.resolver_version,
            resolution_decisions=resolution_decisions,
        )

    def recover_started(self, operation: str | InterpretationReceipt) -> InterpretationReceipt:
        """Mark a possibly interrupted provider call UNCERTAIN, never retry it."""

        operation_id = _as_operation_id(operation)
        with self.store.transaction() as db:
            op = self._operation(db, operation_id)
            if str(op["status"]) != "STARTED":
                raise InterpretationNotReady(str(op["status"]))
            row = db.execute(
                "SELECT attempt,host_ref FROM interpretation_attempts "
                "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
                (operation_id,),
            ).fetchone()
            if row is None:
                raise InterpretationError("started interpretation has no attempt")
            now = _utc()
            db.execute(
                "UPDATE interpretation_attempts SET status='UNCERTAIN',"
                "validation_errors_json=? WHERE operation_id=? AND attempt=?",
                (_json(["process_interrupted"]), operation_id, int(row[0])),
            )
            db.execute(
                "UPDATE interpretation_operations SET status='UNCERTAIN',failure_code=?,"
                "updated_at=? WHERE operation_id=?",
                ("process_interrupted", now, operation_id),
            )
            return InterpretationReceipt(
                operation_id,
                str(op["episode_id"]),
                "UNCERTAIN",
                int(row[0]),
                str(row[1]) if row[1] else None,
            )

    # Explicit aliases make the lifecycle names readable at call sites while
    # preserving the short methods used by the existing publisher API.
    prepare_interpretation = prepare
    execute_interpretation = execute
    persist_interpretation_result = persist_result
    validate_result = validate
    publish_interpretation = publish


__all__ = [
    "EXTRACTOR_VERSION",
    "InterpretationError",
    "InterpretationIdempotencyConflict",
    "InterpretationNotReady",
    "InterpretationReceipt",
    "InterpretationService",
    "InterpretationUncertain",
    "InterpretationValidationError",
    "PublicationError",
    "PublicationReceipt",
    "StalePublication",
]
