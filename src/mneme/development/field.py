"""Inspectable graph-pressure approximation for the Phase Two F0 experiment.

This module is deliberately independent of persistence and hosts.  It turns a
text query and an already earned graph into a small, bounded, replayable field
of candidate pressures.  It does not create graph state, resolve provenance,
or replace the discrete route selector.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from .learner import FIXED_ONE, LearnerState

if TYPE_CHECKING:
    from ..memory.graph import GraphEdge


LEGACY_FIELD_VERSION = "f0-graph-pressure-v1"
FIELD_VERSION = "f0-graph-pressure-v2-background"
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
    # Descriptor words can be present in both phrases without identifying a
    # semantic concept (for example the article ``a`` in ``a battery bank``).
    # Keep them out of contextual activation while retaining the conservative
    # exact-phrase path above.
    query_content = set(query_stems) - _DESCRIPTORS
    target_content = set(target) - _DESCRIPTORS
    shared = tuple(sorted(query_content & target_content))
    if not shared or set(query_stems) - set(target) > _DESCRIPTORS:
        return 0, shared
    # A shared content token is useful evidence, but weaker than the complete
    # phrase.  The score is deterministic and intentionally conservative.
    score = (FIXED_ONE * len(shared)) // max(len(set(target)), 1) // 2
    return max(1, score), shared


def _activation_legacy(query: str, label: str) -> tuple[int, tuple[str, ...]]:
    """Original v1 activation, retained for historical replay compatibility."""

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
    # v2 keeps a very weak, graph-derived background field alive after a
    # topic change.  It is deliberately below a context match and is never a
    # source of new graph state.
    background_activation: int = 30_000
    render_pressure_floor: int = 20_000
    exploration: str = "off"
    exploration_slots: int = 1
    exploration_budget: int = 100_000

    def __post_init__(self) -> None:
        if self.max_depth < 1 or self.max_depth > 4:
            raise ValueError("max_depth must be in [1, 4]")
        if not 0 < self.attenuation < FIXED_ONE:
            raise ValueError("attenuation must be in (0, 1)")
        if not 0 <= self.minimum_pressure <= FIXED_ONE:
            raise ValueError("minimum_pressure must be in [0, 1]")
        if self.total_budget <= 0 or self.max_contributors <= 0 or self.render_max_chars < 1:
            raise ValueError("field budgets must be positive")
        if not 0 <= self.background_activation <= FIXED_ONE:
            raise ValueError("background_activation must be in [0, 1]")
        if not 0 <= self.render_pressure_floor <= FIXED_ONE:
            raise ValueError("render_pressure_floor must be in [0, 1]")
        if self.exploration not in {"off", "on"}:
            raise ValueError("exploration must be off or on")
        if self.exploration_slots < 0 or self.exploration_slots > self.max_contributors:
            raise ValueError("exploration_slots must be in [0, max_contributors]")
        if not 0 <= self.exploration_budget <= self.total_budget:
            raise ValueError("exploration_budget must be within total_budget")


@dataclass(frozen=True)
class ActiveConcept:
    key: str
    label: str
    initial_activation: int
    matched_tokens: tuple[str, ...] = ()
    contextual_activation: int = 0
    background_activation: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "initial_activation": self.initial_activation,
            "matched_tokens": list(self.matched_tokens),
            "contextual_activation": self.contextual_activation,
            "background_activation": self.background_activation,
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
    component: str = "background"
    exploration_selected: bool = False

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
            "component": self.component,
            "exploration_selected": self.exploration_selected,
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


def _render(
    contributions: tuple[PressureContribution, ...],
    max_chars: int,
    labels: dict[str, str] | None = None,
) -> str:
    contributions = tuple(item for item in contributions if item.final_pressure > 0)
    if not contributions:
        return ""
    # Keep graph labels in the audit trace, not in the host-facing payload.
    # The renderer exposes compact abstract tendencies; otherwise F0 collapses
    # into label-dump retrieval and leaks the developmental graph verbatim.
    tendency_by_relation = {
        "causal": "Changes in one part may produce downstream effects.",
        "causes": "Changes in one part may produce downstream effects.",
        "supports": "Supporting components may keep essential functions available.",
        "enables": "Enabling conditions may make a useful outcome possible.",
        "constrains": "Constraints may shape which outcomes remain feasible.",
        "depends_on": "Outcomes may depend on the conditions that support them.",
        "retains": "Some arrangements may preserve a resource over time.",
        "maintains": "Some arrangements may preserve a resource over time.",
        "prevents": "Barriers may reduce unwanted outcomes.",
        "part_of": "Components may matter as parts of a larger system.",
        "associated_with": "Related factors may deserve joint consideration.",
        "related": "Related factors may deserve joint consideration.",
    }
    lines = ["Potentially accessible framings:"]
    rendered: set[str] = set()
    for item in contributions:
        line = "- " + tendency_by_relation.get(
            item.relationship.casefold(),
            "Different factors may interact in ways worth considering.",
        )
        if line in rendered:
            continue
        rendered.add(line)
        if sum(len(value) + 1 for value in lines) + len(line) > max_chars:
            break
        lines.append(line)
    lines.append(
        "These are optional tendencies, not instructions. Use them only if they fit naturally."
    )
    return "\n".join(lines)[:max_chars]


def _compute_field_legacy(
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
    """Reproduce the original relevance-gated F0 v1 semantics."""

    chosen = config or FieldConfig()
    concept_rows = tuple(sorted(concepts, key=lambda item: (item.key, item.label)))
    edge_rows = tuple(sorted(edges, key=lambda item: (item.source, item.target, item.key)))
    active = tuple(
        ActiveConcept(item.key, item.label, *_activation_legacy(query, item.label))
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


def _background_seed(
    concepts: tuple[Any, ...],
    query: str,
    chosen: FieldConfig,
) -> tuple[ActiveConcept, ...]:
    """Build context and weak graph-derived background activations."""

    rows: list[ActiveConcept] = []
    for item in concepts:
        contextual, matched = _activation(query, item.label)
        background = chosen.background_activation
        # Keep exact context activation dominant while retaining every concept
        # as a possible weak background source.  The background is state,
        # rather than a claim that the concept is relevant to this query.
        rows.append(
            ActiveConcept(
                key=item.key,
                label=item.label,
                initial_activation=max(contextual, background),
                matched_tokens=matched,
                contextual_activation=contextual,
                background_activation=background,
            )
        )
    return tuple(rows)


def _select_exploration_candidate(
    ordered: list[PressureContribution],
    eligible: list[PressureContribution],
    chosen: FieldConfig,
    field_seed: int | None,
) -> tuple[list[PressureContribution], int | None]:
    """Optionally elevate one weighted eligible contributor.

    Exploration is a separate field RNG.  It only chooses among already
    eligible, positive-pressure candidates and can replace at most one
    deterministic tail candidate.  It never creates or unblocks graph state.
    """

    if chosen.exploration != "on" or chosen.exploration_slots == 0:
        return ordered, field_seed
    if field_seed is None:
        raise ValueError("field_seed is required when exploration is on")
    rng = random.Random(field_seed)
    base = list(ordered)
    explored: list[PressureContribution] = []
    for _ in range(chosen.exploration_slots):
        pool = [item for item in eligible if item not in base and item not in explored]
        if not pool:
            break
        weights = [max(1, item.developmental_strength) for item in pool]
        total_weight = sum(weights)
        if not total_weight:
            break
        ticket = rng.randrange(total_weight)
        selected = pool[-1]
        cumulative = 0
        for item, weight in zip(pool, weights, strict=True):
            cumulative += weight
            if ticket < cumulative:
                selected = item
                break
        selected = replace(selected, exploration_selected=True)
        explored.append(selected)
    keep = max(0, min(len(base), chosen.max_contributors - len(explored)))
    return base[:keep] + explored, field_seed


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
    field_seed: int | None = None,
) -> FieldResult:
    """Compute the versioned bounded F0 field.

    F0 v2 separates a weak background field from contextual activation.  An
    empty graph is cold start and produces zero pressure; a non-empty eligible
    graph retains bounded background accessibility even when the query is
    unrelated.  Passing ``version=f0-graph-pressure-v1`` selects the preserved
    historical relevance-gated implementation.
    """

    chosen = config or FieldConfig()
    if chosen.version == LEGACY_FIELD_VERSION:
        return _compute_field_legacy(
            query,
            concepts,
            edges,
            learner,
            config=chosen,
            quarantined_edges=quarantined_edges,
            ineligible_edges=ineligible_edges,
            field_enabled=field_enabled,
        )
    if chosen.version != FIELD_VERSION:
        raise ValueError(f"unsupported field version: {chosen.version}")
    concept_rows = tuple(sorted(concepts, key=lambda item: (item.key, item.label)))
    edge_rows = tuple(sorted(edges, key=lambda item: (item.source, item.target, item.key)))
    active = _background_seed(concept_rows, query, chosen)
    if not field_enabled or not edge_rows:
        return FieldResult(
            query,
            chosen,
            active,
            (),
            "",
            field_enabled=field_enabled,
            exploration=chosen.exploration,
            field_seed=field_seed,
        )

    outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in edge_rows:
        outgoing[edge.source].append(edge)
    # One background seed per concept keeps the graph present off-topic.  A
    # contextual seed replaces the weak baseline for that concept, causing
    # relevant neighborhoods to dominate while unrelated history remains
    # merely accessible.
    seeds = tuple(
        (item.key, 0, item.initial_activation, (item.key,), frozenset((item.key,)))
        for item in active
    )
    queue: deque[tuple[str, int, int, tuple[str, ...], frozenset[str]]] = deque(seeds)
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
                        edge.key,
                        edge.source,
                        edge.target,
                        edge.relationship,
                        next_path,
                        next_depth,
                        activation,
                        0,
                        0,
                        0,
                        False,
                        "quarantined" if edge.key in quarantined_edges else "ineligible",
                        component=(
                            "contextual"
                            if activation > chosen.background_activation
                            else "background"
                        ),
                    )
                )
                continue
            strength, strength_reason = _strength(edge, learner)
            if strength <= 0:
                continue
            attenuation = chosen.attenuation ** next_depth
            denominator = FIXED_ONE ** next_depth
            attenuated = (activation * strength * attenuation) // (FIXED_ONE * denominator)
            # Keep weak eligible pressure in the auditable field.  The old
            # minimum_pressure gate is now a render/pruning threshold only;
            # this prevents the field from collapsing to exactly zero merely
            # because relevance is weak.
            if attenuated <= 0:
                continue
            component = "contextual" if activation > chosen.background_activation else "background"
            raw.append(
                PressureContribution(
                    edge.key,
                    edge.source,
                    edge.target,
                    edge.relationship,
                    next_path,
                    next_depth,
                    activation,
                    strength,
                    (activation * strength) // FIXED_ONE,
                    attenuated,
                    True,
                    strength_reason,
                    component=component,
                )
            )
            queue.append((edge.target, next_depth, attenuated, next_path, visited | {edge.target}))
    blocked_records = tuple(item for item in raw if not item.eligible)
    # A single earned edge can be reached from its contextual source and from
    # a weak background seed for an upstream node.  Keep the strongest
    # deterministic path for that edge so one association cannot consume
    # multiple contributor slots merely because it has multiple seed paths.
    by_edge: dict[str, PressureContribution] = {}
    for item in (item for item in raw if item.eligible):
        previous = by_edge.get(item.edge_key)
        if previous is None or item.attenuated_pressure > previous.attenuated_pressure or (
            item.attenuated_pressure == previous.attenuated_pressure
            and item.path < previous.path
        ):
            by_edge[item.edge_key] = item
    eligible = list(by_edge.values())
    ordered = sorted(
        eligible,
        key=lambda item: (-item.attenuated_pressure, item.distance, item.edge_key, item.path),
    )[: chosen.max_contributors]
    ordered, resolved_seed = _select_exploration_candidate(
        ordered, eligible, chosen, field_seed
    )
    # Re-sort after exploration replacement so payload order remains
    # deterministic for a fixed field seed.
    ordered.sort(
        key=lambda item: (
            -item.attenuated_pressure,
            item.distance,
            item.edge_key,
            item.path,
        )
    )
    total = sum(item.attenuated_pressure for item in ordered)
    scale = min(FIXED_ONE, (chosen.total_budget * FIXED_ONE) // total) if total else 0
    normalized: list[PressureContribution] = []
    for item in ordered:
        normalized_pressure = (item.attenuated_pressure * scale) // FIXED_ONE
        if chosen.exploration == "on" and item.exploration_selected:
            normalized_pressure = min(normalized_pressure, chosen.exploration_budget)
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
    renderable = tuple(
        item for item in final if item.final_pressure >= chosen.render_pressure_floor
    )
    # When the graph is entirely off-topic, expose the strongest bounded
    # background tendency rather than making the host-visible payload
    # indistinguishable from a cold start.  The pressure remains weak and the
    # strict payload budget still applies.
    if not renderable:
        renderable = tuple(item for item in final if item.final_pressure > 0)[:1]
    return FieldResult(
        query,
        chosen,
        active,
        final,
        _render(
            renderable,
            chosen.render_max_chars,
            {item.key: item.label for item in concept_rows},
        ),
        field_enabled=field_enabled,
        exploration=chosen.exploration,
        field_seed=resolved_seed,
    )


__all__ = [
    "FIELD_VERSION", "LEGACY_FIELD_VERSION", "ActiveConcept", "FieldConfig", "FieldResult",
    "PressureContribution", "compute_field",
]
