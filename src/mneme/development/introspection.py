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
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

# Version the reviewer-facing contract separately from historical ledger
# formats. Existing ledgers retain their v2 identifier; new two-round ledgers
# identify the live-Gemma contract explicitly.
INTROSPECTION_ROUND_TWO_VERSION = "p3-introspection-v3-live-round-two"
INTROSPECTION_VERSION = "p3-introspection-v2-answer-bank"
_SUPPORTED_LEDGER_VERSIONS = frozenset(
    {
        "p3-introspection-v1",
        INTROSPECTION_VERSION,
        INTROSPECTION_ROUND_TWO_VERSION,
    }
)
MAX_ARC_CHARS = 24_000
MAX_TARGETS_PER_ARC = 8
MAX_EFFECT = 1.0
MAX_CONFIDENCE = 1.0
SELF_ONLY_MAX_DELTA = 80_000
EXTERNAL_MAX_DELTA = 200_000
MAX_ARC_BUDGET = 200_000
MAX_REFLECTION_CHARS = 12_000


class FilingLevel(StrEnum):
    """Bounded filing contracts qualified against the local Gemma runtime."""

    FULL_JSON = "full_json"
    COMPACT_JSON = "compact_json"
    MULTIPLE_CHOICE_JSON = "multiple_choice_json"
    KEY_VALUE = "key_value"
    MINIMAL = "minimal"
    MICROCALL = "microcall"
    MICROCALL_EXPLICIT = "microcall_explicit"


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
                self.basis if isinstance(self.basis, EvidenceBasis) else EvidenceBasis(self.basis)
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


def review_system_prompt(*, compact_targets: bool = False) -> str:
    """Return the reviewer contract.

    ``compact_targets`` is the production contract for small local models.  It
    asks the model to choose a short ordinal from a supplied answer bank.  The
    Python boundary resolves that ordinal to the opaque target identity.  The
    historical alias contract remains available for replay and compatibility.
    """

    target_instruction = (
        "Each target is listed with a 1-based choice number. Set target_choice "
        "to exactly one listed integer; Python resolves it to the association. "
        "Do not invent aliases or identifiers. "
        if compact_targets
        else "Use only supplied target aliases and evidence references. "
    )
    target_field = '"target_choice":1' if compact_targets else '"target_alias":"supplied-alias"'
    return (
        "This is an internal review of a completed conversational arc, not a reply to the "
        "participant. Review the supplied interactions and recorded associative exposures. "
        "Assess how particular associations and their expression landed in this context. "
        "An unusual connection is not inherently a mistake. Separate usefulness or interest "
        "from whether repeating or expressing it was unwelcome. Cite supplied evidence for "
        "external reaction. You may form a self-only opinion when no external reaction exists, "
        "but label it as such. Do not invent feedback or claim hidden reasoning. Return exactly "
        "one JSON object and no markdown or commentary, with this shape: "
        '{"assessments":[{' + target_field + ',"association_effect":0.0,'
        '"expression_effect":0.0,"confidence":0.0,"basis":"INSUFFICIENT",'
        '"evidence_refs":[],"reason":""}]}. ' + target_instruction + "An empty assessments list "
        "is valid when no bounded change is justified. No change is an allowed result."
    )


def reflection_system_prompt() -> str:
    """Return the unconstrained first round of introspection.

    This round is intentionally prose-first.  It gives the small host a
    realistic opportunity to judge the preceding interaction before Python
    asks it to perform the separate clerical filing step.
    """

    return (
        "This is a private internal reflection about a completed conversational arc. "
        "You are reviewing your own immediately preceding interaction and recorded "
        "associative framings. Ordinary developmental learning is paused during this "
        "review. Think naturally in concise prose: say which supplied associations "
        "were useful, harmful, distracting, neutral, or uncertain, and whether an "
        "association was worth expressing or better left latent. Ground yourself in "
        "the supplied interaction and do not invent targets, feedback, outcomes, or "
        "hidden reasoning. This is not a database form. Do not output JSON, aliases, "
        "edge IDs, evidence-reference syntax, or database vocabulary."
    )


def reflection_request(packet: ArcPacket) -> dict[str, Any]:
    """Build the model-visible prose reflection packet.

    Opaque graph identity is withheld.  Target numbers are only stable handles
    for the second round; the reflection itself is free to discuss the supplied
    concepts in ordinary language.
    """

    exposure_rows = []
    for index, target in enumerate(packet.targets, start=1):
        exposure_rows.append(
            {
                "target_number": index,
                "association_context": target.context,
                "exposure_refs": list(target.exposure_refs),
                "exposure": [
                    {
                        key: value
                        for key, value in exposure.items()
                        if key in {"turn_ref", "payload", "context"}
                    }
                    for exposure in packet.exposures
                    if not target.exposure_refs
                    or str(exposure.get("turn_ref", "")) in set(target.exposure_refs)
                ],
            }
        )
    return {
        "arc_id": packet.arc_id,
        "messages": [dict(item) for item in packet.messages],
        "recorded_associations": exposure_rows,
        "missing_aftermath": packet.missing_aftermath,
    }


def filing_system_prompt(level: FilingLevel | str = FilingLevel.COMPACT_JSON) -> str:
    """Return a constrained second-round filing contract.

    All legal values are presented explicitly so Python can retain canonical
    identity, validation, and state mutation responsibilities.
    """

    selected = FilingLevel(level)
    if selected is FilingLevel.FULL_JSON:
        form = (
            '{"target_choice":1,"association_effect":0.0,"expression_effect":0.0,'
            '"confidence":0.0,"basis":"INSUFFICIENT","evidence_refs":[],'
            '"abstain":false}'
        )
    elif selected is FilingLevel.COMPACT_JSON:
        form = (
            '{"target":1,"association":0,"expression":0,"confidence":0,'
            '"basis":"SELF_ONLY","evidence":[]}'
        )
    elif selected is FilingLevel.MULTIPLE_CHOICE_JSON:
        form = (
            '{"target":1,"effect":"C","expression":"C","confidence":3,'
            '"basis":"SELF_ONLY","evidence":[]}'
        )
    elif selected is FilingLevel.KEY_VALUE:
        form = "TARGET: 1\nASSOCIATION: C\nEXPRESSION: C\nCONFIDENCE: 3"
    elif selected is FilingLevel.MINIMAL:
        form = "1 C C 3"
    elif selected is FilingLevel.MICROCALL_EXPLICIT:
        form = (
            "Use one digit per question. Answer bank: 0=no/unclear, 1=yes; "
            "confidence: 1 none through 5 very high."
        )
    else:
        form = "Reply with one integer only for each question."
    return (
        "Translate the opinion you just expressed into this filing form. "
        "This is clerical transcription, not a new reflection. Use only the supplied "
        "target numbers, evidence labels, and legal choices. Never invent an alias, "
        "ID, quote, or target. A target of 0 means abstain. Association and expression "
        "use: -2 substantially worse, -1 somewhat worse, 0 neutral, 1 somewhat better, "
        "2 substantially better. Confidence uses 0 none, 1 low, 2 medium, 3 high, "
        "4 very high. If evidence is insufficient, abstain. Return only the requested "
        f"form, with no explanation. Example shape: {form}"
    )


def filing_request(
    packet: ArcPacket,
    reflection: str,
    *,
    level: FilingLevel | str = FilingLevel.COMPACT_JSON,
) -> dict[str, Any]:
    """Build a bounded Round-Two answer bank plus the preserved reflection."""

    selected = FilingLevel(level)
    choices = [
        {"number": index, "context": target.context}
        for index, target in enumerate(packet.targets, start=1)
    ]
    return {
        "arc_id": packet.arc_id,
        "reflection": str(reflection)[:MAX_REFLECTION_CHARS],
        "target_answer_bank": choices,
        "evidence_labels": sorted(
            {str(item.get("turn_ref")) for item in packet.exposures if item.get("turn_ref")}
        ),
        "filing_level": selected.value,
        "missing_aftermath": packet.missing_aftermath,
    }


def review_request(packet: ArcPacket, *, compact_targets: bool = False) -> dict[str, Any]:
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
    if compact_targets:
        targets: list[dict[str, Any]] = [
            {"choice": index, "context": item.context}
            for index, item in enumerate(packet.targets, start=1)
        ]
    else:
        targets = [{"target_alias": item.alias, "context": item.context} for item in packet.targets]
    return {
        "arc_id": packet.arc_id,
        "messages": [dict(item) for item in packet.messages],
        "recorded_exposures": public_exposures,
        "targets": targets,
        "missing_aftermath": packet.missing_aftermath,
    }


def _resolve_target_alias(item: Mapping[str, Any], packet: ArcPacket) -> str | None:
    """Resolve model-facing ordinal choices without exposing database IDs.

    The compact contract deliberately accepts only a bounded 1-based choice
    from the packet.  A few harmless spellings are accepted so a local model
    can emit ``T1``/``target 1`` while still being resolved deterministically.
    The legacy exact-alias path remains unchanged.
    """

    alias = item.get("target_alias")
    if isinstance(alias, str):
        if alias in {target.alias for target in packet.targets}:
            return alias
        normalized = alias.strip().lower().replace("_", " ")
        match = re.fullmatch(r"(?:t(?:arget)?\s*)?(\d+)", normalized)
        if match:
            ordinal = int(match.group(1))
            if 1 <= ordinal <= len(packet.targets):
                return packet.targets[ordinal - 1].alias
        return None

    for key in ("target_choice", "choice", "target"):
        raw_choice: Any = item.get(key)
        if isinstance(raw_choice, bool):
            continue
        if isinstance(raw_choice, int) or (
            isinstance(raw_choice, str) and raw_choice.strip().isdigit()
        ):
            ordinal = int(raw_choice)
            if 1 <= ordinal <= len(packet.targets):
                return packet.targets[ordinal - 1].alias
    return None


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
    if "assessments" not in value and "proposals" not in value:
        raise IntrospectionError("reflection result has no assessments list")
    raw = value.get("assessments", value.get("proposals", []))
    if not isinstance(raw, list) or len(raw) > MAX_TARGETS_PER_ARC:
        raise IntrospectionError("reflection assessments must be a bounded list")
    aliases = {item.alias for item in packet.targets}
    refs = valid_evidence_refs or {f"turn-{index}" for index in range(len(packet.messages))}
    result: list[ReflectionProposal] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise IntrospectionError("reflection assessment must be an object")
        alias = _resolve_target_alias(item, packet)
        if alias is None or alias not in aliases:
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


_EFFECT_CODES = {
    "A": -1.0,
    "B": -0.5,
    "C": 0.0,
    "D": 0.5,
    "E": 1.0,
}
_ORDINAL_EFFECTS = {-2: -1.0, -1: -0.5, 0: 0.0, 1: 0.5, 2: 1.0}


def _number(value: Any, *, name: str) -> int:
    if isinstance(value, bool):
        raise IntrospectionError(f"{name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise IntrospectionError(f"{name} must be an integer") from exc
    if str(value).strip() not in {str(parsed), f"{parsed}.0"}:
        raise IntrospectionError(f"{name} must be an integer")
    return parsed


def _filing_object(value: Any) -> Mapping[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise IntrospectionError("filing result is not JSON") from exc
    if not isinstance(value, Mapping):
        raise IntrospectionError("filing result must be an object")
    return value


def parse_filing(
    value: Any,
    packet: ArcPacket,
    *,
    level: FilingLevel | str = FilingLevel.COMPACT_JSON,
    valid_evidence_refs: set[str] | None = None,
) -> tuple[ReflectionProposal, ...]:
    """Convert the constrained filing form into canonical proposals.

    This is deliberately deterministic: target choice and enum translation
    happen in Python after the model has selected from the visible answer bank.
    """

    selected = FilingLevel(level)
    if selected is FilingLevel.FULL_JSON:
        obj = _filing_object(value)
        if "assessments" not in obj:
            if _number(obj.get("target_choice", obj.get("target", 0)), name="target") == 0:
                return ()
            obj = {"assessments": [dict(obj)]}
        return parse_proposals(obj, packet, valid_evidence_refs=valid_evidence_refs)

    if selected is FilingLevel.COMPACT_JSON:
        obj = _filing_object(value)
        target = _number(obj.get("target", obj.get("target_choice", 0)), name="target")
        association = _number(obj.get("association", 0), name="association")
        expression = _number(obj.get("expression", 0), name="expression")
        confidence = _number(obj.get("confidence", 0), name="confidence")
        if association not in _ORDINAL_EFFECTS or expression not in _ORDINAL_EFFECTS:
            raise IntrospectionError("compact effects must be in [-2,-1,0,1,2]")
        if not 0 <= confidence <= 4:
            raise IntrospectionError("compact confidence must be in [0,4]")
        if target == 0:
            return ()
        proposal = {
            "target_choice": target,
            "association_effect": _ORDINAL_EFFECTS[association],
            "expression_effect": _ORDINAL_EFFECTS[expression],
            "confidence": confidence / 4.0,
            "basis": str(obj.get("basis", "SELF_ONLY")),
            "evidence_refs": list(obj.get("evidence_refs", obj.get("evidence", []))),
            "reason": str(obj.get("reason", "")),
            "abstain": target == 0,
        }
        return parse_proposals(
            {"assessments": [proposal]}, packet, valid_evidence_refs=valid_evidence_refs
        )

    if selected is FilingLevel.MULTIPLE_CHOICE_JSON:
        obj = _filing_object(value)
        target = _number(obj.get("target", 0), name="target")
        mc_association = str(obj.get("effect", "C")).strip().upper()
        mc_expression = str(obj.get("expression", "C")).strip().upper()
        confidence = _number(obj.get("confidence", 0), name="confidence")
        if mc_association not in _EFFECT_CODES or mc_expression not in _EFFECT_CODES:
            raise IntrospectionError("multiple-choice effects must be A/B/C/D/E")
        if not 0 <= confidence <= 4:
            raise IntrospectionError("multiple-choice confidence must be in [0,4]")
        if target == 0:
            return ()
        proposal = {
            "target_choice": target,
            "association_effect": _EFFECT_CODES[mc_association],
            "expression_effect": _EFFECT_CODES[mc_expression],
            "confidence": confidence / 4.0,
            "basis": str(obj.get("basis", "SELF_ONLY")),
            "evidence_refs": list(obj.get("evidence_refs", obj.get("evidence", []))),
            "reason": str(obj.get("reason", "")),
            "abstain": target == 0,
        }
        return parse_proposals(
            {"assessments": [proposal]}, packet, valid_evidence_refs=valid_evidence_refs
        )

    if selected is FilingLevel.KEY_VALUE:
        if not isinstance(value, str):
            raise IntrospectionError("key/value filing must be text")
        fields: dict[str, str] = {}
        for line in value.splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            fields[key.strip().lower()] = raw.strip()
        kv_target = fields.get("target", "0")
        kv_association = fields.get("association", "C").upper()
        kv_expression = fields.get("expression", "C").upper()
        kv_confidence = fields.get("confidence", "0")
        return parse_filing(
            {
                "target": kv_target,
                "effect": kv_association,
                "expression": kv_expression,
                "confidence": kv_confidence,
                "basis": fields.get("basis", "SELF_ONLY"),
                "evidence_refs": [
                    x.strip() for x in fields.get("evidence", "").split(",") if x.strip()
                ],
            },
            packet,
            level=FilingLevel.MULTIPLE_CHOICE_JSON,
            valid_evidence_refs=valid_evidence_refs,
        )

    if selected is FilingLevel.MINIMAL:
        if not isinstance(value, str):
            raise IntrospectionError("minimal filing must be text")
        tokens = value.strip().split()
        if len(tokens) != 4:
            raise IntrospectionError("minimal filing requires four tokens")
        return parse_filing(
            {
                "target": tokens[0],
                "effect": tokens[1],
                "expression": tokens[2],
                "confidence": tokens[3],
            },
            packet,
            level=FilingLevel.MULTIPLE_CHOICE_JSON,
            valid_evidence_refs=valid_evidence_refs,
        )

    raise IntrospectionError("microcall filings require the staged parser")


def parse_microcall_explicit(
    values: Any,
    packet: ArcPacket,
) -> tuple[ReflectionProposal, ...]:
    """Translate the live-qualified binary filing microcalls deterministically."""

    if not isinstance(values, (list, tuple)):
        raise IntrospectionError("explicit microcall filing must be a sequence")
    digits: list[int] = []
    for value in values:
        if isinstance(value, bool) or not re.fullmatch(r"\s*[0-5]\s*", str(value)):
            raise IntrospectionError("explicit microcall answer must be one digit")
        digits.append(int(str(value).strip()))
    if not digits:
        raise IntrospectionError("explicit microcall filing is empty")
    target = digits[0]
    if target == 0:
        return ()
    if target > len(packet.targets):
        raise IntrospectionError("explicit microcall target is outside answer bank")
    if len(digits) != 7 or any(value not in {0, 1} for value in digits[1:6]):
        raise IntrospectionError("explicit microcall filing has illegal values")
    if not 1 <= digits[6] <= 5:
        raise IntrospectionError("explicit microcall confidence is outside [1,5]")
    clear, useful, harmful, expressed, suppressed = digits[1:6]
    if not clear:
        return ()
    association = 0.0 if useful and harmful else -1.0 if harmful else 1.0 if useful else 0.0
    expression = (
        0.0
        if suppressed and expressed
        else -1.0
        if suppressed
        else 1.0
        if expressed
        else 0.0
    )
    target_item = packet.targets[target - 1]
    return (
        ReflectionProposal(
            target_alias=target_item.alias,
            association_effect=association,
            expression_effect=expression,
            confidence=(digits[6] - 1) / 4.0,
            basis=EvidenceBasis.SELF_ONLY,
            evidence_refs=(),
            reason="live_microcall_explicit",
            abstain=False,
        ),
    )


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
        if data.get("version") not in _SUPPORTED_LEDGER_VERSIONS:
            raise IntrospectionError("unsupported introspection ledger version")
        adjustments = tuple(
            AcceptedAdjustment(
                str(item["arc_id"]),
                str(item["target_alias"]),
                str(item["edge_key"]),
                str(item["context"]),
                int(item["association_delta"]),
                int(item["expression_delta"]),
                EvidenceBasis(item["basis"]),
                tuple(str(x) for x in item.get("evidence_refs", [])),
                str(item["proposal_digest"]),
                str(item.get("reason", "")),
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
        review_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        review = {
            "arc_id": packet.arc_id,
            "packet_digest": packet.digest,
            "status": status,
            "proposals": [item.to_dict() for item in proposals],
            "accepted": [item.to_dict() for item in accepted],
            "ordinary_learning": False,
        }
        if review_metadata:
            # Metadata is an audit sidecar, never input to model generation or
            # learner updates.  Keep it JSON-shaped and bounded at the ledger
            # boundary so an unexpectedly verbose reflection cannot exhaust
            # the normal introspection store.
            for key, value in review_metadata.items():
                if key in {
                    "reflection",
                    "filing",
                    "fallback",
                    "reflection_seed",
                    "filing_seed",
                    "formatting_seed",
                    "filing_level",
                    "status_detail",
                }:
                    if isinstance(value, str):
                        review[key] = value[:MAX_REFLECTION_CHARS]
                    elif isinstance(value, (int, float, bool)) or value is None:
                        review[key] = value
        self.reviews.append(review)
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
    "FilingLevel",
    "INTROSPECTION_VERSION",
    "INTROSPECTION_ROUND_TWO_VERSION",
    "IntrospectionError",
    "IntrospectionLedger",
    "ReflectionProposal",
    "ReviewTarget",
    "accept_proposals",
    "filing_request",
    "filing_system_prompt",
    "parse_proposals",
    "parse_filing",
    "reflection_request",
    "reflection_system_prompt",
    "review_request",
    "review_system_prompt",
]
