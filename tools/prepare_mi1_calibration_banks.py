#!/usr/bin/env python3
"""Build and manifest all host-local MI1 bank variants in the frozen calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import build_calibration_coordinates, canonical_bytes, variant_key
from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.variant import configure_bank


def parse_bank(value: str) -> tuple[str, Path]:
    key, separator, raw_path = value.partition("=")
    if not separator or not key or not raw_path:
        raise argparse.ArgumentTypeError("expected SOURCE_SHA256=NPZ_PATH")
    return key, Path(raw_path)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--site-selection", type=Path, required=True)
    parser.add_argument("--bank", action="append", type=parse_bank, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    args = parser.parse_args()
    plan: dict[str, Any] = json.loads(args.plan.read_text(encoding="utf-8"))
    suite = json.loads(Path("experiments/mi1/fixtures/mi1_frozen_suite.json").read_text())
    coords = build_calibration_coordinates(suite)
    if [row["coordinate_id"] for row in coords] != [
        row["coordinate_id"] for row in plan["coordinates"]
    ]:
        raise ValueError("calibration plan coordinates do not match the frozen builder")
    site = json.loads(args.site_selection.read_text(encoding="utf-8"))
    banks = {source_sha: MemoryBank.load(path) for source_sha, path in args.bank}
    variants: dict[str, dict[str, Any]] = {}
    for coordinate in plan["coordinates"]:
        source_sha = coordinate.get("bank_source_sha256")
        if source_sha is None:
            continue
        config = coordinate.get("bank_config", {})
        key = variant_key(source_sha, config)
        if key in variants:
            continue
        if source_sha not in banks:
            raise ValueError(f"no source bank provided for {source_sha}")
        bank = banks[source_sha]
        if hashlib.sha256(bank.source_text.encode("utf-8")).hexdigest() != source_sha:
            raise ValueError("source bank text does not match frozen coordinate")
        selector_name = config.get("selector")
        selector = site.get(f"{selector_name}_query_sites")
        if not isinstance(selector, list) or not selector:
            raise ValueError(f"frozen query selector is missing: {selector_name}")
        gain = config.get("gain")
        if not isinstance(gain, dict) or not isinstance(gain.get("logit_bias"), (int, float)):
            raise ValueError("bank variant has no frozen numeric logit bias")
        sites = tuple((int(row[0]), int(row[1])) for row in selector)
        configured = configure_bank(
            bank, query_sites=sites, bank_logit_bias=float(gain["logit_bias"])
        )
        name = f"{source_sha[:12]}-{selector_name}-{key[:10]}.mi1"
        local_path = args.output_dir / name
        native_sha = configured.save_native(local_path)
        selector_record = {
            "selector": selector_name,
            "query_sites": [list(row) for row in sites],
            "bank_logit_bias": float(gain["logit_bias"]),
            "relative_prior": gain.get("relative_prior"),
        }
        variants[key] = {
            "source_sha256": source_sha,
            "config": config,
            "local_path": str(local_path),
            "remote_path": f"{args.remote_dir.rstrip('/')}/{name}",
            "native_sha256": native_sha,
            "bank_fingerprint": native_bank_fingerprint(local_path),
            "selector_sha256": sha256(canonical_bytes(selector_record)),
            "selector": selector_record,
        }
    manifest = {
        "schema_version": 1,
        "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(),
        "site_selection_sha256": hashlib.sha256(args.site_selection.read_bytes()).hexdigest(),
        "variant_count": len(variants),
        "variants": variants,
    }
    args.variant_map.parent.mkdir(parents=True, exist_ok=True)
    args.variant_map.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"variants={len(variants)} manifest={args.variant_map}")
    for row in variants.values():
        print(f"{Path(row['local_path']).name} sha256={row['native_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
