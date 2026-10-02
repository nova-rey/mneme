"""Pure, label-blind three-axis meters; frozen formulas live with the experiment.

Only recorded values enter this module. There are no runtime hooks, providers,
store handles or writeback. All extraction-dependent readings are post-response.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from mneme.development.field import _tokens
from mneme.experiments.arc_measurements import (
    _number,
    _overlap,
    _semantic_metrics,
    _semantic_sets,
    measure_conversation,
)

VERSION = "three-pressure-meters-v2-frozen-1"
INPUT_KEYS = frozenset({
    "conversation", "turn", "ordinal", "accepted_turn_id", "arc_id", "opening_task",
    "participant_text", "gemma_text", "residue", "sources", "source_roles",
    "extraction_coverage", "field", "historical_strengths", "accessibility_adjustments",
})
VIEWS = ("participant", "gemma", "combined")
_MARKERS = frozenset({
    "no", "not", "never", "without", "neither", "cannot", "can't", "isn't", "wasn't",
    "if", "unless", "when", "until", "only", "provided", "assuming",
    "passed", "failed", "resolved", "fixed", "unchanged", "increased", "decreased",
    "improved", "worsened", "observed", "measured", "confirmed", "rejected", "result",
})
_QUANTITY = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:\s*[%°a-zA-Zµ]+)?")


def _jaccard(left: set[Any] | None, right: set[Any] | None) -> float | None:
    return _overlap(left, right)


def _text(record: Mapping[str, Any], view: str) -> str | None:
    roles = ("participant", "gemma") if view == "combined" else (view,)
    parts = [record.get(f"{role}_text") for role in roles]
    return "\n".join(x for x in parts if isinstance(x, str)) if all(
        isinstance(x, str) for x in parts
    ) else None


def _span_quotes(
    item: Mapping[str, Any], sources: Mapping[str, Any], roles: Mapping[str, Any],
    selected: set[str],
) -> tuple[list[str], bool]:
    spans = item.get("source_spans")
    if not isinstance(spans, (list, tuple)) or not spans:
        return [], False
    quotes: list[str] = []
    for span in spans:
        if not isinstance(span, Mapping):
            return [], False
        slot, start, end = span.get("source_slot"), span.get("start"), span.get("end")
        if not isinstance(slot, str) or not isinstance(sources.get(slot), str):
            return [], False
        if (not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)
                or not 0 <= start < end <= len(sources[slot])):
            return [], False
        if roles.get(slot) in selected:
            quotes.append(sources[slot][start:end])
    return quotes, True


def source_view(record: Mapping[str, Any], view: str) -> dict[str, Any]:
    """Project validated current-source spans, including edge endpoint provenance."""
    if view not in VIEWS:
        raise ValueError("unknown source view")
    text = _text(record, view)
    result: dict[str, Any] = {
        "text": text, "residue": None, "evidence_quotes": [], "semantic_coverage": False,
        "semantic_unavailable_reason": "missing_sources_or_extraction",
    }
    sources, roles = record.get("sources"), record.get("source_roles")
    coverage, residue = record.get("extraction_coverage"), record.get("residue")
    if not all(isinstance(x, Mapping) for x in (sources, roles, coverage, residue)):
        return result
    assert isinstance(sources, Mapping) and isinstance(roles, Mapping)
    assert isinstance(coverage, Mapping) and isinstance(residue, Mapping)
    selected = {"participant", "gemma"} if view == "combined" else {view}
    for role in selected:
        slots = [slot for slot in sources if roles.get(slot) == role]
        if (not slots or any(coverage.get(slot) is not True for slot in slots)
                or any(sources[slot] != record.get(f"{role}_text") for slot in slots)):
            result["semantic_unavailable_reason"] = "incomplete_or_mismatched_source_coverage"
            return result
    concepts, edges = residue.get("core_concepts"), residue.get("edge_candidates")
    if not isinstance(concepts, list) or not isinstance(edges, list):
        return result
    chosen: set[str] = set()
    quotes: set[str] = set()
    by_key: dict[str, Any] = {}
    for item in concepts:
        if (not isinstance(item, Mapping) or not isinstance(item.get("key"), str)
                or item["key"] in by_key):
            return result
        by_key[item["key"]] = item
        spans, valid = _span_quotes(item, sources, roles, selected)
        if not valid:
            result["semantic_unavailable_reason"] = "invalid_provenance"
            return result
        if spans:
            chosen.add(item["key"])
            quotes.update(spans)
    selected_edges: list[dict[str, Any]] = []
    for item in edges:
        if not isinstance(item, Mapping):
            return result
        spans, valid = _span_quotes(item, sources, roles, selected)
        if not valid or item.get("from") not in by_key or item.get("to") not in by_key:
            result["semantic_unavailable_reason"] = "invalid_provenance"
            return result
        if spans:
            chosen.update((item["from"], item["to"]))
            selected_edges.append(dict(item))
            quotes.update(spans)
    projected = {"core_concepts": [dict(by_key[key]) for key in sorted(chosen)],
                 "edge_candidates": selected_edges}
    c, r = _semantic_sets(projected)
    if c is None or r is None:
        result["semantic_unavailable_reason"] = "invalid_semantic_structure"
        return result
    result.update(residue=projected, evidence_quotes=sorted(quotes), semantic_coverage=True,
                  semantic_unavailable_reason=None)
    return result


def _evidence_atoms(quotes: Sequence[str]) -> set[str] | None:
    atoms: set[str] = set()
    for quote in quotes:
        for match in _QUANTITY.finditer(quote.casefold()):
            atoms.add("quantity:" + " ".join(match.group().split()))
        tokens = _tokens(quote)
        for index, token in enumerate(tokens):
            if token in _MARKERS:
                atoms.add("marker:" + " ".join(tokens[max(0, index - 2):index + 3]))
    return atoms or None


def _grams(text: str | None, *, characters: bool = False) -> set[Any] | None:
    if text is None:
        return None
    sequence: Any = " ".join(text.casefold().split()) if characters else _tokens(text)
    size = 5 if characters else 3
    grams = {tuple(sequence[i:i + size]) for i in range(len(sequence) - size + 1)}
    return grams or None


def _distribution(weights: Any) -> dict[str, float] | None:
    if (not isinstance(weights, Mapping) or not weights
            or any(not isinstance(k, str) or not k or not _number(v)
                   for k, v in weights.items())):
        return None
    total = math.fsum(weights.values())
    return {key: weights[key] / total for key in sorted(weights)} if total else None


def _ranks(distribution: Mapping[str, float]) -> dict[str, float]:
    values = sorted(distribution.values(), reverse=True)
    return {key: (values.index(value) + len(values) - values[::-1].index(value) - 1) / 2
            for key, value in distribution.items()}


def historical_metrics(record: Mapping[str, Any]) -> dict[str, Any]:
    """Compare earned baseline with actual weights on precisely identical candidates."""
    row: dict[str, Any] = dict.fromkeys([
        "history_entropy_nats", "history_effective_count", "history_hhi", "history_top_mass",
        "conditioned_entropy_nats", "conditioned_hhi", "conditioned_top_mass",
        "history_context_tv", "history_rank_displacement", "history_candidate_diagnostics",
        "history_candidate_count", "accessibility_adjustments",
    ])
    adjustments = record.get("accessibility_adjustments")
    if isinstance(adjustments, Mapping) and all(
        isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)
        for k, v in adjustments.items()
    ):
        row["accessibility_adjustments"] = dict(sorted(adjustments.items()))
    p = _distribution(record.get("historical_strengths"))
    field = record.get("field")
    raw = field.get("accessibility_distribution") if isinstance(field, Mapping) else None
    if not isinstance(raw, list) or not all(
        isinstance(x, Mapping) and isinstance(x.get("candidate"), str) for x in raw
    ):
        return row
    weights = {x["candidate"]: x.get("probability") for x in raw}
    q = _distribution(weights) if len(weights) == len(raw) else None
    if p is None or q is None or set(p) != set(q):
        return row
    for name, distribution in (("history", p), ("conditioned", q)):
        entropy = -math.fsum(x * math.log(x) for x in distribution.values() if x > 0)
        row[f"{name}_entropy_nats"] = entropy
        row[f"{name}_hhi"] = math.fsum(x * x for x in distribution.values())
        row[f"{name}_top_mass"] = max(distribution.values())
        if name == "history":
            row["history_effective_count"] = math.exp(entropy)
    rp, rq = _ranks(p), _ranks(q)
    row.update(
        history_candidate_count=len(p),
        history_context_tv=0.5 * math.fsum(abs(p[k] - q[k]) for k in p),
        history_rank_displacement=math.fsum(abs(rp[k] - rq[k]) for k in p)
        / (len(p) * max(1, len(p) - 1)),
        history_candidate_diagnostics=[{
            "candidate": k, "earned_probability": p[k], "conditioned_probability": q[k],
            "earned_rank": rp[k], "conditioned_rank": rq[k], "rank_change": rq[k] - rp[k],
        } for k in p],
    )
    return row


def _activation_metrics(field: Any) -> dict[str, Any]:
    row: dict[str, Any] = dict.fromkeys([
        "context_activation_total", "context_positive_count", "context_positive_coverage",
        "context_positive_mean", "context_hhi",
    ])
    active = field.get("active_concepts") if isinstance(field, Mapping) else None
    if not isinstance(active, list) or not active or not all(
        isinstance(x, Mapping) and _number(x.get("contextual_activation")) for x in active
    ):
        return row
    weights = [x["contextual_activation"] for x in active if x["contextual_activation"] > 0]
    total = math.fsum(weights)
    row.update(context_activation_total=total, context_positive_count=len(weights),
               context_positive_coverage=len(weights) / len(active),
               context_positive_mean=total / len(weights) if weights else None,
               context_hhi=math.fsum((x / total) ** 2 for x in weights) if total else None)
    return row


def _baseline(prefix: list[dict[str, Any]], window: int) -> dict[str, Any]:
    # Old code needs one immutable arc declaration. Supply only the observed
    # prefix, recompute, and take its last row. Never expose future membership.
    arc = {"episode_id": prefix[-1]["arc_id"], "start_ordinal": prefix[0]["ordinal"],
           "end_ordinal": prefix[-1]["ordinal"],
           "turn_ids": [x["accepted_turn_id"] for x in prefix]}
    safe = [{"conversation": x["conversation"], "turn": x["turn"], "ordinal": x["ordinal"],
             "accepted_turn_id": x["accepted_turn_id"], "arc": arc,
             "residue": x["residue"], "field": x["field"]} for x in prefix]
    row = measure_conversation(safe, window)[-1]
    return {k: v for k, v in row.items() if k not in {"condition", "measurement_version"}}


def _union(sets: Sequence[set[Any] | None]) -> set[Any] | None:
    return set().union(*(x for x in sets if x is not None)) if sets and all(
        x is not None for x in sets
    ) else None


def measure_pressure_records(
    records: Sequence[Mapping[str, Any]], windows: Sequence[int] = (3, 5),
) -> list[dict[str, Any]]:
    """Return each accepted turn × source view × frozen window, without side effects.

    Unknown top-level inputs are rejected to keep private experimental design out
    of the meter boundary. The caller joins condition/fidelity labels afterward.
    """
    if not windows or len(set(windows)) != len(windows) or any(
        isinstance(w, bool) or w not in (3, 5) for w in windows
    ):
        raise ValueError("windows must be a unique nonempty selection of 3 and 5")
    states: dict[str, dict[str, Any]] = {}
    output: list[dict[str, Any]] = []
    for record in records:
        if set(record) - INPUT_KEYS:
            unknown = sorted(set(record) - INPUT_KEYS)
            raise ValueError("unexpected meter input keys: " + str(unknown))
        conversation, arc_id, ordinal = (
            record.get(k) for k in ("conversation", "arc_id", "ordinal")
        )
        if (not isinstance(conversation, str) or not conversation
                or not isinstance(arc_id, str) or not arc_id
                or not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0):
            raise ValueError("invalid conversation, arc identity or ordinal")
        state = states.setdefault(conversation, {"ordinal": -1, "arc_id": None,
                                                "seen": set(), "turn_ids": set()})
        if ordinal <= state["ordinal"]:
            raise ValueError("ordinals must strictly increase")
        turn_id = record.get("accepted_turn_id", f"{conversation}:turn:{ordinal}")
        if not isinstance(turn_id, str) or not turn_id or turn_id in state["turn_ids"]:
            raise ValueError("invalid or repeated accepted turn identity")
        pivot = state["arc_id"] is not None and state["arc_id"] != arc_id
        if arc_id != state["arc_id"]:
            if arc_id in state["seen"]:
                raise ValueError("an arc cannot recur after a different arc")
            state.update(arc_id=arc_id, prefixes={v: [] for v in VIEWS}, participant=[],
                         history={(v, w): [] for v in VIEWS for w in windows})
            state["seen"].add(arc_id)
        views = {view: source_view(record, view) for view in VIEWS}
        participant = views["participant"]
        pc, pr = _semantic_sets(participant["residue"])
        participant_sets = {"concept": pc, "relationship": pr,
                            "tokens": set(_tokens(participant["text"]))
                            if participant["text"] is not None else None}
        common = {**_activation_metrics(record.get("field")), **historical_metrics(record)}
        for view, projected in views.items():
            prefix = state["prefixes"][view]
            prefix.append({"conversation": conversation, "turn": record.get("turn"),
                           "ordinal": ordinal, "arc_id": arc_id, "accepted_turn_id": turn_id,
                           "residue": projected["residue"], "field": record.get("field")})
            text = projected["text"]
            tokens = set(_tokens(text)) if text is not None else None
            words = len(_tokens(text)) if text is not None else None
            c, r = _semantic_sets(projected["residue"])
            evidence = _evidence_atoms(projected["evidence_quotes"])
            wordgrams, chargrams = _grams(text), _grams(text, characters=True)
            for window in windows:
                row = _baseline(prefix, window)
                row.update(common)
                row.update(measurement_version=VERSION, source_view=view, arc_pivot=pivot,
                           semantic_coverage=projected["semantic_coverage"],
                           semantic_unavailable_reason=projected["semantic_unavailable_reason"],
                           source_word_count=words, source_character_count=len(text)
                           if text is not None else None,
                           evidence_quotes=list(projected["evidence_quotes"]))
                history = state["history"][(view, window)]
                _semantic_metrics("evidence", evidence, history, row, window=window,
                                  complete_prefix=True, adjacent=bool(history))
                row["evidence_atoms"] = sorted(evidence) if evidence is not None else None
                opening = record.get("opening_task")
                row["opening_text_jaccard"] = _jaccard(
                    tokens, set(_tokens(opening)) if isinstance(opening, str) else None)
                recent = state["participant"][-window:]
                row["recent_participant_turn_count"] = len(recent)
                row["recent_participant_window_complete"] = len(recent) == window
                row["recent_participant_text_jaccard"] = _jaccard(
                    tokens, _union([x["tokens"] for x in recent]))
                anchor = state["participant"][0] if state["participant"] else participant_sets
                for name, current in (("concept", c), ("relationship", r)):
                    row[f"opening_participant_{name}_jaccard"] = _jaccard(current, anchor[name])
                    row[f"recent_participant_{name}_jaccard"] = _jaccard(
                        current, _union([x[name] for x in recent]))
                for name, grams in (("word3", wordgrams), ("char5", chargrams)):
                    row[f"{name}_adjacent_jaccard"] = _jaccard(
                        grams, history[-1][name]) if history else None
                    overlaps = [_jaccard(grams, x[name]) for x in history[-window:]]
                    row[f"{name}_recent_max_jaccard"] = (
                        max(x for x in overlaps if x is not None)
                        if overlaps and all(x is not None for x in overlaps) else None)
                counts = [row[f"{name}_new_count"] for name in ("concept", "relationship")]
                row["structure_new_count"] = sum(counts) if all(x is not None for x in counts) \
                    else None
                for name in ("concept", "relationship", "structure", "evidence"):
                    count = row[f"{name}_new_count"]
                    row[f"{name}_new_per_100_words"] = (
                        100 * count / words if count is not None and words else None)
                cn = row["concept_rolling_novelty_mean"]
                rn = row["relationship_rolling_novelty_mean"]
                en = row["evidence_rolling_novelty_mean"]
                structure = 1 - (cn + rn) / 2 if cn is not None and rn is not None else None
                w, ch = row["word3_recent_max_jaccard"], row["char5_recent_max_jaccard"]
                variants = {
                    "structure_repeat": structure,
                    "evidence_aware_repeat": structure * (1 - en)
                    if structure is not None and en is not None else None,
                    "surface_repeat": (w + ch) / 2 if w is not None and ch is not None else None,
                }
                for name, value in variants.items():
                    row[name + "_raw"] = value
                    row[name + "_age_conditioned"] = (
                        row["maturity"] * value if value is not None else None)
                output.append(row)
                history.append({"evidence": evidence, "age": row["arc_age"], "row": row,
                                "word3": wordgrams, "char5": chargrams})
        state["participant"].append(participant_sets)
        state["ordinal"] = ordinal
        state["turn_ids"].add(turn_id)
    return output
