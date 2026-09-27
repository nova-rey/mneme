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
SAA_FIELD_VERSION = "f0-saa-v1"
_DESCRIPTORS = frozenset(
    {
        "a", "an", "and", "approach", "arrangement", "be", "can", "could",
        "device", "for", "how", "idea", "in", "is", "kind", "method", "my",
        "of", "on", "option", "process", "setup", "solution", "style", "system",
        "technique", "that", "the", "this", "to", "tool", "type", "way", "with",
        "without", "would", "your",
    }
)
_LOW_INFORMATION = _DESCRIPTORS | frozenset(
    {
        "i", "it", "he", "she", "they", "them", "we", "us", "you",
        "me", "this", "that", "these", "those", "there", "here", "who",
        "what", "which", "when", "where", "why", "how", "am", "are", "was",
        "were", "been", "being", "do", "does", "did", "done", "has", "have",
        "had", "will", "shall", "should", "may", "might", "must", "not",
        "very", "just", "more", "most", "some", "any", "one",
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
    target_content = set(target) - _LOW_INFORMATION
    # A pronoun or function-word label can remain in the earned graph for
    # provenance, but it must not make a context appear maximally familiar.
    if not target_content:
        return 0, ()
    if any(
        query_stems[index : index + len(target)] == target
        for index in range(len(query_stems) - len(target) + 1)
    ):
        return FIXED_ONE, tuple(sorted(set(target)))
    # Descriptor words can be present in both phrases without identifying a
    # semantic concept (for example the article ``a`` in ``a battery bank``).
    # Keep them out of contextual activation while retaining the conservative
    # exact-phrase path above.
    query_content = set(query_stems) - _LOW_INFORMATION
    shared = tuple(sorted(query_content & target_content))
    if not shared or set(query_stems) - set(target) > _LOW_INFORMATION:
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
    # SAA v1 parameters.  They are ignored by the historical F0 paths and
    # live here so a single serialisable configuration can be persisted by a
    # caller selecting the new version.
    saa_context_weight: int = 700_000
    saa_background_weight: int = 300_000
    saa_novelty_flattening: int = 650_000
    saa_propagation_attenuation: int = 650_000
    saa_decay: int = 800_000

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
        for name in (
            "saa_context_weight",
            "saa_background_weight",
            "saa_novelty_flattening",
            "saa_propagation_attenuation",
            "saa_decay",
        ):
            value = getattr(self, name)
            if not 0 <= value <= FIXED_ONE:
                raise ValueError(f"{name} must be in [0, 1]")


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
    # SAA diagnostics.  They remain empty for historical F0 results, keeping
    # old receipts and replay records byte-for-byte compatible.
    accessibility_distribution: tuple[tuple[str, int], ...] = ()
    distribution_flatness: int = 0
    selected_landing: str | None = None
    landing_probability: int = 0
    landing_ticket: int | None = None
    active_neighborhood: tuple[str, ...] = ()
    novelty: int = 0

    @property
    def total_pressure(self) -> int:
        return sum(item.final_pressure for item in self.contributions)

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
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
        if self.config.version == SAA_FIELD_VERSION:
            value.update(
                {
                    "accessibility_distribution": [
                        {"candidate": key, "probability": probability}
                        for key, probability in self.accessibility_distribution
                    ],
                    "distribution_flatness": self.distribution_flatness,
                    "selected_landing": self.selected_landing,
                    "landing_probability": self.landing_probability,
                    "landing_ticket": self.landing_ticket,
                    "active_neighborhood": list(self.active_neighborhood),
                    "novelty": self.novelty,
                }
            )
        return value


    @property
    def distribution(self) -> tuple[tuple[str, int], ...]:
        """Compatibility alias for audit consumers."""

        return self.accessibility_distribution

    @property
    def flatness(self) -> int:
        """Compatibility alias for the normalized flatness diagnostic."""

        return self.distribution_flatness


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


_SAA_RELATION_TENDENCIES: dict[str, str] = {
    "causal": "Changes in one part may produce downstream effects.",
    "causes": "Changes in one part may produce downstream effects.",
    "depends_on": "Outcomes may depend on the conditions that support them.",
    "enables": "Enabling conditions may make a useful outcome possible.",
    "supports": "Supporting structures may keep important functions available.",
    "retains": "Some arrangements may preserve a resource over time.",
    "maintains": "Some arrangements may preserve a resource over time.",
    "prevents": "Barriers may reduce unwanted outcomes.",
    "constrains": "Constraints may shape which outcomes remain feasible.",
    "part_of": "A component may matter as part of a larger system.",
    "associated_with": "Related factors may deserve joint consideration.",
    "related": "Related factors may deserve joint consideration.",
    "sequence": "Order and timing may change how a process unfolds.",
    "precedes": "Order and timing may change how a process unfolds.",
    "rhythm": "Repetition and variation may shape how a process unfolds.",
    "varies": "Repetition and variation may shape how a process unfolds.",
    "reduces": "Reducing one pressure may leave more room for another.",
    "isolates": "Separating failures may preserve the rest of a system.",
}

_SAA_LABEL_FAMILIES: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({"rhythm", "variation", "timing", "tempo", "melody", "beat"}),
        "Repetition and variation may shape how a process unfolds.",
    ),
    (
        frozenset({"redundancy", "fallback", "failure", "backup", "isolate"}),
        "Separating failures may preserve the rest of a system.",
    ),
    (
        frozenset({"resource", "reservoir", "water", "moisture", "flow", "buffer"}),
        "Buffers and steady flows may preserve options over time.",
    ),
    (
        frozenset({"choice", "probability", "chance", "risk", "uncertainty"}),
        "Unequal possibilities may still be managed as a structured set.",
    ),
    (
        frozenset({"sequence", "order", "timing", "stage", "transition", "phase"}),
        "Order and transitions may change what is possible next.",
    ),
    (
        frozenset({"role", "shared", "trust", "group", "coordination", "schedule"}),
        "Clear roles and shared expectations may keep coordination workable.",
    ),
    (
        frozenset({"contrast", "pattern", "shape", "color", "texture", "composition"}),
        "Contrast and repetition may organize attention without making it uniform.",
    ),
    (
        frozenset({"cost", "effort", "limited", "constraint", "scarce", "budget"}),
        "Limited resources may make tradeoffs and fallback options more salient.",
    ),
)


def _saa_label_facets(labels: dict[str, str], item: PressureContribution) -> tuple[str, ...]:
    """Return bounded semantic facets without exposing endpoint labels."""

    tokens = {
        _stem(token)
        for endpoint in (item.source, item.target)
        for token in _tokens(labels.get(endpoint, ""))
    }
    return tuple(text for family, text in _SAA_LABEL_FAMILIES if tokens & family)


def _render_saa(
    contributions: tuple[PressureContribution, ...],
    max_chars: int,
    labels: dict[str, str] | None = None,
) -> str:
    """Render active SAA pressure as a small, label-free abstraction.

    Graph labels, IDs, provenance, and scores deliberately never enter this
    function.  Directional relationship semantics are retained through a
    bounded relation vocabulary; unknown relations use a stable generic
    tendency rather than leaking their spelling to the host.
    """

    active = tuple(item for item in contributions if item.final_pressure > 0)
    if not active:
        return ""
    lines = ["Potentially accessible framings:"]
    seen: set[str] = set()
    for item in active:
        relation = re.sub(r"[^a-z0-9_]+", "_", item.relationship.casefold()).strip("_")
        line_text = _SAA_RELATION_TENDENCIES.get(relation)
        facets = _saa_label_facets(labels or {}, item)
        if line_text is None:
            line_text = (
                facets[0]
                if facets
                else "Different factors may interact in ways worth considering."
            )
        elif facets and facets[0] != line_text:
            line_text = f"{line_text} {facets[0]}"
        line = "- " + (line_text or "Different factors may interact in ways worth considering.")
        if line in seen:
            continue
        candidate_length = sum(len(value) + 1 for value in lines) + len(line)
        if candidate_length + 84 > max_chars:
            break
        seen.add(line)
        lines.append(line)
    if len(lines) == 1:
        return ""
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


def _saa_distribution(
    query: str,
    concepts: tuple[Any, ...],
    candidates: tuple[tuple[Any, int], ...],
    chosen: FieldConfig,
) -> tuple[tuple[tuple[str, int], ...], int, int]:
    """Return ``(distribution, flatness, novelty)`` for SAA v1.

    Context is a modulator, never an admission gate.  The baseline component
    keeps every eligible earned edge in the distribution; high contextual
    activation makes the distribution more peaked.  Integer fixed-point
    arithmetic keeps replay stable and makes the receipt self-contained.
    """

    context_by_key = {
        item.key: _activation(query, item.label)[0]
        for item in concepts
    }
    max_context = max(context_by_key.values(), default=0)
    novelty = FIXED_ONE - max_context
    raw_weights: list[tuple[str, int]] = []
    for edge, strength in candidates:
        source_context = context_by_key.get(edge.source, 0)
        target_context = context_by_key.get(edge.target, 0)
        context = max(source_context, target_context)
        # In a novel context flatten contextual discrimination toward the
        # developmental prior.  A familiar context retains a peaked score.
        if max_context < FIXED_ONE // 2:
            contextual = (
                context * (FIXED_ONE - chosen.saa_novelty_flattening)
                + FIXED_ONE * chosen.saa_novelty_flattening
            ) // FIXED_ONE
        else:
            contextual = context
        factor = chosen.saa_background_weight + (
            chosen.saa_context_weight * contextual
        ) // FIXED_ONE
        raw_weights.append((edge.key, max(1, (strength * factor) // FIXED_ONE)))
    total = sum(weight for _, weight in raw_weights)
    if not total:
        return (), 0, novelty
    probabilities = [
        (key, (weight * FIXED_ONE) // total)
        for key, weight in raw_weights
    ]
    # Preserve exact normalization without allowing order-dependent floating
    # point drift.  The residual is assigned to the strongest first candidate;
    # ties are already canonically sorted by edge key.
    residual = FIXED_ONE - sum(probability for _, probability in probabilities)
    if residual:
        probabilities[0] = (probabilities[0][0], probabilities[0][1] + residual)
    max_probability = max(probability for _, probability in probabilities)
    # 0 means maximally peaked; a uniform N-way distribution approaches 1.
    flatness = (
        0
        if len(probabilities) <= 1
        else ((FIXED_ONE - max_probability) * len(probabilities) * FIXED_ONE)
        // (FIXED_ONE * (len(probabilities) - 1))
    )
    return tuple(probabilities), min(FIXED_ONE, flatness), novelty


def _saa_empty_result(
    query: str,
    chosen: FieldConfig,
    active: tuple[ActiveConcept, ...],
    *,
    field_enabled: bool,
    field_seed: int,
    novelty: int = 0,
) -> FieldResult:
    return FieldResult(
        query,
        chosen,
        active,
        (),
        "",
        field_enabled=field_enabled,
        exploration="on",
        field_seed=field_seed,
        accessibility_distribution=(),
        distribution_flatness=0,
        novelty=novelty,
    )


def compute_saa_field(
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
    """Compute the inspectable stochastic associative accessibility field.

    SAA performs exactly one weighted landing over eligible earned edges and
    then conducts activation through a bounded local graph neighborhood.  The
    random stream is explicitly supplied by ``field_seed``; no administrative
    value participates in the draw.  This function is additive: callers using
    :func:`compute_field` with either historical F0 version retain their prior
    behavior unchanged.
    """

    if field_seed is None:
        raise ValueError("field_seed is required for f0-saa-v1")
    chosen = config or FieldConfig(version=SAA_FIELD_VERSION)
    if chosen.version != SAA_FIELD_VERSION:
        chosen = replace(chosen, version=SAA_FIELD_VERSION)
    concept_rows = tuple(sorted(concepts, key=lambda item: (item.key, item.label)))
    edge_rows = tuple(sorted(edges, key=lambda item: (item.source, item.target, item.key)))
    active = tuple(
        ActiveConcept(
            item.key,
            item.label,
            _activation(query, item.label)[0],
            _activation(query, item.label)[1],
            contextual_activation=_activation(query, item.label)[0],
        )
        for item in concept_rows
    )
    if not field_enabled:
        return _saa_empty_result(query, chosen, active, field_enabled=False, field_seed=field_seed)

    blocked_quarantine = set(quarantined_edges)
    blocked_ineligible = set(ineligible_edges)
    blocked = blocked_quarantine | blocked_ineligible
    candidates: list[tuple[Any, int]] = []
    for edge in edge_rows:
        if edge.key in blocked:
            continue
        strength, _ = _strength(edge, learner)
        if strength > 0:
            candidates.append((edge, strength))
    candidates_tuple = tuple(candidates)
    if not candidates_tuple:
        return _saa_empty_result(query, chosen, active, field_enabled=True, field_seed=field_seed)
    distribution, flatness, novelty = _saa_distribution(
        query, concept_rows, candidates_tuple, chosen
    )
    if not distribution:
        return _saa_empty_result(
            query,
            chosen,
            active,
            field_enabled=True,
            field_seed=field_seed,
            novelty=novelty,
        )
    rng = random.Random(field_seed)
    ticket = rng.randrange(FIXED_ONE)
    cumulative = 0
    selected_key = distribution[-1][0]
    selected_probability = distribution[-1][1]
    for key, probability in distribution:
        cumulative += probability
        if ticket < cumulative:
            selected_key = key
            selected_probability = probability
            break
    selected_edge = next(edge for edge, _ in candidates_tuple if edge.key == selected_key)
    strength_by_key = {edge.key: strength for edge, strength in candidates_tuple}
    outgoing: dict[str, list[Any]] = defaultdict(list)
    for edge in edge_rows:
        outgoing[edge.source].append(edge)
    raw: list[PressureContribution] = []
    # The landing itself receives the full local starting activation.  Its
    # graph edge strength still bounds the pressure, while propagation from
    # both endpoints lets a selected nexus conduct to nearby earned edges.
    landing_strength = strength_by_key[selected_key]
    raw.append(
        PressureContribution(
            selected_edge.key,
            selected_edge.source,
            selected_edge.target,
            selected_edge.relationship,
            (selected_edge.key,),
            0,
            FIXED_ONE,
            landing_strength,
            landing_strength,
            landing_strength,
            True,
            "earned",
            component="landing",
            exploration_selected=True,
        )
    )
    queue: deque[tuple[str, int, int, tuple[str, ...], frozenset[str]]] = deque(
        (
            node,
            0,
            FIXED_ONE,
            (selected_edge.key,),
            frozenset((node,)),
        )
        for node in (selected_edge.source, selected_edge.target)
    )
    while queue:
        node, depth, activation, path, visited = queue.popleft()
        if depth >= chosen.max_depth:
            continue
        for edge in outgoing.get(node, ()):
            if edge.target in visited:
                continue
            next_depth = depth + 1
            next_path = (*path, edge.key)
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
                        "quarantined" if edge.key in blocked_quarantine else "ineligible",
                        component="propagated",
                    )
                )
                continue
            propagated_strength = strength_by_key.get(edge.key)
            if propagated_strength is None:
                propagated_strength, _ = _strength(edge, learner)
            if propagated_strength <= 0:
                continue
            attenuation = chosen.saa_propagation_attenuation ** next_depth
            denominator = FIXED_ONE ** next_depth
            attenuated = (
                activation
                * propagated_strength
                * attenuation
                * chosen.saa_decay
                // (FIXED_ONE * denominator * FIXED_ONE)
            )
            if attenuated <= 0:
                continue
            raw.append(
                PressureContribution(
                    edge.key,
                    edge.source,
                    edge.target,
                    edge.relationship,
                    next_path,
                    next_depth,
                    activation,
                    propagated_strength,
                    (activation * propagated_strength) // FIXED_ONE,
                    attenuated,
                    True,
                    "earned",
                    component="propagated",
                )
            )
            queue.append((edge.target, next_depth, attenuated, next_path, visited | {edge.target}))
    by_edge: dict[str, PressureContribution] = {}
    for item in (item for item in raw if item.eligible):
        previous = by_edge.get(item.edge_key)
        if previous is None or item.attenuated_pressure > previous.attenuated_pressure:
            by_edge[item.edge_key] = item
    ordered = sorted(
        by_edge.values(),
        key=lambda item: (-item.attenuated_pressure, item.distance, item.edge_key, item.path),
    )[: chosen.max_contributors]
    total = sum(item.attenuated_pressure for item in ordered)
    scale = min(FIXED_ONE, (chosen.total_budget * FIXED_ONE) // total) if total else 0
    normalized: list[PressureContribution] = []
    for item in ordered:
        pressure = (item.attenuated_pressure * scale) // FIXED_ONE
        normalized.append(
            replace(item, normalized_pressure=pressure, final_pressure=pressure)
        )
    blocked_records = tuple(
        sorted(
            (item for item in raw if not item.eligible),
            key=lambda item: (item.edge_key, item.path),
        )
    )
    final = tuple(normalized) + blocked_records
    active_neighborhood: set[str] = set()
    for item in normalized:
        active_neighborhood.update((item.source, item.target))
    return FieldResult(
        query,
        chosen,
        active,
        final,
        _render_saa(
            tuple(normalized),
            chosen.render_max_chars,
            {item.key: item.label for item in concept_rows},
        ),
        field_enabled=True,
        exploration="on",
        field_seed=field_seed,
        accessibility_distribution=tuple(distribution),
        distribution_flatness=flatness,
        selected_landing=selected_key,
        landing_probability=selected_probability,
        landing_ticket=ticket,
        active_neighborhood=tuple(sorted(active_neighborhood)),
        novelty=novelty,
    )


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
    if chosen.version == SAA_FIELD_VERSION:
        return compute_saa_field(
            query,
            concepts,
            edges,
            learner,
            config=chosen,
            quarantined_edges=quarantined_edges,
            ineligible_edges=ineligible_edges,
            field_enabled=field_enabled,
            field_seed=field_seed,
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
    "FIELD_VERSION", "LEGACY_FIELD_VERSION", "SAA_FIELD_VERSION", "ActiveConcept",
    "FieldConfig", "FieldResult", "PressureContribution", "compute_field",
    "compute_saa_field",
]
