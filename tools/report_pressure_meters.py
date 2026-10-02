"""Offline reports over frozen meter inputs; no hosts, runner or runtime imports.

Run only after publishing a transcript fidelity review. Labels join after the
meter boundary. Every attempt remains visible; primary eligibility is external.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from mneme.experiments.pressure_meters import INPUT_KEYS, measure_pressure_records

Json = dict[str, Any]
PHASES = ("early1-3", "middle4-5", "mature6-10", "outside1-10")
GROUP_KEYS = ("conversation", "domain", "pattern", "attempt", "primary_valid",
              "source_view", "window", "phase")
MATRIX_COLUMNS = (
    *GROUP_KEYS, "turn", "ordinal", "arc_id", "arc_age", "arc_pivot",
    "semantic_coverage", "semantic_unavailable_reason", "source_word_count",
    "response_capped", "context_activation_total", "context_positive_coverage", "context_hhi",
    "opening_text_jaccard", "recent_participant_text_jaccard",
    "opening_participant_concept_jaccard", "recent_participant_concept_jaccard",
    "recent_participant_relationship_jaccard", "history_hhi", "history_top_mass",
    "history_entropy_nats", "history_context_tv", "history_rank_displacement",
    "history_candidate_count", "history_effective_count", "saa_candidate_count",
    "saa_entropy_nats", "saa_effective_candidate_count", "saa_max_mass",
    "background_candidate_count", "background_mass", "background_unselected_count",
    "selected_landing", "selected_landing_rolling_repeat", "active_neighborhood_count",
    "candidates_adjacent_jaccard", "neighborhood_adjacent_jaccard", "routes_adjacent_jaccard",
    "route_count",
    "concept_count", "relationship_count", "concept_rolling_novelty_mean",
    "relationship_rolling_novelty_mean", "concept_rolling_saturation",
    "relationship_rolling_saturation", "concept_new_count", "relationship_new_count",
    "structure_new_count", "concept_new_per_100_words", "relationship_new_per_100_words",
    "structure_new_per_100_words", "concept_rolling_new_per_turn",
    "relationship_rolling_new_per_turn", "evidence_new_count",
    "evidence_new_per_100_words", "evidence_rolling_novelty_mean",
    "word3_recent_max_jaccard", "char5_recent_max_jaccard",
    "c1_concept_persistence_proxy", "c2_structure_persistence_proxy",
    "c3_context_persistence_proxy", "structure_repeat_raw", "structure_repeat_age_conditioned",
    "evidence_aware_repeat_raw", "evidence_aware_repeat_age_conditioned",
    "surface_repeat_raw", "surface_repeat_age_conditioned",
)
_NUMERIC_EXCLUSIONS = {*GROUP_KEYS, "turn", "ordinal", "arc_id", "arc_pivot",
                       "semantic_coverage", "semantic_unavailable_reason", "response_capped",
                       "selected_landing"}


def _encode(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _phase(turn: int) -> str:
    if 1 <= turn <= 3:
        return PHASES[0]
    if 4 <= turn <= 5:
        return PHASES[1]
    return PHASES[2] if 6 <= turn <= 10 else PHASES[3]


def _number(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _stats(values: Sequence[Any]) -> Json:
    usable = [v for v in values if _number(v)]
    return {"available": len(usable), "total": len(values),
            "unavailable": len(values) - len(usable),
            "mean": math.fsum(usable) / len(usable) if usable else None,
            "median": statistics.median(usable) if usable else None,
            "minimum": min(usable) if usable else None,
            "maximum": max(usable) if usable else None}


def _groups(rows: Sequence[Json]) -> list[Json]:
    groups: dict[tuple[Any, ...], list[Json]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in GROUP_KEYS)].append(row)
    # Include all-null numeric meter columns as unavailable rather than losing
    # them through a numeric-value-only discovery pass.
    metrics = sorted({key for row in rows for key, value in row.items()
                      if key not in _NUMERIC_EXCLUSIONS and
                      (_number(value) or value is None) and
                      (key in MATRIX_COLUMNS or _number(value))})
    return [{**dict(zip(GROUP_KEYS, key, strict=True)), "accepted_rows": len(values),
             "response_cap_counts": {
                 "capped": sum(r["response_capped"] is True for r in values),
                 "uncapped": sum(r["response_capped"] is False for r in values),
                 "unknown": sum(r["response_capped"] is None for r in values)},
             "natural_source_word_count": _stats([
                 r["source_word_count"] if r["source_view"] == "participant"
                 or r["response_capped"] is False else None for r in values]),
             "metrics": {metric: _stats([r.get(metric) for r in values]) for metric in metrics}}
            for key, values in sorted(groups.items())]


def _length_matches(rows: Sequence[Json]) -> tuple[list[Json], list[Json]]:
    grouped: dict[tuple[Any, ...], list[Json]] = defaultdict(list)
    keys = ("domain", "source_view", "window", "phase")
    for row in rows:
        if row["pattern"] in {"F-same", "S-rephrased"}:
            grouped[tuple(row[k] for k in keys)].append(row)
    matches: list[Json] = []
    coverage: list[Json] = []
    for key, values in sorted(grouped.items()):
        candidates: dict[str, list[Json]] = {"F-same": [], "S-rephrased": []}
        counts: dict[str, Json] = {}
        for pattern in candidates:
            relevant = [r for r in values if r["pattern"] == pattern]
            eligible = [r for r in relevant if r["primary_valid"] is True
                        and _number(r["source_word_count"]) and r["source_word_count"] > 0
                        and (r["source_view"] == "participant" or r["response_capped"] is False)]
            candidates[pattern] = eligible
            counts[pattern] = {
                "all_attempt_rows": len(relevant), "eligible": len(eligible),
                "excluded_nonprimary": sum(r["primary_valid"] is not True for r in relevant),
                "capped_response_rows": sum(r["response_capped"] is True for r in relevant),
                "unknown_cap_rows": sum(r["response_capped"] is None for r in relevant),
                "missing_or_empty_source_rows": sum(
                    not _number(r["source_word_count"]) or r["source_word_count"] <= 0
                    for r in relevant),
            }
        edges = []
        for i, left in enumerate(candidates["F-same"]):
            for j, right in enumerate(candidates["S-rephrased"]):
                a, b = left["source_word_count"], right["source_word_count"]
                ratio = max(a, b) / min(a, b)
                if ratio <= 1.25:
                    edges.append((ratio, abs(a - b), left["conversation"], left["turn"],
                                  right["conversation"], right["turn"], i, j))
        used_left: set[int] = set()
        used_right: set[int] = set()
        for ratio, _, _, _, _, _, i, j in sorted(edges):
            if i in used_left or j in used_right:
                continue
            used_left.add(i)
            used_right.add(j)
            left, right = candidates["F-same"][i], candidates["S-rephrased"][j]
            match = {**dict(zip(keys, key, strict=True)), "word_count_ratio": ratio}
            for side, item in (("focused", left), ("stagnant", right)):
                for name in ("conversation", "turn", "attempt", "source_word_count"):
                    match[f"{side}_{name}"] = item[name]
            matches.append(match)
        for pattern, used in (("F-same", used_left), ("S-rephrased", used_right)):
            counts[pattern].update(
                matched=len(used), unmatched=len(candidates[pattern]) - len(used))
        coverage.append({**dict(zip(keys, key, strict=True)), "counts": counts})
    return matches, coverage


def build_report(records: Sequence[Mapping[str, Any]], manifest: Sequence[Mapping[str, Any]],
                 fidelity_review: Mapping[str, Any]) -> Json:
    """Pure assembly: frozen measurements first, external labels afterward."""
    review = fidelity_review.get("conversations")
    if not isinstance(review, Mapping):
        raise ValueError("fidelity review requires conversations mapping")
    labels: dict[str, Json] = {}
    for item in manifest:
        identity = item.get("conversation")
        if (not isinstance(identity, str) or not identity or identity in labels
                or not isinstance(item.get("domain"), str)
                or not isinstance(item.get("pattern"), str)):
            raise ValueError("manifest identities must be unique with domain and pattern")
        judgment = review.get(identity)
        if not isinstance(judgment, Mapping) or not isinstance(judgment.get("primary_valid"), bool):
            raise ValueError(f"explicit fidelity primary_valid missing for {identity}")
        labels[identity] = {"domain": item["domain"], "pattern": item["pattern"],
                            "attempt": item.get("attempt", identity),
                            "primary_valid": judgment["primary_valid"]}
    by_turn: dict[tuple[str, int], Mapping[str, Any]] = {}
    safe: list[Json] = []
    for record in records:
        identity, turn = record.get("conversation"), record.get("turn")
        if (identity not in labels or not isinstance(turn, int) or isinstance(turn, bool)
                or turn < 1 or (identity, turn) in by_turn):
            raise ValueError("unmapped conversation, invalid turn, or duplicate accepted turn")
        by_turn[(identity, turn)] = record
        safe.append({key: record[key] for key in INPUT_KEYS if key in record})
    safe.sort(key=lambda r: (r["conversation"], r["ordinal"]))
    measured = measure_pressure_records(safe)
    for row in measured:
        raw = by_turn[(row["conversation"], row["turn"])]
        length = raw.get("length")
        capped = length.get("capped") if isinstance(length, Mapping) else None
        row.update(labels[row["conversation"]])
        row.update(phase=_phase(row["turn"]), response_capped=capped
                   if isinstance(capped, bool) else None)
    matched, coverage = _length_matches(measured)
    attempts = [{"conversation": identity, **label,
                 "accepted_turns": sum(key[0] == identity for key in by_turn),
                 "fidelity": dict(review[identity])} for identity, label in sorted(labels.items())]
    return {"rows": measured, "summary": {
        "attempts": attempts, "conversation_groups": _groups(measured),
        "length_match_coverage": coverage,
        "length_matching_rule": "Primary-valid F-same/S-rephrased within "
        "domain/source/window/phase. "
        "Sort all pairs by word ratio, absolute difference, conversation/turn; "
        "greedily take unused "
        "pairs with ratio <=1.25. Metrics never select pairs. Participant lengths remain eligible "
        "when response cap is unknown; Gemma/combined require explicit uncapped response.",
        "interpretation": "All attempts retained. Groups summarize conversations before pooling. "
        "Overlapping windows and source views are not independent replications. Counts and ratios "
        "describe extracted structure, not human quality. Capped responses remain in meter "
        "matrices; "
        "exclude them from natural-length claims. Missing cap metadata is unknown.",
        "provider_calls": 0, "state_writes": 0,
    }, "length_matches": matched}


def _csv(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def write_report(report: Mapping[str, Any], output: Path, provenance: Mapping[str, Any]) -> Json:
    """Write deterministic derived reports, with no copies of source snapshots."""
    output.mkdir(parents=True, exist_ok=True)
    rows, matches = report["rows"], report["length_matches"]
    match_columns = tuple(matches[0]) if matches else (
        "domain", "source_view", "window", "phase", "word_count_ratio",
        "focused_conversation", "focused_turn", "focused_attempt", "focused_source_word_count",
        "stagnant_conversation", "stagnant_turn", "stagnant_attempt", "stagnant_source_word_count",
    )
    artifacts = {
        "rows.json.gz": gzip.compress(_encode(rows), mtime=0),
        "matrix.csv": _csv(rows, MATRIX_COLUMNS),
        "summary.json": _encode(report["summary"]),
        "length_matches.csv": _csv(matches, match_columns),
    }
    for name, content in artifacts.items():
        (output / name).write_bytes(content)
    receipt = {"inputs": dict(provenance), "provider_calls": 0, "state_writes": 0,
               "measurement_rows": len(rows), "artifacts": {
                   name: {"sha256": _hash(content), "bytes": len(content)}
                   for name, content in artifacts.items()}}
    (output / "receipt.json").write_bytes(_encode(receipt))
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recordings", type=Path, nargs="+")
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--fidelity-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--formulas", type=Path,
                        default=Path("docs/experiments/three_pressure_v2/formulas.json"))
    args = parser.parse_args(argv)
    protected = {p.resolve() for p in
                 [*args.recordings, *args.manifest, args.fidelity_review, args.formulas]}
    outputs = {args.output.resolve() / name for name in
               ("rows.json.gz", "matrix.csv", "summary.json", "length_matches.csv", "receipt.json")}
    if protected & outputs:
        raise ValueError("report output would overwrite an input artifact")
    provenance: Json = {}

    def read(path: Path) -> Any:
        payload = path.read_bytes()
        provenance[str(path)] = _hash(payload)
        return json.loads(gzip.decompress(payload) if path.suffix == ".gz" else payload)

    review = read(args.fidelity_review)
    records = [row for path in args.recordings for row in read(path)]
    manifest = [row for path in args.manifest for row in read(path)]
    read(args.formulas)  # retain exact frozen registry hash in the receipt
    result = build_report(records, manifest, review)
    write_report(result, args.output, provenance)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
