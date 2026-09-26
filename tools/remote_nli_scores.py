#!/usr/bin/env python3
"""Score NLI pairs on the MSI's pinned CPU model.

The caller owns semantic result construction and validation. This helper only
loads the pinned cross-encoder and returns entailment/contradiction/neutral
scores for a bounded JSON batch on stdin.
"""
from __future__ import annotations

import json
import sys

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "cross-encoder/nli-deberta-v3-xsmall"
MODEL_REVISION = "a150876415327c80daeff35ca6f68f5ed8cf5c24"


def main() -> int:
    request = json.load(sys.stdin)
    pairs = request.get("pairs")
    if not isinstance(pairs, list) or any(
        not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(x, str) for x in pair)
        for pair in pairs
    ):
        raise ValueError("pairs must be a list of [premise, hypothesis] strings")
    model_id = str(request.get("model_id", MODEL_ID))
    revision = str(request.get("revision", MODEL_REVISION))
    if model_id != MODEL_ID or revision != MODEL_REVISION:
        raise ValueError("remote NLI helper is pinned to the qualified model revision")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_id, revision=revision, local_files_only=True
    )
    model.eval()
    labels = {int(key): str(value).casefold() for key, value in model.config.id2label.items()}
    required = {"entailment", "contradiction", "neutral"}
    if set(labels.values()) != required:
        raise ValueError(f"unexpected NLI labels: {labels}")
    scores: list[list[float]] = []
    batch_size = max(1, int(request.get("batch_size", 8)))
    max_length = max(1, int(request.get("max_length", 512)))
    for start in range(0, len(pairs), batch_size):
        batch = pairs[start : start + batch_size]
        encoded = tokenizer(
            [pair[0] for pair in batch],
            [pair[1] for pair in batch],
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        with torch.inference_mode():
            rows = torch.softmax(model(**encoded).logits, dim=-1).tolist()
        for row in rows:
            by_label = {labels[index]: float(value) for index, value in enumerate(row)}
            scores.append([by_label["entailment"], by_label["contradiction"], by_label["neutral"]])
    print(json.dumps({"scores": scores, "model_id": model_id, "revision": revision}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
