"""Passive text observations, not semantic judgments or generation controls.

Only exact recorded text enters these deterministic prefix-causal readings.
Quantity/state signatures can expose a change of wording; they cannot establish
that a measurement happened, identify its referent, or establish understanding.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from mneme.experiments.pressure_meters import INPUT_KEYS

VERSION = "movement-closure-v1"
# Fixed general-language lists, declared before prospective evidence.
STOP_WORDS = frozenset("""a an the and or but of to in on at for from with by as is are was were
be been being it its this that these those i me my we our you your he she they their them
do does did have has had can could would should will may might must please also just very
so than then there here what which who how why when where about into up out all any some
more most only still again now same each both""".split())
STATE_MARKERS = frozenset("""no not never without neither cannot can't isn't wasn't aren't weren't
don't doesn't didn't unchanged changed increased decreased improved worsened passed failed
resolved fixed observed measured confirmed rejected tested stopped started remains result results
if unless until""".split())
TOKEN = re.compile(r"\d+(?:\.\d+)?|[^\W\d_]+(?:['’][^\W\d_]+)?", re.UNICODE)
# Units are deliberately literal: no conversion, unit inference, spelled-number
# inference, or normalization of Celsius to Fahrenheit, minutes to seconds, etc.
QUANTITY = re.compile(
    r"(?<![\w.])[+-]?\d+(?:\.\d+)?(?:\s*(?:%|°\s*[CF]|"
    r"milliseconds?|seconds?|minutes?|hours?|days?|weeks?|months?|years?|"
    r"millimeters?|centimeters?|meters?|kilometers?|grams?|kilograms?|"
    r"milliliters?|liters?|volts?|amps?|watts?|hertz|"
    r"ms|sec|min|hr|mm|cm|km|mg|kg|ml|mv|ma|kw|mhz|khz|hz|s|h|g|l|v|a|w)(?!\w))?",
    re.IGNORECASE,
)
FAMILIES = ("quantities", "states", "content", "phrases")


def text_features(text: str | None) -> dict[str, Any]:
    """Return inspectable signatures and exact character spans into original text."""
    if text is None:
        return {"available": False, "word_count": None, "reason": "missing_text",
                **dict.fromkeys(FAMILIES), "spans": None}
    matches = list(TOKEN.finditer(text))
    words = [m.group().casefold().replace("’", "'") for m in matches]
    spans: list[dict[str, Any]] = []
    quantities: set[str] = set()
    for match in QUANTITY.finditer(text):
        # Ordered list numbering is formatting, not a measured quantity.
        line_prefix = text[text.rfind("\n", 0, match.start()) + 1:match.start()]
        if not line_prefix.strip() and re.match(r"[.)]\s", text[match.end():]):
            continue
        numeric = re.match(r"[+-]?\d+(?:\.\d+)?", match.group())
        assert numeric is not None
        value = format(Decimal(numeric.group()).normalize(), "f")
        unit = "".join(match.group()[numeric.end():].casefold().split())
        signature = value + (" " + unit if unit else "")
        quantities.add(signature)
        spans.append({"family": "quantities", "signature": signature,
                      "start": match.start(), "end": match.end(), "quote": match.group()})
    states: set[str] = set()
    for index, word in enumerate(words):
        if word not in STATE_MARKERS:
            continue
        lo, hi = max(0, index - 2), min(len(words), index + 3)
        signature = " ".join(words[lo:hi])
        states.add(signature)
        start, end = matches[lo].start(), matches[hi - 1].end()
        spans.append({"family": "states", "signature": signature,
                      "start": start, "end": end, "quote": text[start:end]})
    content = [word for word in words if word not in STOP_WORDS and not word[0].isdigit()]
    # Contiguous original-word trigrams preserve wording, including negation.
    phrases = {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}
    return {"available": True, "reason": "empty_text" if not words else None,
            "word_count": len(words), "quantities": sorted(quantities),
            "states": sorted(states), "content": sorted(set(content)),
            "phrases": sorted(phrases), "spans": spans}


def _reading(current: dict[str, Any], history: list[dict[str, Any]],
             family: str) -> dict[str, Any]:
    raw = current[family]
    before = [x[family] for x in history]
    available = raw is not None and bool(before) and all(x is not None for x in before)
    current_set = set(raw) if raw is not None else None
    union = set().union(*(set(x) for x in before)) if available else None
    new = sorted(current_set - union) if current_set is not None and union is not None else None
    repeats = (sorted(current_set & union)
               if current_set is not None and union is not None else None)
    overlaps: list[float] = []
    if available and current_set is not None:
        for previous in before:
            other = set(previous)
            denominator = current_set | other
            if denominator:
                overlaps.append(len(current_set & other) / len(denominator))
    count = len(current_set) if current_set is not None else None
    return {"count": count, "new": new, "repeated": repeats,
            "new_count": len(new) if new is not None else None,
            "new_fraction": len(new) / count if new is not None and count else None,
            "recent_max_jaccard": max(overlaps) if len(overlaps) == len(before)
            and overlaps else None,
            "reason": None if available else "missing_text_or_history"}


def _echo(atoms: list[str] | None, features: dict[str, Any], family: str) -> dict[str, Any]:
    target = features[family]
    if atoms is None or target is None:
        return {"denominator": None, "matched": None, "fraction": None}
    matched = sorted(set(atoms) & set(target))
    return {"denominator": len(atoms), "matched": matched,
            "fraction": len(matched) / len(atoms) if atoms else None}


def measure_movement(records: Sequence[Mapping[str, Any]], *,
                     windows: Sequence[int] = (3, 5)) -> list[dict[str, Any]]:
    """Observe accepted records, separately by source, without reading labels.

    Windows contain prior accepted turns of the current arc. A lag-one echo on
    row t compares new environment signatures at t-1 to Gemma at t; no future
    response is inspected or attached retroactively. First-turn novelty is null.
    """
    if not windows or len(set(windows)) != len(windows) or any(
        not isinstance(w, int) or isinstance(w, bool) or w < 1 for w in windows
    ):
        raise ValueError("windows must be distinct positive integers")
    states: dict[str, dict[str, Any]] = {}
    output: list[dict[str, Any]] = []
    for record in records:
        if set(record) - INPUT_KEYS:
            raise ValueError("unknown meter input keys")
        cid, arc, ordinal = (record.get(k) for k in ("conversation", "arc_id", "ordinal"))
        if (not isinstance(cid, str) or not cid or not isinstance(arc, str) or not arc
                or not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 0):
            raise ValueError("invalid conversation, arc or ordinal")
        state = states.setdefault(cid, {"ordinal": -1, "arc": None, "arcs": set(),
                                        "turns": set()})
        turn_id = record.get("accepted_turn_id", f"{cid}:{ordinal}")
        if ordinal <= state["ordinal"] or not isinstance(turn_id, str) or not turn_id \
                or turn_id in state["turns"]:
            raise ValueError("ordinals and accepted turn identities must advance")
        pivot = state["arc"] is not None and arc != state["arc"]
        if arc != state["arc"]:
            if arc in state["arcs"]:
                raise ValueError("an arc cannot recur")
            state.update(arc=arc, history={"participant": [], "gemma": []}, previous={})
            state["arcs"].add(arc)
        features: dict[str, dict[str, Any]] = {}
        for source in ("participant", "gemma"):
            value = record.get(source + "_text")
            if value is not None and not isinstance(value, str):
                raise ValueError("text must be a string or unavailable")
            features[source] = text_features(value)
        for window in windows:
            row: dict[str, Any] = {
                "measurement_version": VERSION, "conversation": cid, "turn": record.get("turn"),
                "ordinal": ordinal, "arc_id": arc, "accepted_turn_id": turn_id,
                "arc_age": len(state["history"]["participant"]) + 1, "arc_pivot": pivot,
                "window": window,
                "prior_turn_count": min(window, len(state["history"]["participant"])),
                "window_complete": len(state["history"]["participant"]) >= window,
                "features": features,
            }
            readings: dict[str, dict[str, Any]] = {}
            for source, current in features.items():
                row[source + "_word_count"] = current["word_count"]
                history = state["history"][source][-window:]
                readings[source] = {}
                for family in FAMILIES:
                    reading = _reading(current, history, family)
                    readings[source][family] = reading
                    for key in ("count", "new_count", "new_fraction", "recent_max_jaccard"):
                        row[f"{source}_{family}_{key}"] = reading[key]
                    new, words = reading["new_count"], current["word_count"]
                    row[f"{source}_{family}_new_per_100_words"] = (
                        100 * new / words if new is not None and words else None)
            row["readings"] = readings
            echoes: dict[str, Any] = {}
            previous = state["previous"].get(window)
            for family in FAMILIES:
                fresh = readings["participant"][family]["new"]
                for lag, atoms in (("same", fresh), ("lag1", previous[family]["new"]
                                                   if previous is not None else None)):
                    echo = _echo(atoms, features["gemma"], family)
                    echoes[f"{family}_{lag}"] = echo
                    row[f"echo_{family}_{lag}_fraction"] = echo["fraction"]
                    row[f"echo_{family}_{lag}_denominator"] = echo["denominator"]
            row["echoes"] = echoes
            # Descriptive paired coordinates, deliberately no mismatch score,
            # category threshold, causal inference, or age weighting.
            row["movement_pair"] = {
                "environment_quantity_new_fraction": row["participant_quantities_new_fraction"],
                "model_phrase_recurrence": row["gemma_phrases_recent_max_jaccard"],
            }
            state["previous"][window] = readings["participant"]
            output.append(row)
        for source in features:
            state["history"][source].append(features[source])
        state["ordinal"] = ordinal
        state["turns"].add(turn_id)
    return output
