"""Production-shaped semantic assessor contracts for Phase Two.

The assessor is responsible for semantic classification.  This module keeps
the provider-facing request and result shape identical for qualification and
the pilot, while deterministic software owns coverage, quotation, source
binding, and developmental provenance resolution.

No model call is made here.  The caller reserves and dispatches a
``GenerationRequest`` and passes the returned JSON object to
``validate_assessor_result``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..contracts import GenerationRequest

ASSESSOR_SCHEMA_VERSION = "p2-assessor-v6"
ASSESSOR_PROMPT_VERSION = "p2-assessor-production-v9"
LEGACY_ASSESSOR_SCHEMA_VERSION = "p2-assessor-v4"
PREVIOUS_ASSESSOR_SCHEMA_VERSION = "p2-assessor-v5"
PROVENANCE_SCHEMA_VERSION = "p2-provenance-v1"

ASSESSMENT_STATUSES = frozenset({"present", "absent", "unknown"})
RELATION_SUPPORT = frozenset({"supported", "contradicted", "unsupported", "unknown"})
EXPRESSION_STATUS = frozenset({"affirmed", "negated", "not_expressed", "unknown"})
LEGACY_RELATION_SUPPORT = frozenset({"supported", "unsupported", "unknown"})
LEGACY_EXPRESSION_STATUS = frozenset({"expressed", "not_expressed", "unknown"})
class AssessorValidationError(ValueError):
    """A production-shaped assessor request or result is invalid."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessorValidationError(f"{field} must be a non-empty string")
    return value


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AssessorValidationError(f"{field} must be an object")
    return value


def _proposition(value: object, field: str) -> dict[str, str]:
    """Validate the complete proposition required by the current relation schema."""

    mapping = _mapping(value, field)
    required = ("from", "to", "relation")
    missing = [name for name in required if name not in mapping]
    if missing:
        raise AssessorValidationError(
            f"{field} requires complete proposition field(s): {', '.join(missing)}"
        )
    return {name: _text(mapping[name], f"{field}.{name}") for name in required}


def _string_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise AssessorValidationError(f"{field} must be an array")
    result = tuple(_text(item, f"{field}[]") for item in value)
    if len(result) != len(set(result)):
        raise AssessorValidationError(f"{field} must not contain duplicates")
    return result


@dataclass(frozen=True)
class AssessorSource:
    """One immutable source slot supplied to the assessor."""

    slot: str
    role: str
    available: bool
    text: str | None = None
    source_id: str | None = None

    def __post_init__(self) -> None:
        _text(self.slot, "source slot")
        _text(self.role, "source role")
        if self.source_id is not None:
            _text(self.source_id, "source_id")
        if self.available and not isinstance(self.text, str):
            raise AssessorValidationError(f"available source {self.slot} requires text")
        if not self.available and self.text is not None:
            raise AssessorValidationError(f"unavailable source {self.slot} cannot carry text")

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "role": self.role,
            "available": self.available,
            "text": self.text,
            "source_id": self.source_id,
        }


@dataclass(frozen=True)
class AssessorMonitor:
    """One required semantic monitor and its source-coverage declaration."""

    monitor_id: str
    relation: Mapping[str, Any]
    required_source_slots: tuple[str, ...]
    evidence_source_slots: tuple[str, ...]
    correspondence_source_slots: tuple[str, ...] = ()
    context: str = "general"

    def __post_init__(self) -> None:
        _text(self.monitor_id, "monitor_id")
        normalized = _proposition(self.relation, f"monitor {self.monitor_id}.relation")
        object.__setattr__(self, "relation", normalized)
        _text(self.context, f"monitor {self.monitor_id}.context")
        required = _string_list(
            self.required_source_slots,
            f"monitor {self.monitor_id}.required_source_slots",
        )
        evidence = _string_list(
            self.evidence_source_slots,
            f"monitor {self.monitor_id}.evidence_source_slots",
        )
        correspondence = _string_list(
            self.correspondence_source_slots,
            f"monitor {self.monitor_id}.correspondence_source_slots",
        )
        if not required:
            raise AssessorValidationError(
                f"monitor {self.monitor_id} requires at least one source slot"
            )
        if not evidence or not set(evidence) <= set(required):
            raise AssessorValidationError(
                f"monitor {self.monitor_id}.evidence_source_slots must be a non-empty "
                "subset of required source slots"
            )
        if not set(correspondence) <= set(required):
            raise AssessorValidationError(
                f"monitor {self.monitor_id}.correspondence_source_slots must be a "
                "subset of required source slots"
            )
        object.__setattr__(self, "required_source_slots", required)
        object.__setattr__(self, "evidence_source_slots", evidence)
        object.__setattr__(self, "correspondence_source_slots", correspondence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "monitor_id": self.monitor_id,
            "relation": dict(self.relation),
            "required_source_slots": list(self.required_source_slots),
            "evidence_source_slots": list(self.evidence_source_slots),
            "correspondence_source_slots": list(self.correspondence_source_slots),
            "context": self.context,
        }


@dataclass(frozen=True)
class AssessorRequest:
    """The common request shape used by qualification and production."""

    candidate: Mapping[str, Any]
    sources: tuple[AssessorSource, ...]
    monitors: tuple[AssessorMonitor, ...]
    memory_exposure: tuple[Mapping[str, Any], ...] = ()
    replay_ancestry: tuple[Mapping[str, Any], ...] = ()
    context: Mapping[str, Any] = field(default_factory=dict)
    source_purpose_mask: tuple[str, ...] = ()
    assessor_version: str = ASSESSOR_PROMPT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate", _proposition(self.candidate, "candidate"))
        if not self.sources:
            raise AssessorValidationError("assessor request requires sources")
        slots = [source.slot for source in self.sources]
        if len(slots) != len(set(slots)):
            raise AssessorValidationError("assessor source slots must be unique")
        monitor_ids = [monitor.monitor_id for monitor in self.monitors]
        if not self.monitors:
            raise AssessorValidationError("assessor request requires monitors")
        if len(monitor_ids) != len(set(monitor_ids)):
            raise AssessorValidationError("assessor monitor IDs must be unique")
        known = set(slots)
        for monitor in self.monitors:
            missing = set(monitor.required_source_slots) - known
            if missing:
                raise AssessorValidationError(
                    f"monitor {monitor.monitor_id} references unknown source slot(s): "
                    + ", ".join(sorted(missing))
                )
        _mapping(self.context, "context")
        _text(self.assessor_version, "assessor_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ASSESSOR_SCHEMA_VERSION,
            "prompt_version": self.assessor_version,
            "candidate": dict(self.candidate),
            "sources": [source.to_dict() for source in self.sources],
            "monitors": [monitor.to_dict() for monitor in self.monitors],
            "memory_exposure": [dict(item) for item in self.memory_exposure],
            "replay_ancestry": [dict(item) for item in self.replay_ancestry],
            "context": dict(self.context),
            "source_purpose_mask": list(self.source_purpose_mask),
        }

    def prompt_payload(self) -> str:
        """Serialize the exact provider payload with no administrative fields."""

        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)


@dataclass(frozen=True)
class EvidenceQuote:
    source_slot: str
    quote: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_slot": self.source_slot,
            "quote": self.quote,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class ValidatedSemanticAssessment:
    """Language-level judgment validated without developmental provenance."""

    monitor_id: str
    status: str
    relation_support: str
    expression_status: str
    coverage: Mapping[str, Any]
    evidence: EvidenceQuote | None
    corresponding_source_slots: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "monitor_id": self.monitor_id,
            "status": self.status,
            "relation_support": self.relation_support,
            "expression_status": self.expression_status,
            "coverage": dict(self.coverage),
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "corresponding_source_slots": list(self.corresponding_source_slots),
        }


@dataclass(frozen=True)
class ProvenanceResolution:
    """Deterministic developmental provenance derived from runtime records."""

    monitor_id: str
    dependence: str
    applicable_categories: tuple[str, ...]
    corresponding_source_slots: tuple[str, ...]
    ancestry: tuple[Mapping[str, Any], ...]
    provenance_group_keys: tuple[str, ...]
    credit_eligible: bool
    resolution_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "monitor_id": self.monitor_id,
            "dependence": self.dependence,
            "applicable_categories": list(self.applicable_categories),
            "corresponding_source_slots": list(self.corresponding_source_slots),
            "ancestry": [dict(item) for item in self.ancestry],
            "provenance_group_keys": list(self.provenance_group_keys),
            "credit_eligible": self.credit_eligible,
            "resolution_reason": self.resolution_reason,
        }


@dataclass(frozen=True)
class ResolvedAssessment:
    """Validated semantic judgment joined to a deterministic resolution."""

    semantic: ValidatedSemanticAssessment
    provenance: ProvenanceResolution

    @property
    def monitor_id(self) -> str:
        return self.semantic.monitor_id

    @property
    def status(self) -> str:
        return self.semantic.status

    @property
    def relation_support(self) -> str:
        return self.semantic.relation_support

    @property
    def expression_status(self) -> str:
        return self.semantic.expression_status

    @property
    def dependence(self) -> str:
        return self.provenance.dependence

    @property
    def provenance_group_keys(self) -> tuple[str, ...]:
        return self.provenance.provenance_group_keys

    @property
    def coverage(self) -> Mapping[str, Any]:
        return self.semantic.coverage

    @property
    def evidence(self) -> EvidenceQuote | None:
        return self.semantic.evidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic": self.semantic.to_dict(),
            "provenance": self.provenance.to_dict(),
        }


def _source_map(request: AssessorRequest) -> dict[str, AssessorSource]:
    return {source.slot: source for source in request.sources}


def _unique_quote(source: AssessorSource, quote: object, monitor_id: str) -> EvidenceQuote:
    if not source.available or source.text is None:
        raise AssessorValidationError(
            f"monitor {monitor_id} supplied evidence for unavailable source {source.slot}"
        )
    value = _text(quote, f"monitor {monitor_id}.evidence.quote")
    starts: list[int] = []
    offset = source.text.find(value)
    while offset >= 0:
        starts.append(offset)
        offset = source.text.find(value, offset + 1)
    if not starts:
        raise AssessorValidationError(
            f"monitor {monitor_id} evidence quote does not occur in source {source.slot}"
        )
    if len(starts) != 1:
        raise AssessorValidationError(
            f"monitor {monitor_id} evidence quote is ambiguous in source {source.slot}"
        )
    start = starts[0]
    end = start + len(value)
    if end <= start or source.text[start:end] != value:
        raise AssessorValidationError(f"monitor {monitor_id} evidence span is invalid")
    return EvidenceQuote(source.slot, value, start, end)


def _validate_coverage(
    request: AssessorRequest,
    monitor: AssessorMonitor,
    raw: object,
    status: str,
) -> dict[str, Any]:
    coverage = _mapping(raw, f"monitor {monitor.monitor_id}.coverage")
    complete = coverage.get("complete")
    covered_slots = _string_list(coverage.get("source_slots"), "coverage.source_slots")
    expected = set(monitor.required_source_slots)
    sources = _source_map(request)
    if not isinstance(complete, bool):
        raise AssessorValidationError(
            f"monitor {monitor.monitor_id}.coverage.complete must be boolean"
        )
    if not set(covered_slots) <= expected:
        raise AssessorValidationError(
            f"monitor {monitor.monitor_id}.coverage names undeclared source slots"
        )
    available_expected = {
        slot for slot in expected if sources[slot].available
    }
    unavailable_expected = expected - available_expected
    if status == "absent":
        if not complete or set(covered_slots) != available_expected or unavailable_expected:
            raise AssessorValidationError(
                f"monitor {monitor.monitor_id} absent requires complete available-source coverage"
            )
        if not _text(coverage.get("reason"), f"monitor {monitor.monitor_id}.coverage.reason"):
            raise AssessorValidationError("absence reason is required")
    elif status == "unknown":
        if complete:
            raise AssessorValidationError(
                f"monitor {monitor.monitor_id} unknown cannot claim complete coverage"
            )
        if not _text(coverage.get("reason"), f"monitor {monitor.monitor_id}.coverage.reason"):
            raise AssessorValidationError("unknown coverage reason is required")
    else:
        if (
            not complete
            or set(covered_slots) != expected
            or unavailable_expected
        ):
            raise AssessorValidationError(
                f"monitor {monitor.monitor_id} present requires complete coverage of "
                "all available required source slots"
            )
    return {
        "complete": complete,
        "source_slots": list(covered_slots),
        "reason": coverage.get("reason"),
    }


def _validate_semantic_matrix(status: str, support: str, expression: str, monitor_id: str) -> None:
    """Enforce the prospective separation of coverage, polarity, and support."""

    if status == "absent":
        expected = ("unsupported", "not_expressed")
        if (support, expression) != expected:
            raise AssessorValidationError(
                f"monitor {monitor_id} absent requires relation_support=unsupported "
                "and expression_status=not_expressed"
            )
        return
    if status == "unknown":
        if (support, expression) != ("unknown", "unknown"):
            raise AssessorValidationError(
                f"monitor {monitor_id} unknown requires relation_support=unknown "
                "and expression_status=unknown"
            )
        return
    if status != "present":
        raise AssessorValidationError(f"unsupported monitor status: {status}")
    expected_expression = {
        "supported": "affirmed",
        "contradicted": "negated",
    }
    if support in expected_expression and expression != expected_expression[support]:
        raise AssessorValidationError(
            f"monitor {monitor_id} {support} requires "
            f"expression_status={expected_expression[support]}"
        )
    if support in {"unsupported", "unknown"} and expression != "unknown":
        raise AssessorValidationError(
            f"monitor {monitor_id} {support} requires expression_status=unknown"
        )


def validate_assessor_result(
    request: AssessorRequest,
    result: Mapping[str, Any],
    *,
    allow_legacy: bool = False,
) -> tuple[ValidatedSemanticAssessment, ...]:
    """Validate semantic judgments without accepting model provenance labels.

    All monitors must be represented exactly once.  The returned rows contain
    only language-level judgments plus source quotations and semantic
    correspondence slots.  Developmental dependence is resolved separately by
    :func:`resolve_provenance` from immutable runtime records.
    """

    top = _mapping(result, "assessor result")
    unknown_fields = set(top) - {"schema_version", "assessments"}
    if unknown_fields:
        raise AssessorValidationError(
            "unknown assessor result field(s): " + ", ".join(sorted(unknown_fields))
        )
    schema_version = top.get("schema_version")
    legacy = schema_version == LEGACY_ASSESSOR_SCHEMA_VERSION
    previous = schema_version == PREVIOUS_ASSESSOR_SCHEMA_VERSION
    if schema_version != ASSESSOR_SCHEMA_VERSION and not (allow_legacy and (legacy or previous)):
        raise AssessorValidationError("unsupported assessor result schema version")
    allowed_support = LEGACY_RELATION_SUPPORT if legacy else RELATION_SUPPORT
    allowed_expression = LEGACY_EXPRESSION_STATUS if legacy else EXPRESSION_STATUS
    rows = top.get("assessments")
    if not isinstance(rows, list):
        raise AssessorValidationError("assessments must be an array")
    expected = {monitor.monitor_id: monitor for monitor in request.monitors}
    if len(rows) != len(expected):
        raise AssessorValidationError("every required monitor must have exactly one row")
    seen: set[str] = set()
    sources = _source_map(request)
    validated: list[ValidatedSemanticAssessment] = []
    for index, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"assessments[{index}]")
        monitor_id = _text(row.get("monitor_id"), f"assessments[{index}].monitor_id")
        unknown_row_fields = set(row) - {
            "monitor_id",
            "status",
            "relation_support",
            "expression_status",
            "coverage",
            "evidence",
            "corresponding_source_slots",
        }
        if unknown_row_fields:
            raise AssessorValidationError(
                f"monitor {monitor_id} has "
                "unknown field(s): " + ", ".join(sorted(unknown_row_fields))
            )
        monitor = expected.get(monitor_id)
        if monitor is None:
            raise AssessorValidationError(f"unknown monitor row: {monitor_id}")
        if monitor_id in seen:
            raise AssessorValidationError(f"duplicate monitor row: {monitor_id}")
        seen.add(monitor_id)
        status = _text(row.get("status"), f"monitor {monitor_id}.status")
        support = _text(row.get("relation_support"), f"monitor {monitor_id}.relation_support")
        expression = _text(row.get("expression_status"), f"monitor {monitor_id}.expression_status")
        if status not in ASSESSMENT_STATUSES:
            raise AssessorValidationError(f"unsupported monitor status: {status}")
        if support not in allowed_support:
            raise AssessorValidationError(f"unsupported relation support: {support}")
        if expression not in allowed_expression:
            raise AssessorValidationError(f"unsupported expression status: {expression}")
        if not legacy:
            _validate_semantic_matrix(status, support, expression, monitor_id)
        coverage = _validate_coverage(request, monitor, row.get("coverage"), status)
        evidence: EvidenceQuote | None = None
        if status == "present":
            evidence_raw = _mapping(row.get("evidence"), f"monitor {monitor_id}.evidence")
            source_slot = _text(evidence_raw.get("source_slot"), "evidence.source_slot")
            source = sources.get(source_slot)
            if source is None or source_slot not in monitor.evidence_source_slots:
                raise AssessorValidationError(
                    f"monitor {monitor_id} evidence references a non-evidence source slot"
                )
            evidence = _unique_quote(source, evidence_raw.get("quote"), monitor_id)
        elif row.get("evidence") is not None:
            raise AssessorValidationError(
                f"monitor {monitor_id} {status} must not include evidence quotation"
            )
        raw_correspondence = row.get("corresponding_source_slots", [])
        corresponding_source_slots = _string_list(
            raw_correspondence,
            f"monitor {monitor_id}.corresponding_source_slots",
        )
        if not set(corresponding_source_slots) <= set(monitor.correspondence_source_slots):
            raise AssessorValidationError(
                f"monitor {monitor_id} correspondence names an undeclared source slot"
            )
        if any(not sources[slot].available for slot in corresponding_source_slots):
            raise AssessorValidationError(
                f"monitor {monitor_id} correspondence references unavailable source"
            )
        if status != "present" and corresponding_source_slots:
            raise AssessorValidationError(
                f"monitor {monitor_id} non-present result cannot declare correspondence"
            )
        validated.append(
            ValidatedSemanticAssessment(
                monitor_id,
                status,
                support,
                expression,
                coverage,
                evidence,
                corresponding_source_slots,
            )
        )
    return tuple(validated)


def read_historical_assessor_result(
    request: AssessorRequest, result: Mapping[str, Any]
) -> tuple[ValidatedSemanticAssessment, ...]:
    """Read preserved v4/v5 results without admitting them to the v6 contract.

    Historical provider outputs retain their original schema vocabulary and
    interpretation.  The production validator remains v6-only unless this
    explicit archival reader is selected.
    """

    return validate_assessor_result(request, result, allow_legacy=True)


def _recorded_ancestry(
    request: AssessorRequest, source_slots: Sequence[str]
) -> tuple[Mapping[str, Any], ...]:
    """Return immutable runtime ancestry records for the named source slots."""

    wanted = set(source_slots)
    records: list[Mapping[str, Any]] = []
    for item in (*request.memory_exposure, *request.replay_ancestry):
        slot = item.get("source_slot")
        if isinstance(slot, str) and slot in wanted:
            records.append(dict(item))
    return tuple(records)


def resolve_provenance(
    request: AssessorRequest,
    semantic_rows: Sequence[ValidatedSemanticAssessment],
) -> tuple[ResolvedAssessment, ...]:
    """Resolve developmental provenance using runtime facts and semantic matches.

    The assessor cannot override source roles, availability, exposure ancestry,
    or replay ancestry.  When several antecedent categories apply, all are
    retained and the canonical category follows the fixed precedence while the
    learner receives ``conflict`` only for genuinely unresolved ambiguity.
    """

    sources = _source_map(request)
    precedence = (
        "current_input_echo",
        "exposure_linked",
        "replay_linked",
        "no_identified_link",
    )
    resolved: list[ResolvedAssessment] = []
    for semantic in semantic_rows:
        if semantic.status != "present" or semantic.evidence is None:
            resolution = ProvenanceResolution(
                semantic.monitor_id,
                "unknown",
                (),
                semantic.corresponding_source_slots,
                (),
                (),
                False,
                "non_present_or_unknown_semantic_result",
            )
            resolved.append(ResolvedAssessment(semantic, resolution))
            continue
        evidence_source = sources[semantic.evidence.source_slot]
        categories: list[str] = []
        antecedents = semantic.corresponding_source_slots
        if evidence_source.role == "external":
            categories.append("external_supported")
        elif evidence_source.role == "model_output":
            if not antecedents:
                categories.append("no_identified_link")
            else:
                antecedent_sources = [sources[slot] for slot in antecedents]
                raw_current_slots = request.context.get("current_input_source_slots", [])
                current_slots = {
                    str(slot)
                    for slot in raw_current_slots
                } if isinstance(raw_current_slots, Sequence) and not isinstance(
                    raw_current_slots, (str, bytes)
                ) else set()
                if any(
                    source.role == "external" and slot in current_slots
                    for slot, source in zip(antecedents, antecedent_sources)
                ):
                    categories.append("current_input_echo")
                memory_slots = {
                    str(item["source_slot"])
                    for item in request.memory_exposure
                    if isinstance(item.get("source_slot"), str)
                }
                replay_slots = {
                    str(item["source_slot"])
                    for item in request.replay_ancestry
                    if isinstance(item.get("source_slot"), str)
                }
                if memory_slots & set(antecedents):
                    categories.append("exposure_linked")
                if replay_slots & set(antecedents):
                    categories.append("replay_linked")
                if not categories:
                    categories.append("no_identified_link")
        else:
            categories.append("unknown")
        unique_categories = tuple(dict.fromkeys(categories))
        if "external_supported" in unique_categories:
            canonical = "external_supported"
        else:
            canonical = next(
                (item for item in precedence if item in unique_categories),
                "unknown",
            )
        ancestry = _recorded_ancestry(
            request,
            tuple(dict.fromkeys((*antecedents, semantic.evidence.source_slot))),
        )
        accounting_ancestry = _recorded_ancestry(request, antecedents)
        group_keys: list[str] = []
        for item in accounting_ancestry:
            before = len(group_keys)
            if isinstance(item.get("exposure_id"), str):
                group_keys.append(f"exposure:{item['exposure_id']}")
            if isinstance(item.get("root"), str):
                group_keys.append(f"replay:{item['root']}")
            if len(group_keys) == before:
                # Source slots are request-local aliases and may be reused for
                # different immutable episodes.  Prefer the durable source
                # identity whenever the runtime supplied one; retain the slot
                # fallback for historical requests that predate source IDs.
                if isinstance(item.get("source_id"), str):
                    group_keys.append(f"source:{item['source_id']}")
                elif isinstance(item.get("source_slot"), str):
                    group_keys.append(f"source:{item['source_slot']}")
        if not group_keys and evidence_source.role == "external":
            source_identity = evidence_source.source_id or evidence_source.slot
            group_keys.append(f"external:{source_identity}")
        resolution = ProvenanceResolution(
            semantic.monitor_id,
            canonical,
            unique_categories,
            antecedents,
            ancestry,
            tuple(dict.fromkeys(group_keys)),
            semantic.relation_support == "supported"
            and canonical not in {"current_input_echo", "unknown", "conflict"},
            "runtime_source_role_and_recorded_ancestry",
        )
        resolved.append(ResolvedAssessment(semantic, resolution))
    return tuple(resolved)


def validate_and_resolve_assessor_result(
    request: AssessorRequest, result: Mapping[str, Any]
) -> tuple[ResolvedAssessment, ...]:
    """Run the shared semantic-validation and provenance-resolution boundary."""

    return resolve_provenance(request, validate_assessor_result(request, result))


@dataclass(frozen=True)
class QualificationCase:
    """One fixed qualification request and its semantic acceptance assertions."""

    case_id: str
    request: AssessorRequest
    expected: Mapping[str, Mapping[str, str]]


def assessor_generation_request(
    request: AssessorRequest, *, max_new_tokens: int = 1_536
) -> GenerationRequest:
    """Build the same bounded provider request used by qualification and pilot."""

    if isinstance(max_new_tokens, bool) or max_new_tokens <= 0:
        raise AssessorValidationError("max_new_tokens must be positive")
    return GenerationRequest(
        messages=(
            {
                "role": "user",
                "content": (
                    "Return raw JSON only. Do not use Markdown fences, introductory "
                    "or concluding prose, comments, or any text outside the JSON. "
                    "Do not invent enum values. Return exactly one row for every "
                    "requested monitor, with no omitted or duplicated monitor IDs. "
                    "The complete output contract is:\n"
                    "{\n"
                    f'  "schema_version": "{ASSESSOR_SCHEMA_VERSION}",\n'
                    '  "assessments": [\n'
                    "    {\n"
                    '      "monitor_id": "<exact monitor_id from the request>",\n'
                    '      "status": "present" | "absent" | "unknown",\n'
                    '      "relation_support": "supported" | "contradicted" | '
                    '"unsupported" | "unknown",\n'
                    '      "expression_status": "affirmed" | "negated" | '
                    '"not_expressed" | "unknown",\n'
                    '      "coverage": {\n'
                    '        "complete": true | false,\n'
                    '        "source_slots": ["<declared source slot>"],\n'
                    '        "reason": "<reason>" | null\n'
                    "      },\n"
                    '      "evidence": {"source_slot": "<declared source slot>", '
                    '"quote": "<short exact verbatim quotation>"} | null,\n'
                    '      "corresponding_source_slots": ["<declared antecedent source slot>"]\n'
                    "    }\n"
                    "  ]\n"
                    "}\n"
                    "Use only the listed top-level and row fields. The schema_version "
                    f"must be exactly {ASSESSOR_SCHEMA_VERSION}. For status=present, coverage "
                    "must name covered declared source slots and evidence must contain "
                    "a non-empty exact quotation from its source_slot. Status=present means "
                    "the proposition is addressed by the available required sources; it "
                    "does not by itself mean the proposition is affirmed. For status=present, "
                    "coverage.complete must be true and source_slots must include every "
                    "available required source slot; an unavailable required source means "
                    "status=unknown. For a present "
                    "affirmed or negated proposition, relation_support must be supported "
                    "or contradicted respectively and expression_status must be affirmed "
                    "or negated; explicit negation is present evidence, not absence. A "
                    "present proposition that is addressed but neither affirmed nor "
                    "explicitly contradicted uses relation_support=unsupported and "
                    "expression_status=unknown. Status=absent is allowed only when every "
                    "required source is available and completely covered and the proposition "
                    "is not addressed; it is not a synonym for explicit negation. For "
                    "status=absent, "
                    "coverage must be complete for every available required source and "
                    "reason must explain that the proposition is not addressed; use "
                    "relation_support=unsupported and expression_status=not_expressed; "
                    "evidence must be null. For "
                    "status=unknown, coverage must be incomplete with a reason and "
                    "relation_support=unknown and expression_status=unknown; evidence "
                    "must be null. Never use not_expressed for explicit negation. Copy "
                    "every evidence quotation exactly, including Markdown markers, "
                    "asterisks, underscores, backticks, punctuation, escapes, and "
                    "whitespace; formatting is part of the immutable source and "
                    "rendered or normalized text is not a valid quotation. Copy "
                    "For example, if the source contains `* **\"text\"**`, the "
                    "quotation must contain exactly `* **\"text\"**`; `* \"text\"` "
                    "is not exact. "
                    "monitor IDs and source slots exactly "
                    "from the request. Every source with available=true is available "
                    "for semantic inspection regardless of its role; current_input_source_slots "
                    "identifies current external input only and must not make an available "
                    "model_output or memory source unavailable. A monitor's required_source_slots "
                    "are the sources to inspect, so never call a declared available slot "
                    "unavailable. Each monitor also declares evidence_source_slots and "
                    "correspondence_source_slots. Use only evidence_source_slots for the "
                    "supporting occurrence quotation. Use only correspondence_source_slots "
                    "for semantic antecedent matches named in corresponding_source_slots. "
                    "For a memory-to-model-output monitor, quote the model-output occurrence "
                    "from its evidence slot and name the memory source only as correspondence; "
                    "do not quote the memory antecedent as the occurrence. Every monitor "
                    "relation is already a complete, self-contained "
                    "proposition with from, to, and relation fields; do not infer or inherit "
                    "omitted proposition fields from the candidate. Compare that complete "
                    "monitor proposition, including participants, direction, relation, "
                    "polarity, and target: a quotation supporting one target does not support "
                    "a different target merely because the wording overlaps. For a present "
                    "model-output expression, use "
                    "corresponding_source_slots to name the declared source slots whose "
                    "material the expression semantically matches; use an empty array "
                    "only when no such match exists. Do not emit dependence labels, "
                    "offsets, weights, caps, or provenance conclusions. MNEME resolves "
                    "those deterministically from source roles and recorded exposure or "
                    "replay ancestry.\n\n"
                    + request.prompt_payload()
                ),
            },
        ),
        parameters={"max_new_tokens": max_new_tokens, "temperature": 0.0},
        # DeepInfra's selected backend has no verified native structured-output
        # contract.  The raw-JSON instruction above is the shared production
        # boundary; local validation remains authoritative.
        response_format=None,
    )


def validate_qualification_case(
    case: QualificationCase, result: Mapping[str, Any]
) -> tuple[ResolvedAssessment, ...]:
    """Apply semantic validation, deterministic provenance, and fixed assertions."""

    rows = validate_and_resolve_assessor_result(case.request, result)
    by_id = {row.monitor_id: row for row in rows}
    for monitor_id, expected in case.expected.items():
        row = by_id[monitor_id]
        for field_name, expected_value in expected.items():
            actual = getattr(row, field_name)
            if actual != expected_value:
                raise AssessorValidationError(
                    f"{case.case_id} monitor {monitor_id} has wrong {field_name}: "
                    f"expected {expected_value!r}, got {actual!r}"
                )
    return rows


def qualification_cases() -> tuple[QualificationCase, ...]:
    """Return the fixed, production-shaped three-call qualification set."""

    q1 = AssessorRequest(
        candidate={"from": "lever", "to": "latch_release", "relation": "causes"},
        sources=(
            AssessorSource("s0", "external", True, "Pulling the lever released the latch."),
            AssessorSource("s1", "model_output", True, "Pulling the lever released the latch."),
        ),
        monitors=(
            AssessorMonitor(
                "latch",
                {"from": "lever", "to": "latch_release", "relation": "causes"},
                ("s0",),
                ("s0",),
            ),
            AssessorMonitor(
                "echo",
                {"from": "lever", "to": "latch_release", "relation": "causes"},
                ("s0", "s1"),
                ("s1",),
                ("s0",),
            ),
            AssessorMonitor(
                "unrelated",
                {"from": "lever", "to": "unrelated", "relation": "causes"},
                ("s0",),
                ("s0",),
            ),
        ),
        context={"current_input_source_slots": ["s0"]},
    )
    q2 = AssessorRequest(
        candidate={"from": "rain_jacket", "to": "shade", "relation": "raises"},
        sources=(
            AssessorSource("s0", "external", True, "The rain jacket kept my shoulders dry."),
            AssessorSource("s1", "memory", True, "Turning the handle raises the shade."),
            AssessorSource("s2", "model_output", True, "Turning the handle raises the shade."),
        ),
        monitors=(
            AssessorMonitor(
                "jacket_direction",
                {"from": "rain_jacket", "to": "shade", "relation": "raises"},
                ("s0",),
                ("s0",),
            ),
            AssessorMonitor(
                "shade",
                {"from": "handle", "to": "shade", "relation": "raises"},
                ("s1", "s2"),
                ("s2",),
                ("s1",),
            ),
        ),
        memory_exposure=(
            {"source_slot": "s1", "exposure_id": "memory-1"},
        ),
        replay_ancestry=({"source_slot": "s1", "root": "memory-root-1"},),
    )
    q3 = AssessorRequest(
        candidate={"from": "dial", "to": "ticking", "relation": "stops"},
        sources=(
            AssessorSource(
                "s0",
                "external",
                True,
                "Turning the dial did not stop the ticking; the sound continued.",
            ),
            AssessorSource("s1", "model_output", False, None, "model-output-unavailable"),
        ),
        monitors=(
            AssessorMonitor(
                "dial",
                {"from": "dial", "to": "ticking", "relation": "stops"},
                ("s0",),
                ("s0",),
            ),
            AssessorMonitor(
                "unavailable_output",
                {"from": "dial", "to": "ticking", "relation": "stops"},
                ("s1",),
                ("s1",),
            ),
        ),
    )
    return (
        QualificationCase(
            "Q1",
            q1,
            {
                "latch": {
                    "status": "present",
                    "relation_support": "supported",
                    "expression_status": "affirmed",
                    "dependence": "external_supported",
                },
                "echo": {
                    "status": "present",
                    "relation_support": "supported",
                    "expression_status": "affirmed",
                    "dependence": "current_input_echo",
                },
                "unrelated": {
                    "status": "absent",
                    "relation_support": "unsupported",
                    "expression_status": "not_expressed",
                },
            },
        ),
        QualificationCase(
            "Q2",
            q2,
            {
                "jacket_direction": {
                    "status": "absent",
                    "relation_support": "unsupported",
                    "expression_status": "not_expressed",
                },
                "shade": {
                    "status": "present",
                    "relation_support": "supported",
                    "expression_status": "affirmed",
                    "dependence": "exposure_linked",
                },
            },
        ),
        QualificationCase(
            "Q3",
            q3,
            {
                "dial": {
                    "status": "present",
                    "relation_support": "contradicted",
                    "expression_status": "negated",
                },
                "unavailable_output": {
                    "status": "unknown",
                    "relation_support": "unknown",
                    "expression_status": "unknown",
                },
            },
        ),
    )


__all__ = [
    "ASSESSOR_PROMPT_VERSION",
    "ASSESSOR_SCHEMA_VERSION",
    "LEGACY_ASSESSOR_SCHEMA_VERSION",
    "PREVIOUS_ASSESSOR_SCHEMA_VERSION",
    "PROVENANCE_SCHEMA_VERSION",
    "AssessorMonitor",
    "AssessorRequest",
    "AssessorSource",
    "AssessorValidationError",
    "EvidenceQuote",
    "QualificationCase",
    "ProvenanceResolution",
    "ResolvedAssessment",
    "ValidatedSemanticAssessment",
    "assessor_generation_request",
    "qualification_cases",
    "resolve_provenance",
    "read_historical_assessor_result",
    "validate_and_resolve_assessor_result",
    "validate_qualification_case",
    "validate_assessor_result",
]
