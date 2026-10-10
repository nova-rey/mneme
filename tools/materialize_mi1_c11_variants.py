#!/usr/bin/env python3
"""Materialize C11 selector metadata on the MSI without retransferring K/V banks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from experiments.mi1.native.native_selector_patch import patch_native_bank_selector


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-map", type=Path, required=True)
    parser.add_argument("--base-root", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.variant_map.read_text(encoding="utf-8"))
    materialized = []
    for row in manifest["variants"].values():
        source_hash = row["source_sha256"]
        source = args.base_root / f"{source_hash}.mi1"
        destination = Path(row["remote_path"])
        selector = row["selector"]
        sites = tuple((int(site[0]), int(site[1])) for site in selector["query_sites"])
        patch_native_bank_selector(
            source,
            destination,
            query_sites=sites,
            bank_logit_bias=float(selector["bank_logit_bias"]),
        )
        actual = sha256(destination)
        if actual != row["native_sha256"]:
            raise ValueError(f"materialized C11 bank hash mismatch: {destination}")
        materialized.append({"path": str(destination), "sha256": actual})
    print(json.dumps({"count": len(materialized), "variants": materialized}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
