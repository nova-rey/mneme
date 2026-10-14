"""Build frozen Qwen3 selector/bias copies of the three MI4 side banks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.native.native_selector_patch import patch_native_bank_selector

BANKS = ("A_resilience", "B_simplicity", "irrelevant_visual_composition")
BIASES = (0.5, 1.0)


def build_variants(
    *,
    bank_root: Path,
    selector_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    selector = json.loads(selector_path.read_text(encoding="utf-8"))
    sites = tuple((int(layer), int(head)) for layer, head in selector["selected_query_sites"])
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for bank_name in BANKS:
        source = bank_root / f"{bank_name}.mi1"
        for bias in BIASES:
            destination = output_root / f"{bank_name}__bias-{bias:.1f}.mi1"
            patch_native_bank_selector(
                source,
                destination,
                query_sites=sites,
                bank_logit_bias=bias,
                layer_count=36,
                query_head_count=32,
            )
            rows.append(
                {
                    "bank": bank_name,
                    "bias": bias,
                    "path": str(destination),
                    "size_bytes": destination.stat().st_size,
                    "sha256": _sha256(destination),
                }
            )
    receipt = {
        "schema_version": 1,
        "selector_sha256": _sha256(selector_path),
        "source_bank_hashes": {
            name: _sha256(bank_root / f"{name}.mi1") for name in BANKS
        },
        "query_sites": [[layer, head] for layer, head in sites],
        "architecture": {"layers": 36, "query_heads": 32},
        "variants": rows,
    }
    receipt_path = output_root / "variants.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--banks", type=Path, required=True)
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = build_variants(
        bank_root=args.banks, selector_path=args.selector, output_root=args.output
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
