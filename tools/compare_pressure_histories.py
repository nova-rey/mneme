"""Offline history diagnostic over recorded queries; never generate or write state."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from mneme.controller import ResponseController, TurnIntent
from mneme.development.field import _strength
from mneme.experiments.pressure_meters import historical_metrics
from mneme.hosts import FakeHost
from mneme.state.storage import SQLiteStore


def compare_histories(records: list[dict[str, Any]], secondary: Path) -> dict[str, Any]:
    """Compare each recorded primary field with R8 using identical input and seed.

    Both meter readings compare earned versus conditioned weights within their
    own eligible candidate set. No cross-universe total variation is invented.
    The read-only legacy interface is used only for historical observation.
    """
    before = hashlib.sha256(secondary.read_bytes()).hexdigest()
    rows = []
    with SQLiteStore(secondary, read_only=True) as store:
        controller = ResponseController(
            store, str(store.current()["active_instance_id"]), FakeHost()
        )
        pin = controller._pin()
        _, edges = controller._field_graph(pin)
        learner = controller._learner_state(pin)
        strengths = {edge.key: _strength(edge, learner)[0] for edge in edges}
        for record in records:
            primary = record["field"]
            prepared = controller.prepare(TurnIntent(
                current_input=primary["query"], mode="observe", memory="graph",
                selection_policy="field-saa-v1", field_seed=primary["field_seed"],
            ))
            if prepared.field_result is None:
                raise ValueError("secondary state produced no SAA field")
            field = prepared.field_result.to_dict()
            secondary_input = {
                "historical_strengths": {
                    item["candidate"]: strengths[item["candidate"]]
                    for item in field["accessibility_distribution"]
                },
                "field": field,
                "accessibility_adjustments": {},
            }
            rows.append({
                "conversation": record["conversation"], "turn": record["turn"],
                "query": primary["query"], "field_seed": primary["field_seed"],
                "primary": historical_metrics(record),
                "secondary": historical_metrics(secondary_input),
                "secondary_input": secondary_input,
            })
    after = hashlib.sha256(secondary.read_bytes()).hexdigest()
    if before != after:
        raise RuntimeError("read-only historical source changed during comparison")
    return {
        "provider_calls": 0, "state_writes": 0,
        "secondary_source": str(secondary), "secondary_sha256": before,
        "source_unchanged": True, "candidate_universes": "compared within each state",
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("--secondary", type=Path, required=True)
    parser.add_argument("--fidelity-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.fidelity_review.is_file():
        raise ValueError("publish the pre-score fidelity review before this diagnostic")
    payload = args.inputs.read_bytes()
    if args.inputs.suffix == ".gz":
        payload = gzip.decompress(payload)
    records = json.loads(payload)
    result = compare_histories(records, args.secondary)
    result["fidelity_review_sha256"] = hashlib.sha256(
        args.fidelity_review.read_bytes()
    ).hexdigest()
    encoded = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(
        gzip.compress(encoded, mtime=0) if args.output.suffix == ".gz" else encoded
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
