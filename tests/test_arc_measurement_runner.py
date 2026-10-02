from pathlib import Path

from mneme.contracts import GenerationRequest, GenerationResult
from tools.run_arc_measurements import (
    TOPICS,
    RecordingHost,
    construction,
    quinn_request,
    run,
)


def test_frozen_plan_has_matched_lengths_and_exact_budget():
    plan = construction()
    assert plan["planned_calls"] == {
        "gemma": 40,
        "extraction": 40,
        "quinn": 36,
        "measurement": 0,
    }
    for topic in TOPICS.values():
        assert len(topic["F"]) == len(topic["S"]) == 9
    assert construction() == plan


def test_shared_partner_private_schedule_is_not_public_message():
    pairs = [("public participant", "public answer")]
    request = quinn_request("network", "S", 2, pairs)
    assert TOPICS["network"]["S"][0] in request.system
    assert all(TOPICS["network"]["S"][0] not in row["content"] for row in request.messages)
    assert request.messages[0]["content"] == "public participant"
    assert '"assistant_A": "public answer"' in request.messages[-1]["content"]
    assert '"assistant_B": "public answer"' in request.messages[-1]["content"]


def test_recording_host_passes_identical_request_and_result_once(tmp_path):
    request = GenerationRequest(({"role": "user", "content": "hello"},))
    result = GenerationResult("answer", "model", "local", {}, None, None, None, "stop")

    class Host:
        calls = 0

        def generate(self, incoming):
            assert incoming is request
            self.calls += 1
            return result

    host = Host()
    wrapper = RecordingHost(host, tmp_path, "test")
    assert wrapper.generate(request) is result
    assert host.calls == wrapper.calls == 1
    assert (tmp_path / "test-001.json").is_file()


def test_existing_output_fails_before_any_host_or_checkpoint_read(tmp_path):
    import pytest

    with pytest.raises(RuntimeError, match="fresh directory"):
        run(tmp_path, Path("missing-checkpoint"))


def test_replay_is_deterministic_and_cannot_dispatch_hosts(tmp_path, monkeypatch):
    import json

    from mneme.development.episodes import declared_conversation_arcs
    from tools import run_arc_measurements as runner

    def forbidden(*args, **kwargs):
        raise AssertionError("replay constructed a provider host")

    for name in ("RemoteLlamaHost", "RemoteGlinerHost", "DeepInfraQwenAssessorHost"):
        monkeypatch.setattr(runner, name, forbidden)
    arc = declared_conversation_arcs(((12, "topic"),), conversation_id="test")[12]
    records = [
        {
            "conversation": "test",
            "condition": "F",
            "turn": 1,
            "ordinal": 12,
            "arc": arc.to_dict(),
            "residue": None,
            "field": None,
            "participant": "Hello",
            "response": "Hi",
        }
    ]
    source = tmp_path / "records.json"
    source.write_text(json.dumps(records))
    original = source.read_bytes()
    first = runner.replay(source, tmp_path / "first")
    second = runner.replay(source, tmp_path / "second")
    assert first == second
    assert first["provider_calls"] == 0
    assert source.read_bytes() == original
    for filename in ("matrix.json", "matrix.csv", "transcripts.md"):
        assert (tmp_path / "first" / filename).read_bytes() == (
            tmp_path / "second" / filename
        ).read_bytes()
