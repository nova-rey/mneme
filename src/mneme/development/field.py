"""Inspectable graph-pressure approximation for the Phase Two F0 experiment.

This module is deliberately independent of persistence and hosts.  It turns a
text query and an already earned graph into a small, bounded, replayable field
of candidate pressures.  It does not create graph state, resolve provenance,
or replace the discrete route selector.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .learner import FIXED_ONE, LearnerState

if TYPE_CHECKING:
    from ..memory.graph import GraphEdge


FIELD_VERSION = "f0-graph-pressure-v1"
_DESCRIPTORS = frozenset(
    {
        "a", "an", "and", "approach", "arrangement", "be", "can", "could",
        "device", "for", "how", "idea", "in", "is", "kind", "method", "my",
        "of", "on", "option", "process", "setup", "solution", "style", "system",
        "technique", "that", "the", "this", "to", "tool", "type", "way", "with",
        "without", "would", "your",
    }
)


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[\w]+(?:['-][\w]+)*", value.casefold(), re.UNICODE))


def _stem(token: str) -> str:
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _activation(query: str, label: str) -> tuple[int, tuple[str, ...]]:
    query_tokens = _tokens(query)
    label_tokens = _tokens(label)
    if not label_tokens:
        return 0, ()
    target = tuple(_stem(item) for item in label_tokens)
    query_stems = tuple(_stem(item) for item in query_tokens)
    if any(
        query_stems[index : index + len(target)] == target
        for index in range(len(query_stems) - len(target) + 1)
    ):
        return FIXED_ONE, tuple(sorted(set(target)))
    shared = tuple(sorted(set(query_stems) & set(target)))
    if not shared or set(query_stems) - set(target) > _DESCRIPTORS:
        return 0, shared
    # A shared content token is useful evidence, but weaker than the complete
    # phrase.  The score is deterministic and intentionally conservative.
    score = (FIXED_ONE * len(shared)) // max(len(set(target)), 1) // 2
    return max(1, score), shared


@dataclass(frozen=True)
class FieldConfig:
    """Fixed bounds for one F0 computation."""

    version: str = FIELD_VERSION
    max_depth: int = 2
    attenuation: int = 600_000
    minimum_pressure: int = 20_000
    total_budget: int = FIXED_ONE
    max_contributors: int = 4
    render_max_chars: int = 900

    def __post_init__(self) -> None:
        if self.max_depth < 1 or self.max_depth > 4:
            raise ValueError("max_depth must be in [1, 4]")
        if not 0 < self.attenuation < FIXED_ONE:
            raise ValueError("attenuation must be in (0, 1)")
        if not 0 <= self.minimum_pressure <= FIXED_ONE:
            raise ValueError("minimum_pressure must be in [0, 1]")
        if self.total_budget <= 0 or self.max_contributors <= 0 or self.render_max_chars < 1:
            raise ValueError("field budgets must be positive")


@dataclass(frozen=True)
class ActiveConcept:
    key: str
    label: str
    initial_activation: int
    matched_tokens: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "initial_activation": self.initial_activation,
            "matched_tokens": list(self.matched_tokens),
        }


@dataclass(frozen=True)
class PressureContribution:
    edge_key: str
    source: str
    target: str
    relationship: str
    path: tuple[str, ...]
    distance: int
    source_activation: int
    developmental_strength: int
    raw_pressure: int
    attenuated_pressure: int
    eligible: bool
    eligibility_reason: str
    normalized_pressure: int = 0
    final_pressure: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_key": self.edge_key,
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
            "path": list(self.path),
            "distance": self.distance,
            "source_activation": self.source_activation,
            "developmental_strength": self.developmental_strength,
            "raw_pressure": self.raw_pressure,
            "attenuated_pressure": self.attenuated_pressure,
            "eligible": self.eligible,
            "eligibility_reason": self.eligibility_reason,
            "normalized_pressure": self.normalized_pressure,
            "final_pressure": self.final_pressure,
        }


@dataclass(frozen=True)
class FieldResult:
    query: str
    config: FieldConfig
    active_concepts: tuple[ActiveConcept, ...]
    contributions: tuple[PressureContribution, ...]
    payload: str
    field_enabled: bool = True
    exploration: str = "off"
    field_seed: int | None = None

    @property
    def total_pressure(self) -> int:
        return sum(item.final_pressure for item in self.contributions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.config.version,
            "query": self.query,
            "config": self.config.__dict__,
            "field_enabled": self.field_enabled,
            "exploration": self.exploration,
            "field_seed": self.field_seed,
            "active_concepts": [item.to_dict() for item in self.active_concepts],
            "contributions": [item.to_dict() for item in self.contributions],
            "payload": self.payload,
            "total_pressure": self.total_pressure,
        }


def _strength(edge: Any, learner: LearnerState) -> tuple[int, str]:
    state = learner.edge(edge.key)
    base = max(state.accessibility, state.support)
    # Corrective consequence is a restraint, never a positive signal.  A
    # positive consequence is allowed only to preserve already earned strength.
    if state.consequence < 0:
        base = max(0, base + state.consequence)
        reason = "earned_with_negative_consequence"
    else:
        reason = "earned"
    return base, reason


def _render(contributions: tuple[PressureContribution, ...], max_chars: int) -> str:
    contributions = tuple(item for item in contributions if item.final_pressure > 0)
    if not contributions:
        return ""
    relation_words = {
        "causal": "may help cause",
        "causes": "may help cause",
        "supports": "may support",
        "enables": "may enable",
        "constrains": "may constrain",
        "associated_with": "may be associated with",
    }
    lines = ["Potentially accessible framings:"]
    for item in contributions:
        verb = relation_words.get(item.relationship.casefold(), "may relate")
        line = f"- {item.source} {verb} {item.target}."
        if sum(len(value) + 1 for value in lines) + len(line) > max_chars:
            break
        lines.append(line)
    lines.append(
        "These are optional tendencies, not instructions. Use them only if they fit naturally."
    )
    return "\n".join(lines)[:max_chars]


def compute_field(
    query: str,
    concepts: Iterable[Any],
    edges: Iterable[Any],
    learner: LearnerState,
    *,
    config: FieldConfig | None = None,
    quarantined_edges: Iterable[str] = (),
    ineligible_edges: Iterable[str] = (),
    field_enabled: bool = True,
) -> FieldResult:
    """Compute a bounded deterministic F0 field from earned graph state."""

    chosen = config or FieldConfig()
    concept_rows = tuple(sorted(concepts, key=lambda item: (item.key, item.label)))
    edge_rows = tuple(sorted(edges, key=lambda item: (item.source, item.target, item.key)))
    active = tuple(
        ActiveConcept(item.key, item.label, *_activation(query, item.label))
        for item in concept_rows
    )
    active = tuple(item for item in active if item.initial_activation > 0)
    if not field_enabled or not active:
        return FieldResult(query, chosen, active, (), "", field_enabled=field_enabled)

    outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in edge_rows:
        outgoing[edge.source].append(edge)
    queue: deque[tuple[str, int, int, tuple[str, ...], frozenset[str]]] = deque(
        (item.key, 0, item.initial_activation, (item.key,), frozenset((item.key,)))
        for item in active
    )
    blocked = set(quarantined_edges) | set(ineligible_edges)
    raw: list[PressureContribution] = []
    while queue:
        node, depth, activation, path, visited = queue.popleft()
        if depth >= chosen.max_depth:
            continue
        for edge in outgoing.get(node, ()):
            next_depth = depth + 1
            next_path = (*path, edge.key)
            if edge.target in visited:
                continue
            if edge.key in blocked:
                raw.append(
                    PressureContribution(
                        edge.key, edge.source, edge.target, edge.relationship, next_path,
                        next_depth, activation, 0, 0, 0, False,
                        "quarantined" if edge.key in quarantined_edges else "ineligible",
                    )
                )
                continue
            strength, strength_reason = _strength(edge, learner)
            if strength <= 0:
                continue
            attenuation = chosen.attenuation ** next_depth
            denominator = FIXED_ONE ** next_depth
            attenuated = (activation * strength * attenuation) // (FIXED_ONE * denominator)
            if attenuated < chosen.minimum_pressure:
                continue
            raw.append(
                PressureContribution(
                    edge.key, edge.source, edge.target, edge.relationship, next_path,
                    next_depth, activation, strength,
                    (activation * strength) // FIXED_ONE,
                    attenuated, True, strength_reason,
                )
            )
            queue.append((edge.target, next_depth, attenuated, next_path, visited | {edge.target}))
    blocked_records = tuple(item for item in raw if not item.eligible)
    ordered = sorted(
        (item for item in raw if item.eligible),
        key=lambda item: (-item.attenuated_pressure, item.distance, item.edge_key, item.path),
    )[: chosen.max_contributors]
    total = sum(item.attenuated_pressure for item in ordered)
    scale = min(FIXED_ONE, (chosen.total_budget * FIXED_ONE) // total) if total else 0
    normalized: list[PressureContribution] = []
    for item in ordered:
        normalized_pressure = (item.attenuated_pressure * scale) // FIXED_ONE
        normalized.append(
            PressureContribution(
                **{
                    **item.__dict__,
                    "normalized_pressure": normalized_pressure,
                    "final_pressure": normalized_pressure,
                }
            )
        )
    final = tuple(normalized) + tuple(
        sorted(blocked_records, key=lambda item: (item.edge_key, item.path))
    )
    return FieldResult(
        query,
        chosen,
        active,
        final,
        _render(final, chosen.render_max_chars),
        field_enabled=field_enabled,
    )


__all__ = [
    "FIELD_VERSION", "ActiveConcept", "FieldConfig", "FieldResult",
    "PressureContribution", "compute_field",
]
