from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from experiments.mi1.native.evidence import EvidenceJournal
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
    load_completed_response,
)


def _coordinate(*, action: str = "attach", cache_prompt: bool = False) -> dict[str, Any]:
    bank = "- Ralo activates Sivi.\n- Sivi releases Teka."
    import hashlib

    return {
        "coordinate_id": "A-fixture-latent-34001",
        "suite": "test_a",
        "metadata": {"seed": 34001},
        "request": {
            "model": "gemma4",
            "messages": [
                {"role": "system", "content": "Only use supplied rules."},
                {"role": "user", "content": "Can Teka become active?"},
            ],
            "stream": False,
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


def test_runner_persists_exact_request_and_raw_output_in_order(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def transport(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((url, payload))
        if url.endswith("/mi1/bank"):
            return {"revision": 4, "enabled": True}
        if url.endswith("/apply-template"):
            return {"prompt": "<bos>exact rendered prompt"}
        return {
            "choices": [
                {
                    "message": {
                        "reasoning_content": "Ralo reaches Teka through Sivi.",
                        "content": "Teka; path Ralo -> Sivi -> Teka.",
                    },
                    "finish_reason": "stop",
                }
            ]
        }

    journal = EvidenceJournal(tmp_path / "journal", hard_call_limit=800)
    budget = GenerationBudget(tmp_path / "budget.json")
    runner = MI1CoordinateRunner(
        base_url="http://localhost:64171",
        journal=journal,
        budget=budget,
        bank_resolver=lambda _text, digest: ResolvedBank(
            Path("/host/banks") / f"{digest}.mi1",
            "a" * 64,
            "b" * 64,
            {"selected_layers": [3, 7, 11, 19]},
        ),
        transport=transport,
    )
    response = runner.execute(_coordinate(), phase="calibration")
    assert response["choices"][0]["finish_reason"] == "stop"
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == [
        "bank",
        "apply-template",
        "completions",
    ]
    assert calls[-1][1]["cache_prompt"] is False
    request_path = tmp_path / "journal/attempts/A-fixture-latent-34001.request.json"
    request = json.loads(request_path.read_text())
    assert request["request"]["model_visible_prompt"] == "<bos>exact rendered prompt"
    assert request["request"]["model_visible_prompt_sha256"]
    assert request["metadata"]["bank_state"]["response"]["revision"] == 4
    assert request["metadata"]["bank_state"]["artifact"]["native_sha256"] == "a" * 64
    durable = load_completed_response(tmp_path / "journal", "A-fixture-latent-34001")
    assert durable == response
    assert journal.verify() == {"COMPLETE": 1}
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
        bank_resolver=lambda _text, _digest: ResolvedBank(
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
        calls += 1
        raise OSError("simulated disconnect")

    journal = EvidenceJournal(tmp_path / "journal")
    runner = MI1CoordinateRunner(
        base_url="http://localhost:64171",
        journal=journal,
        budget=GenerationBudget(tmp_path / "budget.json"),
        bank_resolver=lambda _text, _digest: ResolvedBank(
            Path("/host/bank.mi1"), "a" * 64, "b" * 64, {"selected_layers": [2]}
        ),
        transport=transport,
    )
    with pytest.raises(OSError, match="simulated disconnect"):
        runner.execute(_coordinate(), phase="scored")
    assert calls == 1
    assert journal.verify() == {"FAILED": 1}
    assert GenerationBudget(tmp_path / "budget.json").counts()["scored"] == 1
