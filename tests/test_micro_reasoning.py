"""Model-free controls for isolated reasoning comparison; no live endpoint calls."""
import copy
import json

import pytest

from mneme.experiments.micro_stagnation import build_payload
from tools import run_micro_reasoning as runner


def configs():
    off = {"endpoint": "http://fixture/v1/chat/completions", "model": "resident-alias",
           "temperature": 0.7, "top_p": 0.95, "top_k": 64, "min_p": 0.05,
           "seed": 424242, "cache_prompt": False, "max_tokens": 8,
           "reasoning_effort": "none", "chat_template_kwargs": {"enable_thinking": False},
           "context_tokens": 4096, "context_reserve_tokens": 256}
    on = {**off, "chat_template_kwargs": {"enable_thinking": True},
          "reasoning_format": "deepseek", "max_tokens": 2048}
    on.pop("reasoning_effort")
    return off, on


def manifest():
    call = {"exchanges": [{"participant": f"exact observation {i}",
                           "gemma": f"exact framing {i}"} for i in range(5)],
            "system": "Return only 0, 1, or 2.", "allowed_values": [0, 1, 2],
            "expected": 2, "condition": "PRIVATE"}
    return {"calls": [{**call, "id": "case-a"}, {**call, "id": "case-b"}]}


def transport_fixture(calls, *, reasoning="private reasoning", finish="stop", mismatch=False,
                      fail=False, tokens=100, content="2", cache_n=0):
    def transport(url, payload):
        calls.append((url, copy.deepcopy(payload)))
        if url.endswith("/apply-template"):
            assert payload["chat_template_kwargs"] == {"enable_thinking": True}
            return {"prompt": "thinking prompt"}
        if url.endswith("/tokenize"):
            return {"tokens": [1] * tokens}
        if fail:
            raise OSError("uncertain request")
        number = sum(url.endswith("/completions") for url, _ in calls)
        thought = "different reasoning" if mismatch and number == 2 else reasoning
        return {"choices": [{"message": {"content": content, "reasoning_content": thought},
                             "finish_reason": finish}],
                "usage": {"prompt_tokens": 101, "completion_tokens": 22,
                          "completion_tokens_details": {"reasoning_tokens": 20}},
                "timings": {"prompt_ms": 12.5, "predicted_ms": 3.0, "cache_n": cache_n}}
    return transport


def test_exact_allowed_payload_changes_and_no_input_mutation():
    off, on = configs()
    source = manifest()
    original = copy.deepcopy((source, off, on))
    call = source["calls"][0]
    before = build_payload(call["exchanges"], call["system"], off)
    after = runner.reasoning_payload(call, off, on)
    changed = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
    assert changed == runner.ALLOWED_CHANGES
    assert after["messages"] == before["messages"]
    assert after["cache_prompt"] is False and "reasoning_effort" not in after
    assert "PRIVATE" not in json.dumps(after)
    assert (source, off, on) == original
    for key, value in (("seed", 99), ("temperature", 0), ("cache_prompt", True),
                       ("max_tokens", 4096), ("reasoning_effort", "high")):
        with pytest.raises(ValueError):
            runner.reasoning_payload(call, off, {**on, key: value})


def test_separated_reasoning_scoring_counts_and_resume(tmp_path, monkeypatch):
    from mneme.state.compact import CompactStore
    from mneme.state.compact_runtime import CompactRuntime

    def forbidden(*args, **kwargs):
        raise AssertionError("production path or extra call")

    monkeypatch.setattr(CompactStore, "__init__", forbidden)
    monkeypatch.setattr(CompactRuntime, "evaluate_saa", forbidden)
    calls = []
    ticks = iter(range(10))
    rows = runner.run(manifest(), *configs(), tmp_path, transport=transport_fixture(calls),
                      clock=lambda: next(ticks))
    assert len(calls) == 6
    assert all(r["value"] == 2 and r["reasoning_tokens"] == 20 for r in rows)
    assert rows[0]["content"] == "2" and rows[0]["reasoning_content"] == "private reasoning"
    assert rows[0]["wall_seconds"] == 1
    assert rows[0]["input_tokens"] == 101 and rows[0]["output_tokens"] == 22
    assert rows[0]["prefill_ms"] == 12.5 and rows[0]["generation_ms"] == 3
    assert runner.run(manifest(), *configs(), tmp_path, transport=forbidden) == rows
    frozen = runner.read_gzip(tmp_path / "frozen_execution.json.gz")
    assert len(frozen["requests"]) == 2
    off, on = configs()
    with pytest.raises(ValueError, match="different frozen"):
        runner.run(manifest(), {**off, "seed": 7}, {**on, "seed": 7}, tmp_path,
                   transport=forbidden)


def test_reasoning_mismatch_same_final_halts_and_retains_both(tmp_path):
    calls = []
    for _ in range(2):
        with pytest.raises(RuntimeError, match="identical duplicate changed reasoning"):
            runner.run(manifest(), *configs(), tmp_path,
                       transport=transport_fixture(calls, mismatch=True))
        assert len(calls) == 6
    assert runner.read_gzip(tmp_path / "calls/case-a/response.json.gz")
    assert runner.read_gzip(tmp_path / "calls/case-b/response.json.gz")
    assert len(runner.read_gzip(tmp_path / "readings.json.gz")) == 2


@pytest.mark.parametrize("kwargs,message", [
    ({"reasoning": None}, "reasoning was not observed"),
    ({"reasoning": ""}, "reasoning was not observed"),
    ({"finish": "length"}, "truncated"),
    ({"cache_n": 12}, "cache reuse"),
])
def test_invalid_control_stops_before_more_calls(tmp_path, kwargs, message):
    calls = []
    with pytest.raises(RuntimeError, match=message):
        runner.run(manifest(), *configs(), tmp_path, transport=transport_fixture(calls, **kwargs))
    assert len(calls) == 3
    assert runner.read_gzip(tmp_path / "calls/case-a/response.json.gz")


def test_context_budget_accounts_for_reasoning_cap_without_clipping(tmp_path):
    calls = []
    with pytest.raises(RuntimeError, match="output budget exceed context"):
        runner.run(manifest(), *configs(), tmp_path,
                   transport=transport_fixture(calls, tokens=2000))
    assert len(calls) == 2  # Would fit the old eight-token budget; must not infer now.
    row = runner.read_gzip(tmp_path / "calls/case-a/receipt.json.gz")
    assert not row["model_called"]


def test_uncertain_attempt_not_retried(tmp_path):
    calls = []
    with pytest.raises(OSError):
        runner.run(manifest(), *configs(), tmp_path, transport=transport_fixture(calls, fail=True))
    with pytest.raises(RuntimeError, match="uncertain prior attempt"):
        runner.run(manifest(), *configs(), tmp_path, transport=transport_fixture(calls))
    assert len(calls) == 3


def test_invalid_classification_is_not_rescued_by_reasoning(tmp_path):
    rows = runner.run(manifest(), *configs(), tmp_path,
                      transport=transport_fixture([], content="2 because it circles"))
    assert all(not r["available"] and r["value"] is None for r in rows)


def test_unreported_reasoning_token_count_remains_null():
    row = runner.reading({"choices": [{"message": {"content": "0", "reasoning_content": "x"},
                                       "finish_reason": "stop"}]}, [0, 1], 1)
    assert row["reasoning_observed"] and row["reasoning_tokens"] is None


def test_manifest_pair_validation_precedes_any_transport(tmp_path):
    source = manifest()
    source["calls"][1]["system"] = "Changed prompt"
    with pytest.raises(ValueError, match="adjacent identical"):
        runner.run(source, *configs(), tmp_path,
                   transport=lambda *_: pytest.fail("unexpected call"))
