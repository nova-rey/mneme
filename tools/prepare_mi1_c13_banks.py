#!/usr/bin/env python3
"""Prepare C13 broad-head banks and map frozen selected-site variants."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import variant_key
from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.variant import configure_bank


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--c12-variant-map", type=Path, required=True)
    parser.add_argument("--c12-base-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    args = parser.parse_args()
    plan_raw = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_raw)
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C13 plan must be frozen before bank preparation")
    c12_map_raw = args.c12_variant_map.read_bytes()
    c12 = json.loads(c12_map_raw)
    if c12.get("plan_sha256") != plan.get("parent_c12_plan_sha256"):
        raise ValueError("C12 variants do not match the frozen C13 parent")

    selected_keys: set[str] = set()
    broad_sources: dict[str, str] = {}
    for coordinate in plan["coordinates"]:
        source_sha = coordinate.get("bank_source_sha256")
        config = coordinate.get("bank_config", {})
        if source_sha is None or config.get("selector") == "none":
            continue
        if config["selector"] in {"selected_A", "selected_B"}:
            selected_keys.add(variant_key(source_sha, config))
        elif config["selector"] == "all_heads":
            broad_sources[source_sha] = coordinate["bank_source"]
        else:
            raise ValueError(f"unsupported C13 selector: {config.get('selector')}")

    variants: dict[str, dict[str, Any]] = {}
    for key in sorted(selected_keys):
        row = c12["variants"].get(key)
        if row is None:
            raise ValueError(f"missing frozen selected-site C12 variant {key}")
        variants[key] = row

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_sites = tuple((layer, head) for layer in range(42) for head in range(8))
    bias = 1.3862943611198906
    config = {"selector": "all_heads", "gain": {"logit_bias": bias, "relative_prior": 4.0}}
    for source_sha, source_text in sorted(broad_sources.items()):
        if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != source_sha:
            raise ValueError("C13 bank source hash mismatch")
        base_path = args.c12_base_dir / f"{source_sha}.npz"
        base = MemoryBank.load(base_path)
        bank = configure_bank(base, query_sites=all_sites, bank_logit_bias=bias)
        name = f"{source_sha[:12]}-all-heads-4x.mi1"
        local_path = args.output_dir / name
        native_sha = bank.save_native(local_path)
        selector = {
            "selector": "all_heads",
            "query_sites": [list(pair) for pair in all_sites],
            "bank_logit_bias": bias,
            "relative_prior": 4.0,
        }
        key = variant_key(source_sha, config)
        variants[key] = {
            "source_sha256": source_sha,
            "config": config,
            "local_path": str(local_path),
            "remote_path": f"{args.remote_dir.rstrip('/')}/{name}",
            "native_sha256": native_sha,
            "bank_fingerprint": native_bank_fingerprint(local_path),
            "selector_sha256": hashlib.sha256(
                json.dumps(selector, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "selector": selector,
        }
    manifest = {
        "schema_version": 1,
        "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
        "parent_c12_variant_map_sha256": hashlib.sha256(c12_map_raw).hexdigest(),
        "variant_count": len(variants),
        "variants": variants,
    }
    args.variant_map.parent.mkdir(parents=True, exist_ok=True)
    args.variant_map.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"variants": len(variants), "broad_sources": len(broad_sources)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
