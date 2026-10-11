#!/usr/bin/env python3
"""Build C12 selected-bank variants from exact-host K/V captures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import variant_key
from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.variant import configure_bank


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--site-selection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    args = parser.parse_args()
    plan_bytes = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_bytes)
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C12 plan is not frozen")
    selector_bytes = args.site_selection.read_bytes()
    selector: dict[str, Any] = json.loads(selector_bytes)
    expected_selector = plan.get("site_selection_sha256")
    if hashlib.sha256(selector_bytes).hexdigest() != expected_selector:
        raise ValueError("C12 site-selection artifact hash mismatch")
    sites = {
        "selected_A": selector["selection"]["aggregate"]["A"]["selected_query_sites"],
        "selected_B": selector["selection"]["aggregate"]["B"]["selected_query_sites"],
    }
    sources: dict[str, str] = {}
    configs_by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for coordinate in plan["coordinates"]:
        source = coordinate.get("bank_source")
        source_hash = coordinate.get("bank_source_sha256")
        if source is None:
            continue
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != source_hash:
            raise ValueError("C12 source text/hash mismatch")
        sources[source_hash] = source
        config = coordinate["bank_config"]
        if config.get("selector") in sites and isinstance(config.get("gain"), dict):
            configs_by_source.setdefault(source_hash, {})[variant_key(source_hash, config)] = config

    args.output_dir.mkdir(parents=True, exist_ok=True)
    variants: dict[str, dict[str, Any]] = {}
    for source_hash, source in sorted(sources.items()):
        capture_path = args.captures / f"{source_hash}.mi1cap"
        base = MemoryBank.from_native_capture(
            capture_path,
            source_text=source,
            model_sha256=plan["model"]["gguf_sha256"],
            llama_commit=plan["model"]["llama_cpp_commit"],
        )
        if base.manifest.slot_count < 4:
            raise ValueError("C12 bank capture is unexpectedly short")
        base_path = args.output_dir / f"{source_hash}.npz"
        base.save(base_path)
        for config in sorted(
            configs_by_source.get(source_hash, {}).values(),
            key=lambda item: (item["selector"], item["gain"]["logit_bias"]),
        ):
            key = variant_key(source_hash, config)
            if key in variants:
                continue
            selector_name = config["selector"]
            query_sites = tuple((int(x[0]), int(x[1])) for x in sites[selector_name])
            bank = configure_bank(
                base,
                query_sites=query_sites,
                bank_logit_bias=float(config["gain"]["logit_bias"]),
            )
            name = f"{source_hash[:12]}-{selector_name}-{key[:10]}.mi1"
            local_path = args.output_dir / name
            native_sha = bank.save_native(local_path)
            selector_record = {
                "selector": selector_name,
                "query_sites": [list(pair) for pair in query_sites],
                "bank_logit_bias": float(config["gain"]["logit_bias"]),
                "relative_prior": float(config["gain"]["relative_prior"]),
            }
            variants[key] = {
                "source_sha256": source_hash,
                "config": config,
                "local_path": str(local_path),
                "remote_path": f"{args.remote_dir.rstrip('/')}/{name}",
                "native_sha256": native_sha,
                "bank_fingerprint": native_bank_fingerprint(local_path),
                "selector_sha256": sha256(
                    json.dumps(selector_record, sort_keys=True, separators=(",", ":")).encode()
                ),
                "selector": selector_record,
            }
    manifest = {
        "schema_version": 1,
        "plan_sha256": sha256(plan_bytes),
        "site_selection_sha256": expected_selector,
        "variant_count": len(variants),
        "variants": variants,
    }
    args.variant_map.parent.mkdir(parents=True, exist_ok=True)
    args.variant_map.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "sources": len(sources),
                "variants": len(variants),
                "variant_map": str(args.variant_map),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
