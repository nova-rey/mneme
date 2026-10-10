#!/usr/bin/env python3
"""Compile frozen C3 K/V variants without additional model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import canonical_bytes, variant_key
from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.variant import configure_bank


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_bank(value: str) -> tuple[str, Path]:
    key, separator, path = value.partition("=")
    if not separator or len(key) != 64 or not path:
        raise argparse.ArgumentTypeError("expected SOURCE_SHA256=NPZ_PATH")
    return key, Path(path)


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
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C3 plan is not frozen")
    plan_sha = sha256(args.plan.read_bytes())
    site_bytes = args.site_selection.read_bytes()
    site = json.loads(site_bytes)
    sources = {key: MemoryBank.load(path) for key, path in args.bank}
    variants: dict[str, dict[str, Any]] = {}
    for coordinate in plan["coordinates"]:
        source_sha = coordinate.get("bank_source_sha256")
        if source_sha is None:
            continue
        config = coordinate["bank_config"]
        key = variant_key(source_sha, config)
        if key in variants:
            continue
        bank = sources.get(source_sha)
        if bank is None:
            raise ValueError(f"no frozen C3 bank was supplied for {source_sha}")
        if hashlib.sha256(bank.source_text.encode("utf-8")).hexdigest() != source_sha:
            raise ValueError("encoded source bank text does not match the frozen plan")
        if bank.manifest.model_sha256 != plan["model_gguf_sha256"]:
            raise ValueError("encoded bank was produced from another model")
        selector_name = config["selector"]
        sites = site.get(f"{selector_name}_query_sites")
        if not isinstance(sites, list) or not sites:
            raise ValueError(f"site selector missing from frozen site receipt: {selector_name}")
        bias = float(config["gain"]["logit_bias"])
        configured = configure_bank(
            bank,
            query_sites=tuple((int(row[0]), int(row[1])) for row in sites),
            bank_logit_bias=bias,
        )
        name = f"c3-{source_sha[:12]}-{selector_name}-{key[:10]}.mi1"
        local_path = args.output_dir / name
        native_sha = configured.save_native(local_path)
        selector_record = {
            "selector": selector_name,
            "query_sites": sites,
            "bank_logit_bias": bias,
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
    result = {
        "schema_version": 1,
        "plan_sha256": plan_sha,
        "site_selection_sha256": sha256(site_bytes),
        "source_banks": {
            source_sha: {"path": str(bank_path), "sha256": sha256(bank_path.read_bytes())}
            for source_sha, bank_path in args.bank
        },
        "variant_count": len(variants),
        "variants": variants,
    }
    args.variant_map.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.variant_map.with_suffix(args.variant_map.suffix + ".tmp")
    temporary.write_bytes(canonical_bytes(result) + b"\n")
    os.replace(temporary, args.variant_map)
    print(
        json.dumps(
            {
                "variants": len(variants),
                "manifest_sha256": sha256(args.variant_map.read_bytes()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
