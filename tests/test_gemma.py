import json
import urllib.error

import pytest

from mneme.contracts import GenerationRequest, HostError
from mneme.hosts.gemma import GemmaHost, _parse_response


def test_gemma_does_not_claim_unverified_structured_output():
    host = GemmaHost()
    assert "structured_output" not in host.capabilities().to_dict()
    assert host.fingerprint().chat_template == "mneme_fallback_transcript_v1"
    assert host.fingerprint().execution["rendering_mode"] == "mneme_fallback_transcript_v1"


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("https://example.test", 503, "unavailable", {}, None),
        urllib.error.URLError("offline"),
        TimeoutError("timed out"),
    ],
)
def test_provider_transport_failures_map_to_host_error(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(HostError):
        GemmaHost(token="test-token").generate(
            GenerationRequest(({"role": "user", "content": "hi"},))
        )


def test_malformed_provider_json_maps_to_host_error(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"not-json"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(HostError):
        GemmaHost(token="test-token").generate(
            GenerationRequest(({"role": "user", "content": "hi"},))
        )


def test_provider_declared_error_and_shape_map_to_host_error():
    with pytest.raises(HostError):
        _parse_response({"error": "model unavailable"})
    with pytest.raises(HostError):
        _parse_response(["unexpected"])


def test_provider_success_shape_is_provider_neutral():
    content, metadata = _parse_response([{"generated_text": "hello", "details": {}}])
    assert content == "hello"
    assert json.dumps(metadata)
