#!/usr/bin/env python3
"""Freeze Appendix-C query sites from prefill captures and target/reference banks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from experiments.mi1.native.bank import MemoryBank
from experiments.mi1.native.query_capture import read_query_capture
from experiments.mi1.site_calibration import select_query_sites


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_pair(value: str) -> tuple[str, Path]:
    key, separator, path = value.partition("=")
    if not separator or not key or not path:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    return key, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", action="append", type=parse_pair, required=True)
    parser.add_argument("--target-bank", action="append", type=parse_pair, required=True)
    parser.add_argument("--reference-bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    capture_paths = dict(args.capture)
    bank_paths = dict(args.target_bank)
    if set(capture_paths) != set(bank_paths):
        parser.error("capture and target-bank task names must match")
    captures = {key: read_query_capture(path) for key, path in capture_paths.items()}
    targets = {key: MemoryBank.load(path) for key, path in bank_paths.items()}
    reference = MemoryBank.load(args.reference_bank)
    result = select_query_sites(captures, targets, reference)
    payload = {
        "schema_version": 1,
        "method": "Appendix-C Eq.3 group margin; per-layer top-1 then global top-4",
        "tasks": sorted(captures),
        "capture_sha256": {key: file_sha(path) for key, path in capture_paths.items()},
        "target_bank_native_sha256": {
            key: file_sha(path.with_suffix(".mi1")) for key, path in bank_paths.items()
        },
        "reference_bank_native_sha256": file_sha(args.reference_bank.with_suffix(".mi1")),
        "alignment_margin_by_layer_group": result.alignment.tolist(),
        "target_bank_attention_mass_by_layer_group": result.bank_mass.tolist(),
        "prompt_attention_mass_by_layer_group": result.prompt_mass.tolist(),
        "sparse_groups": [list(row) for row in result.sparse_groups],
        "sparse_query_sites": [list(row) for row in result.sparse_query_sites],
        "broad_groups": [list(row) for row in result.broad_groups],
        "broad_query_sites": [list(row) for row in result.broad_query_sites],
        "source_kv_by_query_layer": [
            list(row) for row in result.source_kv_by_query_layer
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} sha256={file_sha(args.output)} sparse={result.sparse_groups}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
