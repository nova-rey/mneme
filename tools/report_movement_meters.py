"""Inference-free report; construction labels join only after both instruments run."""
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

from mneme.experiments.movement_meters import measure_movement
from mneme.experiments.pressure_meters import INPUT_KEYS, measure_pressure_records

Json = dict[str, Any]


def read_json(path: Path) -> Any:
    payload = path.read_bytes()
    return json.loads(gzip.decompress(payload) if path.suffix == ".gz" else payload)


def write_json(path: Path, value: Any) -> None:
    data = (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       allow_nan=False, separators=(",", ":")) + "\n").encode()
    path.write_bytes(gzip.compress(data, mtime=0) if path.suffix == ".gz" else data)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _stats(values: Sequence[Any]) -> Json:
    found = [float(v) for v in values if _number(v)]
    return {"available": len(found), "unavailable": len(values) - len(found),
            "mean": statistics.mean(found) if found else None,
            "minimum": min(found) if found else None, "maximum": max(found) if found else None}


def _correlation(pairs: Sequence[tuple[Any, Any]]) -> Json:
    valid = [(float(x), float(y)) for x, y in pairs if _number(x) and _number(y)]
    if len(valid) < 3:
        return {"n": len(valid), "pearson_r": None, "reason": "fewer_than_three_pairs"}
    x, y = zip(*valid, strict=True)
    if len(set(x)) == 1 or len(set(y)) == 1:
        return {"n": len(valid), "pearson_r": None, "reason": "constant_series"}
    return {"n": len(valid), "pearson_r": statistics.correlation(x, y), "reason": None}


def build_report(records: Sequence[Mapping[str, Any]], manifest: Sequence[Mapping[str, Any]],
                 review: Mapping[str, Any]) -> Json:
    """Keep every accepted turn, including invalid construction and bad responses.

    Development evidence may have undecided environment validity. Prospective
    evidence requires explicit external environment-only judgments before scoring.
    No primary validity criterion inspects Gemma behavior.
    """
    stage = review.get("stage")
    judgments = review.get("conversations")
    if stage not in {"development", "prospective"} or not isinstance(judgments, Mapping):
        raise ValueError("review requires stage and conversations")
    labels: dict[str, Json] = {}
    for item in manifest:
        cid = item.get("conversation")
        if not isinstance(cid, str) or not cid or cid in labels:
            raise ValueError("manifest requires unique conversation identities")
        judgment = judgments.get(cid)
        if not isinstance(judgment, Mapping) or "environment_valid" not in judgment:
            raise ValueError("environment-only review missing")
        valid = judgment["environment_valid"]
        if not isinstance(valid, bool) and (valid is not None or stage != "development"):
            raise ValueError("prospective environment validity must be explicit")
        labels[cid] = {"domain": item.get("domain"),
                       "pattern": item.get("pattern", item.get("environment")),
                       "environment": item.get("environment"),
                       "planned_opportunity": item.get("planned_opportunity"),
                       "environment_valid": valid, "attempt": item.get("attempt", cid)}
    by_turn: dict[tuple[str, int], Mapping[str, Any]] = {}
    safe: list[Json] = []
    for record in records:
        cid, turn = record.get("conversation"), record.get("turn")
        if (not isinstance(cid, str) or cid not in labels or not isinstance(turn, int)
                or isinstance(turn, bool) or turn < 1 or (cid, turn) in by_turn):
            raise ValueError("unmapped or duplicate turn")
        by_turn[(cid, turn)] = record
        safe.append({key: record[key] for key in INPUT_KEYS if key in record})
    safe.sort(key=lambda x: (x["conversation"], x["ordinal"]))
    rows = measure_movement(safe)
    retained = measure_pressure_records(safe)
    # Joins are downstream, never inputs to either instrument.
    for row in rows:
        row.update(labels[row["conversation"]])
        length = by_turn[(row["conversation"], row["turn"])].get("length")
        length = length if isinstance(length, Mapping) else {}
        usage = length.get("usage")
        usage = usage if isinstance(usage, Mapping) else {}
        row.update(response_capped=length.get("capped"),
                   finish_reason=length.get("finish_reason"),
                   output_tokens=usage.get("completion_tokens"),
                   recorded_gemma_words=length.get("gemma_words"),
                   recorded_participant_words=length.get("participant_words"))
    groups: dict[tuple[str, int], list[Json]] = defaultdict(list)
    for row in rows:
        groups[(row["conversation"], row["window"])].append(row)
    summaries: list[Json] = []
    excluded = {"turn", "ordinal", "arc_age", "window", "prior_turn_count",
                "domain", "pattern", "environment", "planned_opportunity", "finish_reason"}
    metrics = sorted({key for row in rows for key, value in row.items()
                      if key not in excluded and (_number(value) or value is None)})
    for (cid, window), group in sorted(groups.items()):
        natural = [r for r in group if r["response_capped"] is False]
        summary = {"conversation": cid, "window": window, **labels[cid],
                   "accepted_turns": len(group), "uncapped_turns": len(natural),
                   "metrics": {k: _stats([r.get(k) for r in group]) for k in metrics},
                   "uncapped_length_correlations": {
                       k: _correlation([(r["gemma_word_count"], r.get(k)) for r in natural])
                       for k in ("gemma_content_new_fraction", "gemma_phrases_recent_max_jaccard",
                                 "echo_quantities_same_fraction", "echo_content_same_fraction")},
                   "coupling_correlations": {
                       "environment_quantity_vs_model_content_novelty": _correlation([
                           (r["participant_quantities_new_fraction"],
                            r["gemma_content_new_fraction"]) for r in group]),
                       "environment_content_vs_model_content_novelty": _correlation([
                           (r["participant_content_new_fraction"],
                            r["gemma_content_new_fraction"]) for r in group])}}
        summaries.append(summary)
    return {"rows": rows, "retained_v2_rows": retained,
            "summary": {"stage": stage, "trajectory_summaries": summaries,
                        "new_model_calls": 0, "notes": [
                            "Correlations are descriptive within tiny autocorrelated trajectories.",
                            "Exact echoes do not establish correct reference, polarity "
                            "or understanding.",
                            "V2 readings are reused unchanged, including unavailable "
                            "semantic measures."]}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, nargs="+", required=True)
    parser.add_argument("--manifest", type=Path, nargs="+", required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [item for path in args.records for item in read_json(path)]
    manifest = [item for path in args.manifest for item in read_json(path)]
    report = build_report(records, manifest, read_json(args.review))
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output / "rows.json.gz", report["rows"])
    write_json(args.output / "retained_v2_rows.json.gz", report["retained_v2_rows"])
    write_json(args.output / "summary.json", report["summary"])
    # Nested provenance lives in rows.json.gz; CSV contains the scalar vector.
    columns = list(dict.fromkeys(key for row in report["rows"] for key, value in row.items()
                                if not isinstance(value, (dict, list))))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(report["rows"])
    (args.output / "matrix.csv").write_text(stream.getvalue())
    compact = ["conversation", "pattern", "turn", "arc_id", "arc_pivot",
               "arc_age", "window", "environment_valid",
               "participant_quantities_new_fraction", "participant_states_new_fraction",
               "gemma_content_new_fraction", "gemma_phrases_recent_max_jaccard",
               "echo_quantities_same_fraction", "gemma_word_count"]
    headers = ["Conversation", "Condition", "Turn", "Arc", "Pivot", "Age", "W",
               "Quinn valid", "Env qty new",
               "Env state new", "Model token new", "Model phrase repeat", "Qty echo", "Words"]
    lines = ["# Movement matrix", "", "All accepted turns; both frozen windows. "
             "A dash is unavailable, not zero. Exact echo is not understanding.", "",
             "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in report["rows"]:
        cells = ["—" if row.get(key) is None else f"{row[key]:.3f}"
                 if isinstance(row[key], float) else str(row[key]) for key in compact]
        lines.append("| " + " | ".join(cells) + " |")
    (args.output / "matrix.md").write_text("\n".join(lines).rstrip() + "\n")
    # One readable retained vector per accepted turn/window. Common context and
    # history readings are identical across V2 source views; continuity is not.
    retained = {(r["conversation"], r["turn"], r["window"], r["source_view"]): r
                for r in report["retained_v2_rows"]}
    identity = ["conversation", "pattern", "turn", "arc_id", "arc_pivot", "arc_age", "window"]
    context = ["context_activation_total", "context_positive_count",
               "context_positive_coverage", "context_hhi"]
    history = ["history_candidate_count", "history_entropy_nats", "history_effective_count",
               "history_top_mass", "conditioned_hhi", "history_context_tv",
               "history_rank_displacement"]
    continuity = ["opening_text_jaccard", "recent_participant_text_jaccard",
                  "word3_recent_max_jaccard", "semantic_coverage"]
    retained_rows = []
    for row in report["rows"]:
        key = (row["conversation"], row["turn"], row["window"])
        participant = retained[(*key, "participant")]
        joined = {k: row[k] for k in identity}
        joined.update({k: participant[k] for k in context + history})
        for source in ("participant", "gemma"):
            joined.update({source + "_" + k: retained[(*key, source)][k] for k in continuity})
        retained_rows.append(joined)
    retained_columns = identity + context + history + [
        source + "_" + k for source in ("participant", "gemma") for k in continuity]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=retained_columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(retained_rows)
    (args.output / "retained_v2_matrix.csv").write_text(stream.getvalue())
    lines = ["# Retained V2 readings", "", "Values come from the unchanged V2 instrument. "
             "A dash is unavailable. Source coverage flags are extraction coverage, "
             "not coverage of conversational meaning. Common context/history values "
             "are identical across source views; source continuity is shown separately.", ""]
    panels = [("Context", context), ("Historical distributions", history),
              ("Participant continuity", ["participant_" + k for k in continuity]),
              ("Gemma continuity", ["gemma_" + k for k in continuity])]
    for title, values in panels:
        columns = ["conversation", "turn", "window", *values]
        lines.extend(["## " + title, "", "| " + " | ".join(columns) + " |",
                      "| " + " | ".join(["---"] * len(columns)) + " |"])
        for row in retained_rows:
            cells = ["—" if row[k] is None else f"{row[k]:.3f}"
                     if isinstance(row[k], float) else str(row[k]) for k in columns]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    (args.output / "retained_v2_matrix.md").write_text("\n".join(lines).rstrip() + "\n")
    paths = [*args.records, *args.manifest, args.review]
    generated = ("matrix.csv", "matrix.md", "retained_v2_matrix.csv", "retained_v2_matrix.md",
                 "rows.json.gz", "retained_v2_rows.json.gz", "summary.json")
    write_json(args.output / "receipt.json", {
        "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "outputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(args.output / name for name in generated)},
        "new_model_calls": 0})


if __name__ == "__main__":
    main()
