#!/usr/bin/env python3
"""Run the pinned local GLiNER2.5 observation instrument.

Input is JSONL with ``id`` and ``text``.  Output is JSONL containing the raw
specialist result.  No MNEME IDs, learner state, or canonical relationships
are invented here; the repository adapter performs deterministic span checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

RELATION_TYPES = [
    "causes",
    "caused_by",
    "constrains",
    "enables",
    "prevents",
    "retains",
    "supports",
    "depends_on",
    "associated_with",
    "related",
    "contains",
    "part_of",
    "requires",
    "affects",
    "reduces",
    "increases",
    "improves",
    "maintains",
    "allows",
    "helps",
    "uses",
    "provides",
    "leads_to",
    "changes",
    "stabilizes",
    "protects",
    "keeps",
    "wicks",
    "dries",
    "wilts",
    "shades",
    "holds",
    "controls",
    "manages",
    "solves",
    "influences",
    "has",
    "used_for",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="fastino/gliner2.5-base-v1")
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--max-len", type=int, default=4096)
    parser.add_argument("--overlap-policy", default="flat")
    args = parser.parse_args()
    try:
        from gliner2 import AutoExtractor
    except ImportError as exc:  # pragma: no cover - exercised on the MSI only
        raise SystemExit("install gliner2[local] in the isolated extractor environment") from exc
    model = AutoExtractor.from_pretrained(args.model)
    for line in sys.stdin:
        if not line.strip():
            continue
        row: dict[str, Any] = json.loads(line)
        text = row.get("text")
        if not isinstance(text, str):
            raise SystemExit("each input row requires string text")
        result = model.extract_relations(
            text,
            RELATION_TYPES,
            threshold=args.threshold,
            include_confidence=True,
            include_spans=True,
            max_len=args.max_len,
            overlap_policy=args.overlap_policy,
        )
        print(
            json.dumps(
                {
                    "id": row.get("id"),
                    "model": args.model,
                    "threshold": args.threshold,
                    "max_len": args.max_len,
                    "raw": result,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
