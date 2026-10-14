"""Freeze exact Qwen3 chat-template prompts used by the MI4 selector capture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.runner import http_json


def capture_prompts(protocol: dict[str, Any], *, base_url: str) -> dict[str, Any]:
    result: dict[str, Any] = {"thinking": True, "prompts": {}}
    for item in protocol["calibration"]["prompts"]:
        request = {
            "messages": [
                {"role": "system", "content": protocol["generation"]["system"]},
                {"role": "user", "content": item["user"]},
            ],
            "add_generation_prompt": True,
            "chat_template_kwargs": {"enable_thinking": True},
        }
        response = http_json(f"{base_url.rstrip('/')}/apply-template", request)
        prompt = response.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("Qwen3 template endpoint returned no prompt")
        result["prompts"][item["id"]] = {
            "request": request,
            "response": response,
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18473")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    result = capture_prompts(protocol, base_url=args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(args.output)
    for name, row in result["prompts"].items():
        prompt_path = args.output.parent / f"{name}.prompt.txt"
        prompt_path.write_text(row["prompt"], encoding="utf-8")
        print(f"{name} {row['prompt_sha256']} {len(row['prompt'].encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
