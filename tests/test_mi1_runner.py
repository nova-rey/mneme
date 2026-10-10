from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from experiments.mi1.native.evidence import EvidenceJournal
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
    http_sse,
    load_completed_response,
)


def _coordinate(
    *, action: str = "attach", cache_prompt: bool = False, server_role: str = "mi1_server"
) -> dict[str, Any]:
    bank = "- Ralo activates Sivi.\n- Sivi releases Teka."
    import hashlib

    return {
        "coordinate_id": "A-fixture-latent-34001",
        "suite": "test_a",
        "metadata": {"seed": 34001, "server_role": server_role},
        "request": {
            "model": "gemma4",
            "messages": [
                {"role": "system", "content": "Only use supplied rules."},
                {"role": "user", "content": "Can Teka become active?"},
            ],
            "stream": True,
            "cache_prompt": cache_prompt,
            "seed": 34001,
            "max_tokens": 2048,
            "chat_template_kwargs": {"enable_thinking": True},
            "temperature": 0.35,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
        },
        "bank_source": bank if action != "clear" else None,
        "bank_source_sha256": hashlib.sha256(bank.encode()).hexdigest()
        if action != "clear"
        else None,
        "bank_action": action,
        "expected": {"answer": "Teka"},
    }


def _sse_event(value: dict[str, Any]) -> bytes:
    return b"data: " + json.dumps(value, separators=(",", ":")).encode() + b"\n\n"


def test_runner_persists_exact_request_and_raw_output_in_order(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    bank_configs: list[dict[str, Any]] = []

    def resolve_bank(text: str, digest: str, config: dict[str, Any]) -> ResolvedBank:
        bank_configs.append(config)
        return ResolvedBank(
            Path("/host/banks") / f"{digest}.mi1",
            "a" * 64,
            "b" * 64,
            {"selected_layers": [3, 7, 11, 19]},
        )

    def transport(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((url, payload))
        if url.endswith("/mi1/bank"):
            return {"revision": 4, "enabled": True}
        if url.endswith("/apply-template"):
            return {"prompt": "<bos>exact rendered prompt"}
        raise AssertionError(f"unexpected non-stream request: {url}")

    def stream_transport(url: str, payload: dict[str, Any], sink: Any) -> dict[str, Any]:
        calls.append((url, payload))
        sink(
            _sse_event(
                {
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"reasoning_content": "Ralo reaches Teka through Sivi."},
                        }
                    ]
                }
            )
        )
        sink(
            _sse_event(
                {
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "Teka; path Ralo -> Sivi -> Teka."},
                            "finish_reason": "stop",
                        }
                    ]
                }
            )
        )
        sink(b"data: [DONE]\n\n")
        return {
            "choices": [
                {
                    "message": {
                        "reasoning_content": "Ralo reaches Teka through Sivi.",
                        "content": "Teka; path Ralo -> Sivi -> Teka.",
                        "role": "assistant",
                    },
                    "finish_reason": "stop",
                    "index": 0,
                }
            ]
        }

    journal = EvidenceJournal(tmp_path / "journal", hard_call_limit=800)
    budget = GenerationBudget(tmp_path / "budget.json")
    runner = MI1CoordinateRunner(
        base_url="http://localhost:64171",
        journal=journal,
        budget=budget,
        bank_resolver=resolve_bank,
        transport=transport,
        stream_transport=stream_transport,
    )
    coordinate = _coordinate()
    coordinate["bank_config"] = {"selector": "sparse", "gain": {"logit_bias": 0.0}}
    response = runner.execute(coordinate, phase="calibration")
    assert bank_configs == [coordinate["bank_config"]]
    assert response["choices"][0]["finish_reason"] == "stop"
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == [
        "bank",
        "apply-template",
        "completions",
    ]
    assert calls[-1][1]["cache_prompt"] is False
    assert "model_visible_prompt" not in calls[-1][1]
    request_path = tmp_path / "journal/attempts/A-fixture-latent-34001.request.json"
    request = json.loads(request_path.read_text())
    assert request["request"]["model_visible_prompt"] == "<bos>exact rendered prompt"
    assert request["request"]["model_visible_prompt_sha256"]
    assert request["metadata"]["bank_state"]["response"]["revision"] == 4
    assert request["metadata"]["bank_state"]["artifact"]["native_sha256"] == "a" * 64
    durable = load_completed_response(tmp_path / "journal", "A-fixture-latent-34001")
    assert durable == response
    assert journal.verify() == {"COMPLETE": 1}
    stream_path = tmp_path / "journal/attempts/A-fixture-latent-34001.stream.jsonl"
    stream_rows = [json.loads(line) for line in stream_path.read_text().splitlines()]
    assert len(stream_rows) == 3
    raw_event = base64.b64decode(stream_rows[0]["raw_event_base64"], validate=True)
    assert b"reasoning_content" in raw_event
    assert budget.counts() == {"total": 9, "calibration": 9, "scored": 0, "confirmation": 0}


def test_runner_rejects_prompt_cache_before_generation(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(url)
        if url.endswith("/mi1/bank"):
            return {"revision": 1, "enabled": True}
        return {"prompt": "rendered"}

    runner = MI1CoordinateRunner(
        base_url="http://localhost:64171",
        journal=EvidenceJournal(tmp_path / "journal"),
        budget=GenerationBudget(tmp_path / "budget.json"),
        bank_resolver=lambda _text, _digest, _config: ResolvedBank(
            Path("/host/bank.mi1"), "a" * 64, "b" * 64, {"selected_layers": [2]}
        ),
        transport=transport,
    )
    with pytest.raises(ValueError, match="cache_prompt=false"):
        runner.execute(_coordinate(cache_prompt=True), phase="scored")
    assert not any(url.endswith("/v1/chat/completions") for url in calls)


def test_budget_includes_prior_calibration_and_fails_closed(tmp_path: Path) -> None:
    budget = GenerationBudget(
        tmp_path / "budget.json", prior_calibration_calls=119, calibration_limit=120, hard_limit=800
    )
    budget.reserve("last-calibration", "calibration")
    with pytest.raises(RuntimeError, match="calibration generation ceiling"):
        budget.reserve("over-calibration", "calibration")
    budget.reserve("scored-1", "scored")
    assert budget.counts() == {"total": 121, "calibration": 120, "scored": 1, "confirmation": 0}


def test_budget_does_not_allow_unknown_ids_or_duplicate_reservations(tmp_path: Path) -> None:
    budget = GenerationBudget(tmp_path / "budget.json")
    with pytest.raises(ValueError, match="phase must"):
        budget.reserve("bad-phase", "debug")
    budget.reserve("once", "scored")
    with pytest.raises(FileExistsError, match="already reserved"):
        budget.reserve("once", "scored")


def test_runner_stores_http_failure_and_does_not_retry(tmp_path: Path) -> None:
    calls = 0

    def transport(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        if url.endswith("/mi1/bank"):
            return {"revision": 1, "enabled": True}
        if url.endswith("/apply-template"):
            return {"prompt": "rendered"}
        return {}

    def stream_transport(_url: str, _payload: dict[str, Any], _sink: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise OSError("simulated disconnect")

    journal = EvidenceJournal(tmp_path / "journal")
    runner = MI1CoordinateRunner(
        base_url="http://localhost:64171",
        journal=journal,
        budget=GenerationBudget(tmp_path / "budget.json"),
        bank_resolver=lambda _text, _digest, _config: ResolvedBank(
            Path("/host/bank.mi1"), "a" * 64, "b" * 64, {"selected_layers": [2]}
        ),
        transport=transport,
        stream_transport=stream_transport,
    )
    with pytest.raises(OSError, match="simulated disconnect"):
        runner.execute(_coordinate(), phase="scored")
    assert calls == 1
    assert journal.verify() == {"FAILED": 1}
    assert GenerationBudget(tmp_path / "budget.json").counts()["scored"] == 1


def test_runner_preserves_partial_stream_after_disconnect(tmp_path: Path) -> None:
    event = _sse_event(
        {"choices": [{"index": 0, "delta": {"reasoning_content": "partial reasoning"}}]}
    )

    def transport(url: str, _payload: dict[str, Any]) -> dict[str, Any]:
        if url.endswith("/mi1/bank"):
            return {"revision": 1, "enabled": True}
        return {"prompt": "rendered"}

    def stream_transport(_url: str, _payload: dict[str, Any], sink: Any) -> dict[str, Any]:
        sink(event)
        raise OSError("disconnect after one chunk")

    journal = EvidenceJournal(tmp_path / "journal")
    runner = MI1CoordinateRunner(
        base_url="http://localhost:64171",
        journal=journal,
        budget=GenerationBudget(tmp_path / "budget.json"),
        bank_resolver=lambda _text, _digest, _config: ResolvedBank(
            Path("/host/bank.mi1"), "a" * 64, "b" * 64, {"selected_layers": [2]}
        ),
        transport=transport,
        stream_transport=stream_transport,
    )
    with pytest.raises(OSError, match="disconnect after one chunk"):
        runner.execute(_coordinate(), phase="scored")
    stream_path = tmp_path / "journal/attempts/A-fixture-latent-34001.stream.jsonl"
    row = json.loads(stream_path.read_text())
    assert base64.b64decode(row["raw_event_base64"], validate=True) == event
    outcome = json.loads(
        (tmp_path / "journal/attempts/A-fixture-latent-34001.failed.json").read_text()
    )
    assert outcome["metadata"]["stream"]["stream_event_count"] == 1
    assert journal.verify() == {"FAILED": 1}
    assert EvidenceJournal(tmp_path / "journal").verify() == {"FAILED": 1}


def test_http_sse_reconstructs_channels_and_persists_raw_events(monkeypatch: Any) -> None:
    events = [
        _sse_event(
            {
                "id": "r1",
                "choices": [
                    {"index": 0, "delta": {"reasoning_content": "considering "}}
                ],
            }
        ),
        _sse_event(
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {"reasoning_content": "it", "content": "answer"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"completion_tokens": 3},
            }
        ),
        b"data: [DONE]\n\n",
    ]

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> Any:
            raw = b"".join(events)
            return iter(raw.splitlines(keepends=True))

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        assert request.full_url == "http://localhost/v1/chat/completions"
        assert timeout == 1800
        assert json.loads(request.data)["stream"] is True
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    captured: list[bytes] = []

    def store_event(event: bytes) -> int:
        captured.append(event)
        return len(captured)

    response = http_sse(
        "http://localhost/v1/chat/completions", {"stream": True},
        store_event,
    )
    assert captured == events
    message = response["choices"][0]["message"]
    assert message["reasoning_content"] == "considering it"
    assert message["content"] == "answer"
    assert response["usage"] == {"completion_tokens": 3}
    assert response["choices"][0]["finish_reason"] == "stop"


def test_base_server_replay_skips_mi1_bank_endpoint(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(url)
        if url.endswith("/apply-template"):
            return {"prompt": "same exact rendered prompt"}
        raise AssertionError(f"base server must not receive MI1 endpoint: {url}")

    def stream_transport(url: str, _payload: dict[str, Any], sink: Any) -> dict[str, Any]:
        calls.append(url)
        sink(
            _sse_event(
                {
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "unknown"},
                            "finish_reason": "stop",
                        }
                    ]
                }
            )
        )
        sink(b"data: [DONE]\n\n")
        return {"choices": [{"message": {"content": "unknown"}, "finish_reason": "stop"}]}

    runner = MI1CoordinateRunner(
        base_url="http://mi1:64171",
        base_server_url="http://base:64172",
        journal=EvidenceJournal(tmp_path / "journal"),
        budget=GenerationBudget(tmp_path / "budget.json"),
        bank_resolver=lambda *_args: pytest.fail("base server must not resolve a bank"),
        transport=transport,
        stream_transport=stream_transport,
    )
    coordinate = _coordinate(action="clear", server_role="base_server")
    response = runner.execute(coordinate, phase="calibration")
    assert response["choices"][0]["message"]["content"] == "unknown"
    assert calls == ["http://base:64172/apply-template", "http://base:64172/v1/chat/completions"]
    stored = json.loads(
        (tmp_path / "journal/attempts/A-fixture-latent-34001.request.json").read_text()
    )
    assert stored["metadata"]["bank_state"]["status"] == "not_applicable_base_server"


def test_base_server_rejects_mi1_bank_before_call(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(url: str, _payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(url)
        return {}

    runner = MI1CoordinateRunner(
        base_url="http://mi1:64171",
        base_server_url="http://base:64172",
        journal=EvidenceJournal(tmp_path / "journal"),
        budget=GenerationBudget(tmp_path / "budget.json"),
        bank_resolver=lambda *_args: pytest.fail("base server must not resolve a bank"),
        transport=transport,
    )
    coordinate = _coordinate(server_role="base_server")
    with pytest.raises(ValueError, match="must not attach an MI1 bank"):
        runner.execute(coordinate, phase="calibration")
    assert calls == []
