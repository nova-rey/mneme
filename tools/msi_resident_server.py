#!/usr/bin/env python3
"""Resident MSI specialist service for bounded MNEME experiments.

The service deliberately exposes only the already-qualified specialist
operations.  Gemma is served by llama.cpp's resident HTTP server; this file
keeps GLiNER2.5 and the pinned DeBERTa NLI model loaded between requests.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

MODEL_ID = "cross-encoder/nli-deberta-v3-xsmall"
MODEL_REVISION = "a150876415327c80daeff35ca6f68f5ed8cf5c24"
GLINER_ID = "fastino/gliner2.5-base-v1"
RELATION_TYPES = [
    "causes", "caused_by", "constrains", "enables", "prevents", "retains",
    "supports", "depends_on", "associated_with", "related", "contains",
    "part_of", "requires", "affects", "reduces", "increases", "improves",
    "maintains", "allows", "helps", "uses", "provides", "leads_to",
    "changes", "stabilizes", "protects", "keeps", "wicks", "dries", "wilts",
    "shades", "holds", "controls", "manages", "solves", "influences", "has",
    "used_for",
]


class _State:
    role: str
    model: Any
    tokenizer: Any
    labels: dict[int, str]


STATE = _State()


def _load(role: str) -> None:
    STATE.role = role
    STATE.model = None
    STATE.tokenizer = None
    STATE.labels = {}
    if role == "nli":
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        STATE.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, local_files_only=True
        )
        STATE.model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, local_files_only=True
        )
        STATE.model.eval()
        STATE.labels = {int(k): str(v).casefold() for k, v in STATE.model.config.id2label.items()}
        if set(STATE.labels.values()) != {"entailment", "contradiction", "neutral"}:
            raise RuntimeError(f"unexpected NLI labels: {STATE.labels}")
    elif role == "gliner":
        from gliner2 import AutoExtractor

        STATE.model = AutoExtractor.from_pretrained(GLINER_ID)
    else:
        raise ValueError(role)


def _score(body: dict[str, Any]) -> dict[str, Any]:
    import torch

    pairs = body.get("pairs")
    if not isinstance(pairs, list) or any(
        not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(x, str) for x in pair)
        for pair in pairs
    ):
        raise ValueError("pairs must be a list of [premise, hypothesis] strings")
    batch_size = max(1, int(body.get("batch_size", 8)))
    max_length = max(1, int(body.get("max_length", 512)))
    scores: list[list[float]] = []
    for start in range(0, len(pairs), batch_size):
        batch = pairs[start : start + batch_size]
        encoded = STATE.tokenizer(
            [pair[0] for pair in batch], [pair[1] for pair in batch],
            padding=True, truncation=True, max_length=max_length, return_tensors="pt"
        )
        with torch.inference_mode():
            rows = torch.softmax(STATE.model(**encoded).logits, dim=-1).tolist()
        for row in rows:
            by_label = {STATE.labels[index]: float(value) for index, value in enumerate(row)}
            scores.append([by_label["entailment"], by_label["contradiction"], by_label["neutral"]])
    return {"scores": scores, "model_id": MODEL_ID, "revision": MODEL_REVISION}


def _extract(body: dict[str, Any]) -> dict[str, Any]:
    source_slots = body.get("source_slots")
    if not isinstance(source_slots, dict):
        raise ValueError("source_slots must be an object")
    text = "\n".join(str(value) for value in source_slots.values())
    raw = STATE.model.extract_relations(
        text, RELATION_TYPES, threshold=float(body.get("threshold", 0.35)),
        include_confidence=True, include_spans=True,
        max_len=int(body.get("max_len", 4096)), overlap_policy="flat"
    )
    return {"id": "episode", "model": GLINER_ID, "threshold": 0.35, "max_len": 4096, "raw": raw}


class Handler(BaseHTTPRequestHandler):
    server_version = "mneme-msi-resident/1"

    def log_message(self, *_args: Any) -> None:
        return

    def _write(self, status: int, body: dict[str, Any]) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self._write(404, {"error": "not_found"})
            return
        model = MODEL_ID if STATE.role == "nli" else GLINER_ID
        self._write(200, {"status": "ready", "role": STATE.role, "model": model})

    def do_POST(self) -> None:  # noqa: N802
        try:
            size = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(size))
            if STATE.role == "nli" and self.path == "/score":
                result = _score(body)
            elif STATE.role == "gliner" and self.path == "/extract":
                result = _extract(body)
            else:
                result = None
            if result is None:
                self._write(404, {"error": "not_found"})
            else:
                self._write(200, result)
        except Exception as exc:  # pragma: no cover - exercised on MSI
            self._write(400, {"error": type(exc).__name__, "message": str(exc)})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("nli", "gliner"), required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    _load(args.role)
    HTTPServer((args.host, args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
