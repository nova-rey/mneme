"""Temporary semantic evidence reconciliation for the Phase Two pilot.

The exact residue validator remains authoritative.  This module only prepares
the narrow language judgment needed when a proposed quotation is semantically
plausible but cannot be found byte-for-byte in the immutable source.  It never
computes provenance, offsets, learner credit, or developmental consequences.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from ..contracts import GenerationRequest


class EvidenceReviewError(ValueError):
    """A bounded evidence review cannot be safely reconciled."""


PathPart = str | int


@dataclass(frozen=True)
class EvidenceCandidate:
    """One unresolved extractor quotation and its owning residue records."""

    paths: tuple[tuple[PathPart, ...], ...]
    source_slot: str
    source_text: str
    source_role: str
    proposed_quote: str
    proposition: Mapping[str, Any]
    reason: str


@dataclass(frozen=True)
class EvidenceReview:
    """Validated semantic reviewer response before source resolution."""

    grounded: bool | None
    quote: str | None


def _proposition(record: Mapping[str, Any]) -> dict[str, Any]:
    if {"from", "to", "relationship"} <= set(record):
        return {
            "kind": "relationship",
            "from": str(record["from"]),
            "relation": str(record["relationship"]),
            "to": str(record["to"]),
        }
    if {"key", "label", "kind"} <= set(record):
        return {
            "kind": "concept",
            "key": str(record["key"]),
            "label": str(record["label"]),
            "concept_kind": str(record["kind"]),
        }
    if "edge_keys" in record:
        return {
            "kind": "route",
            "key": str(record.get("key", "")),
            "edge_keys": record["edge_keys"],
        }
    return {"kind": "assertion"}


def _matches(source: str, quote: str) -> list[int]:
    if not quote:
        return []
    result: list[int] = []
    start = 0
    while True:
        found = source.find(quote, start)
        if found < 0:
            return result
        result.append(found)
        start = found + 1


def collect_unresolved_evidence(
    payload: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
) -> tuple[EvidenceCandidate, ...]:
    """Collect only quote failures; structural failures remain fail-closed."""

    source_by_slot: dict[str, tuple[str, str]] = {}
    for source in source_records:
        slot = source.get("slot")
        content = source.get("content")
        if isinstance(slot, str) and isinstance(content, str):
            source_by_slot[slot] = (content, str(source.get("role", "unknown")))
    candidates: dict[tuple[str, str, str], list[tuple[PathPart, ...]]] = {}

    def walk(value: Any, path: tuple[PathPart, ...], proposition: Mapping[str, Any]) -> None:
        if isinstance(value, Mapping):
            current = _proposition(value) if any(
                key in value
                for key in ("from", "to", "relationship", "key", "label", "kind", "edge_keys")
            ) else proposition
            evidence = value.get("evidence")
            if isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
                for index, item in enumerate(evidence):
                    if not isinstance(item, Mapping):
                        continue
                    source_slot = item.get("source")
                    quote = item.get("evidence")
                    if not isinstance(source_slot, str) or not isinstance(quote, str):
                        continue
                    source = source_by_slot.get(source_slot)
                    if source is None:
                        raise EvidenceReviewError(
                            f"evidence source slot is unavailable: {source_slot}"
                        )
                    positions = _matches(source[0], quote)
                    if len(positions) == 1:
                        continue
                    key = (source_slot, quote, json.dumps(dict(current), sort_keys=True))
                    candidates.setdefault(key, []).append(path + ("evidence", index))
            for key, child in value.items():
                if key != "evidence":
                    walk(child, path + (str(key),), current)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for index, child in enumerate(value):
                walk(child, path + (index,), proposition)

    for field, value in payload.items():
        if isinstance(value, (list, tuple)):
            walk(value, (field,), {"kind": "assertion"})
    output: list[EvidenceCandidate] = []
    for key, paths in candidates.items():
        source_slot, quote, proposition_json = key
        source_text, source_role = source_by_slot[source_slot]
        positions = _matches(source_text, quote)
        output.append(
            EvidenceCandidate(
                tuple(paths),
                source_slot,
                source_text,
                source_role,
                quote,
                cast(Mapping[str, Any], json.loads(proposition_json)),
                "missing" if not positions else "ambiguous",
            )
        )
    return tuple(output)


def reviewer_request(candidate: EvidenceCandidate) -> GenerationRequest:
    body = json.dumps(
        {
            "source_slot": candidate.source_slot,
            "source_role": candidate.source_role,
            "source": candidate.source_text,
            "proposition": dict(candidate.proposition),
            "proposed_evidence": candidate.proposed_quote,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return GenerationRequest(
        messages=({"role": "user", "content": body},),
        system=(
            "You are a temporary semantic evidence reviewer. Decide only whether the "
            "immutable source expresses/supports the extracted proposition as claimed. "
            "Return raw JSON with exactly grounded and, when grounded is true, "
            "evidence. grounded must be true, false, or unknown. If true, evidence "
            "must be one exact verbatim quotation copied from source. If grounded is "
            "false or unknown, omit evidence or use a logically empty value (null, empty "
            "string, object, or list). Do not provide a quotation in those cases. Do not calculate "
            "offsets, infer provenance, change the proposition, assign credit, or add "
            "any other fields."
        ),
        parameters={"temperature": 0, "max_new_tokens": 768},
    )


def validate_reviewer_result(content: str) -> EvidenceReview:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise EvidenceReviewError("reviewer result is not JSON") from exc
    if not isinstance(value, Mapping) or set(value) - {"grounded", "evidence"}:
        raise EvidenceReviewError("reviewer result has an invalid shape")
    grounded = value.get("grounded")
    if grounded is True:
        quote = value.get("evidence")
        if not isinstance(quote, str) or not quote:
            raise EvidenceReviewError("grounded reviewer result requires evidence")
        return EvidenceReview(True, quote)
    if grounded is False:
        if "evidence" in value and not _is_empty_evidence(value["evidence"]):
            raise EvidenceReviewError("false reviewer result must not include evidence")
        return EvidenceReview(False, None)
    if grounded == "unknown":
        if "evidence" in value and not _is_empty_evidence(value["evidence"]):
            raise EvidenceReviewError("unknown reviewer result must not include evidence")
        return EvidenceReview(None, None)
    raise EvidenceReviewError("grounded must be true, false, or unknown")


def _is_empty_evidence(value: Any) -> bool:
    """Return whether a reviewer placeholder carries no quotation."""

    return value is None or value == "" or value == {} or value == []


def resolve_review(candidate: EvidenceCandidate, review: EvidenceReview) -> str:
    if review.grounded is not True or review.quote is None:
        raise EvidenceReviewError("reviewer did not ground evidence")
    if len(_matches(candidate.source_text, review.quote)) != 1:
        raise EvidenceReviewError("reviewer quotation is missing or ambiguous")
    return review.quote


def apply_replacements(
    payload: Mapping[str, Any], replacements: Mapping[tuple[PathPart, ...], str]
) -> dict[str, Any]:
    result: dict[str, Any] = copy.deepcopy(dict(payload))
    for path, quote in replacements.items():
        current: Any = result
        for part in path[:-1]:
            current = current[part]
        item = current[path[-1]]
        if not isinstance(item, dict):
            raise EvidenceReviewError("evidence path is not mutable")
        item["evidence"] = quote
    return result


__all__ = [
    "EvidenceCandidate",
    "EvidenceReview",
    "EvidenceReviewError",
    "apply_replacements",
    "collect_unresolved_evidence",
    "resolve_review",
    "reviewer_request",
    "validate_reviewer_result",
]
