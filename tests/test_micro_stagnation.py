"""Inference-free checks of the isolated diagnostic boundary."""
import copy
import json

import pytest

from mneme.experiments.micro_stagnation import (
    build_payload,
    checkpoint_windows,
    parse_classification,
)
from tools import run_micro_stagnation as runner


def config():
    return {"endpoint": "http://fixture/v1/chat/completions", "model": "resident-alias",
            "temperature": 0.7, "top_p": 0.95, "top_k": 64, "min_p": 0.05,
            "seed": 424242, "cache_prompt": False, "max_tokens": 8,
            "reasoning_effort": "none", "context_tokens": 4096,
            "context_reserve_tokens": 256}


def exchanges():
    return [{"participant": f"Observation {i}: exact 0.0 volts.\nNext line.",
             "gemma": f"Assistant framing {i}"} for i in range(5)]


def manifest():
    call = {"exchanges": exchanges(), "system": "Return only 0, 1, or 2.",
            "allowed_values": [0, 1, 2], "condition": "PRIVATE", "expected": 2}
    return {"calls": [{**call, "id": "case01-a"}, {**call, "id": "case01-b"}]}


def records(arcs):
    return [{"conversation": "c", "arc_id": arc, "ordinal": 2 * i,
             "accepted_turn_id": f"accepted-{i}", "turn": i,
             "participant_text": f"exact participant {i}", "gemma_text": f"exact Gemma {i}",
             "field": {"payload": "SAA PRIVATE"}, "opening_task": "PRIVATE LABEL"}
            for i, arc in enumerate(arcs, 1)]


def test_cadence_counts_accepted_turns_resets_and_is_prefix_causal():
    source = records(["A"] * 7 + ["B"] * 10)
    original = copy.deepcopy(source)
    result = checkpoint_windows(source)
    assert [(r["arc_id"], r["arc_age"], r["turn"]) for r in result] == [
        ("A", 5, 5), ("B", 5, 12), ("B", 10, 17)]
    assert result[1]["window_turn_ids"] == [f"accepted-{i}" for i in range(8, 13)]
    assert checkpoint_windows(source[:12]) == result[:2]
    source[-1]["gemma_text"] = "future revised"
    assert checkpoint_windows(source)[0] == result[0]
    assert checkpoint_windows(original) == result


def test_cadence_missing_full_source_is_unavailable_and_bad_identity_rejected():
    source = records(["A"] * 5)
    source[2]["gemma_text"] = None
    result = checkpoint_windows(source)[0]
    assert not result["available"] and len(result["exchanges"]) == 5
    with pytest.raises(ValueError, match="exact participant"):
        build_payload(result["exchanges"], "prompt", config())
    for altered in ([*source, source[-1]], records(["A", "B", "A"])):
        with pytest.raises(ValueError):
            checkpoint_windows(altered)
    with pytest.raises(ValueError, match="unexpected"):
        checkpoint_windows([{**source[0], "condition": "private"}])


def test_payload_exact_sources_only_and_no_input_mutation():
    original = exchanges()
    frozen = copy.deepcopy(original)
    payload = build_payload(original, "tiny frozen prompt", config())
    assert json.loads(payload["messages"][1]["content"])["recent_conversation"] == frozen
    assert len(payload["messages"]) == 2
    assert original == frozen
    assert payload["reasoning_effort"] == "none"
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["cache_prompt"] is False
    assert payload["max_tokens"] == 8
    with pytest.raises(ValueError):
        build_payload([{**original[0], "condition": "PRIVATE"}] * 5, "prompt", config())
    with pytest.raises(ValueError):
        build_payload(original[:4], "prompt", config())


@pytest.mark.parametrize("content,finish,available", [
    ("0", "stop", True), (" \n2\n", "stop", True), ("2 because", "stop", False),
    ("12", "stop", False), ("1", "length", False), (None, "stop", False),
    ("２", "stop", False), ("1", None, False), ("", "stop", False),
])
def test_strict_parse(content, finish, available):
    row = parse_classification(content, finish, [0, 1, 2])
    assert row["available"] is available
    assert (row["value"] is not None) is available
    assert not parse_classification("2", "stop", [0, 1])["available"]


def transport_fixture(calls, *, oversized=False, mismatch=False, fail=False):
    def transport(url, payload):
        calls.append((url, copy.deepcopy(payload)))
        if url.endswith("/apply-template"):
            return {"prompt": "templated"}
        if url.endswith("/tokenize"):
            return {"tokens": [1] * (4090 if oversized else 100)}
        if fail:
            raise OSError("transport interrupted after submission")
        number = sum(url.endswith("/completions") for url, _ in calls)
        return {"choices": [{"message": {"content": "0" if mismatch and number == 2 else "2"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 101, "completion_tokens": 2},
                "timings": {"prompt_ms": 12.5, "predicted_ms": 3.0, "cache_n": 0}}
    return transport


def test_serial_recorder_isolated_raw_returns_and_resume_no_calls(tmp_path, monkeypatch):
    # Production paths must remain untouched even with diagnostic inference enabled.
    from mneme.state.compact import CompactStore
    from mneme.state.compact_runtime import CompactRuntime

    def forbidden(*args, **kwargs):
        raise AssertionError("production state/generation path called")

    monkeypatch.setattr(CompactStore, "__init__", forbidden)
    monkeypatch.setattr(CompactRuntime, "evaluate_saa", forbidden)
    calls = []
    source = manifest()
    original = copy.deepcopy(source)
    ticks = iter(range(10))
    result = runner.run(source, config(), tmp_path, transport=transport_fixture(calls),
                        clock=lambda: next(ticks))
    assert source == original
    assert len(calls) == 6  # Four model-free sizing calls, exactly two assessment calls.
    assert all(r["value"] == 2 and r["wall_seconds"] == 1 for r in result)
    assert result[0]["prefill_ms"] == 12.5 and result[0]["generation_ms"] == 3
    assert result[0]["input_tokens"] == 101 and result[0]["output_tokens"] == 2
    assert all("PRIVATE" not in json.dumps(payload) for _, payload in calls)
    assert json.loads((tmp_path / "calls/case01-a/response.json").read_text())["timings"][
        "cache_n"] == 0
    assert runner.run(source, config(), tmp_path, transport=forbidden) == result
    with pytest.raises(ValueError, match="different frozen"):
        runner.run(source, {**config(), "seed": 9}, tmp_path, transport=forbidden)


def test_oversize_unavailable_without_inference_or_clipping(tmp_path):
    calls = []
    result = runner.run(manifest(), config(), tmp_path,
                        transport=transport_fixture(calls, oversized=True))
    assert len(calls) == 4 and all(not r["model_called"] for r in result)
    assert all(not r["available"] and r["value"] is None for r in result)


def test_uncertain_attempt_never_retried(tmp_path):
    calls = []
    with pytest.raises(OSError):
        runner.run(manifest(), config(), tmp_path, transport=transport_fixture(calls, fail=True))
    assert (tmp_path / "calls/case01-a/pending.json").exists()
    with pytest.raises(RuntimeError, match="uncertain prior attempt"):
        runner.run(manifest(), config(), tmp_path, transport=transport_fixture(calls))
    assert len(calls) == 3


def test_duplicate_mismatch_stops_after_preserving_both_raw_returns(tmp_path):
    calls = []
    with pytest.raises(RuntimeError, match="duplicate changed"):
        runner.run(manifest(), config(), tmp_path,
                   transport=transport_fixture(calls, mismatch=True))
    assert len(calls) == 6
    assert (tmp_path / "calls/case01-a/response.json").exists()
    assert (tmp_path / "calls/case01-b/response.json").exists()
    with pytest.raises(RuntimeError, match="duplicate changed"):
        runner.run(manifest(), config(), tmp_path, transport=transport_fixture(calls))
    assert len(calls) == 6


def test_missing_provider_usage_and_timings_stay_unavailable():
    row = runner.response_reading({"choices": [{"message": {"content": "0"},
                                               "finish_reason": "stop"}]}, [0, 1], 2.0)
    assert row["input_tokens"] is row["output_tokens"] is None
    assert row["prefill_ms"] is row["generation_ms"] is None


def test_later_phase_can_run_one_assessment_per_checkpoint(tmp_path):
    calls = []
    source = {"paired_replay": False, "calls": manifest()["calls"][:1]}
    result = runner.run(source, config(), tmp_path, transport=transport_fixture(calls))
    assert len(calls) == 3 and len(result) == 1
    assert result[0]["observation_wall_seconds"] >= result[0]["wall_seconds"]
    with pytest.raises(ValueError, match="adjacent identical"):
        runner.run({"calls": source["calls"]}, config(), tmp_path / "other",
                   transport=transport_fixture(calls))
    assert len(calls) == 3
