#!/usr/bin/env python3
"""Build only the immutable host-side banks required by frozen C11."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes, variant_key
from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.evidence import atomic_json_write
from experiments.mi1.native.variant import configure_bank


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--bank-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    args = parser.parse_args()
    plan_bytes = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_bytes)
    if plan.get("experiment") != "MNEME Phase 4-MI1 C11 query-site diagnostic execution":
        raise ValueError("bank builder requires the frozen C11 execution plan")
    plan_hash = hashlib.sha256(plan_bytes).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    banks: dict[str, MemoryBank] = {}
    variants: dict[str, dict[str, Any]] = {}
    for coordinate in plan["coordinates"]:
        source_hash = coordinate.get("bank_source_sha256")
        if source_hash is None:
            continue
        source_text = coordinate["bank_source"]
        if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != source_hash:
            raise ValueError(f"frozen C11 bank source hash mismatch: {coordinate['coordinate_id']}")
        config = coordinate["bank_config"]
        key = variant_key(source_hash, config)
        if key in variants:
            continue
        base_path = args.bank_root / f"{source_hash}.npz"
        if source_hash not in banks:
            banks[source_hash] = MemoryBank.load(base_path)
        bank = banks[source_hash]
        if bank.source_text != source_text:
            raise ValueError(f"C11 source bank differs from prebuilt bank: {source_hash}")
        selector = config["selector"]
        sites = tuple(
            (int(site[0]), int(site[1]))
            for site in plan["bank_selectors"][selector]["query_sites"]
        )
        logit_bias = float(config["gain"]["logit_bias"])
        configured = configure_bank(bank, query_sites=sites, bank_logit_bias=logit_bias)
        name = f"{source_hash[:12]}-{selector}-{key[:10]}.mi1"
        local_path = args.output_dir / name
        native_hash = configured.save_native(local_path)
        selector_record = {
            "selector": selector,
            "query_sites": [list(site) for site in sites],
            "bank_logit_bias": logit_bias,
        }
        variants[key] = {
            "source_sha256": source_hash,
            "config": config,
            "local_path": str(local_path),
            "remote_path": f"{args.remote_dir.rstrip('/')}/{name}",
            "native_sha256": native_hash,
            "bank_fingerprint": native_bank_fingerprint(local_path),
            "selector_sha256": hashlib.sha256(canonical_bytes(selector_record)).hexdigest(),
            "selector": selector_record,
        }
    manifest = {
        "schema_version": 1,
        "plan_sha256": plan_hash,
        "variant_count": len(variants),
        "source_bank_count": len(banks),
        "variants": variants,
    }
    atomic_json_write(args.variant_map, manifest)
    print(
        json.dumps(
            {
                "source_banks": len(banks),
                "variants": len(variants),
                "variant_map": str(args.variant_map),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
