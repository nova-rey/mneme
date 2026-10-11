#!/usr/bin/env python3
"""Build all-head C17 variants from immutable C16 base K/V captures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.c17_allhead_calibration import ALL_HEAD_CONFIG
from experiments.mi1.calibration import canonical_bytes, variant_key
from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.evidence import atomic_json_write
from experiments.mi1.native.variant import configure_bank


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(
    plan: dict[str, Any],
    *,
    plan_sha256: str,
    source_manifest_path: Path,
    base_bank_root: Path,
    output_dir: Path,
    remote_dir: str,
    variant_map_path: Path,
) -> dict[str, Any]:
    sources = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if sources.get("source_count") != 16:
        raise ValueError("C17 must reuse all 16 frozen C16 calibration/held-out sources")
    output_dir.mkdir(parents=True, exist_ok=True)
    variants: dict[str, dict[str, Any]] = {}
    source_rows: list[dict[str, Any]] = []
    for source in sources["sources"]:
        source_hash = source["sha256"]
        source_file = Path(source["path"])
        if sha256(source_file) != source_hash:
            raise ValueError(f"C16 source hash mismatch: {source_file}")
        base_path = base_bank_root / f"{source_hash}.npz"
        bank = MemoryBank.load(base_path)
        if bank.source_text != source_file.read_text(encoding="utf-8"):
            raise ValueError(f"C16 base bank source text mismatch: {source_hash}")
        if len(bank.manifest.layer_ids) != 24:
            raise ValueError(f"C17 expects all 24 KV-producing layer captures: {source_hash}")
        configured = configure_bank(
            bank, query_sites=(), bank_logit_bias=ALL_HEAD_CONFIG["gain"]["logit_bias"]
        )
        variant_id = variant_key(source_hash, ALL_HEAD_CONFIG)
        output_path = output_dir / f"{source_hash[:12]}-allhead-{variant_id[:10]}.mi1"
        native_hash = configured.save_native(output_path)
        selector_record = {
            "selector": ALL_HEAD_CONFIG["selector"],
            "query_sites": [],
            "bank_logit_bias": ALL_HEAD_CONFIG["gain"]["logit_bias"],
        }
        variants[variant_id] = {
            "source_sha256": source_hash,
            "config": ALL_HEAD_CONFIG,
            "local_path": str(output_path),
            "remote_path": f"{remote_dir.rstrip('/')}/{output_path.name}",
            "native_sha256": native_hash,
            "bank_fingerprint": native_bank_fingerprint(output_path),
            "selector_sha256": hashlib.sha256(canonical_bytes(selector_record)).hexdigest(),
            "selector": selector_record,
            "slot_count": configured.manifest.slot_count,
            "layer_ids": list(configured.manifest.layer_ids),
            "source_npz_sha256": sha256(base_path),
        }
        source_rows.append({"source_sha256": source_hash, "base_npz_sha256": sha256(base_path)})
    result = {
        "schema_version": 1,
        "plan_sha256": plan_sha256,
        "source_manifest_sha256": sha256(source_manifest_path),
        "variant_count": len(variants),
        "source_bank_count": len(source_rows),
        "sources": source_rows,
        "variants": variants,
    }
    atomic_json_write(variant_map_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--base-bank-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if plan.get("status") != "FROZEN_BEFORE_GENERATION":
        raise ValueError("C17 design is not frozen")
    result = prepare(
        plan,
        plan_sha256=sha256(args.plan),
        source_manifest_path=args.source_manifest,
        base_bank_root=args.base_bank_root,
        output_dir=args.output_dir,
        remote_dir=args.remote_dir,
        variant_map_path=args.variant_map,
    )
    print(json.dumps({k: result[k] for k in ("plan_sha256", "variant_count", "source_bank_count")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
