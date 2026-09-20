"""Production-shaped semantic assessor contracts for Phase Two.

The assessor is responsible for semantic classification.  This module keeps
the provider-facing request and result shape identical for qualification and
the pilot, while deterministic software owns coverage, quotation, source
binding, and dependence validation.

No model call is made here.  The caller reserves and dispatches a
``GenerationRequest`` and passes the returned JSON object to
``validate_assessor_result``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from ..contracts import GenerationRequest

ASSESSOR_SCHEMA_VERSION = "p2-assessor-v1"
ASSESSOR_PROMPT_VERSION = "p2-assessor-production-v1"

ASSESSMENT_STATUSES = frozenset({"present", "absent", "unknown"})
RELATION_SUPPORT = frozenset({"supported", "unsupported", "unknown"})
EXPRESSION_STATUS = frozenset({"expressed", "not_expressed", "unknown"})
DEPENDENCE_CATEGORIES = frozenset(
    {
        "external_supported",
        "current_input_echo",
        "replay_linked",
        "exposure_linked",
        "no_identified_link",
        "unknown",
        "conflict",
    }
)


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
    context: str = "general"

    def __post_init__(self) -> None:
        _text(self.monitor_id, "monitor_id")
        _mapping(self.relation, f"monitor {self.monitor_id}.relation")
        _text(self.context, f"monitor {self.monitor_id}.context")
        if not self.required_source_slots:
            raise AssessorValidationError(
                f"monitor {self.monitor_id} requires at least one source slot"
            )
        if len(self.required_source_slots) != len(set(self.required_source_slots)):
            raise AssessorValidationError(
                f"monitor {self.monitor_id} has duplicate required source slots"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "monitor_id": self.monitor_id,
            "relation": dict(self.relation),
            "required_source_slots": list(self.required_source_slots),
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
        _mapping(self.candidate, "candidate")
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
class ValidatedAssessment:
    monitor_id: str
    status: str
    relation_support: str
    expression_status: str
    dependence: str
    coverage: Mapping[str, Any]
    evidence: EvidenceQuote | None
    dependence_group: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "monitor_id": self.monitor_id,
            "status": self.status,
            "relation_support": self.relation_support,
            "expression_status": self.expression_status,
            "dependence": self.dependence,
            "coverage": dict(self.coverage),
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "dependence_group": self.dependence_group,
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
        if not covered_slots:
            raise AssessorValidationError(
                f"monitor {monitor.monitor_id} present requires covered source slots"
            )
    return {
        "complete": complete,
        "source_slots": list(covered_slots),
        "reason": coverage.get("reason"),
    }


def validate_assessor_result(
    request: AssessorRequest, result: Mapping[str, Any]
) -> tuple[ValidatedAssessment, ...]:
    """Validate and canonicalize one production-shaped assessor result.

    All monitors must be represented exactly once.  Recorded replay/exposure
    ancestry overrides an assessor's claim of independence, so a row with a
    known inherited source cannot claim ``no_identified_link``.
    """

    top = _mapping(result, "assessor result")
    unknown_fields = set(top) - {"schema_version", "assessments"}
    if unknown_fields:
        raise AssessorValidationError(
            "unknown assessor result field(s): " + ", ".join(sorted(unknown_fields))
        )
    if top.get("schema_version") != ASSESSOR_SCHEMA_VERSION:
        raise AssessorValidationError("unsupported assessor result schema version")
    rows = top.get("assessments")
    if not isinstance(rows, list):
        raise AssessorValidationError("assessments must be an array")
    expected = {monitor.monitor_id: monitor for monitor in request.monitors}
    if len(rows) != len(expected):
        raise AssessorValidationError("every required monitor must have exactly one row")
    seen: set[str] = set()
    sources = _source_map(request)
    known_ancestry = bool(request.memory_exposure or request.replay_ancestry)
    validated: list[ValidatedAssessment] = []
    for index, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"assessments[{index}]")
        monitor_id = _text(row.get("monitor_id"), f"assessments[{index}].monitor_id")
        monitor = expected.get(monitor_id)
        if monitor is None:
            raise AssessorValidationError(f"unknown monitor row: {monitor_id}")
        if monitor_id in seen:
            raise AssessorValidationError(f"duplicate monitor row: {monitor_id}")
        seen.add(monitor_id)
        status = _text(row.get("status"), f"monitor {monitor_id}.status")
        support = _text(row.get("relation_support"), f"monitor {monitor_id}.relation_support")
        expression = _text(row.get("expression_status"), f"monitor {monitor_id}.expression_status")
        dependence = _text(row.get("dependence"), f"monitor {monitor_id}.dependence")
        if status not in ASSESSMENT_STATUSES:
            raise AssessorValidationError(f"unsupported monitor status: {status}")
        if support not in RELATION_SUPPORT:
            raise AssessorValidationError(f"unsupported relation support: {support}")
        if expression not in EXPRESSION_STATUS:
            raise AssessorValidationError(f"unsupported expression status: {expression}")
        if dependence not in DEPENDENCE_CATEGORIES:
            raise AssessorValidationError(f"unsupported dependence category: {dependence}")
        coverage = _validate_coverage(request, monitor, row.get("coverage"), status)
        evidence: EvidenceQuote | None = None
        if status == "present":
            evidence_raw = _mapping(row.get("evidence"), f"monitor {monitor_id}.evidence")
            source_slot = _text(evidence_raw.get("source_slot"), "evidence.source_slot")
            source = sources.get(source_slot)
            if source is None or source_slot not in monitor.required_source_slots:
                raise AssessorValidationError(
                    f"monitor {monitor_id} evidence references the wrong source slot"
                )
            evidence = _unique_quote(source, evidence_raw.get("quote"), monitor_id)
        elif row.get("evidence") is not None:
            raise AssessorValidationError(
                f"monitor {monitor_id} {status} must not include evidence quotation"
            )
        if known_ancestry and dependence == "no_identified_link":
            raise AssessorValidationError(
                f"monitor {monitor_id} claims independence despite recorded ancestry"
            )
        group = row.get("dependence_group")
        if group is not None:
            _text(group, f"monitor {monitor_id}.dependence_group")
        validated.append(
            ValidatedAssessment(
                monitor_id,
                status,
                support,
                expression,
                dependence,
                coverage,
                evidence,
                cast(str | None, group),
            )
        )
    return tuple(validated)


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
                    "Return raw JSON only. Do not use Markdown fences or prose. "
                    "Return exactly one assessment row for every requested monitor. "
                    "Use only the declared status, relation_support, expression_status, "
                    "and dependence enum values.\n\n"
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
) -> tuple[ValidatedAssessment, ...]:
    """Apply generic validation plus the fixed Q1/Q2/Q3 assertions."""

    rows = validate_assessor_result(case.request, result)
    by_id = {row.monitor_id: row for row in rows}
    for monitor_id, expected in case.expected.items():
        row = by_id[monitor_id]
        for field_name, expected_value in expected.items():
            if getattr(row, field_name) != expected_value:
                raise AssessorValidationError(
                    f"{case.case_id} monitor {monitor_id} has wrong {field_name}: "
                    f"expected {expected_value!r}, got {getattr(row, field_name)!r}"
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
            AssessorMonitor("latch", {"relation": "causes"}, ("s0",)),
            AssessorMonitor("echo", {"relation": "causes"}, ("s1",)),
            AssessorMonitor("unrelated", {"relation": "causes", "to": "unrelated"}, ("s0",)),
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
            AssessorMonitor("jacket_direction", {"relation": "raises"}, ("s0",)),
            AssessorMonitor("shade", {"relation": "raises"}, ("s1", "s2")),
        ),
        memory_exposure=(
            {"source_slot": "s1", "exposure_id": "memory-1", "dependence": "replay_linked"},
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
            AssessorMonitor("dial", {"relation": "stops"}, ("s0",)),
            AssessorMonitor("unavailable_output", {"relation": "stops"}, ("s1",)),
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
                    "dependence": "external_supported",
                },
                "echo": {
                    "status": "present",
                    "relation_support": "supported",
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
                    "relation_support": "unsupported",
                    "expression_status": "expressed",
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
    "AssessorMonitor",
    "AssessorRequest",
    "AssessorSource",
    "AssessorValidationError",
    "EvidenceQuote",
    "QualificationCase",
    "ValidatedAssessment",
    "assessor_generation_request",
    "qualification_cases",
    "validate_qualification_case",
    "validate_assessor_result",
]
