#!/usr/bin/env python3
"""Isolated reasoning-ON paired replay; frozen OFF inputs remain unmodified."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mneme.experiments.micro_stagnation import build_payload, parse_classification
from tools.run_micro_stagnation import Json, Transport, encode, post_json, response_reading

ALLOWED_CHANGES = {"reasoning_effort", "chat_template_kwargs", "reasoning_format", "max_tokens"}


def write_gzip(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(gzip.compress(encode(value), mtime=0))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def read_gzip(path: Path) -> Any:
    return json.loads(gzip.decompress(path.read_bytes()))


def reasoning_payload(call: Json, off: Json, on: Json) -> Json:
    """Derive unchanged prompt bytes from the qualified OFF serializer."""
    changed = {key for key in off.keys() | on.keys() if off.get(key) != on.get(key)}
    if changed != ALLOWED_CHANGES:
        raise ValueError("only the four declared reasoning/budget controls may change")
    if ("reasoning_effort" in on
            or on.get("chat_template_kwargs") != {"enable_thinking": True}
            or on.get("reasoning_format") != "deepseek"
            or type(on.get("max_tokens")) is not int or on["max_tokens"] != 2048):
        raise ValueError("explicit native reasoning and adequate output budget required")
    payload = build_payload(call["exchanges"], call["system"], off)
    payload.pop("reasoning_effort")
    return {**payload, **{key: on[key] for key in ALLOWED_CHANGES if key in on}}


def preprocess(endpoint: str, payload: Json, transport: Transport) -> Json:
    base = endpoint.split("/v1/")[0]
    template = transport(base + "/apply-template", {
        "messages": payload["messages"], "add_generation_prompt": True,
        "chat_template_kwargs": payload["chat_template_kwargs"],
    })
    prompt = template.get("prompt")
    if not isinstance(prompt, str):
        raise ValueError("native template did not return prompt")
    tokenized = transport(base + "/tokenize", {"content": prompt, "add_special": False})
    tokens = tokenized.get("tokens")
    if not isinstance(tokens, list):
        raise ValueError("native tokenizer did not return token list")
    return {"prompt": prompt, "tokens": tokens, "prompt_tokens": len(tokens),
            "template_response": template}


def reading(response: Json, allowed: list[int], elapsed: float) -> Json:
    result = response_reading(response, allowed, elapsed)
    choices = response.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    reasoning = message.get("reasoning_content") if isinstance(message, dict) else None
    usage = response.get("usage", {})
    details = usage.get("completion_tokens_details", {}) if isinstance(usage, dict) else {}
    count = details.get("reasoning_tokens") if isinstance(details, dict) else None
    timing = response.get("timings", {})
    return {**result, "reasoning_content": reasoning,
            "reasoning_observed": isinstance(reasoning, str) and bool(reasoning.strip()),
            "reasoning_tokens": count,
            "cache_n": timing.get("cache_n") if isinstance(timing, dict) else None}


def validate_reading(row: Json, previous: Json | None) -> None:
    if row.get("model_called") is not True:
        raise RuntimeError("INVALID: complete window and output budget exceed context")
    if row.get("cache_n") not in (None, 0):
        raise RuntimeError("INVALID: provider reported prompt-cache reuse")
    if not row.get("reasoning_observed"):
        raise RuntimeError("INVALID: native separated reasoning was not observed")
    if row.get("finish_reason") != "stop":
        raise RuntimeError("INVALID: truncated or abnormal completion")
    if previous is not None and previous["request_sha256"] == row["request_sha256"] and any(
        previous.get(key) != row.get(key)
        for key in ("reasoning_content", "content", "finish_reason")
    ):
        raise RuntimeError(
            "INVALID: identical duplicate changed reasoning, final content or finish")


def run(manifest: Json, off: Json, on: Json, output: Path, *,
        transport: Transport = post_json,
        clock: Callable[[], float] = time.perf_counter) -> list[Json]:
    calls = manifest.get("calls")
    if (not isinstance(calls, list) or not 2 <= len(calls) <= 128 or len(calls) % 2
            or manifest.get("paired_replay", True) is not True):
        raise ValueError("manifest requires 2..128 adjacent paired calls")
    endpoint = on["endpoint"]
    if not isinstance(endpoint, str) or not endpoint.endswith("/v1/chat/completions"):
        raise ValueError("explicit resident endpoint required")
    limit, reserve = on["context_tokens"], on["context_reserve_tokens"]
    if type(limit) is not int or type(reserve) is not int or reserve < 1 or limit <= reserve:
        raise ValueError("explicit context limit and positive reserve required")
    prepared = []
    seen = set()
    for call in calls:
        identity = call["id"]
        if (not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", identity)
                or identity in seen):
            raise ValueError("unsafe or duplicate call identity")
        seen.add(identity)
        parse_classification("", "stop", call["allowed_values"])
        prepared.append((call, reasoning_payload(call, off, on)))
    if any(encode(prepared[i][1]) != encode(prepared[i + 1][1])
           for i in range(0, len(prepared), 2)):
        raise ValueError("manifest requires adjacent identical payload pairs")
    frozen = {"manifest": manifest, "off_config": off, "on_config": on,
              "requests": [{"id": call["id"], "payload": payload} for call, payload in prepared]}
    path = output / "frozen_execution.json.gz"
    if path.exists() and read_gzip(path) != frozen:
        raise ValueError("output belongs to different frozen execution")
    write_gzip(path, frozen)
    rows: list[Json] = []
    previous: Json | None = None
    for call, payload in prepared:
        directory = output / "calls" / call["id"]
        receipt = directory / "receipt.json.gz"
        pending = directory / "pending.json.gz"
        if receipt.exists():
            row = read_gzip(receipt)
        else:
            if pending.exists():
                raise RuntimeError(f"uncertain prior attempt at {call['id']}; no automatic retry")
            start = clock()
            context = preprocess(endpoint, payload, transport)
            preprocessing_seconds = clock() - start
            write_gzip(directory / "context.json.gz", context)
            write_gzip(directory / "request.json.gz", payload)
            row = {key: value for key, value in call.items() if key not in {"exchanges", "system"}}
            row.update(request_sha256=hashlib.sha256(encode(payload)).hexdigest(),
                       preprocessing_seconds=preprocessing_seconds,
                       native_prompt_tokens=context["prompt_tokens"])
            if context["prompt_tokens"] + payload["max_tokens"] + reserve > limit:
                row.update(available=False, value=None, model_called=False,
                           unavailable_reason="complete window and output budget exceed context")
            else:
                write_gzip(pending, {"id": call["id"], "request_sha256": row["request_sha256"],
                                    "status": "pending_or_uncertain"})
                started = clock()
                response = transport(endpoint, payload)
                elapsed = clock() - started
                write_gzip(directory / "response.json.gz", response)
                row.update(reading(response, call["allowed_values"], elapsed), model_called=True)
            row["observation_wall_seconds"] = clock() - start
            write_gzip(receipt, row)
        rows.append(row)
        write_gzip(output / "readings.json.gz", rows)
        validate_reading(row, previous)
        previous = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "off-config", "on-config", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    run(json.loads(args.manifest.read_text()), json.loads(args.off_config.read_text()),
        json.loads(args.on_config.read_text()), args.output)


if __name__ == "__main__":
    main()
