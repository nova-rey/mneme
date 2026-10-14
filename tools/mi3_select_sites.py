#!/usr/bin/env python3
"""Freeze the shared MI3 query-site set from development-only prefill captures."""

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
from experiments.mi1.native.selector import (
    appendix_c_sparse_selector,
    attention_mass,
    expand_kv_groups,
    grouped_alignment_margin,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--bank-build", type=Path, required=True)
    ap.add_argument("--bank-dir", type=Path, required=True)
    ap.add_argument("--query-dir", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    args = ap.parse_args()
    protocol: dict[str, Any] = json.loads(args.protocol.read_text(encoding="utf-8"))
    keys = list(protocol["neighborhoods"])
    banks = {key: MemoryBank.load(args.bank_dir / f"{key}.npz") for key in keys}
    if len({bank.manifest.slot_count for bank in banks.values()}) != 1:
        raise ValueError("unselected bank slot counts differ")
    if len({bank.manifest.layer_ids for bank in banks.values()}) != 1:
        raise ValueError("unselected bank source layer IDs differ")

    capture_paths = sorted(args.query_dir.glob("*.mi1qry"))
    expected = {
        f"{prompt['id']}-{key}.mi1qry"
        for prompt in protocol["calibration"]["prompts"]
        for key in keys
    }
    if {path.name for path in capture_paths} != expected:
        raise ValueError(
            "query-site calibration requires the exact six D1/D2 × A/B/control captures"
        )

    layer_count = 42
    kv_groups = banks[keys[0]].manifest.kv_heads_by_layer[0]
    alignment_rows: list[np.ndarray] = []
    bank_mass_rows: list[np.ndarray] = []
    prompt_mass_rows: list[np.ndarray] = []
    capture_records: list[dict[str, Any]] = []
    for path in capture_paths:
        prompt_id, active_key = path.stem.rsplit("-", 1)
        if active_key not in banks:
            # The control ID itself contains hyphens; recover by suffix.
            active_key = next((key for key in keys if path.stem.endswith(f"-{key}")), "")
            if not active_key:
                raise ValueError(f"cannot identify active bank for {path.name}")
            prompt_id = path.stem[: -(len(active_key) + 1)]
        capture = read_query_capture(path)
        if set(capture.layers) != set(range(layer_count)):
            raise ValueError(f"{path.name}: expected all 42 query layers")
        active = banks[active_key]
        competitors = [banks[key] for key in keys if key != active_key]
        by_layer_alignment: list[np.ndarray] = []
        by_layer_bank_mass: list[np.ndarray] = []
        by_layer_prompt_mass: list[np.ndarray] = []
        for layer in range(layer_count):
            q = capture.layers[layer].query[-1]
            source_layer = (
                layer
                if layer < 24
                else (22 if capture.layers[layer].query.shape[-1] == 256 else 23)
            )
            active_keys = active.keys[source_layer]
            alignments = [
                grouped_alignment_margin(q, active_keys, other.keys[source_layer])
                for other in competitors
            ]
            by_layer_alignment.append(np.mean(np.stack(alignments), axis=0, dtype=np.float32))
            probs = capture.layers[layer].attention[-1].T
            prompt_mass, bank_mass = attention_mass(
                probs, prompt_slots=len(capture.token_ids), bank_slots=active.manifest.slot_count
            )
            q_per_group = q.shape[0] // kv_groups
            by_layer_bank_mass.append(bank_mass.reshape(kv_groups, q_per_group).mean(axis=1))
            by_layer_prompt_mass.append(prompt_mass.reshape(kv_groups, q_per_group).mean(axis=1))
        alignment_rows.append(np.stack(by_layer_alignment))
        bank_mass_rows.append(np.stack(by_layer_bank_mass))
        prompt_mass_rows.append(np.stack(by_layer_prompt_mass))
        capture_records.append(
            {
                "file": path.name,
                "sha256": sha(path),
                "prompt_id": prompt_id,
                "active_bank": active_key,
                "prompt_tokens": len(capture.token_ids),
            }
        )

    alignment = np.mean(np.stack(alignment_rows), axis=0, dtype=np.float32)
    bank_mass = np.mean(np.stack(bank_mass_rows), axis=0, dtype=np.float32)
    prompt_mass = np.mean(np.stack(prompt_mass_rows), axis=0, dtype=np.float32)
    groups = appendix_c_sparse_selector(
        alignment, bank_mass, prompt_mass, groups_per_layer=1, top_layers=4
    )
    sites = expand_kv_groups(groups, query_heads=8, kv_groups=kv_groups)
    out = {
        "schema_version": 1,
        "protocol_sha256": sha(args.protocol),
        "bank_build_receipt_sha256": sha(args.bank_build),
        "method": (
            "For each D1/D2 prompt and active A/B/control bank, average active-versus-other "
            "bank key-alignment margins by KV group. Average all six captures; choose one "
            "group per layer and then the top four layers, using bank attention mass as a "
            "tie-break; expand each KV group to its four query heads."
        ),
        "capture_records": capture_records,
        "alignment_by_layer_group": alignment.tolist(),
        "bank_mass_by_layer_group": bank_mass.tolist(),
        "prompt_mass_by_layer_group": prompt_mass.tolist(),
        "selected_kv_groups": [list(pair) for pair in groups],
        "selected_query_sites": [list(pair) for pair in sites],
        "common_to_all_bank_identities": True,
        "no_generation_calls_used": True,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
