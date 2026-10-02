from __future__ import annotations

import copy
import json
import socket
import sqlite3

import pytest

from mneme.experiments.movement_meters import measure_movement, text_features
from mneme.experiments.pressure_meters import measure_pressure_records
from tools.report_movement_meters import build_report


def record(i=0, participant="The sensor measured 10 ms, not fixed.",
           gemma="Check the cable and test the power.", arc="arc"):
    return {"conversation": "c", "turn": i + 1, "ordinal": i * 3,
            "accepted_turn_id": f"t{i}", "arc_id": arc,
            "participant_text": participant, "gemma_text": gemma}


def rows(records):
    return measure_movement(records, windows=(3,))


def test_passive_replay_no_io_and_no_input_mutation(monkeypatch):
    records = [record(i) for i in range(6)]
    before = copy.deepcopy(records)

    def forbidden(*args, **kwargs):
        pytest.fail("measurement attempted IO")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    output = rows(records)
    assert output == rows(records)
    assert records == before
    json.dumps(output, allow_nan=False)
    output[-1]["features"]["participant"]["quantities"].append("invented")
    assert records == before
    assert rows(records)[-1]["participant_quantities_new_count"] == 0


def test_causal_age_pivot_and_lag():
    records = [record(i, participant=f"Measured {i} ms.", gemma=f"Consider {i - 1} ms.",
                      arc="a" if i < 4 else "b") for i in range(7)]
    output = rows(records)
    assert [r["arc_age"] for r in output] == [1, 2, 3, 4, 1, 2, 3]
    assert [r["arc_pivot"] for r in output] == [False] * 4 + [True, False, False]
    assert output[0]["participant_quantities_new_fraction"] is None
    assert output[2]["echo_quantities_lag1_fraction"] == 1
    assert output[4]["echo_quantities_lag1_fraction"] is None
    for n in range(1, len(records) + 1):
        assert rows(records[:n]) == output[:n]


def test_same_nouns_changed_quantities_and_negation():
    data = [record(0, "Sensor measured 10 ms and failed."),
            record(1, "Sensor measured 20 ms and passed."),
            record(2, "Sensor measured 20 ms and did not pass.")]
    output = rows(data)
    assert output[1]["participant_quantities_new_fraction"] == 1
    assert output[2]["participant_quantities_new_fraction"] == 0
    assert output[2]["participant_states_new_count"] > 0
    for r in output:
        for source, features in r["features"].items():
            text = data[r["turn"] - 1][source + "_text"]
            assert all(text[s["start"]:s["end"]] == s["quote"] for s in features["spans"])


def test_literal_repetition_vs_wording_change_is_only_surface_evidence():
    output = rows([record(0), record(1),
                   record(2, gemma="Inspect wiring; assess supply stability.")])
    assert output[1]["gemma_phrases_recent_max_jaccard"] == 1
    assert output[1]["gemma_content_new_fraction"] == 0
    # A paraphrase falsely appears new. The instrument must retain this limit.
    assert output[2]["gemma_content_new_fraction"] == 1


def test_concise_resolution_and_repeated_padding_are_not_quality_scores():
    output = rows([record(0, gemma="Resolved."), record(1, gemma="Resolved."),
                   record(2, gemma="Resolved. " * 30), record(3, gemma="Resolved. " * 30)])
    assert output[1]["gemma_content_new_fraction"] == 0
    assert output[1]["gemma_phrases_recent_max_jaccard"] is None
    assert output[2]["gemma_content_new_fraction"] == 0
    assert output[3]["gemma_phrases_new_fraction"] == 0
    assert output[3]["gemma_word_count"] == 30


def test_echo_can_be_wrong_polarity_and_cannot_mean_understanding():
    output = rows([record(0, "A baseline."),
                   record(1, "The sensor failed at 20 ms.", "The sensor did not fail at 20 ms.")])
    assert output[1]["echo_quantities_same_fraction"] == 1
    assert output[1]["echo_content_same_fraction"] < 1
    assert "understanding" not in output[1]


def test_moving_environment_static_model_remains_separate():
    output = rows([record(i, f"Measured {i + 10} ms.") for i in range(7)])
    assert output[-1]["participant_quantities_new_fraction"] == 1
    assert output[-1]["gemma_content_new_fraction"] == 0
    assert output[-1]["gemma_phrases_recent_max_jaccard"] == 1
    assert output[-1]["echo_quantities_same_fraction"] == 0


def test_missing_empty_and_no_signature_are_distinct():
    data = [record(0), record(1, participant=None), record(2, participant=""),
            record(3, participant="Hello."), record(4, participant="Hello.")]
    output = rows(data)
    assert output[1]["participant_quantities_count"] is None
    assert output[2]["participant_quantities_count"] == 0
    assert output[2]["features"]["participant"]["reason"] == "empty_text"
    assert output[4]["participant_quantities_new_count"] is None  # missing t2 in W3
    assert output[4]["echo_quantities_same_fraction"] is None
    complete = rows([record(i, participant="Hello.") for i in range(4)])[-1]
    assert complete["participant_quantities_new_count"] == 0
    assert complete["participant_quantities_new_fraction"] is None


def test_numeric_units_signs_and_list_numbers():
    features = text_features("1. Check supply.\n2) Then measured -2.50 V and 20 ms, not 25%.")
    assert features["quantities"] == ["-2.5 v", "20 ms", "25 %"]


@pytest.mark.parametrize("windows", [(), (0,), (True,), (3, 3)])
def test_bad_windows(windows):
    with pytest.raises(ValueError):
        measure_movement([record()], windows=windows)


def test_bad_order_labels_and_arc_recurrence():
    for records in ([record(1), record(0)], [record(), record()],
                    [{**record(), "pattern": "F"}],
                    [record(0, arc="a"), record(1, arc="b"), record(2, arc="a")]):
        with pytest.raises(ValueError):
            rows(records)


def test_report_retains_v2_and_joins_environment_review_only_after_measurement():
    records = [record(i) for i in range(4)]
    manifest = [{"conversation": "c", "domain": "test", "pattern": "moving"}]
    review = {"stage": "prospective", "conversations": {"c": {
        "environment_valid": True, "gemma_behavior": "incorrect and repetitive"}}}
    output = build_report(records, manifest, review)
    assert output["retained_v2_rows"] == measure_pressure_records(records)
    assert all(r["environment_valid"] for r in output["rows"])
    alternate = copy.deepcopy(review)
    alternate["conversations"]["c"]["environment_valid"] = False
    other = build_report(records, manifest, alternate)
    for left, right in zip(output["rows"], other["rows"], strict=True):
        assert {k: v for k, v in left.items() if k != "environment_valid"} == {
            k: v for k, v in right.items() if k != "environment_valid"}
    alternate["conversations"]["c"]["environment_valid"] = None
    with pytest.raises(ValueError):
        build_report(records, manifest, alternate)


def test_report_prospective_environment_labels_and_lengths():
    records = [record(i) for i in range(3)]
    for r in records:
        r["length"] = {"capped": False, "finish_reason": "stop", "gemma_words": 8,
                       "participant_words": 9, "usage": {"completion_tokens": 12}}
        r["private_condition"] = "Never admitted to meter input"
    manifest = [{"conversation": "c", "environment": "moving",
                 "planned_opportunity": "fixation_possible"}]
    review = {"stage": "prospective", "conversations": {"c": {"environment_valid": True}}}
    result = build_report(records, manifest, review)
    assert result["rows"][-1]["environment"] == "moving"
    assert result["rows"][-1]["pattern"] == "moving"
    assert result["rows"][-1]["planned_opportunity"] == "fixation_possible"
    assert result["rows"][-1]["output_tokens"] == 12
    assert result["rows"][-1]["recorded_gemma_words"] == 8
    assert "private_condition" not in json.dumps(result)


def test_report_cli_is_byte_replayable(tmp_path, monkeypatch):
    from tools.report_movement_meters import main, read_json, write_json

    records_path = tmp_path / "records.json.gz"
    manifest_path = tmp_path / "manifest.json"
    review_path = tmp_path / "review.json"
    output = tmp_path / "output"
    write_json(records_path, [record(i) for i in range(4)])
    write_json(manifest_path, [{"conversation": "c", "environment": "static"}])
    write_json(review_path, {"stage": "prospective", "conversations": {
        "c": {"environment_valid": True}}})
    monkeypatch.setattr("sys.argv", ["report_movement_meters", "--records", str(records_path),
                                     "--manifest", str(manifest_path), "--review", str(review_path),
                                     "--output", str(output)])
    main()
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    unrelated = output / "external_analysis.json"
    unrelated.write_text('{"independent":true}\n')
    main()
    assert before == {p.name: p.read_bytes() for p in output.iterdir() if p != unrelated}
    assert unrelated.read_text() == '{"independent":true}\n'
    assert unrelated.name not in read_json(output / "receipt.json")["outputs"]
    assert read_json(output / "receipt.json")["new_model_calls"] == 0
    assert "Quinn valid" in (output / "matrix.md").read_text()
    assert "| Condition | Turn | Arc | Pivot |" in (output / "matrix.md").read_text()
    assert "history_context_tv" in (output / "retained_v2_matrix.csv").read_text()
    assert "Gemma continuity" in (output / "retained_v2_matrix.md").read_text()
    assert b"\r" not in (output / "matrix.csv").read_bytes()
    assert b"\r" not in (output / "retained_v2_matrix.csv").read_bytes()
    assert not (output / "retained_v2_matrix.md").read_bytes().endswith(b"\n\n")
