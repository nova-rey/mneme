import json
from pathlib import Path

import pytest

from mneme.contracts import GenerationRequest, GenerationResult
from mneme.state.compact import CompactStore
from tools import run_three_pressure_v2 as runner


def result(content, metadata=None):
    return GenerationResult(content, "fixture", "test", {}, None, None, 0, "stop", metadata or {})


def plan():
    return json.loads(Path("docs/experiments/three_pressure_v2/construction.json").read_text())


def test_private_ledger_and_shared_roles():
    facts = {"required_facts": ["No tests were run."], "action": "Ask about power."}
    request = runner.quinn_request("Opening", facts, 2, [("Prior user", "Prior answer")])
    assert "No tests were run." in request.system
    assert request.messages[0] == {"role": "assistant", "content": "Prior user"}
    payload = request.messages[1]["content"]
    assert '"assistant_A": "Prior answer"' in payload
    assert '"assistant_B": "Prior answer"' in payload
    assert request.seed is None
    assert request.parameters["max_new_tokens"] == 384


@pytest.mark.parametrize(
    "text",
    [
        "Nothing changed.",
        "No tests were run. No tests were run.",
        "No tests were run. It reached 57 volts.",
        "F-same: No tests were run.",
        "SHARED_ENVIRONMENT_DIVERGENCE",
        "",
    ],
)
def test_gate_rejects_before_gemma(text):
    assert runner.fact_gate(text, ["No tests were run."], "Opening")


def test_gate_preserves_quantities_negation_and_order():
    facts = ["There were 0 resets.", "The position is not changed."]
    assert not runner.fact_gate(" ".join(facts) + " What follows?", facts, "Opening")
    assert runner.fact_gate(" ".join(reversed(facts)), facts, "Opening")
    assert runner.fact_gate("There were 0 resets. The position is changed.", facts, "Opening")


def test_context_drops_whole_pairs_and_never_clips():
    pairs = [("old user", "old answer"), ("new user", "new answer")]
    seen = []

    def preprocess(messages):
        seen.append(messages)
        return {"prompt_tokens": len(messages) * 100, "serialized_prompt": str(messages)}

    request, record = runner.bounded_request(
        pairs,
        "current unchanged",
        "system",
        1,
        {"max_complete_prior_pairs": 2, "prompt_token_limit": 400},
        {},
        preprocess,
    )
    assert record["omitted_prior_turns"] == [1]
    assert [row["role"] for row in request.messages] == ["user", "assistant", "user"]
    assert request.messages[-1]["content"] == "current unchanged"
    assert len(seen) == 2
    with pytest.raises(ValueError, match="no clipping"):
        runner.bounded_request(
            [],
            "current",
            "system",
            1,
            {"max_complete_prior_pairs": 2, "prompt_token_limit": 100},
            {},
            preprocess,
        )


def test_native_preprocessing_is_not_inference(monkeypatch):
    calls = []

    def post(url, payload):
        calls.append((url, payload))
        return {"prompt": "rendered"} if url.endswith("apply-template") else {"tokens": [1, 2]}

    monkeypatch.setattr(runner, "post_json", post)
    recorded = runner.native_preprocess([{"role": "user", "content": "hello"}])
    assert recorded["prompt_tokens"] == 2
    assert [url.rsplit("/", 1)[1] for url, _ in calls] == ["apply-template", "tokenize"]


def test_recording_host_charges_before_dispatch_and_never_retries(tmp_path):
    budget = runner.CallBudget(tmp_path / "budget.json", plan()["budget"])
    request = GenerationRequest(
        ({"role": "user", "content": "hello"},), parameters={"max_new_tokens": 2048}
    )

    class Host:
        calls = 0

        def generate(self, incoming):
            self.calls += 1
            assert incoming is request
            assert (
                json.loads((tmp_path / "calls" / "one-gemma.json").read_text())["status"]
                == "DISPATCHED"
            )
            assert len(json.loads((tmp_path / "budget.json").read_text())["calls"]) == 1
            raise ValueError("uncertain provider failure")

    host = Host()
    wrapper = runner.RecordingHost(host, tmp_path / "calls", "gemma", budget)
    with pytest.raises(ValueError):
        wrapper.generate(request, "one")
    with pytest.raises(RuntimeError, match="duplicate"):
        wrapper.generate(request, "one")
    assert host.calls == 1
    assert json.loads((tmp_path / "calls" / "one-gemma.json").read_text())["status"] == "ERROR"


def test_budget_global_limit_and_run_reservations(tmp_path):
    limits = {"max_calls": 1, "requested_output_tokens_ceiling": 2048, "counts": {"gemma": 1}}
    budget = runner.CallBudget(tmp_path / "budget.json", limits)
    budget.register_run("main", tmp_path / "main")
    with pytest.raises(RuntimeError, match="reserved"):
        budget.register_run("main", tmp_path / "other")
    budget.charge("first", "gemma", 2048)
    with pytest.raises(RuntimeError, match="exhausted"):
        budget.charge("second", "gemma", 1)


def test_coverage_uses_verified_token_limit_and_slot_boundaries():
    assert runner.input_coverage({"s0": "no tests", "s1": "good reply"}, 4)["slots"] == {
        "s0": True,
        "s1": True,
    }
    assert runner.input_coverage({"s0": "no tests", "s1": "good reply"}, 3)["slots"] == {
        "s0": True,
        "s1": False,
    }


def test_capacity_omission_marks_only_affected_source_incomplete():
    sources = {
        "s0": "one supports two.",
        "s1": " ".join(f"node{i} supports thing{i}." for i in range(7)),
    }
    proposals = [
        {
            "from": "one",
            "relation": "supports",
            "to": "two",
            "source": "s0",
            "evidence": sources["s0"],
        }
    ]
    proposals += [
        {
            "from": f"node{i}",
            "relation": "supports",
            "to": f"thing{i}",
            "source": "s1",
            "evidence": f"node{i} supports thing{i}.",
        }
        for i in range(7)
    ]
    recorded = runner.extraction_record(result(json.dumps({"relationships": proposals})), sources)
    assert recorded["extraction_coverage"]["s1"] is False
    assert any("omission" in row["kind"] for row in recorded["normalization_decisions"])


def test_export_is_deterministic_label_blind_no_hosts(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("export constructed host")

    for name in ("RemoteLlamaHost", "RecordingGlinerHost", "DeepInfraQwenAssessorHost"):
        monkeypatch.setattr(runner, name, forbidden)
    records = [
        {
            "conversation": "c01",
            "turn": 1,
            "participant_text": "hi",
            "gemma_text": "hello",
            "condition": "secret",
            "ledger": ["secret"],
            "field": None,
        }
    ]
    for name in ("a", "b"):
        output = tmp_path / name
        output.mkdir()
        runner.export_records(records, output)
    assert (tmp_path / "a/meter_inputs.json").read_bytes() == (
        tmp_path / "b/meter_inputs.json"
    ).read_bytes()
    assert "secret" not in (tmp_path / "a/meter_inputs.json").read_text()
    assert set(json.loads((tmp_path / "a/meter_inputs.json").read_text())[0]) <= runner.INPUT_KEYS


def test_injected_run_is_read_only_and_extraction_failure_is_unavailable(tmp_path, monkeypatch):
    state = tmp_path / "state.sqlite3"
    store = CompactStore(state)
    store.close()
    digest = runner.file_digest(state)
    construction = plan()
    construction["preflight"] = [{"domain": "network", "pattern": "F-same", "turns": 2}]
    called = []

    class EmptyField:
        payload = ""
        accessibility_distribution = ()

        def to_dict(self):
            return {}

    class Evaluation:
        field = EmptyField()

    monkeypatch.setattr(runner.CompactRuntime, "evaluate_saa", lambda *args, **kw: Evaluation())

    def forbidden(*args, **kwargs):
        raise AssertionError("write invoked")

    monkeypatch.setattr(CompactStore, "set_metadata", forbidden)
    monkeypatch.setattr(runner.CompactRuntime, "publish_state", forbidden)

    class Host:
        def __init__(self, role):
            self.role = role

        def generate(self, request):
            called.append(self.role)
            if self.role == "gemma":
                assert "F-same" not in request.system
                return result("Measure it.")
            if self.role == "extractor":
                raise ValueError("missing extraction")
            return result("Invented unsupported result 9999.")

    receipt = runner.run(
        tmp_path / "output",
        state,
        construction,
        mode="preflight",
        budget_path=tmp_path / "budget.json",
        hosts={r: Host(r) for r in ("gemma", "extractor", "quinn")},
        preprocess=lambda messages: {"prompt_tokens": 10, "serialized_prompt": "test"},
        expected_sha=digest,
    )
    assert receipt["unchanged"] and receipt["measurement_calls"] == 0
    assert receipt["accepted_turns"] == receipt["rejections"] == 1
    assert called == ["gemma", "extractor", "quinn"]
    rows = json.loads((tmp_path / "output/records.json").read_text())
    assert rows[0]["residue"] is None
    assert rows[0]["extraction_coverage"] == {"s0": None, "s1": None}
    assert rows[0]["arc"]["turn_ids"] == ["c101:turn:1"]
    assert runner.file_digest(state) == digest


def test_unicode_token_offsets_are_original_text_offsets():
    coverage = runner.input_coverage({"s0": "İ", "s1": "tail extra"}, 2)
    assert coverage["covered_char_end"] == 6
    assert coverage["slots"] == {"s0": True, "s1": False}


def test_compression_roundtrip_and_alternate_cleanup(tmp_path):
    path = tmp_path / "large.json"
    runner.write_json(path, {"small": True})
    payload = {"raw": "unchanged complete text " * 10000}
    runner.write_json(path, payload)
    compressed = path.with_suffix(".json.gz")
    first = compressed.read_bytes()
    assert not path.exists()
    assert runner.read_json(path) == payload
    runner.write_json(path, payload)
    assert compressed.read_bytes() == first
    runner.write_json(path, {"small": True})
    assert not compressed.exists()


def test_storage_guard_prevents_provider_call(tmp_path, monkeypatch):
    class Host:
        def generate(self, request):
            raise AssertionError("provider called below storage reserve")

    class Disk:
        free = 1

    monkeypatch.setattr(runner.shutil, "disk_usage", lambda path: Disk())
    host = runner.RecordingHost(
        Host(),
        tmp_path / "calls",
        "gemma",
        runner.CallBudget(tmp_path / "budget.json", plan()["budget"]),
    )
    with pytest.raises(RuntimeError, match="reserve"):
        host.generate(GenerationRequest((), parameters={"max_new_tokens": 2048}), "one")
    assert not (tmp_path / "budget.json").exists()


def test_raw_transport_and_parser_omissions_preserve_source_isolation():
    sources = {"s0": "alpha supports beta.", "s1": "gamma supports delta."}
    offset = len(sources["s0"]) + 1
    raw = {
        "raw": {
            "relation_extraction": {
                "supports": [
                    {
                        "head": {"text": "alpha", "start": 0, "end": 5},
                        "tail": {"text": "beta", "start": 15, "end": 19},
                        "confidence": 0.9,
                    },
                    {
                        "head": {"text": "WRONG", "start": offset, "end": offset + 5},
                        "tail": {"text": "delta", "start": offset + 15, "end": offset + 20},
                        "confidence": 0.9,
                    },
                ]
            }
        }
    }
    host = runner.RecordingGlinerHost(lambda url, payload: raw)
    request = GenerationRequest(
        ({"role": "user", "content": json.dumps({"source_slots": sources})},)
    )
    response = host.generate(request)
    assert response.raw_metadata["transport"] == raw
    recorded = runner.extraction_record(response, sources)
    assert recorded["extraction_coverage"] == {"s0": True, "s1": False}
    assert all(
        span["source_slot"] == "s0"
        for edge in recorded["residue"]["edge_candidates"]
        for span in edge["source_spans"]
    )
