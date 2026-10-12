#!/usr/bin/env python3
"""Render only the three frozen v3.1 baseline prompts; never call generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

CALIBRATION_IDS = ["atomic/1-48", "atomic/1-12", "atomic/1-41"]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def run_remote(host: str, command: str) -> str:
    result = subprocess.run(
        ["ssh", "-S", "/tmp/mi2-ssh-control.sock", host, command],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def copy_to_remote(host: str, local_path: Path, remote_path: str) -> None:
    subprocess.run(
        [
            "scp",
            "-q",
            "-o",
            "ControlPath=/tmp/mi2-ssh-control.sock",
            str(local_path),
            f"{host}:{remote_path}",
        ],
        check=True,
    )


def copy_from_remote(host: str, remote_path: str, local_path: Path) -> None:
    subprocess.run(
        [
            "scp",
            "-q",
            "-o",
            "ControlPath=/tmp/mi2-ssh-control.sock",
            f"{host}:{remote_path}",
            str(local_path),
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--host", default="brokeass-msi")
    parser.add_argument("--remote-root", default="/tmp/mi2-v3.1-capture")
    parser.add_argument("--port", type=int, default=18473)
    args = parser.parse_args()
    plan_bytes = args.plan.read_bytes()
    plan_sha = sha_bytes(plan_bytes)
    if plan_sha != args.approved_plan_sha256:
        raise ValueError("v3.1 plan hash differs from Root-approved freeze")
    plan: dict[str, Any] = json.loads(plan_bytes)
    items = plan.get("calibration", {}).get("items")
    if [row.get("id") for row in items or []] != CALIBRATION_IDS:
        raise ValueError("render tool accepts only the three frozen Atomic calibration prompts")
    health = json.loads(run_remote(args.host, f"curl -fsS http://127.0.0.1:{args.port}/health"))
    if health.get("status") != "ok":
        raise RuntimeError("isolated llama.cpp server is not healthy")

    output_root = args.run_root / "rendered"
    request_root = args.run_root / "requests"
    output_root.mkdir(parents=True, exist_ok=True)
    records: dict[str, Any] = {}
    for item in items:
        item_id = item["id"]
        name = item_id.replace("/", "_")
        request_path = request_root / f"{name}.json"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if request.get("messages") != [
            {"role": "system", "content": plan["prompt_contract"]["system_baseline"]},
            {"role": "user", "content": item["question_utf8"]},
        ]:
            raise ValueError(f"{item_id}: request messages differ from frozen baseline")
        remote_request = f"{args.remote_root}/requests/{name}.json"
        remote_apply = f"{args.remote_root}/rendered/{name}.apply.json"
        copy_to_remote(args.host, request_path, remote_request)
        run_remote(
            args.host,
            f"curl -fsS -H 'Content-Type: application/json' --data-binary @{remote_request} "
            f"http://127.0.0.1:{args.port}/apply-template > {remote_apply}",
        )
        apply_local = output_root / f"{name}.apply.json"
        copy_from_remote(args.host, remote_apply, apply_local)
        applied = json.loads(apply_local.read_text(encoding="utf-8"))
        prompt = applied.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError(f"{item_id}: /apply-template omitted exact rendered prompt")
        if plan["paper_card"]["trigger"].split(";")[0] in prompt or "Trap Check:" in prompt:
            raise ValueError(f"{item_id}: secret target card leaked into baseline rendered prompt")
        prompt_path = output_root / f"{name}.prompt.txt"
        prompt_path.write_bytes(prompt.encode("utf-8"))
        token_request = output_root / f"{name}.tokenize-request.json"
        token_request.write_text(
            json.dumps({"content": prompt, "add_special": True}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        remote_token_request = f"{args.remote_root}/requests/{name}.tokenize.json"
        remote_tokenized = f"{args.remote_root}/rendered/{name}.tokenize.json"
        copy_to_remote(args.host, token_request, remote_token_request)
        run_remote(
            args.host,
            f"curl -fsS -H 'Content-Type: application/json' "
            f"--data-binary @{remote_token_request} http://127.0.0.1:{args.port}/tokenize "
            f"> {remote_tokenized}",
        )
        tokenized_path = output_root / f"{name}.tokenize.json"
        copy_from_remote(args.host, remote_tokenized, tokenized_path)
        tokenized = json.loads(tokenized_path.read_text(encoding="utf-8"))
        raw_tokens = tokenized.get("tokens")
        if (
            not isinstance(raw_tokens, list)
            or not raw_tokens
            or any(not isinstance(token, int) for token in raw_tokens)
        ):
            raise ValueError(f"{item_id}: server /tokenize did not return token ID records")
        rows = [{"id": token} for token in raw_tokens]
        rendered = {
            "id": item_id,
            "plan_sha256": plan_sha,
            "messages": request["messages"],
            "rendered_prompt": prompt,
            "rendered_sha256": sha(prompt_path),
            "apply_template_response_sha256": sha(apply_local),
            "server_tokenization": rows,
            "token_ids": [row["id"] for row in rows],
            "token_count": len(rows),
            "tokenize_response_sha256": sha(tokenized_path),
            "contains_target_card": False,
            "generation_dispatched": False,
        }
        rendered_path = output_root / f"{name}.json"
        rendered_path.write_text(
            json.dumps(rendered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        records[item_id] = {
            "rendered_path": str(rendered_path),
            "rendered_sha256": sha(rendered_path),
            "prompt_sha256": rendered["rendered_sha256"],
            "prompt_tokens": len(rows),
            "token_ids_sha256": sha_bytes(
                json.dumps(rendered["token_ids"], separators=(",", ":")).encode()
            ),
            "apply_template_response_sha256": rendered["apply_template_response_sha256"],
            "tokenize_response_sha256": rendered["tokenize_response_sha256"],
        }
        print(json.dumps({item_id: records[item_id]}), flush=True)
    print(
        json.dumps(
            {"status": "THREE_BASELINE_PROMPTS_RENDERED_NO_GENERATION", "records": records},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
