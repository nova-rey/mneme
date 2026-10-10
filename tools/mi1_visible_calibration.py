"""Separate visible-text task-comprehension calibration for MI1.

This is intentionally independent of the frozen scored fixtures. It runs a
small answer-keyed rule task with the bank shown in ordinary prompt text and
persists every request/result after each call.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

MODEL = "/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf"
MODEL_SHA256 = "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"
LLAMA_SERVER = "/home/rey/src/llama.cpp/build-cuda/bin/llama-server"
LLAMA_COMMIT = "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0"
SEEDS = (34031, 34037)
SAMPLER = {"temperature": 0.35, "top_k": 40, "top_p": 0.90, "min_p": 0.05}

CASES = (
    {
        "id": "CAL-VISIBLE-01",
        "nodes": ("Zepi", "Moru", "Kadi", "Velo", "Runi"),
        "rules": (
            "Zepi activates Moru.",
            "Moru activates Kadi.",
            "Kadi activates Velo.",
            "Velo activates Runi.",
        ),
        "start": "Zepi",
        "target": "Runi",
        "path": ("Zepi", "Moru", "Kadi", "Velo", "Runi"),
    },
    {
        "id": "CAL-VISIBLE-02",
        "nodes": ("Heku", "Pali", "Dovo", "Senu", "Xari"),
        "rules": (
            "Heku activates Pali.",
            "Pali activates Dovo.",
            "Dovo activates Senu.",
            "Xari activates Heku.",
        ),
        "start": "Heku",
        "target": "Senu",
        "path": ("Heku", "Pali", "Dovo", "Senu"),
    },
    {
        "id": "CAL-VISIBLE-03",
        "nodes": ("Bemi", "Tavo", "Neki", "Lusa", "Gori"),
        "rules": (
            "Bemi activates Tavo.",
            "Tavo activates Neki.",
            "Neki activates Lusa.",
            "Gori activates Bemi.",
        ),
        "start": "Bemi",
        "target": "Lusa",
        "path": ("Bemi", "Tavo", "Neki", "Lusa"),
    },
    {
        "id": "CAL-VISIBLE-04",
        "nodes": ("Fenu", "Rako", "Wimi", "Jesa", "Cupo"),
        "rules": (
            "Fenu activates Rako.",
            "Rako activates Wimi.",
            "Wimi activates Jesa.",
            "Cupo activates Fenu.",
        ),
        "start": "Fenu",
        "target": "Jesa",
        "path": ("Fenu", "Rako", "Wimi", "Jesa"),
    },
)

SYSTEM = (
    "You are solving a fictional rule task. Use only the supplied rules. "
    "Give the answer and the complete rule path. Do not infer unstated rules."
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def post(base: str, path: str, value: dict[str, Any], timeout: float = 1800.0) -> dict[str, Any]:
    request = urllib.request.Request(
        base + path,
        data=canonical(value),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_ready(base: str, process: subprocess.Popen[str]) -> None:
    until = time.monotonic() + 180
    while time.monotonic() < until:
        if process.poll() is not None:
            raise RuntimeError("pinned llama-server exited before ready")
        try:
            post(base, "/tokenize", {"content": "ready", "add_special": False}, timeout=10)
            return
        except (OSError, urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise TimeoutError("pinned llama-server did not become ready")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=64371)
    args = parser.parse_args()
    if hashlib.sha256(Path(MODEL).read_bytes()).hexdigest() != MODEL_SHA256:
        raise RuntimeError("Gemma GGUF hash mismatch")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.output.with_suffix(".server.log")
    server_version = subprocess.run(
        [LLAMA_SERVER, "--version"], capture_output=True, text=True, check=False
    )
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        check=False,
    )
    llama_binary_sha256 = hashlib.sha256(Path(LLAMA_SERVER).read_bytes()).hexdigest()
    host_fingerprint = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "gpu": gpu.stdout.strip() if gpu.returncode == 0 else None,
        "environment": {
            name: os.environ.get(name)
            for name in (
                "CUDA_VISIBLE_DEVICES",
                "CUDA_LAUNCH_BLOCKING",
                "OMP_NUM_THREADS",
                "GGML_CUDA_DISABLE_GRAPHS",
            )
        },
    }
    command = [
        LLAMA_SERVER,
        "-m",
        MODEL,
        "-ngl",
        "99",
        "-c",
        "8192",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
        "--reasoning-format",
        "deepseek",
        "--no-warmup",
        "--no-webui",
    ]
    rows: list[dict[str, Any]] = []
    started_server = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            base = f"http://127.0.0.1:{args.port}"
            wait_ready(base, process)
            for case in CASES:
                rules = "\n".join(f"- {rule}" for rule in case["rules"])
                prompt = (
                    "These are fictional labels and rules. An active label activates the target of each rule that starts with it. "
                    f"Initially only {case['start']} is active.\n\nRules:\n{rules}\n\n"
                    f"Can {case['target']} become active? Give YES or NO and show the complete directed path from {case['start']}."
                )
                messages = [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ]
                for seed in SEEDS:
                    request = {
                        "model": Path(MODEL).name,
                        "messages": messages,
                        "stream": False,
                        "cache_prompt": False,
                        "seed": seed,
                        "max_tokens": 2048,
                        "chat_template_kwargs": {"enable_thinking": True},
                        **SAMPLER,
                    }
                    rendered = post(
                        base,
                        "/apply-template",
                        {
                            "messages": messages,
                            "add_generation_prompt": True,
                            "chat_template_kwargs": {"enable_thinking": True},
                        },
                    )
                    call_started = time.monotonic()
                    response = post(base, "/v1/chat/completions", request)
                    elapsed = time.monotonic() - call_started
                    choice = response.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    reasoning = message.get("reasoning_content", "")
                    final = message.get("content", "")
                    answer_key = case["target"]
                    path_ok = all(label in final for label in case["path"])
                    answer_ok = answer_key in final and "yes" in final.lower()
                    row = {
                        "fixture_id": case["id"],
                        "seed": seed,
                        "expected_answer": answer_key,
                        "expected_path": list(case["path"]),
                        "request": request,
                        "request_sha256": hashlib.sha256(canonical(request)).hexdigest(),
                        "model_visible_prompt": rendered.get("prompt"),
                        "model_visible_prompt_sha256": hashlib.sha256(
                            str(rendered.get("prompt", "")).encode()
                        ).hexdigest(),
                        "response": response,
                        "reasoning": reasoning,
                        "final": final,
                        "finish_reason": choice.get("finish_reason"),
                        "answer_key_present": answer_ok,
                        "complete_path_present": path_ok,
                        "comprehension_pass": bool(
                            answer_ok and path_ok and choice.get("finish_reason") == "stop"
                        ),
                        "elapsed_s": elapsed,
                    }
                    rows.append(row)
                    receipt = {
                        "status": "IN_PROGRESS",
                        "model": Path(MODEL).name,
                        "model_sha256": MODEL_SHA256,
                        "llama_cpp_commit": LLAMA_COMMIT,
                        "llama_server_version_output": (
                            server_version.stdout + server_version.stderr
                        ).strip(),
                        "llama_server_binary_sha256": llama_binary_sha256,
                        "host_fingerprint": host_fingerprint,
                        "server_command": command,
                        "server_started_unix": started_server,
                        "reasoning": "ON",
                        "cache_prompt": False,
                        "sampler": SAMPLER,
                        "rows": rows,
                    }
                    temp = args.output.with_suffix(args.output.suffix + ".tmp")
                    temp.write_text(
                        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                    )
                    temp.replace(args.output)
                    print(
                        json.dumps(
                            {
                                "fixture": case["id"],
                                "seed": seed,
                                "pass": row["comprehension_pass"],
                                "elapsed_s": round(elapsed, 2),
                            }
                        ),
                        flush=True,
                    )
            receipt["status"] = "COMPLETE"
            receipt["summary"] = {
                "passed": sum(row["comprehension_pass"] for row in rows),
                "total": len(rows),
            }
            temp = args.output.with_suffix(args.output.suffix + ".tmp")
            temp.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            temp.replace(args.output)
        finally:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=30)


if __name__ == "__main__":
    main()
