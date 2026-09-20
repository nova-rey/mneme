import json
import urllib.error

import pytest

from mneme.contracts import Capability, GenerationRequest, HostError
from mneme.hosts.deepinfra import DeepInfraGemmaHost, DeepInfraQwenAssessorHost, _parse_response


def request() -> GenerationRequest:
    return GenerationRequest(
        ({"role": "system", "content": "Be concise."}, {"role": "user", "content": "Hello"}),
        parameters={"temperature": 0.2, "max_new_tokens": 12},
        run_metadata={"instance_id": "admin-only", "run_id": "run-only"},
    )


def test_deepinfra_capabilities_and_fingerprint():
    host = DeepInfraGemmaHost()
    assert host.capabilities().supported == {Capability.TEXT_GENERATION, Capability.TOKEN_USAGE}
    fingerprint = host.fingerprint().to_dict()
    assert fingerprint["model_id"] == "google/gemma-4-E4B-it"
    assert fingerprint["model_revision"] is None
    assert fingerprint["execution"]["canonical_upstream_model"] == "google/gemma-4-E4B-it"
    assert fingerprint["chat_template"] == "deepinfra_openai_chat"
    assert "admin-only" not in json.dumps(fingerprint)


def test_qwen_assessor_fingerprint_is_not_gemma_metadata():
    fingerprint = DeepInfraQwenAssessorHost().fingerprint().to_dict()
    assert fingerprint["model_id"] == "Qwen/Qwen3-235B-A22B-Instruct-2507"
    assert fingerprint["model_family"] == "Qwen3 235B A22B Instruct 2507"
    assert fingerprint["tokenizer_id"] is None
    assert fingerprint["tokenizer_revision"] is None
    assert fingerprint["model_revision"] is None
    assert fingerprint["execution"]["canonical_upstream_model"] == (
        "Qwen/Qwen3-235B-A22B-Instruct-2507"
    )
    assert fingerprint["execution"]["hosted_model_revision"] == "unknown"
    assert "Gemma" not in json.dumps(fingerprint)
    assert "ee0ef6023621cff504d758262d4e04895a5af4a2" not in json.dumps(fingerprint)


def test_request_uses_structured_messages_and_bearer_without_leak(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
                }
            ).encode()

    def fake_urlopen(req, timeout):
        captured["request"] = req
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = DeepInfraGemmaHost(token="secret-token").generate(request())
    body = json.loads(captured["request"].data)
    assert body["messages"][0]["role"] == "system"
    assert body["max_tokens"] == 12
    assert "max_new_tokens" not in body
    assert "admin-only" not in captured["request"].data.decode()
    assert captured["request"].get_header("Authorization") == "Bearer secret-token"
    assert "secret-token" not in json.dumps(result.to_dict())
    assert result.token_usage.total_tokens == 4
    assert result.finish_reason == "stop"


def test_request_system_field_is_rendered_once(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"hi"}}]}'

    def fake_urlopen(req, timeout):
        captured["request"] = req
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    DeepInfraGemmaHost(token="secret-token").generate(
        GenerationRequest(
            ({"role": "user", "content": "Hello"},),
            system="Controller instructions.",
        )
    )
    body = json.loads(captured["request"].data)
    assert body["messages"] == [
        {"role": "system", "content": "Controller instructions."},
        {"role": "user", "content": "Hello"},
    ]


def test_request_system_field_deduplicates_legacy_message(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"hi"}}]}'

    def fake_urlopen(req, timeout):
        captured["request"] = req
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    DeepInfraGemmaHost(token="secret-token").generate(
        GenerationRequest(
            (
                {"role": "system", "content": "Controller instructions."},
                {"role": "system", "content": "Controller instructions."},
                {"role": "user", "content": "Hello"},
            ),
            system="Controller instructions.",
        )
    )
    body = json.loads(captured["request"].data)
    assert body["messages"].count(
        {"role": "system", "content": "Controller instructions."}
    ) == 1


def test_message_only_request_remains_unchanged(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"hi"}}]}'

    def fake_urlopen(req, timeout):
        captured["request"] = req
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    messages = (
        {"role": "system", "content": "Message-only system."},
        {"role": "user", "content": "Hello"},
    )
    DeepInfraGemmaHost(token="secret-token").generate(GenerationRequest(messages))
    body = json.loads(captured["request"].data)
    assert body["messages"] == list(messages)


def test_unsupported_response_format_is_rejected_before_transport(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("unsupported request reached transport")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(HostError, match="response_format"):
        DeepInfraGemmaHost(token="secret-token").generate(
            GenerationRequest(
                ({"role": "user", "content": "Return JSON."},),
                response_format={"type": "json_schema"},
            )
        )


def test_deepinfra_missing_token_and_seed_fail_closed():
    with pytest.raises(HostError, match="DEEPINFRA_TOKEN"):
        DeepInfraGemmaHost(token=None).generate(request())
    with pytest.raises(HostError, match="seed"):
        DeepInfraGemmaHost(token="x").generate(GenerationRequest(request().messages, seed=1))


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("https://example.test", 402, "payment", {}, None),
        urllib.error.URLError("offline"),
        TimeoutError("timed out"),
    ],
)
def test_deepinfra_transport_errors_map_to_host_error(monkeypatch, failure):
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(failure)
    )
    with pytest.raises(HostError):
        DeepInfraGemmaHost(token="x").generate(request())


def test_deepinfra_malformed_and_provider_errors_map_to_host_error(monkeypatch):
    class BadResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"bad-json"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: BadResponse())
    with pytest.raises(HostError):
        DeepInfraGemmaHost(token="x").generate(request())
    with pytest.raises(HostError):
        _parse_response({"error": {"message": "quota"}})
    with pytest.raises(HostError):
        _parse_response({"choices": []})
