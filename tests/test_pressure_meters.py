from __future__ import annotations

import copy
import json
import math
import socket
import sqlite3

import pytest

from mneme.experiments.pressure_meters import (
    historical_metrics,
    measure_pressure_records,
    source_view,
)


def fixture_record(index=0, *, participant=None, gemma=None, arc="arc", new_label=None):
    participant = participant if participant is not None else (
        "The sensor measured 10 ms, not fixed.")
    gemma = gemma if gemma is not None else "The sensor result remains unresolved."
    sources = {"s0": participant, "s1": gemma}
    concepts = [{"key": "a", "label": "sensor",
                 "source_spans": [{"source_slot": "s0", "start": 0, "end": len(participant)}]},
                {"key": "b", "label": "result",
                 "source_spans": [{"source_slot": "s0", "start": 0, "end": len(participant)}]}]
    if new_label:
        concepts[1]["label"] = new_label
    edges = [{"key": f"edge{index}{slot}", "from": "a", "to": "b", "relationship": "causal",
              "source_spans": [{"source_slot": slot, "start": 0, "end": len(text)}]}
             for slot, text in sources.items()]
    return {
        "conversation": "fixture", "turn": index + 1, "ordinal": index * 3,
        "accepted_turn_id": f"t{index}", "arc_id": arc,
        "opening_task": "The sensor measured 10 ms, not fixed.",
        "participant_text": participant, "gemma_text": gemma,
        "residue": {"core_concepts": concepts, "edge_candidates": edges},
        "sources": sources, "source_roles": {"s0": "participant", "s1": "gemma"},
        "extraction_coverage": {"s0": True, "s1": True},
        "historical_strengths": {"a": 1, "b": 1}, "accessibility_adjustments": {},
        "field": {
            "active_concepts": [{"key": "sensor", "contextual_activation": 3},
                                {"key": "other", "contextual_activation": 1},
                                {"key": "unused", "contextual_activation": 0}],
            "accessibility_distribution": [{"candidate": "a", "probability": 3},
                                          {"candidate": "b", "probability": 1}],
            "selected_landing": "a", "active_neighborhood": ["sensor"],
            "contributions": [{"path": ["sensor", "result"]}],
        },
    }


def rows(records, *, view="participant", window=3):
    return [r for r in measure_pressure_records(records)
            if r["source_view"] == view and r["window"] == window]


def test_replay_is_pure_and_needs_no_io_or_provider(monkeypatch):
    data = [fixture_record(i) for i in range(7)]
    before = copy.deepcopy(data)

    def forbidden(*args, **kwargs):
        pytest.fail("passive measurement attempted external IO")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    first = measure_pressure_records(data)
    assert first == measure_pressure_records(data)
    assert data == before
    json.dumps(first, allow_nan=False)
    first[-1]["evidence_quotes"].append("mutated result")
    first[-1]["accessibility_adjustments"]["a"] = 99
    assert data == before


def test_prefix_causality_observed_age_and_existing_arc_reset():
    data = [fixture_record(i, arc="first" if i < 4 else "second") for i in range(7)]
    full = rows(data)
    assert [r["arc_age"] for r in full] == [1, 2, 3, 4, 1, 2, 3]
    assert [r["arc_pivot"] for r in full] == [False] * 4 + [True, False, False]
    assert full[4]["concept_arc_novelty"] is None
    assert full[4]["word3_adjacent_jaccard"] is None
    for n in range(1, len(data) + 1):
        assert rows(data[:n]) == full[:n]


def test_views_recover_endpoints_with_only_first_concept_span():
    record = fixture_record()
    # Minimal converter retains only s0 concept spans; s1 edge establishes
    # both endpoint concepts in Gemma view without pretending s0 was Gemma.
    assert len(source_view(record, "gemma")["residue"]["core_concepts"]) == 2
    record["residue"]["edge_candidates"] = record["residue"]["edge_candidates"][:1]
    gemma = source_view(record, "gemma")
    assert gemma["residue"] == {"core_concepts": [], "edge_candidates": []}
    assert gemma["evidence_quotes"] == []
    assert len(source_view(record, "participant")["residue"]["core_concepts"]) == 2


def test_source_isolation_gemma_novelty_does_not_hide_participant_repetition():
    data = [fixture_record(i) for i in range(7)]
    for i, record in enumerate(data):
        extra = {"key": f"g{i}", "label": f"assistant novelty {i}",
                 "source_spans": [{"source_slot": "s1", "start": 0,
                                   "end": len(record["gemma_text"])}]}
        record["residue"]["core_concepts"].append(extra)
    assert rows(data)[-1]["concept_rolling_novelty_mean"] == 0
    assert rows(data, view="gemma")[-1]["concept_rolling_novelty_mean"] > 0
    assert rows(data, view="combined")[-1]["concept_rolling_novelty_mean"] > 0


def test_high_movement_and_repetition_both_windows():
    repeated = [fixture_record(i) for i in range(8)]
    moving = [fixture_record(i, new_label=f"new constraint {i}") for i in range(8)]
    for window in (3, 5):
        f, s = rows(moving, window=window)[-1], rows(repeated, window=window)[-1]
        assert f["concept_rolling_novelty_mean"] == 0.5
        assert f["relationship_rolling_novelty_mean"] == 1
        assert s["concept_rolling_novelty_mean"] == 0
        assert s["relationship_rolling_novelty_mean"] == 0
        assert f["structure_repeat_raw"] == 0.25
        assert s["structure_repeat_raw"] == 1
        assert s["concept_rolling_saturation"] == pytest.approx(1 - 1 / window)
        assert s["surface_repeat_raw"] == 1
        assert f["structure_new_per_100_words"] == 100 * 2 / f["source_word_count"]


def test_same_labels_changed_quantities_are_inspectable_movement():
    data = [fixture_record(i, participant=f"The sensor measured {10 + i} ms, not fixed.")
            for i in range(8)]
    last = rows(data)[-1]
    assert last["concept_rolling_novelty_mean"] == 0
    assert last["relationship_rolling_novelty_mean"] == 0
    assert last["evidence_rolling_novelty_mean"] > 0
    assert "quantity:17 ms" in last["evidence_atoms"]
    assert last["evidence_aware_repeat_raw"] < last["structure_repeat_raw"]
    assert last["evidence_quotes"] == [data[-1]["participant_text"]]


@pytest.mark.parametrize("bad", ["missing", "partial", "mismatch", "bad_span", "context_only"])
def test_missing_or_partial_semantics_are_unavailable_not_stagnant(bad):
    data = [fixture_record(i) for i in range(7)]
    record = data[4]
    if bad == "missing":
        record["residue"] = None
    elif bad == "partial":
        record["extraction_coverage"]["s0"] = False
    elif bad == "mismatch":
        record["sources"]["s0"] += " clipped coverage"
    elif bad == "bad_span":
        record["residue"]["core_concepts"][0]["source_spans"][0]["end"] = 10000
    else:
        record["source_roles"]["s0"] = "context"
    measured = rows(data)
    assert measured[4]["concept_count"] is None
    assert measured[4]["semantic_coverage"] is False
    assert measured[-1]["concept_rolling_novelty_mean"] is None
    assert measured[-1]["structure_repeat_raw"] is None
    assert measured[-1]["evidence_aware_repeat_raw"] is None
    assert measured[-1]["surface_repeat_raw"] == 1


def test_empty_structure_and_unsupported_evidence_do_not_fake_progress():
    data = [fixture_record(i, participant="Ordinary descriptive words here.") for i in range(7)]
    assert rows(data)[-1]["evidence_atoms"] is None
    assert rows(data)[-1]["evidence_aware_repeat_raw"] is None
    for record in data:
        record["residue"] = {"core_concepts": [], "edge_candidates": []}
    last = rows(data)[-1]
    assert last["concept_count"] == 0
    assert last["concept_rolling_novelty_mean"] is None
    assert last["concept_new_count"] == 0
    assert last["c1_concept_persistence_proxy"] is None


def test_three_axes_are_distinct_and_activation_dimensions_separate():
    record = fixture_record()
    row = rows([record])[0]
    assert row["context_activation_total"] == 4
    assert row["context_positive_coverage"] == pytest.approx(2 / 3)
    assert row["context_hhi"] == 0.625
    assert row["history_hhi"] == 0.5
    assert row["history_context_tv"] == 0.25
    assert row["surface_repeat_raw"] is None
    record["field"]["active_concepts"] = [
        {"key": "none", "contextual_activation": 0}]
    row = rows([record])[0]
    assert row["context_positive_coverage"] == 0
    assert row["context_activation_total"] == 0
    assert row["context_hhi"] is None
    assert row["history_context_tv"] == 0.25


def test_balanced_and_concentrated_history_same_context_and_tie_ranks():
    balanced = fixture_record()
    concentrated = copy.deepcopy(balanced)
    concentrated["historical_strengths"] = {"a": 9, "b": 1}
    a, b = historical_metrics(balanced), historical_metrics(concentrated)
    assert a["history_entropy_nats"] == pytest.approx(math.log(2))
    assert b["history_entropy_nats"] < a["history_entropy_nats"]
    assert a["history_top_mass"] == 0.5
    assert b["history_top_mass"] == 0.9
    assert a["conditioned_top_mass"] == b["conditioned_top_mass"] == 0.75
    assert a["history_context_tv"] == 0.25
    assert b["history_context_tv"] == pytest.approx(0.15)
    assert a["history_rank_displacement"] == 0.5
    assert b["history_rank_displacement"] == 0
    concentrated["accessibility_adjustments"] = {"a": -100}
    changed = historical_metrics(concentrated)
    assert changed["history_top_mass"] == b["history_top_mass"]
    assert changed["accessibility_adjustments"] == {"a": -100}


@pytest.mark.parametrize("strengths", [{}, {"a": 0, "b": 0}, {"a": 1},
                                      {"a": -1, "b": 2}, {"a": math.nan, "b": 1}])
def test_invalid_history_is_unavailable(strengths):
    record = fixture_record()
    record["historical_strengths"] = strengths
    assert historical_metrics(record)["history_context_tv"] is None


def test_topic_pivot_challenges_continuity_and_resets_arc():
    data = [fixture_record(i) for i in range(3)]
    data.append(fixture_record(3, participant="Orchestral harmony follows melodic counterpoint.",
                               new_label="melodic counterpoint", arc="music"))
    measured = rows(data)
    assert measured[2]["opening_text_jaccard"] == 1
    assert measured[3]["opening_text_jaccard"] == 0
    assert measured[3]["arc_pivot"] is True
    assert measured[3]["arc_age"] == 1


def test_concise_resolution_is_a_documented_false_positive_not_a_quality_judge():
    data = [fixture_record(i) for i in range(6)]
    data.append(fixture_record(6, participant="Sensor fixed. Result passed."))
    row = rows(data)[-1]
    assert row["structure_repeat_raw"] == 1  # same nouns is not proof of stagnation
    assert row["evidence_window_novelty"] == 1
    assert row["word3_adjacent_jaccard"] == 0


def test_padding_preserves_semantics_but_exposes_marker_boundary_false_signal():
    data = [fixture_record(i) for i in range(7)]
    data[-1] = fixture_record(6, participant=(data[-1]["participant_text"] + " ") * 8)
    row = rows(data)[-1]
    assert row["concept_window_novelty"] == 0
    assert row["evidence_window_novelty"] == pytest.approx(1 / 3)
    # Frozen +/-2-token marker windows cross repeated-copy boundaries.
    # Preserve this observed failure instead of tuning away the control.
    assert "marker:ms not fixed the sensor" in row["evidence_atoms"]
    assert row["structure_new_per_100_words"] == 0
    assert row["surface_repeat_raw"] > 0.6  # boundary shingles remain inspectable
    assert row["source_word_count"] == 8 * rows(data[:1])[0]["source_word_count"]


@pytest.mark.parametrize("key", ["condition", "schedule", "fidelity", "future_arc_membership"])
def test_private_metadata_and_future_membership_cannot_enter_meter(key):
    record = fixture_record()
    record[key] = "hidden"
    with pytest.raises(ValueError, match="unexpected meter input"):
        measure_pressure_records([record])


def test_baselines_ignore_local_keys_and_have_frozen_age_formula():
    data = [fixture_record(i) for i in range(7)]
    for i, record in enumerate(data):
        for c in record["residue"]["core_concepts"]:
            c["key"] += str(i)
        for e in record["residue"]["edge_candidates"]:
            e["from"] += str(i)
            e["to"] += str(i)
    row = rows(data)[3]
    assert row["maturity"] == 0.6
    assert row["concept_window_novelty"] == 0
    assert row["c1_concept_persistence_proxy"] == 0.6
    assert row["c2_structure_persistence_proxy"] == 0.6
    assert row["c3_context_persistence_proxy"] == 0.6 * 0.625


def test_invalid_identity_windows_and_empty_input():
    assert measure_pressure_records([]) == []
    for window in ((), (1,), (3, 3), (True,)):
        with pytest.raises(ValueError):
            measure_pressure_records([], window)
    data = [fixture_record(0), fixture_record(0)]
    with pytest.raises(ValueError, match="ordinals"):
        measure_pressure_records(data)
    data = [fixture_record(0), fixture_record(1, arc="next"), fixture_record(2)]
    with pytest.raises(ValueError, match="recur"):
        measure_pressure_records(data)


def test_short_text_without_grams_is_unavailable():
    data = [fixture_record(0), fixture_record(1, participant="ok")]
    row = rows(data)[-1]
    assert row["word3_adjacent_jaccard"] is None
    assert row["char5_adjacent_jaccard"] is None
    assert row["surface_repeat_raw"] is None
