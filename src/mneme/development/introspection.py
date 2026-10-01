"""Bounded, auditable review of completed conversational arcs.

Introspection is deliberately a separate operating mode.  It can propose a
small contextual adjustment to an existing earned edge, but it never emits
ordinary graph observations or recurrence credit.  The ledger is JSON so the
review and replay boundary remains inspectable without adding a hidden model
state.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

INTROSPECTION_VERSION = "p3-introspection-v1"
MAX_ARC_CHARS = 24_000
MAX_TARGETS_PER_ARC = 8
MAX_EFFECT = 1.0
MAX_CONFIDENCE = 1.0
SELF_ONLY_MAX_DELTA = 80_000
EXTERNAL_MAX_DELTA = 200_000
MAX_ARC_BUDGET = 200_000


class IntrospectionError(ValueError):
    """A review packet or proposal violates the bounded contract."""


class EvidenceBasis(StrEnum):
    SELF_ONLY = "SELF_ONLY"
    EXTERNAL_REACTION = "EXTERNAL_REACTION"
    LATER_OUTCOME = "LATER_OUTCOME"
    MIXED = "MIXED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class ReviewTarget:
    alias: str
    edge_key: str
    context: str
    exposure_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.alias or not self.edge_key or not self.context:
            raise IntrospectionError("review target identity is incomplete")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_alias": self.alias,
            "edge_key": self.edge_key,
            "context": self.context,
            "exposure_refs": list(self.exposure_refs),
        }


@dataclass(frozen=True)
class ArcPacket:
    arc_id: str
    messages: tuple[Mapping[str, str], ...]
    exposures: tuple[Mapping[str, Any], ...]
    targets: tuple[ReviewTarget, ...]
    missing_aftermath: bool = False
    source_digest: str = ""

    def __post_init__(self) -> None:
        if not self.arc_id or not self.messages:
            raise IntrospectionError("review packet must contain an arc and messages")
        size = sum(len(str(item.get("content", ""))) for item in self.messages)
        if size > MAX_ARC_CHARS:
            raise IntrospectionError("review packet exceeds bounded character budget")
        for item in self.messages:
            if item.get("role") not in {"user", "assistant"}:
                raise IntrospectionError("review packet roles must be user or assistant")

    @property
    def digest(self) -> str:
        if self.source_digest:
            return self.source_digest
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "arc_id": self.arc_id,
            "messages": [dict(item) for item in self.messages],
            "exposures": [dict(item) for item in self.exposures],
            "targets": [item.to_dict() for item in self.targets],
            "missing_aftermath": self.missing_aftermath,
            "source_digest": self.source_digest,
        }


@dataclass(frozen=True)
class ReflectionProposal:
    target_alias: str
    association_effect: float
    expression_effect: float
    confidence: float
    basis: EvidenceBasis | str
    evidence_refs: tuple[str, ...] = ()
    reason: str = ""
    abstain: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("association_effect", self.association_effect),
            ("expression_effect", self.expression_effect),
            ("confidence", self.confidence),
        ):
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise IntrospectionError(f"{name} must be finite")
        if not -MAX_EFFECT <= self.association_effect <= MAX_EFFECT:
            raise IntrospectionError("association_effect is outside [-1,1]")
        if not -MAX_EFFECT <= self.expression_effect <= MAX_EFFECT:
            raise IntrospectionError("expression_effect is outside [-1,1]")
        if not 0 <= self.confidence <= MAX_CONFIDENCE:
            raise IntrospectionError("confidence is outside [0,1]")
        try:
            basis = (
                self.basis
                if isinstance(self.basis, EvidenceBasis)
                else EvidenceBasis(self.basis)
            )
        except ValueError as exc:
            raise IntrospectionError("unsupported evidence basis") from exc
        object.__setattr__(self, "basis", basis)
        if self.abstain and (self.association_effect or self.expression_effect):
            raise IntrospectionError("abstention cannot carry an effect")

    def to_dict(self) -> dict[str, Any]:
        basis = cast(EvidenceBasis, self.basis)
        return {
            "target_alias": self.target_alias,
            "association_effect": self.association_effect,
            "expression_effect": self.expression_effect,
            "confidence": self.confidence,
            "basis": basis.value,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
            "abstain": self.abstain,
        }


@dataclass(frozen=True)
class AcceptedAdjustment:
    arc_id: str
    target_alias: str
    edge_key: str
    context: str
    association_delta: int
    expression_delta: int
    basis: EvidenceBasis
    evidence_refs: tuple[str, ...]
    proposal_digest: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "arc_id": self.arc_id,
            "target_alias": self.target_alias,
            "edge_key": self.edge_key,
            "context": self.context,
            "association_delta": self.association_delta,
            "expression_delta": self.expression_delta,
            "basis": self.basis.value,
            "evidence_refs": list(self.evidence_refs),
            "proposal_digest": self.proposal_digest,
            "reason": self.reason,
        }


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def review_system_prompt() -> str:
    return (
        "This is an internal review of a completed conversational arc, not a reply to the "
        "participant. Review the supplied interactions and recorded associative exposures. "
        "Assess how particular associations and their expression landed in this context. "
        "An unusual connection is not inherently a mistake. Separate usefulness or interest "
        "from whether repeating or expressing it was unwelcome. Cite supplied evidence for "
        "external reaction. You may form a self-only opinion when no external reaction exists, "
        "but label it as such. Do not invent feedback or claim hidden reasoning. Return exactly "
        "one JSON object and no markdown or commentary, with this shape: "
        '{"assessments":[{"target_alias":"supplied-alias","association_effect":0.0,'
        '"expression_effect":0.0,"confidence":0.0,"basis":"INSUFFICIENT",'
        '"evidence_refs":[],"reason":""}]}. '
        "Use only supplied target aliases and evidence references. An empty assessments list "
        "is valid when no bounded change is justified. No change is an allowed result."
    )


def review_request(packet: ArcPacket) -> dict[str, Any]:
    """Return a model-visible review request with no administrative metadata."""

    # Exposure records are audit-rich internally.  The reviewer receives only
    # the turn reference and compact conceptual payload; edge IDs, scores,
    # lineage IDs, and provenance are deliberately withheld.
    public_exposures = []
    for exposure in packet.exposures:
        public_exposures.append(
            {
                key: value
                for key, value in exposure.items()
                if key in {"turn_ref", "payload", "context"}
            }
        )
    return {
        "arc_id": packet.arc_id,
        "messages": [dict(item) for item in packet.messages],
        "recorded_exposures": public_exposures,
        "targets": [
            {"target_alias": item.alias, "context": item.context}
            for item in packet.targets
        ],
        "missing_aftermath": packet.missing_aftermath,
    }


def parse_proposals(
    value: Any,
    packet: ArcPacket,
    *,
    valid_evidence_refs: set[str] | None = None,
) -> tuple[ReflectionProposal, ...]:
    """Validate a bounded model result without assigning truth to its claims."""

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise IntrospectionError("reflection result is not JSON") from exc
    if not isinstance(value, Mapping):
        raise IntrospectionError("reflection result must be an object")
    raw = value.get("assessments", value.get("proposals", []))
    if not isinstance(raw, list) or len(raw) > MAX_TARGETS_PER_ARC:
        raise IntrospectionError("reflection assessments must be a bounded list")
    aliases = {item.alias for item in packet.targets}
    refs = valid_evidence_refs or {f"turn-{index}" for index in range(len(packet.messages))}
    result: list[ReflectionProposal] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise IntrospectionError("reflection assessment must be an object")
        alias = item.get("target_alias")
        if not isinstance(alias, str) or alias not in aliases:
            raise IntrospectionError("reflection target alias is not supplied")
        evidence = item.get("evidence_refs", [])
        if not isinstance(evidence, list) or any(not isinstance(ref, str) for ref in evidence):
            raise IntrospectionError("evidence_refs must be a string list")
        unknown = set(evidence) - refs
        if unknown:
            raise IntrospectionError(f"reflection cites unknown evidence: {sorted(unknown)}")
        result.append(
            ReflectionProposal(
                target_alias=alias,
                association_effect=float(item.get("association_effect", 0.0)),
                expression_effect=float(item.get("expression_effect", 0.0)),
                confidence=float(item.get("confidence", 0.0)),
                basis=str(item.get("basis", EvidenceBasis.INSUFFICIENT.value)),
                evidence_refs=tuple(evidence),
                reason=str(item.get("reason", "")),
                abstain=bool(item.get("abstain", False)),
            )
        )
    return tuple(result)


def _basis_cap(basis: EvidenceBasis) -> int:
    if basis is EvidenceBasis.SELF_ONLY:
        return SELF_ONLY_MAX_DELTA
    if basis in {EvidenceBasis.EXTERNAL_REACTION, EvidenceBasis.LATER_OUTCOME, EvidenceBasis.MIXED}:
        return EXTERNAL_MAX_DELTA
    return 0


def accept_proposals(
    packet: ArcPacket,
    proposals: tuple[ReflectionProposal, ...],
    *,
    existing_dedup: set[str] | None = None,
) -> tuple[AcceptedAdjustment, ...]:
    """Translate proposals into one finite, signed, deduplicated arc update."""

    target_by_alias = {target.alias: target for target in packet.targets}
    dedup = existing_dedup or set()
    accepted: list[AcceptedAdjustment] = []
    remaining = MAX_ARC_BUDGET
    for proposal in proposals:
        target = target_by_alias.get(proposal.target_alias)
        if target is None or proposal.abstain or proposal.basis is EvidenceBasis.INSUFFICIENT:
            continue
        key = _digest(
            {
                "arc": packet.arc_id,
                "target": target.alias,
                "edge": target.edge_key,
                "exposure": target.exposure_refs,
                "evidence": proposal.evidence_refs,
            }
        )
        if key in dedup:
            continue
        basis = cast(EvidenceBasis, proposal.basis)
        cap = _basis_cap(basis)
        if cap == 0:
            continue
        signed = int(round(proposal.association_effect * proposal.confidence * cap))
        expression = int(round(proposal.expression_effect * proposal.confidence * cap))
        signed = max(-cap, min(cap, signed))
        expression = max(-cap, min(cap, expression))
        cost = abs(signed) + abs(expression)
        if cost == 0:
            continue
        if cost > remaining:
            scale = remaining / cost
            signed = int(signed * scale)
            expression = int(expression * scale)
            cost = abs(signed) + abs(expression)
        if cost == 0:
            continue
        accepted.append(
            AcceptedAdjustment(
                packet.arc_id,
                target.alias,
                target.edge_key,
                target.context,
                signed,
                expression,
                basis,
                proposal.evidence_refs,
                key,
                proposal.reason,
            )
        )
        dedup.add(key)
        remaining -= cost
        if remaining <= 0:
            break
    return tuple(accepted)


@dataclass
class IntrospectionLedger:
    """Durable sidecar ledger for introspection proposals and updates."""

    path: Path
    version: str = INTROSPECTION_VERSION
    parent_digest: str = ""
    adjustments: list[AcceptedAdjustment] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    dedup_keys: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: str | Path, *, parent_digest: str = "") -> IntrospectionLedger:
        destination = Path(path)
        if not destination.exists():
            return cls(destination, parent_digest=parent_digest)
        data = json.loads(destination.read_text(encoding="utf-8"))
        if data.get("version") != INTROSPECTION_VERSION:
            raise IntrospectionError("unsupported introspection ledger version")
        adjustments = tuple(
            AcceptedAdjustment(
                str(item["arc_id"]), str(item["target_alias"]), str(item["edge_key"]),
                str(item["context"]), int(item["association_delta"]),
                int(item["expression_delta"]), EvidenceBasis(item["basis"]),
                tuple(str(x) for x in item.get("evidence_refs", [])),
                str(item["proposal_digest"]), str(item.get("reason", "")),
            )
            for item in data.get("adjustments", [])
        )
        return cls(
            destination,
            parent_digest=str(data.get("parent_digest", parent_digest)),
            adjustments=list(adjustments),
            reviews=list(data.get("reviews", [])),
            dedup_keys={str(x) for x in data.get("dedup_keys", [])},
        )

    def accessibility_adjustments(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.adjustments:
            result[item.edge_key] = result.get(item.edge_key, 0) + item.association_delta
        return {key: max(-200_000, min(200_000, value)) for key, value in result.items()}

    def expression_adjustments(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.adjustments:
            result[item.edge_key] = result.get(item.edge_key, 0) + item.expression_delta
        return {key: max(-200_000, min(200_000, value)) for key, value in result.items()}

    def record_review(
        self,
        packet: ArcPacket,
        proposals: tuple[ReflectionProposal, ...],
        *,
        accepted: tuple[AcceptedAdjustment, ...],
        status: str = "COMPLETE",
    ) -> None:
        self.reviews.append(
            {
                "arc_id": packet.arc_id,
                "packet_digest": packet.digest,
                "status": status,
                "proposals": [item.to_dict() for item in proposals],
                "accepted": [item.to_dict() for item in accepted],
                "ordinary_learning": False,
            }
        )
        self.adjustments.extend(accepted)
        self.dedup_keys.update(item.proposal_digest for item in accepted)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "parent_digest": self.parent_digest,
            "adjustments": [item.to_dict() for item in self.adjustments],
            "reviews": self.reviews,
            "dedup_keys": sorted(self.dedup_keys),
        }
        fd, name = tempfile.mkstemp(prefix=self.path.name + ".", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)


__all__ = [
    "AcceptedAdjustment",
    "ArcPacket",
    "EvidenceBasis",
    "INTROSPECTION_VERSION",
    "IntrospectionError",
    "IntrospectionLedger",
    "ReflectionProposal",
    "ReviewTarget",
    "accept_proposals",
    "parse_proposals",
    "review_request",
    "review_system_prompt",
]
