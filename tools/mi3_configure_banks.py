#!/usr/bin/env python3
"""Apply the single frozen MI3 selector to each bank and gain candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.evidence import atomic_json_write
from experiments.mi1.native.variant import configure_bank


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--site-selection", type=Path, required=True)
    ap.add_argument("--bank-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    args = ap.parse_args()
    protocol: dict[str, Any] = json.loads(args.protocol.read_text(encoding="utf-8"))
    sites_doc = json.loads(args.site_selection.read_text(encoding="utf-8"))
    sites = tuple(tuple(map(int, row)) for row in sites_doc["selected_query_sites"])
    if len(sites) != 16 or len(set(sites)) != 16:
        raise ValueError("MI3 must use exactly 16 unique Q-head sites")
    if not sites_doc.get("common_to_all_bank_identities"):
        raise ValueError("selector receipt does not declare a common selector")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records: dict[str, Any] = {}
    for bank_id in protocol["neighborhoods"]:
        base = MemoryBank.load(args.bank_dir / f"{bank_id}.npz")
        for gain in protocol["calibration"]["global_bias_candidates"]:
            configured = configure_bank(base, query_sites=sites, bank_logit_bias=float(gain))
            safe_gain = str(gain).replace(".", "p")
            name = f"{bank_id}__bias-{safe_gain}"
            path = args.output_dir / f"{name}.mi1"
            configured.save_native(path)
            records[name] = {
                "bank_id": bank_id,
                "gain": float(gain),
                "path": str(path),
                "sha256": sha(path),
                "native_fingerprint": native_bank_fingerprint(path),
                "query_sites": [list(pair) for pair in sites],
                "slot_count": configured.manifest.slot_count,
                "layer_ids": list(configured.manifest.layer_ids),
            }
    atomic_json_write(
        args.receipt,
        {
            "schema_version": 1,
            "protocol_sha256": sha(args.protocol),
            "site_selection_sha256": sha(args.site_selection),
            "common_query_sites": [list(pair) for pair in sites],
            "variants": records,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
