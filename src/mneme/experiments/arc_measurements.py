"""Passive, replayable arc statistics from already recorded runtime outputs.

No runtime hooks, state/store handles, model calls, or selection policy live here.
Labels use the runtime's exact lookup normalization, not semantic synonym matching.
Relationship identity is (source label, canonical relation, target label), ignoring
local keys and evidence-quotation hashes. Field identities use persisted graph keys.

A window contains accepted members of ONE frozen arc, including the current turn.
Novelty compares each turn to up to ``window`` preceding members; its rolling mean
requires ``window`` defined fractions. The first member has no novelty baseline, so
with the default window=3 composites first exist at age 4. ``warmup`` describes
the set window; ``composite_warmup`` describes the extra novelty-baseline turn.
Missing members/semantics invalidate affected windows; cumulative claims stay
unavailable after a gap.

Frozen exploratory proxies (not quality scores or intervention thresholds):
  maturity = min(1, (accepted_member_age - 1) / 5)
  C1 = maturity * (1 - rolling_concept_novelty_mean)
  C2 = maturity * (1 - (concept_mean + relationship_mean) / 2)
  C3 = C2 * contextual_HHI
HHI uses positive contextual activation, not lottery odds. No metric changes SAA.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from mneme.memory.residue import RELATIONSHIP_ALIASES, SUPPORTED_RELATIONSHIP_KINDS
from mneme.memory.resolution import normalize_lookup_label

VERSION = "passive-arc-measurements-v1"


def _semantic_sets(residue: Any) -> tuple[set[str] | None, set[tuple[str, str, str]] | None]:
    if not isinstance(residue, Mapping) or not isinstance(residue.get("core_concepts"), list):
        return None, None
    labels: dict[str, str] = {}
    try:
        for item in residue["core_concepts"]:
            key = item["key"]
            if not isinstance(key, str) or not key or key in labels:
                return None, None
            labels[key] = normalize_lookup_label(item["label"])
    except (KeyError, TypeError, ValueError):
        return None, None
    concepts = set(labels.values())
    if not isinstance(residue.get("edge_candidates"), list):
        return concepts, None
    relationships: set[tuple[str, str, str]] = set()
    try:
        for item in residue["edge_candidates"]:
            relation = item["relationship"]
            relation = RELATIONSHIP_ALIASES.get(relation, relation)
            if relation not in SUPPORTED_RELATIONSHIP_KINDS:
                return concepts, None
            relationships.add((labels[item["from"]], relation, labels[item["to"]]))
    except (KeyError, TypeError, ValueError):
        return concepts, None
    return concepts, relationships


def _overlap(left: set[Any] | None, right: set[Any] | None) -> float | None:
    if left is None or right is None or not left.union(right):
        return None
    return len(left.intersection(right)) / len(left.union(right))


def _mean(values: Sequence[float | None], window: int) -> float | None:
    if len(values) != window or any(value is None for value in values):
        return None
    return math.fsum(value for value in values if value is not None) / window


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and value >= 0
    )


def _key_set(value: Any) -> set[str] | None:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        return None
    return set(value)


def _field(field: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics: dict[str, Any] = dict.fromkeys([
        "saa_candidate_count", "saa_entropy_nats", "saa_effective_candidate_count",
        "saa_max_mass", "contextual_hhi", "background_candidate_count", "background_mass",
        "background_unselected_count", "selected_landing", "active_neighborhood_count",
        "route_count",
    ])
    sets: dict[str, Any] = {"candidates": None, "neighborhood": None, "routes": None}
    if not isinstance(field, Mapping):
        return metrics, sets
    active = field.get("active_concepts")
    if isinstance(active, list) and all(
        isinstance(x, Mapping) and _number(x.get("contextual_activation")) for x in active
    ):
        context_weights = [
            x["contextual_activation"] for x in active if x["contextual_activation"] > 0
        ]
        total = math.fsum(context_weights)
        if total:
            metrics["contextual_hhi"] = math.fsum((x / total) ** 2 for x in context_weights)
    neighborhood = _key_set(field.get("active_neighborhood"))
    sets["neighborhood"] = neighborhood
    if neighborhood is not None:
        metrics["active_neighborhood_count"] = len(neighborhood)
    contributions = field.get("contributions")
    if isinstance(contributions, list) and all(
        isinstance(x, Mapping) and _key_set(x.get("path")) is not None
        and len(x["path"]) > 0 for x in contributions
    ):
        sets["routes"] = {tuple(x["path"]) for x in contributions}
        metrics["route_count"] = len(sets["routes"])
    distribution = field.get("accessibility_distribution")
    if not isinstance(distribution, list) or not distribution or not all(
        isinstance(x, Mapping) and isinstance(x.get("candidate"), str) and x["candidate"]
        and _number(x.get("probability")) for x in distribution
    ):
        return metrics, sets
    weights = {x["candidate"]: x["probability"] for x in distribution}
    total = math.fsum(weights.values())
    if len(weights) != len(distribution) or not total:
        return metrics, sets
    probabilities = {key: value / total for key, value in weights.items()}
    entropy = -math.fsum(p * math.log(p) for p in probabilities.values() if p > 0)
    sets["candidates"] = set(weights)
    metrics.update(saa_candidate_count=len(weights), saa_entropy_nats=entropy,
                   saa_effective_candidate_count=math.exp(entropy),
                   saa_max_mass=max(probabilities.values()))
    selected = field.get("selected_landing")
    if isinstance(selected, str) and selected in weights:
        metrics["selected_landing"] = selected
    components = field.get("distribution_components")
    if isinstance(components, list) and all(
        isinstance(x, Mapping) and isinstance(x.get("candidate"), str)
        and x.get("component") in {"background", "contextual_and_background"} for x in components
    ):
        by_key = {x["candidate"]: x["component"] for x in components}
        if set(by_key) == set(weights) and len(by_key) == len(components):
            background = {key for key, value in by_key.items() if value == "background"}
            metrics["background_candidate_count"] = len(background)
            metrics["background_mass"] = math.fsum(probabilities[key] for key in background)
            if metrics["selected_landing"] is not None:
                metrics["background_unselected_count"] = len(background - {selected})
    return metrics, sets


def _semantic_metrics(
    name: str, current: set[Any] | None, history: list[dict[str, Any]],
    row: dict[str, Any], *, window: int, complete_prefix: bool, adjacent: bool,
) -> None:
    prior = [item[name] for item in history]
    recent = prior[-window:]
    valid_recent = bool(recent) and adjacent and all(x is not None for x in recent)
    # A missing accepted member cannot be hidden by a sparse list of recorded rows.
    if recent and history[-1]["age"] - history[-len(recent)]["age"] + 1 != len(recent):
        valid_recent = False
    row[f"{name}_count"] = None if current is None else len(current)
    row[f"{name}_labels" if name == "concept" else "relationship_triples"] = (
        None if current is None else sorted(current)
    )
    row[f"{name}_arc_novelty"] = None
    row[f"{name}_new_count"] = None
    if current is not None and prior and complete_prefix and all(x is not None for x in prior):
        new = len(current - set().union(*prior))
        row[f"{name}_arc_novelty"] = new / len(current) if current else None
        row[f"{name}_new_count"] = new
    overlap = _overlap(current, prior[-1]) if prior and adjacent else None
    row[f"{name}_adjacent_movement"] = None if overlap is None else 1 - overlap
    novelty = None
    if current and valid_recent:
        novelty = len(current - set().union(*recent)) / len(current)
    row[f"{name}_window_novelty"] = novelty
    row[f"{name}_window_repeat"] = None if novelty is None else 1 - novelty
    observations = [*history[-(window - 1):], {name: current, "age": row["arc_age"]}] \
        if window > 1 else [{name: current, "age": row["arc_age"]}]
    sets = [item[name] for item in observations]
    contiguous = observations[-1]["age"] - observations[0]["age"] + 1 == len(observations)
    full = len(sets) == window and contiguous and all(x is not None for x in sets)
    row[f"{name}_window_coverage"] = sum(x is not None for x in sets) / window
    row[f"{name}_rolling_saturation"] = None
    if full:
        total = sum(len(x) for x in sets if x is not None)
        if total:
            row[f"{name}_rolling_saturation"] = 1 - len(set().union(*sets)) / total
    previous_rows = [item["row"] for item in history[-(window - 1):]] if window > 1 else []
    fractions = [item[f"{name}_window_novelty"] for item in previous_rows] + [novelty]
    row[f"{name}_rolling_novelty_mean"] = _mean(fractions, window) if full else None
    new_counts = [item[f"{name}_new_count"] for item in previous_rows]
    new_counts.append(row[f"{name}_new_count"])
    row[f"{name}_rolling_new_per_turn"] = _mean(new_counts, window) if full else None


def measure_conversation(
    records: Sequence[Mapping[str, Any]], window: int = 3,
) -> list[dict[str, Any]]:
    """Measure recorded accepted turns without mutating inputs or any runtime state.

    Required: conversation, condition, turn, ordinal, arc (ConversationEpisode dict),
    residue (Residue dict or None), field (FieldResult dict or None). Optional
    accepted_turn_id defaults to the declared-runner ``conversation:turn:ordinal``.
    Malformed identity/order raises ValueError. Missing/malformed semantic or field
    inputs produce null statistics. Raw residue source quotes are not revalidated;
    callers must supply the runtime's validated residue, never an unvalidated model
    proposal. Structural measurement validity is independently checked here.
    """
    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        raise ValueError("window must be a positive integer")
    states: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for record in records:
        conversation = record.get("conversation")
        ordinal = record.get("ordinal")
        arc = record.get("arc")
        if not isinstance(conversation, str) or not conversation:
            raise ValueError("conversation must be a nonempty string")
        if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0:
            raise ValueError("ordinal must be a nonnegative integer")
        if not isinstance(arc, Mapping):
            raise ValueError("arc must be a frozen ConversationEpisode dict")
        members = arc.get("turn_ids")
        arc_id = arc.get("episode_id")
        start, end = arc.get("start_ordinal"), arc.get("end_ordinal")
        if (not isinstance(arc_id, str) or not arc_id or not isinstance(members, list)
                or not members or any(not isinstance(x, str) or not x for x in members)
                or len(set(members)) != len(members)
                or not isinstance(start, int) or not isinstance(end, int)
                or not 0 <= start <= ordinal <= end):
            raise ValueError("invalid arc membership/bounds")
        turn_id = record.get("accepted_turn_id", f"{conversation}:turn:{ordinal}")
        if turn_id not in members:
            raise ValueError("accepted turn identity is not in arc membership")
        age = members.index(turn_id) + 1
        if (age == 1 and ordinal != start) or (age == len(members) and ordinal != end):
            raise ValueError("arc endpoint ordinal disagrees with membership")
        state = states.setdefault(conversation, {"ordinal": -1, "arc_id": None, "seen": set()})
        if ordinal <= state["ordinal"]:
            raise ValueError("ordinals must strictly increase per conversation")
        pivot = state["arc_id"] is not None and state["arc_id"] != arc_id
        if state["arc_id"] != arc_id:
            if arc_id in state["seen"]:
                raise ValueError("a frozen arc cannot recur after a different arc")
            state.update(arc_id=arc_id, arc=dict(arc), history=[])
            state["seen"].add(arc_id)
        elif state["arc"] != arc:
            raise ValueError("arc declaration changed during replay")
        history = state["history"]
        if history and age <= history[-1]["age"]:
            raise ValueError("arc membership must strictly increase")
        adjacent = bool(history) and age == history[-1]["age"] + 1
        prefix = age == len(history) + 1 and (not history or history[0]["age"] == 1)
        row = {
            "measurement_version": VERSION, "conversation": conversation,
            "condition": record.get("condition"), "turn": record.get("turn"),
            "ordinal": ordinal, "accepted_turn_id": turn_id, "arc_id": arc_id,
            "arc_age": age, "ordinal_span": ordinal - start + 1,
            "arc_pivot": pivot, "window": window, "warmup": len(history) + 1 < window,
            "composite_warmup": len(history) + 1 <= window,
            "membership_prefix_complete": prefix,
            "maturity": min(1.0, (age - 1) / 5),
        }
        concept, relationship = _semantic_sets(record.get("residue"))
        for name, current in (("concept", concept), ("relationship", relationship)):
            _semantic_metrics(name, current, history, row, window=window,
                              complete_prefix=prefix, adjacent=adjacent)
        field_metrics, field_sets = _field(record.get("field"))
        row.update(field_metrics)
        for name in ("candidates", "neighborhood", "routes"):
            row[f"{name}_adjacent_jaccard"] = (
                _overlap(field_sets[name], history[-1]["field_sets"][name]) if adjacent else None
            )
        prior_rows = [item["row"] for item in history[-(window - 1):]] if window > 1 else []
        landings = [item["selected_landing"] for item in prior_rows] + [row["selected_landing"]]
        full = len(landings) == window and all(x is not None for x in landings)
        if full and window > 1:
            full = age - history[-(window - 1)]["age"] + 1 == window
        row["selected_landing_rolling_repeat"] = (
            1 - len(set(landings)) / window if full else None
        )
        c = row["concept_rolling_novelty_mean"]
        r = row["relationship_rolling_novelty_mean"]
        row["c1_concept_persistence_proxy"] = row["maturity"] * (1 - c) if c is not None else None
        c2 = row["maturity"] * (1 - (c + r) / 2) if c is not None and r is not None else None
        row["c2_structure_persistence_proxy"] = c2
        hhi = row["contextual_hhi"]
        row["c3_context_persistence_proxy"] = (
            c2 * hhi if c2 is not None and hhi is not None else None
        )
        history.append({"age": age, "concept": concept, "relationship": relationship,
                        "field_sets": field_sets, "row": row})
        state["ordinal"] = ordinal
        rows.append(row)
    return rows
