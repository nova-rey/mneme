#!/usr/bin/env python3
"""Materialize C15's frozen bank strings and tokenization modes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    raw = args.plan.read_bytes()
    plan: dict[str, Any] = json.loads(raw)
    if plan.get("status") != "FROZEN_BEFORE_CALIBRATION_GENERATION":
        raise ValueError("C15 plan must be frozen before source preparation")
    sources: dict[str, dict[str, str]] = {}
    for row in (
        *plan["coordinates"],
        *plan["confirmation_coordinates_frozen_not_authorized_until_gate"],
    ):
        text, digest = row.get("bank_source"), row.get("bank_source_sha256")
        if text is None:
            continue
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != digest:
            raise ValueError(f"source hash mismatch: {row['coordinate_id']}")
        entry = {"text": text, "tokenization_mode": row["tokenization_mode"]}
        old = sources.setdefault(digest, entry)
        if old != entry:
            raise ValueError("same C15 source digest has conflicting tokenization mode")
    args.source_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for digest, entry in sorted(sources.items()):
        path = args.source_dir / f"{digest}.txt"
        temporary = path.with_suffix(".txt.tmp")
        temporary.write_text(entry["text"], encoding="utf-8")
        temporary.replace(path)
        entries.append(
            {
                "sha256": digest,
                "path": str(path),
                "bytes": len(entry["text"].encode("utf-8")),
                "tokenization_mode": entry["tokenization_mode"],
            }
        )
    manifest = {
        "schema_version": 1,
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "source_count": len(entries),
        "sources": entries,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary_manifest.replace(args.manifest)
    print(
        json.dumps(
            {"sources": len(entries), "plan_sha256": manifest["plan_sha256"]}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
