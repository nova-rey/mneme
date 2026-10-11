#!/usr/bin/env python3
"""Package frozen C14 sources as exact-Q2 selected-site MI1 bank variants."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from experiments.mi1.calibration import variant_key
from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.variant import configure_bank


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--c12-variant-map", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--variant-map", type=Path, required=True)
    args = parser.parse_args()
    plan_raw = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(plan_raw)
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C14 plan must be frozen before bank construction")
    manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    if manifest.get("plan_sha256") != hashlib.sha256(plan_raw).hexdigest():
        raise ValueError("C14 source manifest belongs to a different frozen plan")
    c12 = json.loads(args.c12_variant_map.read_text(encoding="utf-8"))
    selectors: dict[str, tuple[tuple[int, int], ...]] = {}
    for side in ("A", "B"):
        variants = [
            row
            for row in c12["variants"].values()
            if row.get("selector", {}).get("selector") == f"selected_{side}"
            and row.get("selector", {}).get("relative_prior") == 4.0
        ]
        if not variants:
            raise ValueError(f"missing frozen C12 selected_{side} query sites")
        sites = tuple(
            tuple(int(value) for value in pair) for pair in variants[0]["selector"]["query_sites"]
        )
        if any(
            row["selector"]["query_sites"] != [list(pair) for pair in sites] for row in variants
        ):
            raise ValueError(f"C12 selected_{side} query sites are inconsistent")
        selectors[side] = sites

    source_side: dict[str, str] = {}
    for row in plan["coordinates"]:
        digest = row.get("bank_source_sha256")
        if digest is None:
            continue
        side = "A" if "latent_A_" in row["condition"] else "B"
        old = source_side.setdefault(digest, side)
        if old != side:
            raise ValueError("one C14 source was assigned to opposing polarity selectors")
    listed = {row["sha256"]: row for row in manifest["sources"]}
    if set(listed) != set(source_side):
        raise ValueError("C14 source manifest does not exactly match latent calibration sources")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    variants: dict[str, dict[str, Any]] = {}
    source_rows = []
    for digest, side in sorted(source_side.items()):
        source_row = listed[digest]
        source_path = Path(source_row["path"])
        if _sha(source_path) != digest:
            raise ValueError(f"C14 source changed after freeze: {digest}")
        capture = args.capture_dir / f"{digest}.mi1cap"
        if not capture.is_file():
            raise FileNotFoundError(f"missing native C14 capture {capture}")
        base = MemoryBank.from_native_capture(
            capture,
            source_text=source_path.read_text(encoding="utf-8"),
            model_sha256=plan["model"]["gguf_sha256"],
            llama_commit="4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0",
        )
        base_path = args.output_dir / f"{digest}.npz"
        base_npz_sha = base.save(base_path)
        source_rows.append(
            {
                "source_sha256": digest,
                "capture_path": str(capture),
                "capture_sha256": _sha(capture),
                "capture_bytes": capture.stat().st_size,
                "slot_count": base.manifest.slot_count,
                "layer_count": len(base.manifest.layer_ids),
                "base_npz_sha256": base_npz_sha,
                "base_native_sha256": _sha(base_path.with_suffix(".mi1")),
                "selector": f"selected_{side}",
                "query_sites": [list(pair) for pair in selectors[side]],
            }
        )
        for gain in (2.0, 4.0):
            config = {
                "selector": f"selected_{side}",
                "gain": {"logit_bias": math.log(gain), "relative_prior": gain},
            }
            bank = configure_bank(
                base,
                query_sites=selectors[side],
                bank_logit_bias=config["gain"]["logit_bias"],
            )
            key = variant_key(digest, config)
            name = f"{digest[:12]}-{config['selector']}-{gain:g}x.mi1"
            local_path = args.output_dir / name
            native_sha = bank.save_native(local_path)
            selector = {
                "selector": config["selector"],
                "query_sites": [list(pair) for pair in selectors[side]],
                "bank_logit_bias": config["gain"]["logit_bias"],
                "relative_prior": gain,
            }
            variants[key] = {
                "source_sha256": digest,
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
    output = {
        "schema_version": 1,
        "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
        "source_manifest_sha256": _sha(args.source_manifest),
        "c12_selector_map_sha256": _sha(args.c12_variant_map),
        "source_count": len(source_rows),
        "variant_count": len(variants),
        "sources": source_rows,
        "variants": variants,
    }
    args.variant_map.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.variant_map.with_suffix(args.variant_map.suffix + ".tmp")
    tmp.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(args.variant_map)
    print(json.dumps({"sources": len(source_rows), "variants": len(variants)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
