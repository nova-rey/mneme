#!/usr/bin/env python3
"""Package C15 exact-Q2 role/raw capture variants at frozen C12 sites."""

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
        raise ValueError("C15 plan must be frozen before bank preparation")
    source_manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    if source_manifest.get("plan_sha256") != hashlib.sha256(plan_raw).hexdigest():
        raise ValueError("C15 source manifest belongs to another plan")
    c12 = json.loads(args.c12_variant_map.read_text(encoding="utf-8"))
    selectors: dict[str, tuple[tuple[int, int], ...]] = {}
    for side in ("A", "B"):
        candidates = [
            row
            for row in c12["variants"].values()
            if row.get("selector", {}).get("selector") == f"selected_{side}"
            and row.get("selector", {}).get("relative_prior") == 4.0
        ]
        if not candidates:
            raise ValueError(f"missing C12 selected_{side} sites")
        sites = tuple(
            tuple(int(value) for value in pair) for pair in candidates[0]["selector"]["query_sites"]
        )
        if any(
            row["selector"]["query_sites"] != [list(pair) for pair in sites] for row in candidates
        ):
            raise ValueError(f"C12 selected_{side} sites are inconsistent")
        selectors[side] = sites
    source_side: dict[str, str] = {}
    source_mode: dict[str, str] = {}
    for row in (
        *plan["coordinates"],
        *plan["confirmation_coordinates_frozen_not_authorized_until_gate"],
    ):
        digest = row.get("bank_source_sha256")
        if digest is None:
            continue
        side = "A" if row["condition"].endswith("_A") else "B"
        if digest in source_side and source_side[digest] != side:
            raise ValueError("one bank source is assigned opposing selectors")
        source_side[digest] = side
        mode = row["tokenization_mode"]
        if digest in source_mode and source_mode[digest] != mode:
            raise ValueError("one source has conflicting tokenization modes")
        source_mode[digest] = mode
    listed = {row["sha256"]: row for row in source_manifest["sources"]}
    if set(listed) != set(source_side):
        raise ValueError("C15 source manifest does not exactly match frozen plan")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    variants: dict[str, dict[str, Any]] = {}
    sources = []
    for digest, side in sorted(source_side.items()):
        source = listed[digest]
        if (
            source["tokenization_mode"] != source_mode[digest]
            or _sha(Path(source["path"])) != digest
        ):
            raise ValueError(f"C15 source bytes/mode changed: {digest}")
        capture = args.capture_dir / f"{digest}.mi1cap"
        if not capture.is_file():
            raise FileNotFoundError(f"missing C15 native capture: {capture}")
        mode = source_mode[digest]
        tokenization = (
            "llama_tokenize(add_special=true,parse_special=true)"
            if mode == "chat-special"
            else "llama_tokenize(add_special=true,parse_special=false)"
        )
        base = MemoryBank.from_native_capture(
            capture,
            source_text=Path(source["path"]).read_text(encoding="utf-8"),
            model_sha256=plan["model"]["gguf_sha256"],
            llama_commit=plan["model"]["llama_cpp_commit"],
            tokenization=tokenization,
        )
        base_path = args.output_dir / f"{digest}.npz"
        base_npz_sha = base.save(base_path)
        sources.append(
            {
                "source_sha256": digest,
                "capture_sha256": _sha(capture),
                "capture_bytes": capture.stat().st_size,
                "tokenization_mode": mode,
                "tokenization": tokenization,
                "slot_count": base.manifest.slot_count,
                "layer_count": len(base.manifest.layer_ids),
                "base_npz_sha256": base_npz_sha,
                "base_native_sha256": _sha(base_path.with_suffix(".mi1")),
                "selector": f"selected_{side}",
                "query_sites": [list(pair) for pair in selectors[side]],
            }
        )
        config = {
            "selector": f"selected_{side}",
            "gain": {"logit_bias": math.log(4.0), "relative_prior": 4.0},
        }
        bank = configure_bank(base, query_sites=selectors[side], bank_logit_bias=math.log(4.0))
        name = f"{digest[:12]}-{config['selector']}-4x.mi1"
        native_path = args.output_dir / name
        native_sha = bank.save_native(native_path)
        selector = {
            "selector": config["selector"],
            "query_sites": [list(pair) for pair in selectors[side]],
            "bank_logit_bias": math.log(4.0),
            "relative_prior": 4.0,
        }
        variants[variant_key(digest, config)] = {
            "source_sha256": digest,
            "config": config,
            "local_path": str(native_path),
            "remote_path": f"{args.remote_dir.rstrip('/')}/{name}",
            "native_sha256": native_sha,
            "bank_fingerprint": native_bank_fingerprint(native_path),
            "selector_sha256": hashlib.sha256(
                json.dumps(selector, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "selector": selector,
        }
    value = {
        "schema_version": 1,
        "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
        "source_manifest_sha256": _sha(args.source_manifest),
        "c12_selector_map_sha256": _sha(args.c12_variant_map),
        "sources": sources,
        "variants": variants,
    }
    args.variant_map.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.variant_map.with_suffix(args.variant_map.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.variant_map)
    print(json.dumps({"sources": len(sources), "variants": len(variants)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
