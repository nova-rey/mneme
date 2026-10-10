"""Replay the frozen MI1 fictional rule-test scorer from a durable call journal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.native.evidence import atomic_json_write
from experiments.mi1.scoring import load_journal_rows, score_test_a


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("experiments/mi1/fixtures/mi1_frozen_suite.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hard-call-limit", type=int, default=800)
    args = parser.parse_args()

    suite_bytes = args.suite.read_bytes()
    index_bytes = (args.journal / "index.json").read_bytes()
    suite = json.loads(suite_bytes)
    rows = load_journal_rows(args.journal, hard_call_limit=args.hard_call_limit)
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "scorer": "mi1-test-a-v3-live-request-and-sse-envelope",
        "frozen_suite_sha256": hashlib.sha256(suite_bytes).hexdigest(),
        "journal_index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "journal_attempts": len(rows),
        "test_a": score_test_a(suite, rows),
    }
    atomic_json_write(args.output, receipt)
    print(
        json.dumps(
            {"output": str(args.output), "test_a": receipt["test_a"]["condition_accuracy"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
