#!/usr/bin/env python3
"""Create an anonymized calibration scoring packet from durable call outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--coordinates", type=Path, required=True)
    ap.add_argument("--journal", type=Path, required=True)
    ap.add_argument("--output-root", type=Path, required=True)
    args = ap.parse_args()
    protocol: dict[str, Any] = json.loads(args.protocol.read_text(encoding="utf-8"))
    coordinates = json.loads(args.coordinates.read_text(encoding="utf-8"))["coordinates"]
    journal = EvidenceJournal(args.journal, hard_call_limit=100)
    statuses = journal.verify()
    if statuses != {"COMPLETE": 18}:
        raise ValueError(f"expected exactly 18 completed calibration calls; got {statuses}")
    index = json.loads((args.journal / "index.json").read_text(encoding="utf-8"))
    by_attempt = {row["attempt_id"]: row for row in index["attempts"]}
    prompt_text = {row["id"]: row["user"] for row in protocol["calibration"]["prompts"]}

    eligible: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for coordinate in coordinates:
        condition = coordinate["metadata"]["condition"]
        if not (condition.startswith("latent_A_bias_") or condition.startswith("latent_B_bias_")):
            continue
        attempt_id = coordinate["coordinate_id"]
        row = by_attempt[attempt_id]
        outcome_path = args.journal / "attempts" / row["outcome_file"]
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        response = outcome["payload"]
        choice = response["choices"][0]
        message = choice["message"]
        reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
        final = message.get("content") or ""
        eligible.append(
            (
                coordinate,
                {
                    "task": prompt_text[coordinate["metadata"]["prompt_id"]],
                    "reasoning": reasoning,
                    "final": final,
                    "finish_reason": choice.get("finish_reason"),
                    "usage": response.get("usage"),
                },
            )
        )
    if len(eligible) != 8:
        raise ValueError(
            f"expected eight latent A/B gain outputs for blind scoring, got {len(eligible)}"
        )
    order = list(range(len(eligible)))
    shuffle_seed = 2026101409
    random.Random(shuffle_seed).shuffle(order)
    outputs: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    for i, raw_i in enumerate(order, start=1):
        coordinate, payload = eligible[raw_i]
        opaque_id = f"blind-{i:02d}"
        outputs.append({"opaque_id": opaque_id, **payload})
        mapping.append(
            {
                "opaque_id": opaque_id,
                "attempt_id": coordinate["coordinate_id"],
                **coordinate["metadata"],
            }
        )

    args.output_root.mkdir(parents=True, exist_ok=True)
    packet = args.output_root / "blind-calibration-packet.json"
    key = args.output_root / "blind-calibration-key.json"
    atomic_json_write(
        packet,
        {
            "purpose": (
                "Blind A/B direction scoring to select one global gain; only calibration "
                "latent A/B outputs, with no bank labels or visible conditions."
            ),
            "scoring_rubric": protocol["scoring"]["blind_semantic_rubric"],
            "outputs": outputs,
        },
    )
    atomic_json_write(
        key,
        {
            "sealed_until_scores_final": True,
            "randomization_seed": shuffle_seed,
            "mapping": mapping,
        },
    )
    print(
        json.dumps(
            {
                "statuses": statuses,
                "blind_output_count": len(outputs),
                "packet": str(packet),
                "packet_sha256": sha(packet),
                "key": str(key),
                "key_sha256": sha(key),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
