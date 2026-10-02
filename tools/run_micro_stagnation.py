#!/usr/bin/env python3
"""Serial, explicit diagnostic calls with durable no-retry attempt records.

No conversation generation, MNEME state, learner, SAA or extraction path is
imported. The manifest is frozen externally before invoking this recorder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from mneme.experiments.micro_stagnation import build_payload, parse_classification

Json = dict[str, Any]
Transport = Callable[[str, Json], Json]


def encode(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def write_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(encode(value))
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def post_json(url: str, payload: Json) -> Json:
    request = urllib.request.Request(url, data=encode(payload),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("provider did not return a JSON object")
    return decoded


def native_preprocess(endpoint: str, payload: Json, transport: Transport) -> Json:
    base = endpoint.split("/v1/")[0]
    template = transport(base + "/apply-template", {
        "messages": payload["messages"], "add_generation_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
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


def response_reading(response: Json, allowed: list[int], elapsed: float) -> Json:
    choices = response.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    finish = choice.get("finish_reason") if isinstance(choice, dict) else None
    usage = response.get("usage")
    timing = response.get("timings")
    usage = usage if isinstance(usage, Mapping) else {}
    timing = timing if isinstance(timing, Mapping) else {}
    return {**parse_classification(content, finish, allowed), "content": content,
            "finish_reason": finish, "wall_seconds": elapsed,
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "prefill_ms": timing.get("prompt_ms"), "generation_ms": timing.get("predicted_ms")}


def run(manifest: Json, config: Json, output: Path, *,
        transport: Transport = post_json,
        clock: Callable[[], float] = time.perf_counter) -> list[Json]:
    """Resume only completed attempts; an uncertain attempt always halts.

    Native sizing is model-free. Oversized five-exchange windows are unavailable,
    never clipped. Wall time covers the generation HTTP call; preprocessing time
    is recorded separately and is not relabeled as native model prefill time.
    """
    calls = manifest.get("calls")
    if not isinstance(calls, list) or not 1 <= len(calls) <= 128:
        raise ValueError("manifest requires 1..128 ordered calls")
    endpoint = config["endpoint"]
    if not isinstance(endpoint, str) or not endpoint.endswith("/v1/chat/completions"):
        raise ValueError("explicit resident chat-completion endpoint required")
    limit = config["context_tokens"]
    reserve = config["context_reserve_tokens"]
    if type(limit) is not int or type(reserve) is not int or limit <= 8 or reserve < 1:
        raise ValueError("explicit context limit and positive token reserve required")
    prepared = []
    seen = set()
    for call in calls:
        call_id = call["id"]
        if not isinstance(call_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", call_id):
            raise ValueError("unsafe call identity")
        if call_id in seen:
            raise ValueError("duplicate call identity")
        seen.add(call_id)
        parse_classification("", "stop", call["allowed_values"])
        prepared.append((call, build_payload(call["exchanges"], call["system"], config)))
    # Each independent coordinate is tested twice consecutively, beginning with
    # the resident-operation duplicate qualification before further work.
    paired_replay = manifest.get("paired_replay", True)
    if type(paired_replay) is not bool:
        raise ValueError("paired_replay must be boolean")
    if paired_replay and (len(prepared) % 2 or any(
        encode(prepared[i][1]) != encode(prepared[i + 1][1])
        for i in range(0, len(prepared), 2)
    )):
        raise ValueError("manifest requires adjacent identical payload pairs")
    frozen = {"manifest": manifest, "config": config}
    frozen_path = output / "frozen_execution.json"
    if frozen_path.exists() and frozen_path.read_bytes() != encode(frozen):
        raise ValueError("output directory belongs to different frozen execution")
    write_atomic(frozen_path, frozen)
    readings = []
    previous: Json | None = None
    for call, payload in prepared:
        directory = output / "calls" / call["id"]
        receipt = directory / "receipt.json"
        pending = directory / "pending.json"
        if receipt.exists():
            retained = json.loads(receipt.read_text())
            check_duplicate(previous, retained)
            previous = retained
            readings.append(retained)
            continue
        if pending.exists():
            raise RuntimeError(f"uncertain prior attempt at {call['id']}; no automatic retry")
        start = clock()
        context = native_preprocess(endpoint, payload, transport)
        preprocessing_seconds = clock() - start
        write_atomic(directory / "context.json", context)
        write_atomic(directory / "request.json", payload)
        metadata = {key: value for key, value in call.items()
                    if key not in {"exchanges", "system"}}
        row = {**metadata, "request_sha256": hashlib.sha256(encode(payload)).hexdigest(),
               "preprocessing_seconds": preprocessing_seconds,
               "native_prompt_tokens": context["prompt_tokens"]}
        if context["prompt_tokens"] + 8 + reserve > limit:
            row.update(available=False, value=None,
                       unavailable_reason="complete five-exchange window exceeds context budget",
                       model_called=False, observation_wall_seconds=clock() - start)
        else:
            write_atomic(pending, {"id": call["id"], "request_sha256": row["request_sha256"],
                                   "status": "pending_or_uncertain"})
            started = clock()
            response = transport(endpoint, payload)
            elapsed = clock() - started
            # Store the untouched provider reply before deriving any reading.
            write_atomic(directory / "response.json", response)
            row.update(response_reading(response, call["allowed_values"], elapsed),
                       model_called=True, observation_wall_seconds=clock() - start)
        write_atomic(receipt, row)
        readings.append(row)
        # Save both replies before stopping on a reproducibility contradiction.
        check_duplicate(previous, row)
        previous = row
    write_atomic(output / "readings.json", readings)
    return readings


def check_duplicate(previous: Json | None, current: Json) -> None:
    if previous is None or previous["request_sha256"] != current["request_sha256"]:
        return
    if previous.get("model_called") and current.get("model_called") and any(
        previous.get(key) != current.get(key) for key in ("content", "finish_reason")
    ):
        raise RuntimeError("identical payload duplicate changed content or finish reason; stop")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(json.loads(args.manifest.read_text()), json.loads(args.config.read_text()), args.output)


if __name__ == "__main__":
    main()
