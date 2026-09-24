"""Validation and immutable contracts for the Phase One residue format.

The residue is an annotation of a bounded, explicitly supplied set of source
slots.  It is deliberately kept separate from persistence and from graph
selection: validating a residue does not make any claim that its assertions
are true, and it does not make the residue available to a model.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, cast

MAX_CONCEPTS = 16
MAX_RELATIONSHIPS = 24
MAX_ROUTES = 8
MAX_AUXILIARY_RECORDS = 8
MAX_ROUTE_EDGES = 3
MAX_SPANS_PER_ITEM = 8
MAX_LABEL_LENGTH = 160
MAX_CONTEXT_LENGTH = 64
MAX_RESIDUE_BYTES = 24 * 1024
# This is a narrow acquisition-boundary normalization.  It preserves the
# extractor's raw result while translating one source-supported equivalent
# label and rejecting unrelated unsupported items without discarding valid
# residue items.
RELATIONSHIP_RECONCILIATION_VERSION = "relationship-normalization-v1"
RELATIONSHIP_ALIASES = {"holds": "retains"}
# This is an admission/uncertainty threshold only.  It is deliberately not
# carried into graph selection as a weight or accessibility bonus.
DEFAULT_ADMISSION_CONFIDENCE_THRESHOLD = 0.70

SUPPORTED_CONCEPT_KINDS = frozenset(
    {
        "concept",
        "entity",
        "topic",
        "pattern",
        "behavior",
        "constraint",
        "value",
        "strategy",
        "resource",
        "fact",
        "event",
        "person",
        "object",
        "process",
        "question",
        "trait",
        "style",
        "warning",
        "identity",
    }
)
SUPPORTED_RELATIONSHIP_KINDS = frozenset(
    {
        "association",
        "analogy",
        "causal",
        "contrast",
        "dependency",
        "explanation",
        "related",
        "semantic",
        "temporal",
        "contradiction",
        "user-specific",
        "style",
        "habit",
        "warning",
        "identity",
        "task-utility",
        "reasoning-strategy",
        "conversational-pattern",
        "constrains",
        "supports",
        "retains",
        "depends-on",
        "depends_on",
        "enables",
        "explains",
        "refines",
        "corrects",
        "causes",
        "caused-by",
        "caused_by",
        "part-of",
        "part_of",
        "same-as",
        "same_as",
    }
)

_TOP_LEVEL_FIELDS = frozenset(
    {
        "store",
        "episode_id",
        "core_concepts",
        "salient_phrases",
        "observed_patterns",
        "edge_candidates",
        "route_candidates",
        "declared_memories",
        "earned_candidates",
        "identity_candidates",
        "developmental_observation_refs",
        "evidence_refs",
        "extraction_confidence",
        "intrusion_risk_estimate",
    }
)

_RECORD_FIELDS = frozenset(
    {
        "id",
        "key",
        "label",
        "kind",
        "node_type",
        "relationship",
        "edge_type",
        "polarity",
        "from",
        "to",
        "from_concept",
        "to_concept",
        "source_slot",
        "evidence",
        "source_spans",
        "spans",
        "evidence_refs",
        "source_refs",
        "context",
        "valid_contexts",
        "confidence",
        "salience",
        "uncertainty",
        "subject",
        "referent",
        "subject_ref",
        "referent_ref",
        "edge_keys",
        "edges",
        "route",
        "origin",
        "attribution",
        "text",
        "value",
        "scope",
        "target",
        "proposal",
        "self_referential",
    }
)


class ResidueValidationError(ValueError):
    """Raised when a model-returned residue is not a valid residue v1."""


@dataclass(frozen=True)
class SourceSpan:
    """A half-open Unicode code-point span in one request-local source slot."""

    source_slot: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        return {"source_slot": self.source_slot, "start": self.start, "end": self.end}

    def extract(self, sources: Mapping[str, str]) -> str:
        return sources[self.source_slot][self.start : self.end]


@dataclass(frozen=True)
class Residue:
    """Validated immutable residue data.

    Records are exposed as tuples of read-only-by-convention dictionaries.  A
    fresh deep copy is returned by :meth:`to_dict`, so callers cannot mutate
    the validated representation through the serialization API.
    """

    data: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(self.data))

    @property
    def episode_id(self) -> str | None:
        value = self.data.get("episode_id")
        return value if isinstance(value, str) else None

    @property
    def core_concepts(self) -> tuple[Mapping[str, Any], ...]:
        return cast(tuple[Mapping[str, Any], ...], self.data["core_concepts"])

    @property
    def edge_candidates(self) -> tuple[Mapping[str, Any], ...]:
        return cast(tuple[Mapping[str, Any], ...], self.data["edge_candidates"])

    @property
    def route_candidates(self) -> tuple[Mapping[str, Any], ...]:
        return cast(tuple[Mapping[str, Any], ...], self.data["route_candidates"])

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], _thaw(self.data))

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict()).encode("utf-8")

    @property
    def content_digest(self) -> str:
        """Digest of the validated residue, independent of map insertion order."""

        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def canonical_json(value: Any) -> str:
    """Serialize JSON-compatible values deterministically."""

    try:
        return json.dumps(_thaw(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ResidueValidationError("residue contains a non-JSON value") from exc


def normalize_label(value: str) -> str:
    """Normalize a label without discarding meaningful punctuation or negation."""

    if not isinstance(value, str):
        raise ResidueValidationError("label must be a string")
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if not normalized:
        raise ResidueValidationError("label must not be empty")
    if len(normalized) > MAX_LABEL_LENGTH:
        raise ResidueValidationError(f"label exceeds {MAX_LABEL_LENGTH} characters")
    return normalized


def _error(path: str, message: str) -> ResidueValidationError:
    return ResidueValidationError(f"{path}: {message}")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return copy.deepcopy(value)


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(path, "must be an object")
    for key in value:
        if not isinstance(key, str):
            raise _error(path, "field names must be strings")
    return value


def _require_string(value: Any, path: str, *, max_length: int | None = None) -> str:
    if not isinstance(value, str):
        raise _error(path, "must be a string")
    if not value:
        raise _error(path, "must not be empty")
    if max_length is not None and len(value) > max_length:
        raise _error(path, f"exceeds {max_length} characters")
    return value


def _require_number(value: Any, path: str, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(path, "must be a finite number, not a boolean")
    converted = float(value)
    if not math.isfinite(converted) or not minimum <= converted <= maximum:
        raise _error(path, f"must be finite and in [{minimum}, {maximum}]")
    return converted


def _list(value: Any, path: str, *, maximum: int | None = None) -> list[Any]:
    if not isinstance(value, list):
        raise _error(path, "must be an array")
    if maximum is not None and len(value) > maximum:
        raise _error(path, f"contains more than {maximum} items")
    return value


def _validate_span(value: Any, path: str, sources: Mapping[str, str]) -> dict[str, Any]:
    span = _require_mapping(value, path)
    allowed = {"source_slot", "start", "end"}
    unknown = set(span) - allowed
    if unknown:
        raise _error(path, f"unknown fields: {sorted(unknown)}")
    if set(span) != allowed:
        raise _error(path, "requires source_slot, start, and end")
    source_slot = _require_string(span["source_slot"], f"{path}.source_slot")
    if source_slot not in sources:
        raise _error(path, f"fabricated or unavailable source slot {source_slot!r}")
    start, end = span["start"], span["end"]
    if isinstance(start, bool) or not isinstance(start, int):
        raise _error(f"{path}.start", "must be an integer")
    if isinstance(end, bool) or not isinstance(end, int):
        raise _error(f"{path}.end", "must be an integer")
    source_length = len(sources[source_slot])
    if start < 0 or end > source_length or start >= end:
        raise _error(path, "span must satisfy 0 <= start < end <= source length")
    return {"source_slot": source_slot, "start": start, "end": end}


def _spans(
    record: Mapping[str, Any],
    path: str,
    sources: Mapping[str, str],
    *,
    require_evidence_quotes: bool = False,
) -> tuple[dict[str, Any], ...]:
    fields = [name for name in ("evidence", "source_spans", "spans") if name in record]
    if len(fields) > 1:
        raise _error(path, "use only one of evidence, source_spans, or spans")
    if not fields:
        return ()
    if require_evidence_quotes and fields[0] != "evidence":
        raise _error(path, "model evidence requires quotation evidence")
    if fields[0] == "evidence":
        values = _list(record[fields[0]], f"{path}.evidence", maximum=MAX_SPANS_PER_ITEM)
        resolved: list[dict[str, Any]] = []
        for index, value in enumerate(values):
            evidence_path = f"{path}.evidence[{index}]"
            item = _require_mapping(value, evidence_path)
            unknown = set(item) - {"source", "evidence"}
            if unknown:
                raise _error(evidence_path, f"unknown fields: {sorted(unknown)}")
            if set(item) != {"source", "evidence"}:
                raise _error(evidence_path, "requires source and evidence")
            source_slot = _require_string(item["source"], f"{evidence_path}.source")
            if source_slot not in sources:
                raise _error(
                    evidence_path,
                    f"fabricated or unavailable source slot {source_slot!r}",
                )
            quotation = _require_string(item["evidence"], f"{evidence_path}.evidence")
            source_text = sources[source_slot]
            matches: list[int] = []
            search_from = 0
            while True:
                match = source_text.find(quotation, search_from)
                if match < 0:
                    break
                matches.append(match)
                search_from = match + 1
            if not matches:
                raise _error(
                    evidence_path,
                    "evidence quotation does not occur verbatim in source",
                )
            if len(matches) != 1:
                raise _error(
                    evidence_path,
                    "evidence quotation is ambiguous in source",
                )
            start = matches[0]
            end = start + len(quotation)
            span = {"source_slot": source_slot, "start": start, "end": end}
            if source_text[start:end] != quotation:
                raise _error(evidence_path, "derived span does not equal evidence quotation")
            resolved.append(span)
        return tuple(resolved)
    values = _list(record[fields[0]], f"{path}.{fields[0]}", maximum=MAX_SPANS_PER_ITEM)
    return tuple(
        _validate_span(value, f"{path}.{fields[0]}[{index}]", sources)
        for index, value in enumerate(values)
    )


def _record(
    value: Any,
    path: str,
    sources: Mapping[str, str],
    *,
    require_label: bool = False,
    require_evidence_quotes: bool = False,
) -> dict[str, Any]:
    record = _require_mapping(value, path)
    unknown = set(record) - _RECORD_FIELDS
    if unknown:
        raise _error(path, f"unknown fields: {sorted(unknown)}")
    result = copy.deepcopy(dict(record))
    if "label" in result:
        result["label"] = normalize_label(result["label"])
    elif require_label:
        raise _error(path, "requires label")
    if "context" in result:
        context = _list(result["context"], f"{path}.context", maximum=16)
        result["context"] = tuple(
            _require_string(item, f"{path}.context[{index}]", max_length=MAX_CONTEXT_LENGTH)
            for index, item in enumerate(context)
        )
    if "valid_contexts" in result:
        contexts = _list(result["valid_contexts"], f"{path}.valid_contexts", maximum=16)
        result["valid_contexts"] = tuple(
            _require_string(item, f"{path}.valid_contexts[{index}]", max_length=MAX_CONTEXT_LENGTH)
            for index, item in enumerate(contexts)
        )
    if "source_slot" in result:
        source_slot = _require_string(result["source_slot"], f"{path}.source_slot")
        if source_slot not in sources:
            raise _error(path, f"fabricated or unavailable source slot {source_slot!r}")
    for field in ("confidence", "salience", "uncertainty"):
        if field in result and result[field] is not None:
            result[field] = _require_number(result[field], f"{path}.{field}")
    result["source_spans"] = _spans(
        result,
        path,
        sources,
        require_evidence_quotes=require_evidence_quotes,
    )
    result.pop("evidence", None)
    result.pop("spans", None)
    return result


def _key(record: Mapping[str, Any], path: str) -> str:
    candidates = [name for name in ("key", "id") if name in record]
    if len(candidates) != 1:
        raise _error(path, "requires exactly one of key or id")
    return _require_string(record[candidates[0]], f"{path}.{candidates[0]}", max_length=160)


def _require_graph_admission(
    record: Mapping[str, Any],
    path: str,
    *,
    confidence_threshold: float,
) -> None:
    """Require provenance and admission evidence for graph-bearing records.

    A source span establishes where an assertion came from; confidence is an
    extraction/admission signal.  Neither becomes a later route-ranking
    weight.  Records without either field must not become graph state.
    """

    source_spans = record.get("source_spans", ())
    if not source_spans:
        raise _error(path, "graph material requires at least one source span")
    confidence = record.get("confidence")
    if confidence is None:
        raise _error(path, "graph material requires confidence")
    confidence_value = _require_number(confidence, f"{path}.confidence")
    if confidence_value < confidence_threshold:
        raise _error(
            f"{path}.confidence",
            f"must meet admission threshold {confidence_threshold:.2f}",
        )


def validate_graph_admission(
    residue: Residue,
    *,
    confidence_threshold: float = DEFAULT_ADMISSION_CONFIDENCE_THRESHOLD,
) -> None:
    """Validate graph admission on an already normalized residue.

    This second boundary is used by publication so a manually constructed or
    deserialized :class:`Residue` cannot bypass the source-backed admission
    rules.  Full source-slot and offset validation remains the responsibility
    of :func:`validate_residue`.
    """

    threshold = _require_number(
        confidence_threshold, "confidence_threshold", minimum=0.0, maximum=1.0
    )
    for field in ("core_concepts", "edge_candidates", "route_candidates"):
        records = residue.data.get(field, ())
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                raise ResidueValidationError(f"residue.{field}[{index}]: must be an object")
            _require_graph_admission(
                record,
                f"residue.{field}[{index}]",
                confidence_threshold=threshold,
            )


def validate_residue(
    payload: Mapping[str, Any],
    sources: Mapping[str, str] | None = None,
    *,
    source_slots: Mapping[str, str] | None = None,
    confidence_threshold: float = DEFAULT_ADMISSION_CONFIDENCE_THRESHOLD,
    require_evidence_quotes: bool = False,
) -> Residue:
    """Validate and return a normalized immutable residue.

    ``sources``/``source_slots`` is the complete request-local slot map. Every
    span must point into it, which prevents a model response from inventing a
    source or smuggling an external episode identifier into evidence. When
    ``require_evidence_quotes`` is true, graph records must use model-facing
    quotation evidence; numeric ``source_spans`` remain available to callers
    constructing canonical/internal residues directly.
    """

    if sources is None:
        sources = source_slots
    elif source_slots is not None and sources != source_slots:
        raise ResidueValidationError("sources and source_slots disagree")
    if sources is None:
        raise ResidueValidationError("source slots are required")

    threshold = _require_number(
        confidence_threshold, "confidence_threshold", minimum=0.0, maximum=1.0
    )

    root = _require_mapping(payload, "residue")
    unknown = set(root) - _TOP_LEVEL_FIELDS
    if unknown:
        raise _error("residue", f"unknown fields: {sorted(unknown)}")
    if not isinstance(sources, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in sources.items()
    ):
        raise ResidueValidationError("sources must map string slots to string content")
    normalized: dict[str, Any] = {}
    if "store" in root:
        if not isinstance(root["store"], bool):
            raise _error("residue.store", "must be boolean")
        normalized["store"] = root["store"]
    if "episode_id" in root:
        normalized["episode_id"] = _require_string(root["episode_id"], "residue.episode_id")
    if "extraction_confidence" in root and root["extraction_confidence"] is not None:
        normalized["extraction_confidence"] = _require_number(
            root["extraction_confidence"], "residue.extraction_confidence"
        )
    if "intrusion_risk_estimate" in root and root["intrusion_risk_estimate"] is not None:
        normalized["intrusion_risk_estimate"] = _require_number(
            root["intrusion_risk_estimate"], "residue.intrusion_risk_estimate"
        )

    concepts_raw = _list(
        root.get("core_concepts", []), "residue.core_concepts", maximum=MAX_CONCEPTS
    )
    concepts: list[dict[str, Any]] = []
    concept_keys: set[str] = set()
    for index, value in enumerate(concepts_raw):
        record = _record(
            value,
            f"residue.core_concepts[{index}]",
            sources,
            require_label=True,
            require_evidence_quotes=require_evidence_quotes,
        )
        key = _key(record, f"residue.core_concepts[{index}]")
        if key in concept_keys:
            raise _error("residue.core_concepts", f"duplicate key {key!r}")
        concept_keys.add(key)
        kind = record.get("kind", record.get("node_type", "concept"))
        if not isinstance(kind, str) or kind not in SUPPORTED_CONCEPT_KINDS:
            raise _error(f"residue.core_concepts[{index}].kind", "unsupported concept kind")
        _require_graph_admission(
            record,
            f"residue.core_concepts[{index}]",
            confidence_threshold=threshold,
        )
        record["key"] = key
        record["kind"] = kind
        concepts.append(record)
    normalized["core_concepts"] = tuple(concepts)

    edges_raw = _list(
        root.get("edge_candidates", []),
        "residue.edge_candidates",
        maximum=MAX_RELATIONSHIPS,
    )
    edges: list[dict[str, Any]] = []
    edge_keys: set[str] = set()
    for index, value in enumerate(edges_raw):
        path = f"residue.edge_candidates[{index}]"
        record = _record(value, path, sources, require_evidence_quotes=require_evidence_quotes)
        key = _key(record, path)
        if key in edge_keys:
            raise _error("residue.edge_candidates", f"duplicate key {key!r}")
        edge_keys.add(key)
        source = record.get("from", record.get("from_concept"))
        target = record.get("to", record.get("to_concept"))
        if not isinstance(source, str) or not isinstance(target, str):
            raise _error(path, "requires from/to concept keys")
        if source not in concept_keys or target not in concept_keys:
            raise _error(path, "relationship endpoint does not reference a concept")
        relationship = record.get("relationship", record.get("edge_type", "association"))
        if not isinstance(relationship, str) or relationship not in SUPPORTED_RELATIONSHIP_KINDS:
            raise _error(path, "unsupported relationship kind")
        _require_graph_admission(record, path, confidence_threshold=threshold)
        record.update({"key": key, "from": source, "to": target, "relationship": relationship})
        edges.append(record)
    normalized["edge_candidates"] = tuple(edges)

    routes_raw = _list(
        root.get("route_candidates", []),
        "residue.route_candidates",
        maximum=MAX_ROUTES,
    )
    routes: list[dict[str, Any]] = []
    route_keys: set[str] = set()
    for index, value in enumerate(routes_raw):
        path = f"residue.route_candidates[{index}]"
        record = _record(value, path, sources, require_evidence_quotes=require_evidence_quotes)
        key = _key(record, path)
        if key in route_keys:
            raise _error("residue.route_candidates", f"duplicate key {key!r}")
        route_keys.add(key)
        edge_refs = record.get("edge_keys", record.get("edges"))
        if not isinstance(edge_refs, list) or not 1 <= len(edge_refs) <= MAX_ROUTE_EDGES:
            raise _error(path, "requires one to three edge references")
        if any(not isinstance(ref, str) for ref in edge_refs) or len(set(edge_refs)) != len(
            edge_refs
        ):
            raise _error(path, "edge references must be unique strings")
        if any(ref not in edge_keys for ref in edge_refs):
            raise _error(path, "route references a missing relationship")
        _require_graph_admission(record, path, confidence_threshold=threshold)
        route_edges = [next(edge for edge in edges if edge["key"] == ref) for ref in edge_refs]
        for left, right in zip(route_edges, route_edges[1:]):
            if left["to"] != right["from"]:
                raise _error(path, "route edges are discontinuous or reversed")
        record["key"] = key
        record["edge_keys"] = tuple(edge_refs)
        record.pop("edges", None)
        routes.append(record)
    normalized["route_candidates"] = tuple(routes)

    for field in (
        "salient_phrases",
        "observed_patterns",
        "declared_memories",
        "earned_candidates",
        "identity_candidates",
    ):
        values = _list(root.get(field, []), f"residue.{field}", maximum=MAX_AUXILIARY_RECORDS)
        records: list[dict[str, Any]] = []
        keys: set[str] = set()
        for index, value in enumerate(values):
            path = f"residue.{field}[{index}]"
            if field == "salient_phrases" and isinstance(value, str):
                record = {"label": normalize_label(value), "source_spans": ()}
            else:
                record = _record(
                    value,
                    path,
                    sources,
                    require_evidence_quotes=require_evidence_quotes,
                )
            if "key" in record or "id" in record:
                key = _key(record, path)
                if key in keys:
                    raise _error(f"residue.{field}", f"duplicate key {key!r}")
                keys.add(key)
                record["key"] = key
            records.append(record)
        normalized[field] = tuple(records)
    for field in ("developmental_observation_refs", "evidence_refs"):
        values = _list(root.get(field, []), f"residue.{field}", maximum=MAX_AUXILIARY_RECORDS)
        normalized[field] = tuple(
            _require_string(value, f"residue.{field}[{index}]" )
            for index, value in enumerate(values)
        )

    encoded = canonical_json(normalized).encode("utf-8")
    if len(encoded) > MAX_RESIDUE_BYTES:
        raise ResidueValidationError(f"residue exceeds {MAX_RESIDUE_BYTES} UTF-8 bytes")
    residue = Residue(_freeze(normalized))
    validate_graph_admission(residue, confidence_threshold=threshold)
    return residue


def normalize_relationship_items(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Normalize one approved alias and reject unrelated edge items.

    This is deliberately narrower than residue validation.  Only a well-shaped
    edge with a stable key is eligible for alias normalization or item-level
    rejection.  Other malformed structures continue through
    :func:`validate_residue` and fail closed.  Route candidates that depend on
    a rejected edge are rejected as well; no route is invented.

    The returned payload is a fresh copy, so the raw provider result remains
    durable and auditable alongside the normalized/admitted residue.  The
    second result contains both alias decisions and rejected-item records.
    """

    normalized = copy.deepcopy(dict(payload))
    raw_edges = normalized.get("edge_candidates")
    if not isinstance(raw_edges, list):
        return normalized, ()
    kept_edges: list[Any] = []
    rejected_keys: set[str] = set()
    rejected: list[dict[str, Any]] = []
    for index, value in enumerate(raw_edges):
        if not isinstance(value, Mapping):
            kept_edges.append(value)
            continue
        relationship = value.get("relationship", value.get("edge_type", "association"))
        key = value.get("key", value.get("id"))
        if (
            isinstance(relationship, str)
            and isinstance(key, str)
            and bool(key)
        ):
            alias = RELATIONSHIP_ALIASES.get(relationship)
            if alias is not None:
                normalized_value = dict(value)
                normalized_value["relationship"] = alias
                kept_edges.append(normalized_value)
                rejected.append(
                    {
                        "kind": "relationship_alias",
                        "path": f"residue.edge_candidates[{index}]",
                        "key": key,
                        "raw_relationship": relationship,
                        "normalized_relationship": alias,
                        "reason": (
                            "source-supported retention wording is normalized to the "
                            "canonical retains relation"
                        ),
                        "raw_record": dict(value),
                    }
                )
                continue
            if relationship in SUPPORTED_RELATIONSHIP_KINDS:
                kept_edges.append(value)
                continue
            rejected_keys.add(key)
            rejected.append(
                {
                    "kind": "unsupported_relationship",
                    "path": f"residue.edge_candidates[{index}]",
                    "key": key,
                    "relationship": relationship,
                    "reason": "relationship kind is outside the approved vocabulary",
                    "raw_record": dict(value),
                }
            )
            continue
        kept_edges.append(value)
    normalized["edge_candidates"] = kept_edges

    raw_routes = normalized.get("route_candidates")
    if isinstance(raw_routes, list):
        kept_routes: list[Any] = []
        for index, value in enumerate(raw_routes):
            if not isinstance(value, Mapping):
                kept_routes.append(value)
                continue
            refs = value.get("edge_keys", value.get("edges"))
            if (
                isinstance(refs, list)
                and any(isinstance(ref, str) and ref in rejected_keys for ref in refs)
            ):
                rejected.append(
                    {
                        "kind": "route_depends_on_rejected_relationship",
                        "path": f"residue.route_candidates[{index}]",
                        "key": value.get("key", value.get("id")),
                        "edge_keys": list(refs),
                        "reason": "route references an item rejected at the relationship boundary",
                        "raw_record": dict(value),
                    }
                )
                continue
            kept_routes.append(value)
        normalized["route_candidates"] = kept_routes
    return normalized, tuple(rejected)


__all__ = [
    "MAX_AUXILIARY_RECORDS",
    "DEFAULT_ADMISSION_CONFIDENCE_THRESHOLD",
    "MAX_CONCEPTS",
    "MAX_LABEL_LENGTH",
    "MAX_RELATIONSHIPS",
    "MAX_RESIDUE_BYTES",
    "MAX_ROUTE_EDGES",
    "MAX_ROUTES",
    "MAX_SPANS_PER_ITEM",
    "Residue",
    "ResidueValidationError",
    "SourceSpan",
    "canonical_json",
    "normalize_label",
    "normalize_relationship_items",
    "RELATIONSHIP_ALIASES",
    "RELATIONSHIP_RECONCILIATION_VERSION",
    "validate_graph_admission",
    "validate_residue",
]
