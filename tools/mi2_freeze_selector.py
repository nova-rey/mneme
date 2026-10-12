#!/usr/bin/env python3
"""Validate calibration query capture and freeze MI2's Gemma site selector."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.bank import MemoryBank
from experiments.mi1.native.query_capture import read_query_capture
from experiments.mi1.native.selector import attention_mass
from experiments.mi1.site_calibration import select_query_sites


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--clarification", type=Path, required=True)
    parser.add_argument("--amendment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    amp = json.loads(args.amendment.read_text(encoding="utf-8"))
    assert amp["base_plan_sha256"] == sha(args.plan)
    target_path = args.root / "banks/target.npz"
    reference_path = args.root / "banks/reference.npz"
    target = MemoryBank.load(target_path)
    reference = MemoryBank.load(reference_path)
    assert target.manifest.layer_ids == tuple(range(24))
    assert target.manifest.kv_heads_by_layer == (2,) * 24
    assert target.manifest.slot_count == 270
    assert reference.manifest.slot_count == 132

    captures: dict[str, Any] = {}
    targets: dict[str, MemoryBank] = {}
    records: dict[str, Any] = {}
    for item in plan["splits"]["calibration"]:
        short = item["id"].replace("/", "_")
        capture_path = args.root / f"captures/query_{short.split('_')[1]}.mi1qry"
        rendered_path = args.root / f"rendered/{short}.json"
        rendered = json.loads(rendered_path.read_text(encoding="utf-8"))
        capture = read_query_capture(capture_path)
        expected_tokens = tuple(row["id"] for row in rendered["server_tokenization"])
        if capture.token_ids != expected_tokens:
            raise ValueError(f"{item['id']}: native capture token IDs differ from server /tokenize")
        if set(capture.layers) != set(range(42)):
            raise ValueError(f"{item['id']}: expected query layers 0..41")
        prompt_cache_capacities: set[int] = set()
        for layer, row in capture.layers.items():
            if row.query.shape[0] != len(expected_tokens) or row.query.shape[1] != 8:
                raise ValueError(f"{item['id']}: unexpected Q shape at layer {layer}")
            if not np.isfinite(row.query).all() or not np.isfinite(row.attention).all():
                raise ValueError(f"{item['id']}: non-finite captured tensor at layer {layer}")
            if row.attention.shape[0:2] != (len(expected_tokens), 8):
                actual = row.attention.shape
                raise ValueError(
                    f"{item['id']}: unexpected KQ query/head shape "
                    f"at layer {layer}: {actual}"
                )
            cache_capacity = row.attention.shape[-1] - target.manifest.slot_count
            if cache_capacity < len(expected_tokens):
                raise ValueError(
                    f"{item['id']}: KQ cache capacity shorter than prompt at layer {layer}"
                )
            # The pinned native graph reserves prompt KV capacity in variable
            # 256-token blocks. The bank occupies the final slots; selector
            # attention_mass() verifies every unused capacity slot is masked.
            attention_mass(
                row.attention[-1].T,
                prompt_slots=len(expected_tokens),
                bank_slots=target.manifest.slot_count,
            )
            prompt_cache_capacities.add(cache_capacity)
        if len(prompt_cache_capacities) != 1:
            raise ValueError(f"{item['id']}: layers disagree on prompt cache capacity")
        captures[item["id"]] = capture
        targets[item["id"]] = target
        records[item["id"]] = {
            "query_capture_sha256": sha(capture_path),
            "rendered_prompt_sha256": rendered["rendered_sha256"],
            "server_token_ids_sha256": hashlib.sha256(
                json.dumps(expected_tokens, separators=(",", ":")).encode()
            ).hexdigest(),
            "token_id_parity": "EXACT",
            "prompt_tokens": len(expected_tokens),
            "reserved_prompt_cache_capacity": next(iter(prompt_cache_capacities)),
            "query_layers": len(capture.layers),
            "query_heads_per_layer": 8,
            "head_dims_by_layer": [
                int(capture.layers[layer].query.shape[-1]) for layer in range(42)
            ],
            "attention_keys_by_layer": [
                int(capture.layers[layer].attention.shape[-1]) for layer in range(42)
            ],
        }

    selected = select_query_sites(captures, targets, reference, top_layers=4)
    payload = {
        "schema_version": 1,
        "status": "CALIBRATION_SELECTOR_FROZEN_BEFORE_GENERATION",
        "base_plan_sha256": sha(args.plan),
        "clarification_sha256": sha(args.clarification),
        "process_score_amendment_sha256": sha(args.amendment),
        "target_bank_native_sha256": sha(target_path.with_suffix(".mi1")),
        "reference_bank_native_sha256": sha(reference_path.with_suffix(".mi1")),
        "calibration_query_records": records,
        "query_to_kv_source_mapping": [list(row) for row in selected.source_kv_by_query_layer],
        "alignment_margin_by_layer_group": selected.alignment.tolist(),
        "target_attention_mass_by_layer_group": selected.bank_mass.tolist(),
        "prompt_attention_mass_by_layer_group": selected.prompt_mass.tolist(),
        "selected_kv_groups": [list(row) for row in selected.sparse_groups],
        "selected_query_sites": [list(row) for row in selected.sparse_query_sites],
        "selection_rule": (
            "Frozen Appendix-C Eq.3 max target/reference pre-RoPE K alignment; "
            "per-layer top-1 KV group with bank mass tie-break; global top-4 "
            "layers; each KV group expands to its 4 associated Q heads."
        ),
        "bank_bias_for_selector_capture": 0.0,
        "heldout_queries_used": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": sha(args.output),
                "groups": payload["selected_kv_groups"],
                "sites": payload["selected_query_sites"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
