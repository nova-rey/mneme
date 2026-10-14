"""Durable mechanical preflight for the frozen MI4 Qwen bank experiment."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import GenerationBudget, MI1CoordinateRunner, ResolvedBank


def _request(url: str, value: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if value is None else json.dumps(value).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={} if data is None else {"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=1800) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError(f"expected JSON object from {url}")
    return decoded


def build_generation_request(
    *,
    messages: list[dict[str, str]],
    seed: int,
    thinking: bool,
    sampler: dict[str, Any],
) -> dict[str, Any]:
    """Build only frozen request settings; prompt text is supplied by protocol."""
    return {
        "messages": messages,
        "seed": seed,
        "temperature": sampler["temperature"],
        "top_k": sampler["top_k"],
        "top_p": sampler["top_p"],
        "min_p": sampler["min_p"],
        "max_tokens": sampler["max_tokens"],
        "cache_prompt": False,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }


def _messages(protocol: dict[str, Any], condition: str, user: str) -> list[dict[str, str]]:
    system = protocol["generation"]["system"]
    if condition == "visible_A_resilience":
        descriptor = protocol["neighborhoods"]["A_resilience"]["descriptor_text"]
        wrapper = protocol["calibration"]["visible_prompt_wrapper"]
        user = wrapper["prefix"] + descriptor + wrapper["suffix"] + user
    elif condition == "visible_B_simplicity":
        descriptor = protocol["neighborhoods"]["B_simplicity"]["descriptor_text"]
        wrapper = protocol["calibration"]["visible_prompt_wrapper"]
        user = wrapper["prefix"] + descriptor + wrapper["suffix"] + user
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def bank_lifecycle(
    *,
    base_url: str,
    bank_paths: dict[str, Path],
    output: Path,
) -> dict[str, Any]:
    """Prove all six variants attach/replace/disable/restore without generation."""
    url = base_url.rstrip("/") + "/mi1/bank"
    events: list[dict[str, Any]] = []
    fingerprints: dict[str, str] = {}
    before = _request(url)
    if before.get("enabled"):
        raise RuntimeError("bank lifecycle requires a disabled initial server")

    def apply(operation: str, key: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"operation": operation}
        if key is not None:
            body["path"] = str(bank_paths[key])
        response = _request(url, body)
        expected_enabled = operation in {"attach", "replace"}
        if response.get("enabled") is not expected_enabled:
            raise RuntimeError(f"{operation} returned unexpected enabled state")
        if key is not None:
            fingerprint = response.get("bank_fingerprint")
            if not isinstance(fingerprint, str) or len(fingerprint) != 16:
                raise RuntimeError(f"{operation} omitted the bank fingerprint")
            fingerprints[key] = fingerprint
        events.append({"operation": operation, "variant": key, "response": response})
        return response

    variants = tuple(bank_paths)
    for index, key in enumerate(variants):
        apply("attach" if index == 0 else "replace", key)
    apply("disable")
    disabled = _request(url)
    if disabled.get("enabled") is not False:
        raise RuntimeError("disabled bank state did not survive a GET")
    apply("attach", variants[0])
    apply("clear")
    cleared = _request(url)
    if cleared.get("enabled") is not False or cleared.get("bank_fingerprint"):
        raise RuntimeError("clear did not remove the active bank")
    receipt = {
        "schema_version": 1,
        "initial_state": before,
        "events": events,
        "final_state": cleared,
        "variant_fingerprints": fingerprints,
        "generation_calls": 0,
    }
    atomic_json_write(output, receipt)
    return receipt


def preflight(
    *,
    protocol_path: Path,
    selector_path: Path,
    bank_paths: dict[str, Path],
    bank_source_hashes: dict[str, str],
    bank_fingerprints: dict[str, str],
    output: Path,
    base_url: str,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    selector = json.loads(selector_path.read_text(encoding="utf-8"))
    sampler = protocol["generation"]["sampler"]
    if sampler["cache_prompt"] is not False:
        raise ValueError("frozen MI4 preflight requires cache_prompt=false")
    health = _request(base_url.rstrip("/") + "/health")
    initial_bank_state = _request(base_url.rstrip("/") + "/mi1/bank")
    if initial_bank_state.get("enabled"):
        raise RuntimeError("server must begin with no enabled MI4 bank")

    def resolve(source: str, _digest: str, config: dict[str, Any]) -> ResolvedBank:
        key = f"{source}__bias-{float(config['bias']):.1f}"
        path = bank_paths[key]
        return ResolvedBank(
            path=path,
            native_sha256=_sha256(path),
            bank_fingerprint=bank_fingerprints[key],
            selector_sha256=_sha256(selector_path),
            selector={"sites": selector["selected_query_sites"], "bias": config["bias"]},
        )

    journal = EvidenceJournal(output / "journal", hard_call_limit=24)
    budget = GenerationBudget(
        output / "budget.json", prior_calibration_calls=0, calibration_limit=24, hard_limit=24
    )
    runner = MI1CoordinateRunner(
        base_url=base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    prompt = protocol["calibration"]["prompts"][0]
    bank_for = {
        "no_bank": None,
        "visible_A_resilience": None,
        "visible_B_simplicity": None,
        "latent_A_resilience": "A_resilience",
        "latent_B_simplicity": "B_simplicity",
        "latent_irrelevant_visual_composition": "irrelevant_visual_composition",
    }
    outcomes: dict[str, dict[str, Any]] = {}
    started = time.time()
    attempt_count = 0
    for thinking_mode in (False, True):
        mode = "ON" if thinking_mode else "OFF"
        for condition, bank_name in bank_for.items():
            outputs: list[dict[str, str]] = []
            for repetition in (1, 2):
                attempt_count += 1
                coordinate_id = f"preflight_{mode.lower()}_{condition}_{repetition}"
                request = build_generation_request(
                    messages=_messages(protocol, condition, prompt["user"]),
                    seed=protocol["mechanical_preflight"]["seed"],
                    thinking=thinking_mode,
                    sampler=sampler,
                )
                coordinate = {
                    "coordinate_id": coordinate_id,
                    "request": request,
                    "metadata": {"server_role": "mi1_server"},
                    "bank_action": "clear" if bank_name is None else "attach",
                    "bank_source": bank_name,
                    "bank_source_sha256": None
                    if bank_name is None
                    else bank_source_hashes[bank_name],
                    "bank_config": {"bias": 0.5},
                }
                response = runner.execute(coordinate, phase="calibration")
                try:
                    outputs.append(_visible_output(response))
                except (KeyError, TypeError, ValueError) as exc:
                    atomic_json_write(
                        output / "preflight-failure.json",
                        {
                            "status": "FAILED_RESPONSE_VALIDATION",
                            "coordinate_id": coordinate_id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "completed_calls": attempt_count,
                            "journal_status_counts": journal.verify(),
                        },
                    )
                    raise
            equal = outputs[0] == outputs[1]
            outcomes[f"{mode}:{condition}"] = {
                "identical": equal,
                "output_hash": hashlib.sha256(
                    json.dumps(outputs[0], sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
                "reasoning_chars": len(outputs[0]["reasoning"]),
                "answer_chars": len(outputs[0]["answer"]),
            }
            if not equal:
                atomic_json_write(
                    output / "preflight-failure.json",
                    {
                        "status": "NONDETERMINISTIC_DUPLICATE",
                        "mode": mode,
                        "condition": condition,
                        "attempt_ids": [
                            f"preflight_{mode.lower()}_{condition}_1",
                            f"preflight_{mode.lower()}_{condition}_2",
                        ],
                        "output_hashes": [
                            hashlib.sha256(
                                json.dumps(
                                    item, sort_keys=True, ensure_ascii=False
                                ).encode("utf-8")
                            ).hexdigest()
                            for item in outputs
                        ],
                        "completed_calls": attempt_count,
                        "journal_status_counts": journal.verify(),
                    },
                )
                raise RuntimeError(f"same-condition duplicate differed: {mode}:{condition}")
    verification = journal.verify()
    if sum(verification.values()) != attempt_count or verification.get("COMPLETE") != 24:
        raise RuntimeError(f"preflight journal is incomplete: {verification}")
    result = {
        "schema_version": 1,
        "protocol_sha256": _sha256(protocol_path),
        "health": health,
        "initial_bank_state": initial_bank_state,
        "calls": attempt_count,
        "conditions": outcomes,
        "journal_status_counts": verification,
        "elapsed_seconds": round(time.time() - started, 3),
        "journal_path": str(output / "journal"),
        "interpretation": "Mechanical/reproducibility gate only; no semantic scores are assigned.",
    }
    atomic_json_write(output / "preflight-receipt.json", result)
    return result


def _visible_output(response: dict[str, Any]) -> dict[str, str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Qwen response has no choices")
    message = choices[0].get("message", {})
    reasoning = message.get("reasoning_content", message.get("reasoning", ""))
    answer = message.get("content", "")
    if not isinstance(reasoning, str) or not isinstance(answer, str):
        raise ValueError("Qwen reasoning/final content must be text")
    if not answer.strip():
        raise ValueError("Qwen returned no visible final answer")
    if choices[0].get("finish_reason") not in {"stop", "eos"}:
        raise ValueError(f"Qwen ended abnormally: {choices[0].get('finish_reason')!r}")
    return {"reasoning": reasoning, "answer": answer}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
