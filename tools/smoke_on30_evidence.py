#!/usr/bin/env python3
# ruff: noqa: E501, E402, I001
"""Disposable evidence-chain smoke test; never opens a developmental store."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from mneme.contracts import GenerationRequest
from mneme.experiments.shared_interloper import GEMMA_SYSTEM_PROMPT
from tools.run_p23_cross_thread import RemoteGlinerHost
from tools.run_p23_f0_background_shared_interloper import RemoteNliBackend
from tools.run_reasoning_25_thread import DeterministicRemoteGemma, digest_bytes


def produce(path: Path) -> None:
    prompt = "A route can keep a backup option when weather changes; explain the idea in a few sentences."
    host = DeterministicRemoteGemma("smoke-Gemma-ON", 64173, "on", 1024)
    request = GenerationRequest(({"role": "user", "content": prompt},), system=GEMMA_SYSTEM_PROMPT, parameters={"temperature": 0.35, "top_k": 40, "top_p": 0.9, "min_p": 0.05, "max_new_tokens": 1024}, seed=899901)
    result = host.generate(request)
    source = prompt + "\n" + result.content
    gliner = RemoteGlinerHost()
    extraction = gliner.generate(GenerationRequest(({"role": "user", "content": json.dumps({"source_slots": {"s0": source}})},), parameters={"max_new_tokens": 768}))
    parsed = json.loads(extraction.content)
    relationships = parsed.get("relationships", []) if isinstance(parsed, dict) else []
    nli_pairs = []
    for rel in relationships if isinstance(relationships, list) else []:
        if isinstance(rel, dict):
            nli_pairs.append((source, f"{rel.get('from', '')} {rel.get('relation', '').replace('_', ' ')} {rel.get('to', '')}."))
    scores = RemoteNliBackend().score_pairs(nli_pairs) if nli_pairs else ()
    payload = {
        "schema": "mneme.on30.evidence-smoke.v1",
        "disposable": True,
        "developmental_state_touched": False,
        "context": prompt,
        "saa_payload": "Potentially accessible framing: preserve options when conditions change.",
        "model_visible_request": result.raw_metadata.get("request_payload"),
        "model_visible_request_utf8": result.raw_metadata.get("request_body_utf8"),
        "request_sha256": result.raw_metadata.get("request_sha256"),
        "reasoning_text": result.raw_metadata.get("reasoning_content", ""),
        "reasoning_sha256": digest_bytes(str(result.raw_metadata.get("reasoning_content", "")).encode()),
        "final_answer": result.content,
        "finish_reason": result.finish_reason,
        "extraction_candidates": relationships,
        "nli_scores": [{"entailment": s.entailment, "contradiction": s.contradiction, "neutral": s.neutral} for s in scores],
        "nli_candidate_count": len(nli_pairs),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def verify(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ("context", "saa_payload", "model_visible_request", "reasoning_text", "final_answer", "extraction_candidates", "nli_scores")
    missing = [key for key in required if key not in data]
    if missing or not data.get("model_visible_request_utf8") or not data.get("request_sha256"):
        raise SystemExit(f"smoke evidence incomplete: {missing}")
    print(json.dumps({"smoke": "PASS", "fresh_process": True, "reasoning_bytes": len(data["reasoning_text"].encode()), "candidates": len(data["extraction_candidates"]), "nli_scores": len(data["nli_scores"])}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    verify(args.path) if args.verify else produce(args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
