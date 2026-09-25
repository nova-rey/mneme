"""Small, auditable adapters for specialist relation extraction.

The specialist is an observation instrument, not an MNEME state writer.  It
returns source-language spans and the model's relation phrase.  Canonical
identities, provenance, admission, and learner transitions remain owned by
the existing memory pipeline.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

SPECIALIST_EXTRACTOR_VERSION = "gliner2.5-base-v1-relations-v1"


@dataclass(frozen=True)
class RawRelationshipObservation:
    """One source-grounded observation emitted by a specialist model."""

    subject: str
    relation: str
    object: str
    source_slot: str
    subject_start: int
    subject_end: int
    object_start: int
    object_end: int
    score: float
    model: str
    model_revision: str | None = None
    chunk_index: int = 0

    @property
    def evidence_start(self) -> int:
        return min(self.subject_start, self.object_start)

    @property
    def evidence_end(self) -> int:
        return max(self.subject_end, self.object_end)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "source_slot": self.source_slot,
            "subject_span": {"start": self.subject_start, "end": self.subject_end},
            "object_span": {"start": self.object_start, "end": self.object_end},
            "evidence_span": {"start": self.evidence_start, "end": self.evidence_end},
            "score": self.score,
            "model": self.model,
            "model_revision": self.model_revision,
            "chunk_index": self.chunk_index,
        }

    def content_key(self) -> tuple[Any, ...]:
        """Stable duplicate key independent of UUIDs or insertion order."""

        return (
            self.source_slot,
            self.subject_start,
            self.subject_end,
            self.object_start,
            self.object_end,
            self.relation,
            self.subject,
            self.object,
        )


@dataclass(frozen=True)
class SpecialistExtraction:
    """Immutable raw result plus deterministic coverage metadata."""

    version: str
    model: str
    model_revision: str | None
    source_digests: Mapping[str, str]
    observations: tuple[RawRelationshipObservation, ...]
    coverage_complete: bool = True
    omitted_reason: str | None = None

    @property
    def content_digest(self) -> str:
        payload = {
            "version": self.version,
            "model": self.model,
            "model_revision": self.model_revision,
            "source_digests": dict(sorted(self.source_digests.items())),
            "observations": [o.to_dict() for o in self.observations],
            "coverage_complete": self.coverage_complete,
            "omitted_reason": self.omitted_reason,
        }
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "model": self.model,
            "model_revision": self.model_revision,
            "source_digests": dict(self.source_digests),
            "observations": [o.to_dict() for o in self.observations],
            "coverage_complete": self.coverage_complete,
            "omitted_reason": self.omitted_reason,
            "content_digest": self.content_digest,
        }


def _span(value: Any, path: str) -> tuple[int, int]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    start, end = value.get("start"), value.get("end")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
    ):
        raise ValueError(f"{path} must contain integer start/end")
    if start < 0 or end <= start:
        raise ValueError(f"{path} must be a non-empty half-open span")
    return start, end


def parse_gliner_relations(
    payload: Mapping[str, Any],
    sources: Mapping[str, str],
    *,
    model: str,
    model_revision: str | None = None,
    version: str = SPECIALIST_EXTRACTOR_VERSION,
    chunk_index: int = 0,
) -> SpecialistExtraction:
    """Parse GLiNER relation output without assigning canonical meaning.

    Invalid records are rejected item-wise.  A missing source or bad span
    never becomes an accepted relationship.  Duplicate overlapping chunks are
    deduplicated by content and source coordinates.
    """

    raw = payload.get("relation_extraction") if isinstance(payload, Mapping) else None
    if not isinstance(raw, Mapping):
        raise ValueError("specialist payload must contain relation_extraction")
    candidates: list[RawRelationshipObservation] = []
    for relation, values in raw.items():
        if not isinstance(relation, str) or not isinstance(values, list):
            continue
        for value in values:
            try:
                if not isinstance(value, Mapping):
                    continue
                head, tail = value.get("head"), value.get("tail")
                if not isinstance(head, Mapping) or not isinstance(tail, Mapping):
                    continue
                subject = head.get("text")
                obj = tail.get("text")
                if (
                    not isinstance(subject, str)
                    or not subject.strip()
                    or not isinstance(obj, str)
                    or not obj.strip()
                ):
                    continue
                source_slot = str(value.get("source_slot", "s0"))
                if source_slot not in sources:
                    continue
                subject_start, subject_end = _span(
                    {"start": head.get("start"), "end": head.get("end")}, "head"
                )
                object_start, object_end = _span(
                    {"start": tail.get("start"), "end": tail.get("end")}, "tail"
                )
                source = sources[source_slot]
                if (
                    source[subject_start:subject_end] != subject
                    or source[object_start:object_end] != obj
                ):
                    continue
                score = value.get("confidence")
                if score is None:
                    head_score = head.get("confidence")
                    tail_score = tail.get("confidence")
                    if isinstance(head_score, (int, float)) and not isinstance(
                        head_score, bool
                    ):
                        if isinstance(tail_score, (int, float)) and not isinstance(
                            tail_score, bool
                        ):
                            score = min(float(head_score), float(tail_score))
                        else:
                            score = head_score
                    elif isinstance(tail_score, (int, float)) and not isinstance(tail_score, bool):
                        score = tail_score
                    else:
                        score = 0.0
                if isinstance(score, bool) or not isinstance(score, (int, float)):
                    continue
                if not 0.0 <= float(score) <= 1.0:
                    continue
                candidates.append(
                    RawRelationshipObservation(
                        subject=subject,
                        relation=relation,
                        object=obj,
                        source_slot=source_slot,
                        subject_start=subject_start,
                        subject_end=subject_end,
                        object_start=object_start,
                        object_end=object_end,
                        score=float(score),
                        model=model,
                        model_revision=model_revision,
                        chunk_index=chunk_index,
                    )
                )
            except (TypeError, ValueError, KeyError):
                continue
    unique: dict[tuple[Any, ...], RawRelationshipObservation] = {}
    for candidate in sorted(candidates, key=lambda item: (item.content_key(), -item.score)):
        unique.setdefault(candidate.content_key(), candidate)
    digests = {
        slot: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for slot, text in sorted(sources.items())
    }
    return SpecialistExtraction(
        version=version,
        model=model,
        model_revision=model_revision,
        source_digests=digests,
        observations=tuple(unique.values()),
    )


def observations_to_minimal_payload(
    extraction: SpecialistExtraction,
    sources: Mapping[str, str],
    *,
    supported_relations: frozenset[str],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Create a strict downstream payload while retaining raw dispositions.

    The raw relation phrase is never rewritten here.  Only an exact member of
    the already approved downstream vocabulary can enter the existing
    source-grounding/assessment path; other observations remain auditable
    rejections instead of being silently coerced.
    """

    relationships: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for index, observation in enumerate(extraction.observations):
        if observation.relation not in supported_relations:
            decisions.append(
                {
                    "index": index,
                    "kind": "unsupported_specialist_relation",
                    "relation": observation.relation,
                    "status": "rejected",
                }
            )
            continue
        evidence = sources[observation.source_slot][
            observation.evidence_start : observation.evidence_end
        ]
        relationships.append(
            {
                "from": observation.subject,
                "relation": observation.relation,
                "to": observation.object,
                "source": observation.source_slot,
                "evidence": evidence,
            }
        )
        decisions.append(
            {
                "index": index,
                "kind": "specialist_observation",
                "relation": observation.relation,
                "status": "forwarded",
            }
        )
    return {"relationships": relationships}, tuple(decisions)


def observations_to_residue_payload(
    extraction: SpecialistExtraction,
    sources: Mapping[str, str],
    *,
    supported_relations: frozenset[str],
    episode_id: str | None = None,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Build the existing residue shape without the provider six-item cap.

    This is the specialist bridge: the model may return a variable number of
    source-grounded observations, while existing admission still applies its
    storage/resource bounds and the normal semantic pipeline remains the
    authority for acceptance.
    """

    concepts: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    def key(label: str) -> str:
        return "c-" + hashlib.sha256(label.casefold().encode("utf-8")).hexdigest()[:24]

    for index, observation in enumerate(extraction.observations):
        if observation.relation not in supported_relations:
            decisions.append(
                {
                    "index": index,
                    "kind": "unsupported_specialist_relation",
                    "relation": observation.relation,
                    "status": "rejected",
                }
            )
            continue
        source = sources[observation.source_slot]
        evidence_text = source[observation.evidence_start : observation.evidence_end]
        evidence = [{"source": observation.source_slot, "evidence": evidence_text}]
        from_key, to_key = key(observation.subject), key(observation.object)
        concepts.setdefault(
            from_key,
            {
                "key": from_key,
                "label": observation.subject,
                "kind": "concept",
                "evidence": evidence,
                # The specialist score is preserved in context.  The existing
                # residue confidence is an admission floor, not a learned
                # weight, so candidates remain available for semantic review.
                "confidence": max(0.70, observation.score),
                "context": [f"specialist_score={observation.score:.6f}"],
            },
        )
        concepts.setdefault(
            to_key,
            {
                "key": to_key,
                "label": observation.object,
                "kind": "concept",
                "evidence": evidence,
                "confidence": max(0.70, observation.score),
                "context": [f"specialist_score={observation.score:.6f}"],
            },
        )
        edge_material = {
            "from": from_key,
            "to": to_key,
            "relationship": observation.relation,
            "evidence": evidence,
        }
        edge_key = "e-" + hashlib.sha256(
            json.dumps(
                edge_material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()[:24]
        edges.append(
            {
                "key": edge_key,
                "from": from_key,
                "to": to_key,
                "relationship": observation.relation,
                "evidence": evidence,
                "confidence": max(0.70, observation.score),
                "context": [f"specialist_score={observation.score:.6f}"],
            }
        )
        decisions.append(
            {
                "index": index,
                "kind": "specialist_observation",
                "relation": observation.relation,
                "status": "forwarded",
                "score": observation.score,
            }
        )
    payload: dict[str, Any] = {
        "core_concepts": list(concepts.values()),
        "edge_candidates": edges,
        "route_candidates": [],
    }
    if episode_id is not None:
        payload["episode_id"] = episode_id
    return payload, tuple(decisions)


__all__ = [
    "SPECIALIST_EXTRACTOR_VERSION",
    "RawRelationshipObservation",
    "SpecialistExtraction",
    "observations_to_minimal_payload",
    "observations_to_residue_payload",
    "parse_gliner_relations",
]
