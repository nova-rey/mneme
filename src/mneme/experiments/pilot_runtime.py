"""Small P2.3 execution boundary built from the existing durable services.

This module intentionally contains orchestration only.  ``PilotRun`` owns
laboratory call reservations and receipts, ``ContinuityService`` owns an
accepted developmental episode, and the interpretation/publication services
own residue and learner state.  No model-visible context is manufactured
here, and evaluation is restricted to :class:`FrozenEvaluationView`.

The methods use caller supplied coordinates as durable idempotency keys.  A
returned reservation is read and validated again without dispatching another
provider call.  A dispatched reservation with no returned result is uncertain
and is never regenerated.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts import GenerationRequest, GenerationResult
from ..host import Host
from ..memory.interpretation import (
    EXTRACTOR_VERSION,
    MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
    InterpretationError,
    InterpretationService,
    InterpretationUncertain,
    InterpretationValidationError,
    _decode_json_document,
)
from ..memory.publication import InterpretationPublisher, PublicationReceipt
from ..memory.residue import Residue
from ..state.policy import PolicyError, PolicyService, host_ref
from ..state.service import ContinuityError, ContinuityService, OperationReceipt
from ..state.storage import SQLiteStore
from .artifacts import file_digest
from .evaluation import EvaluationError, FrozenEvaluationView
from .evidence_review import (
    EvidenceReview,
    EvidenceReviewError,
    apply_replacements,
    collect_unresolved_evidence,
    drop_candidate_items,
    resolve_review,
    reviewer_request,
    validate_reviewer_result,
)
from .pilot import CallStatus, PilotError, PilotRun


class PilotRuntimeError(RuntimeError):
    """A bounded P2.3 coordinate cannot safely advance."""


class PilotRuntimeUncertain(PilotRuntimeError):
    """A provider call has no durable terminal result and cannot be retried."""


@dataclass(frozen=True)
class RuntimeSubject:
    """Writable lineage and host binding supplied by the laboratory runner."""

    slot: int
    store: SQLiteStore
    instance_id: str
    host: Host


@dataclass(frozen=True)
class DevelopmentOutcome:
    call_id: str
    operation: OperationReceipt
    provider_called: bool
    result: Mapping[str, Any]


@dataclass(frozen=True)
class ExtractionOutcome:
    call_id: str
    operation_id: str
    episode_id: str
    attempt: int
    provider_called: bool
    residue: Residue | None
    validation_error: str | None


@dataclass(frozen=True)
class ProviderOutcome:
    call_id: str
    result: Mapping[str, Any]
    provider_called: bool
    validated: Any = None
    validation_error: str | None = None


def _result_payload(result: GenerationResult) -> dict[str, Any]:
    usage = result.token_usage
    return {
        "content": result.content,
        "model_id": result.model_id,
        "provider": result.provider,
        "effective_parameters": dict(result.effective_parameters),
        "seed": result.seed,
        "finish_reason": result.finish_reason,
        "usage": None
        if usage is None
        else {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        },
        "provenance": dict(result.provenance),
    }


def _host_fingerprint(host: Host) -> dict[str, Any]:
    return host.fingerprint().to_dict()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PilotRuntimeError(f"{label} must be an object")
    return value


def _persisted_usage(value: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Normalize usage retained by the interpretation result ledger."""

    usage = value.get("usage")
    if isinstance(usage, Mapping):
        return usage
    token_usage = value.get("token_usage")
    return token_usage if isinstance(token_usage, Mapping) else None


class PilotRuntime:
    """Execute finite P2.3 coordinates without creating a second state system.

    The runtime does not choose schedules or semantic rules.  It receives
    already resolved calls from a prepared experiment and records the result
    before invoking any validator.  ``publish_interpretation`` is deliberately
    separate from extraction so a caller can apply the production assessor
    and deterministic provenance resolver before the atomic learner boundary.
    """

    def __init__(
        self,
        pilot: PilotRun,
        subjects: Mapping[int, RuntimeSubject],
    ) -> None:
        self.pilot = pilot
        self.subjects = dict(subjects)

    def _subject(self, slot: int) -> RuntimeSubject:
        subject = self.subjects.get(slot)
        if subject is None or subject.slot != slot:
            raise PilotRuntimeError(f"no runtime subject for slot {slot}")
        return subject

    def _expected_host(self, host: Host, role: str) -> dict[str, Any]:
        state = self.pilot.status()
        envelope = state.get("envelope")
        if isinstance(envelope, Mapping) and isinstance(envelope.get("role_bindings"), Mapping):
            # The prepared envelope binds the developing host once, while
            # the ledger keeps response and extraction calls as separate
            # accounting roles.  Both developmental call roles must resolve
            # to that one scientific host binding; assessor/evaluation roles
            # remain independently bound.
            binding_role = "developing" if role == "development-response" else role
            if role in {"assessor-qualification", "evaluation-assessor"}:
                binding_role = "assessor"
            if role == "development-extraction":
                configured_roles = envelope.get("role_bindings")
                if (
                    not isinstance(configured_roles, Mapping)
                    or "development-extraction" not in configured_roles
                ):
                    # Preserve legacy single-host prepared runs. Mixed-role
                    # runs publish an explicit specialist binding.
                    binding_role = "developing"
            configured = self.pilot.require_role_host(binding_role, host)
            expected = configured.get("fingerprint")
            if isinstance(expected, Mapping):
                return dict(expected)
        return _host_fingerprint(host)

    def _reserve_dispatch(
        self,
        *,
        call_id: str,
        role: str,
        coordinate: Mapping[str, Any],
        max_output_tokens: int,
        host: Host,
    ) -> tuple[Mapping[str, Any], bool]:
        reservation = self.pilot.reserve_call(
            call_id=call_id,
            role=role,
            coordinate=coordinate,
            max_output_tokens=max_output_tokens,
        )
        status = str(reservation.get("status"))
        if status == CallStatus.RETURNED.value:
            return reservation, False
        if status != CallStatus.RESERVED.value:
            if status in {CallStatus.DISPATCHED.value, CallStatus.UNCERTAIN.value}:
                raise PilotRuntimeUncertain(
                    f"call {call_id} has no safe terminal result ({status})"
                )
            raise PilotRuntimeError(f"call {call_id} is not dispatchable: {status}")
        expected = self._expected_host(host, role)
        return self.pilot.dispatch_call(
            call_id,
            expected_host_fingerprint=expected,
        ), True

    def _returned_result(self, call_id: str) -> Mapping[str, Any]:
        reservation = self.pilot.artifacts._read_json(self.pilot._reservation_path(call_id))
        result = reservation.get("result")
        return _mapping(result, f"persisted result for {call_id}")

    def _publish_call_artifact(
        self, category: str, call_id: str, payload: Mapping[str, Any]
    ) -> None:
        self.pilot.publish_artifact(category, f"{call_id}.json", payload)

    def execute_development(
        self,
        *,
        slot: int,
        call_id: str,
        coordinate: Mapping[str, Any],
        request: GenerationRequest,
        max_output_tokens: int,
    ) -> DevelopmentOutcome:
        """Reserve, generate, persist, and accept one developmental episode."""

        subject = self._subject(slot)
        continuity = ContinuityService(subject.store, subject.instance_id, subject.host)
        try:
            prepared = continuity.prepare_episode(request, operation_id=call_id)
        except ContinuityError as exc:
            raise PilotRuntimeError(f"development preparation failed: {call_id}") from exc
        if prepared.status not in {"PREPARED", "RESULT_READY", "ACCEPTED"}:
            raise PilotRuntimeError(
                f"development operation is not resumable: {call_id} ({prepared.status})"
            )
        _reservation, dispatched = self._reserve_dispatch(
            call_id=call_id,
            role="development-response",
            coordinate=coordinate,
            max_output_tokens=max_output_tokens,
            host=subject.host,
        )
        provider_called = dispatched and prepared.status == "PREPARED"
        if provider_called:
            try:
                continuity.generate_operation(call_id)
            except Exception as exc:
                try:
                    self.pilot.mark_uncertain(call_id, type(exc).__name__)
                except PilotError:
                    pass
                raise PilotRuntimeUncertain(f"development call is uncertain: {call_id}") from exc
            generation = subject.store.connection.execute(
                "SELECT g.returned_model,g.returned_provider,g.finish_reason,g.usage_json,"
                "g.provider_evidence_json,"
                "s.content "
                "FROM generation_records g JOIN sources s ON s.source_id=g.output_source_id "
                "WHERE g.operation_id=?",
                (call_id,),
            ).fetchone()
            if generation is None:
                raise PilotRuntimeError(f"development result is not persisted: {call_id}")
            try:
                usage = json.loads(str(generation[3])) if generation[3] else None
                provenance = json.loads(str(generation[4])) if generation[4] else {}
            except json.JSONDecodeError as exc:
                raise PilotRuntimeError(
                    f"development result metadata is invalid: {call_id}"
                ) from exc
            result: Mapping[str, Any] = {
                "content": str(generation[5]),
                "model_id": str(generation[0]),
                "provider": str(generation[1]),
                "finish_reason": generation[2],
                "usage": usage,
                "provenance": provenance,
            }
            returned = self.pilot.return_call(
                call_id,
                result=result,
                usage=usage if isinstance(usage, Mapping) else None,
                output_tokens=(
                    int(usage["output_tokens"])
                    if isinstance(usage, Mapping) and isinstance(usage.get("output_tokens"), int)
                    else None
                ),
                actual_host_fingerprint=_host_fingerprint(subject.host),
            )
            _ = returned
        else:
            if dispatched:
                # A terminal P0.2 operation may predate its laboratory
                # reservation (for example, a crash after acceptance).  Bind
                # that durable result to the coordinate without dispatching.
                generation = subject.store.connection.execute(
                    "SELECT g.returned_model,g.returned_provider,g.finish_reason,"
                    "g.usage_json,g.provider_evidence_json,s.content "
                    "FROM generation_records g JOIN sources s "
                    "ON s.source_id=g.output_source_id WHERE g.operation_id=?",
                    (call_id,),
                ).fetchone()
                if generation is None:
                    raise PilotRuntimeUncertain(
                        f"terminal development operation has no persisted result: {call_id}"
                    )
                usage = json.loads(str(generation[3])) if generation[3] else None
                provenance = json.loads(str(generation[4])) if generation[4] else {}
                result = {
                    "content": str(generation[5]),
                    "model_id": str(generation[0]),
                    "provider": str(generation[1]),
                    "finish_reason": generation[2],
                    "usage": usage,
                    "provenance": provenance,
                }
                self.pilot.return_call(
                    call_id,
                    result=result,
                    usage=usage if isinstance(usage, Mapping) else None,
                    output_tokens=(
                        int(usage["output_tokens"])
                        if isinstance(usage, Mapping)
                        and isinstance(usage.get("output_tokens"), int)
                        else None
                    ),
                    actual_host_fingerprint=_host_fingerprint(subject.host),
                )
            else:
                result = self._returned_result(call_id)
        status = self._operation_status(subject.store, call_id)
        if status in {"STARTED", "UNCERTAIN"}:
            raise PilotRuntimeUncertain(f"development operation is {status}: {call_id}")
        try:
            accepted = continuity.accept_episode(call_id)
        except ContinuityError as exc:
            raise PilotRuntimeError(f"development acceptance failed: {call_id}") from exc
        if accepted.status != "ACCEPTED":
            raise PilotRuntimeError(f"development operation did not accept: {call_id}")
        self._publish_call_artifact(
            "development",
            call_id,
            {
                "coordinate": dict(coordinate),
                "request": request.to_dict(),
                "operation": {
                    "operation_id": accepted.operation_id,
                    "episode_id": accepted.episode_id,
                    "status": accepted.status,
                    "revision": accepted.revision,
                    "manifest_id": accepted.manifest_id,
                },
                "provider_called": provider_called,
                "result": dict(result),
            },
        )
        return DevelopmentOutcome(call_id, accepted, provider_called, dict(result))

    @staticmethod
    def _operation_status(store: SQLiteStore, operation_id: str) -> str | None:
        row = store.connection.execute(
            "SELECT status FROM operations WHERE operation_id=?", (operation_id,)
        ).fetchone()
        return None if row is None else str(row[0])

    def failed_interpretation_operation(self, *, slot: int, episode_id: str) -> str | None:
        """Return the latest failed extraction operation for explicit recovery.

        A failed operation is historical evidence and is never reused for a
        new provider call.  The caller must supply the returned ID as the
        recovery source when preparing a distinct operation.
        """

        subject = self._subject(slot)
        row = subject.store.connection.execute(
            "SELECT operation_id FROM interpretation_operations "
            "WHERE episode_id=? AND instance_id=? AND status='FAILED' "
            "ORDER BY updated_at DESC, operation_id DESC LIMIT 1",
            (episode_id, subject.instance_id),
        ).fetchone()
        return None if row is None else str(row[0])

    def extract(
        self,
        *,
        slot: int,
        call_id: str,
        coordinate: Mapping[str, Any],
        episode_id: str,
        extractor_host: Host,
        max_output_tokens: int,
        repair: bool = False,
        operation_id: str | None = None,
        recovery_of: str | None = None,
        recovery_version: str | None = None,
        extractor_version: str | None = None,
    ) -> ExtractionOutcome:
        """Run one extraction attempt; validation happens after durable return."""

        subject = self._subject(slot)
        service = InterpretationService(
            subject.store,
            subject.instance_id,
            extractor_host,
            extractor_version=extractor_version or recovery_version or EXTRACTOR_VERSION,
            allow_extractor_host_mismatch=(
                (extractor_version or recovery_version or EXTRACTOR_VERSION).startswith(
                    "gliner2.5"
                )
                or (
                    extractor_version == MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION
                    and extractor_host.fingerprint().model_id.startswith("fastino/gliner")
                )
            ),
        )
        prepared = service.prepare(
            episode_id,
            operation_id=operation_id or call_id,
            recovery_of=recovery_of,
            recovery_version=recovery_version,
        )
        if prepared.operation_id != call_id and not repair:
            raise PilotRuntimeError(
                f"episode already has a different interpretation coordinate: {episode_id}"
            )
        operation_id = prepared.operation_id
        _reservation, dispatched = self._reserve_dispatch(
            call_id=call_id,
            role="development-extraction",
            coordinate=coordinate,
            max_output_tokens=max_output_tokens,
            host=extractor_host,
        )
        provider_called = dispatched and (
            prepared.status == "PREPARED" or (repair and prepared.status == "FAILED")
        )
        if provider_called:
            try:
                service.execute(operation_id, repair=repair)
            except InterpretationUncertain as exc:
                self.pilot.mark_uncertain(call_id, str(exc))
                raise PilotRuntimeUncertain(f"extraction call is uncertain: {call_id}") from exc
            except InterpretationError as exc:
                status = self._interpretation_status(subject.store, operation_id)
                if status == "UNCERTAIN":
                    self.pilot.mark_uncertain(call_id, str(exc))
                    raise PilotRuntimeUncertain(f"extraction call is uncertain: {call_id}") from exc
                raise PilotRuntimeError(f"extraction failed before result: {call_id}") from exc
            persisted: Mapping[str, Any] = self._interpretation_payload(subject.store, operation_id)
            usage = _persisted_usage(persisted)
            _returned = self.pilot.return_call(
                call_id,
                result=persisted,
                usage=usage if isinstance(usage, Mapping) else None,
                output_tokens=(
                    int(usage["output_tokens"])
                    if isinstance(usage, Mapping) and isinstance(usage.get("output_tokens"), int)
                    else None
                ),
                actual_host_fingerprint=_host_fingerprint(extractor_host),
            )
        else:
            if dispatched:
                persisted = self._interpretation_payload(subject.store, operation_id)
                usage = _persisted_usage(persisted)
                self.pilot.return_call(
                    call_id,
                    result=persisted,
                    usage=usage if isinstance(usage, Mapping) else None,
                    output_tokens=(
                        int(usage["output_tokens"])
                        if isinstance(usage, Mapping)
                        and isinstance(usage.get("output_tokens"), int)
                        else None
                    ),
                    actual_host_fingerprint=_host_fingerprint(extractor_host),
                )
            else:
                persisted = self._returned_result(call_id)
        residue: Residue | None = None
        validation_error: str | None = None
        validated_attempt: int | None = None
        recovery_id = f"{operation_id}-evidence-review"
        recovery_row = subject.store.connection.execute(
            "SELECT status FROM interpretation_operations WHERE operation_id=?",
            (recovery_id,),
        ).fetchone()
        if (
            not operation_id.endswith("-evidence-review")
            and recovery_row is not None
            and str(recovery_row[0]) in {"RESULT_READY", "ACCEPTED"}
        ):
            recovery_service = InterpretationService(
                subject.store,
                subject.instance_id,
                extractor_host,
                extractor_version="semantic-evidence-reconciliation-v2",
            )
            try:
                residue = recovery_service.validate(recovery_id)
                operation_id = recovery_id
                validated_attempt = 0
                persisted = self._interpretation_payload(subject.store, recovery_id)
            except InterpretationValidationError:
                # A recorded recovery that no longer validates must not hide
                # the original extraction failure; the normal path below will
                # preserve the failure and fail closed.
                residue = None
        try:
            # A returned coordinate can contain a result rejected by an
            # older deterministic validator.  Revalidate that persisted
            # result explicitly after an in-scope validator correction; this
            # never calls the provider or changes the raw attempt evidence.
            if residue is None:
                residue = service.validate(operation_id, revalidate_invalid=not dispatched)
                validated_attempt = int(self._interpretation_attempt(subject.store, operation_id))
        except InterpretationValidationError as exc:
            validation_error = str(exc)
            # A bounded repair may have been spent before a validator
            # correction made the original result admissible.  Revalidate the
            # earlier persisted attempt deterministically; never dispatch a
            # replacement provider call and never discard the failed repair.
            rows = subject.store.connection.execute(
                "SELECT attempt FROM interpretation_attempts "
                "WHERE operation_id=? ORDER BY attempt DESC",
                (operation_id,),
            ).fetchall()
            latest_attempt = int(self._interpretation_attempt(subject.store, operation_id))
            for row in rows:
                candidate_attempt = int(row[0])
                if candidate_attempt == latest_attempt:
                    continue
                try:
                    residue = service.validate_persisted_attempt(operation_id, candidate_attempt)
                    validated_attempt = candidate_attempt
                    validation_error = None
                    break
                except InterpretationValidationError:
                    continue
        attempt = int(self._interpretation_attempt(subject.store, operation_id))
        if validated_attempt is not None:
            attempt = validated_attempt
        self._publish_call_artifact(
            "extraction",
            operation_id,
            {
                "coordinate": dict(coordinate),
                "episode_id": episode_id,
                "extractor_version": service.extractor_version,
                "interpretation_origin": "retrospective" if recovery_of else "original",
                "recovery_of": recovery_of,
                "attempt": attempt,
                "validated_attempt": validated_attempt,
                "request": self._interpretation_request(subject.store, operation_id),
                "provider_called": provider_called,
                "result": dict(persisted),
                "valid": residue is not None,
                "validation_error": validation_error,
                "normalization": (
                    service.normalization_report(operation_id, attempt=validated_attempt)
                    if residue is not None
                    else None
                ),
            },
        )
        return ExtractionOutcome(
            call_id,
            operation_id,
            episode_id,
            attempt,
            provider_called,
            residue,
            validation_error,
        )

    @staticmethod
    def _interpretation_request(store: SQLiteStore, operation_id: str) -> Mapping[str, Any]:
        row = store.connection.execute(
            "SELECT request_json FROM interpretation_attempts "
            "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
            (operation_id,),
        ).fetchone()
        if row is None or row[0] is None:
            raise PilotRuntimeError(f"interpretation request is not persisted: {operation_id}")
        try:
            value = json.loads(str(row[0]))
        except json.JSONDecodeError as exc:
            raise PilotRuntimeError(
                f"interpretation request is invalid JSON: {operation_id}"
            ) from exc
        return _mapping(value, f"interpretation request {operation_id}")

    @staticmethod
    def _interpretation_status(store: SQLiteStore, operation_id: str) -> str:
        row = store.connection.execute(
            "SELECT status FROM interpretation_operations WHERE operation_id=?", (operation_id,)
        ).fetchone()
        return "UNKNOWN" if row is None else str(row[0])

    @staticmethod
    def _interpretation_attempt(store: SQLiteStore, operation_id: str) -> int:
        row = store.connection.execute(
            "SELECT attempt FROM interpretation_attempts WHERE operation_id=? "
            "ORDER BY attempt DESC LIMIT 1",
            (operation_id,),
        ).fetchone()
        return 0 if row is None else int(row[0])

    @staticmethod
    def _interpretation_payload(store: SQLiteStore, operation_id: str) -> dict[str, Any]:
        row = store.connection.execute(
            "SELECT result_json FROM interpretation_attempts WHERE operation_id=? "
            "ORDER BY attempt DESC LIMIT 1",
            (operation_id,),
        ).fetchone()
        if row is None or row[0] is None:
            raise PilotRuntimeError(f"interpretation result is not persisted: {operation_id}")
        try:
            value = json.loads(str(row[0]))
        except json.JSONDecodeError as exc:
            raise PilotRuntimeError(
                f"interpretation result is invalid JSON: {operation_id}"
            ) from exc
        return dict(_mapping(value, f"interpretation result {operation_id}"))

    def publish_interpretation(
        self,
        *,
        slot: int,
        operation_id: str,
        residue: Residue,
        **publication: Any,
    ) -> PublicationReceipt:
        """Use the existing atomic graph/learner publication boundary."""

        subject = self._subject(slot)
        return InterpretationPublisher(subject.store, subject.instance_id).publish(
            operation_id, residue, **publication
        )

    def review_extraction(
        self,
        *,
        slot: int,
        extraction: ExtractionOutcome,
        reviewer_host: Host,
        max_output_tokens: int = 384,
    ) -> ExtractionOutcome:
        """Reconcile only unresolved quotations through temporary review scaffolding."""

        if extraction.residue is not None:
            return extraction
        if extraction.validation_error is None or not any(
            marker in extraction.validation_error
            for marker in (
                "evidence quotation does not occur verbatim",
                "evidence quotation is ambiguous",
            )
        ):
            return extraction
        subject = self._subject(slot)
        persisted = self._interpretation_payload(subject.store, extraction.operation_id)
        payload: Any = persisted
        if isinstance(payload.get("content"), str):
            try:
                payload = _decode_json_document(str(payload["content"]))
            except json.JSONDecodeError as exc:
                raise PilotRuntimeError("extraction payload is not JSON") from exc
        if isinstance(payload, Mapping) and isinstance(payload.get("residue"), Mapping):
            payload = payload["residue"]
        if not isinstance(payload, Mapping):
            raise PilotRuntimeError("extraction payload is not an object")
        request_record = json.loads(
            str(
                subject.store.connection.execute(
                    "SELECT request_json FROM interpretation_attempts "
                    "WHERE operation_id=? ORDER BY attempt DESC LIMIT 1",
                    (extraction.operation_id,),
                ).fetchone()[0]
            )
        )
        bundle = request_record.get("source_bundle")
        if not isinstance(bundle, Mapping) or not isinstance(bundle.get("sources"), list):
            raise PilotRuntimeError("extraction source bundle is unavailable")
        candidates = collect_unresolved_evidence(payload, bundle["sources"])
        if not candidates:
            return extraction
        if len(candidates) > 4:
            raise PilotRuntimeError("bounded evidence review has too many unresolved items")
        recovery_id = f"{extraction.operation_id}-evidence-review"
        existing_recovery = subject.store.connection.execute(
            "SELECT status FROM interpretation_operations WHERE operation_id=?",
            (recovery_id,),
        ).fetchone()
        if existing_recovery is not None and str(existing_recovery[0]) in {
            "RESULT_READY",
            "ACCEPTED",
        }:
            service = InterpretationService(
                subject.store,
                subject.instance_id,
                reviewer_host,
                extractor_version="semantic-evidence-reconciliation-v2",
            )
            residue = service.validate(recovery_id)
            return ExtractionOutcome(
                extraction.call_id,
                recovery_id,
                extraction.episode_id,
                0,
                False,
                residue,
                None,
            )
        replacements: dict[tuple[str | int, ...], str] = {}
        rejected_candidates: list[Any] = []
        review_records: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            call_id = f"{extraction.call_id}-evidence-review-{index}"
            outcome = self.provider_call(
                call_id=call_id,
                role="evidence-reviewer",
                coordinate={
                    "kind": "semantic-evidence-reconciliation",
                    "extraction_call": extraction.call_id,
                    "evidence_index": index,
                },
                host=reviewer_host,
                request=reviewer_request(candidate),
                max_output_tokens=max_output_tokens,
                validator=validate_reviewer_result,
                artifact_category="evidence-review",
            )
            review = outcome.validated
            if not isinstance(review, EvidenceReview):
                raise PilotRuntimeError("evidence reviewer returned an invalid decision")
            try:
                quote = resolve_review(candidate, review)
            except EvidenceReviewError as exc:
                rejected_candidates.append(candidate)
                review_records.append(
                    {
                        "call_id": call_id,
                        "source_slot": candidate.source_slot,
                        "source_role": candidate.source_role,
                        "proposition": dict(candidate.proposition),
                        "proposed_evidence": candidate.proposed_quote,
                        "grounded": review.grounded,
                        "replacement_evidence": None,
                        "disposition": "rejected",
                        "rejection_reason": str(exc),
                    }
                )
                continue
            for path in candidate.paths:
                replacements[path] = quote
            review_records.append(
                {
                    "call_id": call_id,
                    "source_slot": candidate.source_slot,
                    "source_role": candidate.source_role,
                    "proposition": dict(candidate.proposition),
                    "proposed_evidence": candidate.proposed_quote,
                    "grounded": review.grounded,
                    "replacement_evidence": quote,
                    "disposition": "accepted",
                }
            )
        corrected = apply_replacements(payload, replacements)
        if rejected_candidates:
            corrected = drop_candidate_items(corrected, rejected_candidates)
        service = InterpretationService(
            subject.store,
            subject.instance_id,
            reviewer_host,
            extractor_version="semantic-evidence-reconciliation-v2",
        )
        prepared = service.prepare(
            extraction.episode_id,
            operation_id=recovery_id,
            recovery_of=extraction.operation_id,
            recovery_version="semantic-evidence-reconciliation-v2",
        )
        service.record_reviewed_result(prepared, corrected)
        try:
            residue = service.validate(prepared)
        except InterpretationValidationError as exc:
            raise PilotRuntimeError(f"reviewed evidence did not validate: {exc}") from exc
        self._publish_call_artifact(
            "evidence-review",
            recovery_id,
            {
                "original_extraction_operation": extraction.operation_id,
                "reconciled_operation": recovery_id,
                "validation_error": extraction.validation_error,
                "reviews": review_records,
                "reconciled_payload": corrected,
                "residue_digest": residue.content_digest,
            },
        )
        return ExtractionOutcome(
            extraction.call_id,
            recovery_id,
            extraction.episode_id,
            0,
            False,
            residue,
            None,
        )

    def provider_call(
        self,
        *,
        call_id: str,
        role: str,
        coordinate: Mapping[str, Any],
        host: Host,
        request: GenerationRequest,
        max_output_tokens: int,
        validator: Callable[[str], Any] | None = None,
        artifact_category: str = "assessment",
    ) -> ProviderOutcome:
        """Reserve/persist one assessor-like call, then validate its content."""

        _reservation, provider_called = self._reserve_dispatch(
            call_id=call_id,
            role=role,
            coordinate=coordinate,
            max_output_tokens=max_output_tokens,
            host=host,
        )
        if provider_called:
            try:
                generated = host.generate(request)
            except Exception as exc:
                self.pilot.mark_uncertain(call_id, type(exc).__name__)
                raise PilotRuntimeUncertain(f"provider call is uncertain: {call_id}") from exc
            payload = _result_payload(generated)
            usage = payload.get("usage")
            _returned = self.pilot.return_call(
                call_id,
                result=payload,
                usage=usage if isinstance(usage, Mapping) else None,
                output_tokens=(
                    int(usage["output_tokens"])
                    if isinstance(usage, Mapping) and isinstance(usage.get("output_tokens"), int)
                    else None
                ),
                actual_host_fingerprint=_host_fingerprint(host),
            )
        else:
            payload = dict(self._returned_result(call_id))
        validated: Any = None
        validation_error: str | None = None
        if validator is not None:
            try:
                validated = validator(str(payload.get("content", "")))
            except Exception as exc:  # validator errors are retained, never hidden
                validation_error = f"{type(exc).__name__}: {exc}"
        self._publish_call_artifact(
            artifact_category,
            call_id,
            {
                "coordinate": dict(coordinate),
                "request": request.to_dict(),
                "provider_called": provider_called,
                "result": payload,
                "valid": validation_error is None,
                "validation_error": validation_error,
            },
        )
        return ProviderOutcome(call_id, payload, provider_called, validated, validation_error)

    def evaluate(
        self,
        *,
        slot: int,
        call_id: str,
        coordinate: Mapping[str, Any],
        checkpoint: str | Path,
        private_snapshot: str | Path,
        host: Host,
        messages: Sequence[Mapping[str, str]],
        max_output_tokens: int,
        seed: int | None = None,
        parameters: Mapping[str, Any] | None = None,
        system: str | None = None,
    ) -> ProviderOutcome:
        """Run a read-only frozen probe and publish only an external receipt."""

        subject = self._subject(slot)
        checkpoint_path = Path(checkpoint)
        private_path = Path(private_snapshot)
        if not private_path.is_file() or private_path.is_symlink():
            raise EvaluationError("bound evaluation snapshot is missing")
        if checkpoint_path.resolve() != private_path.resolve():
            raise EvaluationError("evaluation checkpoint is not the subject's private snapshot")
        self._validate_evaluation_binding(slot, subject, private_path)
        before = (
            str(subject.store.current()["active_instance_id"]),
            int(subject.store.current()["current_revision"]),
            str(subject.store.current()["current_manifest_id"]),
        )
        reservation, provider_called = self._reserve_dispatch(
            call_id=call_id,
            role="evaluation",
            coordinate=coordinate,
            max_output_tokens=max_output_tokens,
            host=host,
        )
        if provider_called:
            try:
                with FrozenEvaluationView(private_path) as view:
                    result = view.generate(
                        host,
                        messages,
                        seed=seed,
                        parameters=parameters,
                        system=system,
                    )
                    view.assert_unchanged()
                payload = _result_payload(result)
            except Exception as exc:
                self.pilot.mark_uncertain(call_id, type(exc).__name__)
                raise PilotRuntimeUncertain(f"evaluation call is uncertain: {call_id}") from exc
            usage = payload.get("usage")
            self.pilot.return_call(
                call_id,
                result=payload,
                usage=usage if isinstance(usage, Mapping) else None,
                output_tokens=(
                    int(usage["output_tokens"])
                    if isinstance(usage, Mapping) and isinstance(usage.get("output_tokens"), int)
                    else None
                ),
                actual_host_fingerprint=_host_fingerprint(host),
            )
        else:
            payload = dict(self._returned_result(call_id))
        after = (
            str(subject.store.current()["active_instance_id"]),
            int(subject.store.current()["current_revision"]),
            str(subject.store.current()["current_manifest_id"]),
        )
        if after != before:
            raise EvaluationError("evaluation changed developmental lineage state")
        self._publish_call_artifact(
            "evaluation",
            call_id,
            {
                "coordinate": dict(coordinate),
                "checkpoint_sha256": file_digest(private_path),
                "request": {
                    "messages": [dict(message) for message in messages],
                    "system": system,
                    "parameters": dict(parameters or {}),
                    "seed": seed,
                },
                "provider_called": provider_called,
                "result": payload,
                "developmental_state_before": before,
                "developmental_state_after": after,
            },
        )
        return ProviderOutcome(call_id, payload, provider_called)

    def _validate_evaluation_binding(
        self, slot: int, subject: RuntimeSubject, checkpoint: Path
    ) -> None:
        """Reject a valid checkpoint that is not this subject's frozen boundary.

        The caller-provided path is not sufficient evidence of subject
        identity: another lineage can contain a valid, readable checkpoint.
        Validate the checkpoint's immutable source descriptor and the current
        authority before reserving an evaluation call.  If the prepared run
        publishes a private snapshot binding, that exact artifact is also
        required.
        """

        bindings = self.pilot.bindings
        subjects = bindings.get("subjects")
        if isinstance(subjects, list) and subjects:
            selected = [
                item for item in subjects
                if isinstance(item, Mapping) and item.get("slot") == slot
            ]
            if len(selected) != 1:
                raise EvaluationError(f"subject slot is not uniquely bound: {slot}")
            start = selected[0].get("start")
            checkpoint_bindings = bindings.get("checkpoints")
            if isinstance(checkpoint_bindings, Mapping) and isinstance(start, str):
                binding = checkpoint_bindings.get(start)
                if isinstance(binding, Mapping):
                    snapshot_name = binding.get("snapshot_path")
                    if isinstance(snapshot_name, str):
                        expected = self.pilot.run_path / "snapshots" / snapshot_name
                        if not expected.is_file() or expected.is_symlink():
                            raise EvaluationError("bound evaluation snapshot is missing")
                        if checkpoint.resolve() != expected.resolve():
                            raise EvaluationError(
                                "evaluation checkpoint is not the subject's private snapshot"
                            )

        try:
            policy = PolicyService(subject.store, subject.instance_id).current()
        except PolicyError as exc:
            raise EvaluationError(str(exc)) from exc
        if not policy.authority_available:
            raise EvaluationError("evaluation permission authority is unavailable")

        try:
            with FrozenEvaluationView(checkpoint) as view:
                manifest = view.manifest()
                current = subject.store.current()
                checkpoint_authority = int(manifest.get("authority_revision") or 0)
                current_authority = 0
                current_manifest = subject.store.connection.execute(
                    "SELECT authority_revision FROM manifests WHERE manifest_id=?",
                    (current["current_manifest_id"],),
                ).fetchone()
                if current_manifest is not None:
                    current_authority = max(
                        current_authority, int(current_manifest[0] or 0)
                    )
                if current_authority > checkpoint_authority:
                    raise EvaluationError("evaluation checkpoint authority has drifted")
                if manifest.get("source_instance_id") != subject.instance_id:
                    raise EvaluationError("evaluation checkpoint is not bound to the subject")
                if int(manifest.get("source_revision", -1)) != int(
                    current["current_revision"]
                ) or manifest.get("manifest_id") != current["current_manifest_id"]:
                    raise EvaluationError(
                        "evaluation checkpoint is not the subject's current boundary"
                    )
                checkpoint_policy = view.permissions()
                if not checkpoint_policy.authority_available:
                    raise EvaluationError("checkpoint permission authority is unavailable")
                if (
                    checkpoint_policy.revocation_revision > 0
                    and not checkpoint_policy.recall_allowed
                ):
                    raise EvaluationError("checkpoint recall permission is revoked")
                if (
                    checkpoint_policy.bound_host_ref is not None
                    and not checkpoint_policy.provider_reuse_allowed
                ):
                    raise EvaluationError("checkpoint provider-reuse permission is revoked")
                if (
                    checkpoint_policy.bound_host_ref is not None
                    and host_ref(subject.host.fingerprint().to_dict())
                    != checkpoint_policy.bound_host_ref
                ):
                    raise EvaluationError("checkpoint selected host binding does not match")
        except EvaluationError:
            raise
        except (OSError, ValueError, PolicyError) as exc:
            raise EvaluationError(f"evaluation checkpoint binding is invalid: {exc}") from exc


__all__ = [
    "DevelopmentOutcome",
    "ExtractionOutcome",
    "PilotRuntime",
    "PilotRuntimeError",
    "PilotRuntimeUncertain",
    "ProviderOutcome",
    "RuntimeSubject",
]
