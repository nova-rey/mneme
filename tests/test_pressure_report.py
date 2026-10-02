from __future__ import annotations

import copy
import gzip
import json
import socket

import pytest

from mneme.experiments.pressure_meters import INPUT_KEYS
from tools import report_pressure_meters as report


def dataset():
    data = []
    manifest = [
        {"conversation": "a", "domain": "first", "pattern": "F-same", "attempt": "initial-f"},
        {"conversation": "b", "domain": "first", "pattern": "S-rephrased", "attempt": "initial-s"},
        {"conversation": "rejected", "domain": "first", "pattern": "S-rephrased"},
        {"conversation": "no-turns", "domain": "second", "pattern": "F-new"},
    ]
    fidelity = {"conversations": {x["conversation"]: {
        "primary_valid": x["conversation"] in {"a", "b"}, "reason": "synthetic judgment"}
        for x in manifest}}
    for conversation in ("a", "b", "rejected"):
        for turn in range(1, 11):
            text = f"The sensor measured {turn} ms and remains unchanged."
            data.append({
                "conversation": conversation, "turn": turn, "ordinal": turn,
                "arc_id": conversation + "arc", "participant_text": text,
                "gemma_text": "The reading remains unresolved and we need further evidence.",
                "opening_task": "The sensor remains unchanged.", "residue": None,
                "sources": {}, "source_roles": {}, "extraction_coverage": {}, "field": None,
                "historical_strengths": {}, "accessibility_adjustments": {},
                "length": {"capped": False}, "condition": "must never enter meter",
                "fidelity": "also never enters", "arc": {"turn_ids": ["future"]},
            })
    return data, manifest, fidelity


def test_labels_join_only_after_meter_and_no_calls_or_mutation(monkeypatch):
    data, manifest, fidelity = dataset()
    before = copy.deepcopy((data, manifest, fidelity))
    actual = report.measure_pressure_records
    captured = []

    def spy(records):
        captured.extend(records)
        assert all(set(row) <= INPUT_KEYS for row in records)
        assert all("condition" not in row and "arc" not in row for row in records)
        return actual(records)

    def forbidden(*args, **kwargs):
        pytest.fail("offline report attempted network or file access")

    monkeypatch.setattr(report, "measure_pressure_records", spy)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    result = report.build_report(data, manifest, fidelity)
    assert len(captured) == len(data)
    assert len(result["rows"]) == 180
    assert (data, manifest, fidelity) == before
    assert all(row["primary_valid"] is False for row in result["rows"]
               if row["conversation"] == "rejected")
    attempts = result["summary"]["attempts"]
    assert next(x for x in attempts if x["conversation"] == "no-turns")["accepted_turns"] == 0
    assert result["summary"]["provider_calls"] == 0
    assert result["summary"]["state_writes"] == 0


def test_grouped_phases_and_unavailability_denominators():
    result = report.build_report(*dataset())
    groups = result["summary"]["conversation_groups"]
    selected = [g for g in groups if g["conversation"] == "a"
                and g["source_view"] == "participant" and g["window"] == 3]
    assert {g["phase"]: g["accepted_rows"] for g in selected} == {
        "early1-3": 3, "middle4-5": 2, "mature6-10": 5}
    mature = next(g for g in selected if g["phase"] == "mature6-10")
    assert mature["metrics"]["concept_new_count"]["available"] == 0
    assert mature["metrics"]["concept_new_count"]["unavailable"] == 5
    assert mature["metrics"]["concept_new_count"]["mean"] is None
    assert mature["metrics"]["source_word_count"]["available"] == 5
    assert "structure_new_per_100_words" in mature["metrics"]
    assert "semantic_unavailable_reason" not in mature["metrics"]
    assert "selected_landing" not in mature["metrics"]


def test_length_matching_uses_only_lengths_and_no_replacement():
    result = report.build_report(*dataset())
    matches = result["length_matches"]
    assert len(matches) == 60  # ten turns times three source views times two windows
    assert all(m["word_count_ratio"] == 1 for m in matches)
    identities = [(m["source_view"], m["window"], m["focused_conversation"], m["focused_turn"])
                  for m in matches]
    assert len(identities) == len(set(identities))
    changed = copy.deepcopy(result["rows"])
    for index, row in enumerate(changed):
        row["structure_repeat_raw"] = index % 2
        row["opening_text_jaccard"] = index / 1000
    assert report._length_matches(changed)[0] == matches
    shuffled = list(reversed(result["rows"]))
    assert report._length_matches(shuffled)[0] == matches


def test_ratio_cutoff_cap_handling_and_coverage():
    data, manifest, fidelity = dataset()
    for row in data:
        if row["conversation"] == "b":
            row["participant_text"] = "word " * 50
            row["length"]["capped"] = True
    result = report.build_report(data, manifest, fidelity)
    assert result["length_matches"] == []
    coverage = result["summary"]["length_match_coverage"]
    participant = next(g for g in coverage if g["source_view"] == "participant")
    assert participant["counts"]["S-rephrased"]["eligible"] > 0
    assert participant["counts"]["S-rephrased"]["matched"] == 0
    gemma = next(g for g in coverage if g["source_view"] == "gemma")
    assert gemma["counts"]["S-rephrased"]["eligible"] == 0
    assert gemma["counts"]["S-rephrased"]["capped_response_rows"] > 0
    assert len(result["rows"]) == 180  # caps never silently remove recorded attempts
    groups = result["summary"]["conversation_groups"]
    capped_group = next(g for g in groups if g["conversation"] == "b"
                        and g["source_view"] == "gemma")
    assert capped_group["natural_source_word_count"]["available"] == 0
    assert capped_group["metrics"]["source_word_count"]["available"] > 0


def test_missing_cap_metadata_is_unknown_excluded_from_response_length_claims():
    data, manifest, fidelity = dataset()
    for row in data:
        del row["length"]
    result = report.build_report(data, manifest, fidelity)
    assert all(row["response_capped"] is None for row in result["rows"])
    assert {m["source_view"] for m in result["length_matches"]} == {"participant"}


@pytest.mark.parametrize("problem", ["review", "judgment", "duplicate", "manifest"])
def test_missing_review_or_ambiguous_identity_fails_closed(problem):
    data, manifest, fidelity = dataset()
    if problem == "review":
        fidelity = {}
    elif problem == "judgment":
        del fidelity["conversations"]["a"]["primary_valid"]
    elif problem == "duplicate":
        data.append(data[0])
    else:
        manifest.append(manifest[0])
    with pytest.raises(ValueError):
        report.build_report(data, manifest, fidelity)


def test_serialized_outputs_replay_byte_identically_and_do_not_modify_sources(tmp_path):
    data, manifest, fidelity = dataset()
    recorded = tmp_path / "recording.json.gz"
    recorded.write_bytes(gzip.compress(json.dumps(data).encode(), mtime=0))
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(fidelity))
    formulas = tmp_path / "formulas.json"
    formulas.write_text('{"kind":"synthetic report test registry"}')
    before = {p: p.read_bytes() for p in (recorded, manifest_path, review_path, formulas)}
    for directory in ("one", "two"):
        assert report.main([str(recorded), "--manifest", str(manifest_path),
                            "--fidelity-review", str(review_path), "--formulas", str(formulas),
                            "--output", str(tmp_path / directory)]) == 0
    for name in ("rows.json.gz", "matrix.csv", "summary.json",
                 "length_matches.csv", "receipt.json"):
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()
    assert before == {p: p.read_bytes() for p in before}
    assert len(json.loads(gzip.decompress((tmp_path / "one" / "rows.json.gz").read_bytes()))) == 180
    csv_text = (tmp_path / "one" / "matrix.csv").read_text()
    assert "structure_new_per_100_words" in csv_text.splitlines()[0]
    assert "saa_effective_candidate_count" in csv_text.splitlines()[0]
    assert "selected_landing" in csv_text.splitlines()[0]
    assert "history_effective_count" in csv_text.splitlines()[0]
    assert len(csv_text.splitlines()) == 181


def test_cli_refuses_to_overwrite_recorded_input(tmp_path):
    recorded = tmp_path / "rows.json.gz"
    recorded.write_bytes(b"preserve this source")
    with pytest.raises(ValueError, match="overwrite"):
        report.main([str(recorded), "--manifest", str(tmp_path / "manifest"),
                     "--fidelity-review", str(tmp_path / "review"), "--output", str(tmp_path)])
    assert recorded.read_bytes() == b"preserve this source"
