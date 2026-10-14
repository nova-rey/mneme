#!/usr/bin/env python3
"""Build equal-slot MI3 banks from frozen Gemma native K/V captures.

This is an isolated research utility. It does not load MNEME state or call the
generation endpoint. Captures are produced by the pinned local Gemma encoder;
this script retains descriptor-aligned slots in three contextual variants and
concatenates them without averaging.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.contextual_bank import (
    concatenate_banks,
    contextualized_descriptor,
    descriptor_positions_in_wrapped_tokens,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    protocol: dict[str, Any] = json.loads(args.protocol.read_text(encoding="utf-8"))
    host = protocol["host"]
    construction = protocol["bank_construction"]
    args.output_root.mkdir(parents=True, exist_ok=True)
    bank_rows: dict[str, Any] = {}
    expected_source_token_count: int | None = None

    for kind, neighborhood in protocol["neighborhoods"].items():
        source = neighborhood["descriptor_text"]
        raw_text_path = args.input_root / f"{kind}.raw.txt"
        raw_capture_path = args.capture_root / f"{kind}.raw.mi1cap"
        if raw_text_path.read_text(encoding="utf-8") != source:
            raise ValueError(f"{kind}: raw source differs from protocol")
        raw = MemoryBank.from_native_capture(
            raw_capture_path,
            source_text=source,
            model_sha256=host["gguf_sha256"],
            llama_commit=host["llama_cpp_commit"],
        )
        if (
            raw.manifest.layer_ids != tuple(range(24))
            or raw.manifest.kv_heads_by_layer != (2,) * 24
        ):
            raise ValueError(f"{kind}: unexpected Gemma native encoder shape")
        if expected_source_token_count is None:
            expected_source_token_count = len(raw.token_ids)
        elif len(raw.token_ids) != expected_source_token_count:
            raise ValueError("A/B/control raw token counts are not exactly aligned")

        parts: list[MemoryBank] = []
        template_rows: list[dict[str, Any]] = []
        for template in construction["templates"]:
            template_id = template["id"]
            wrapped_text = template["text"].replace("{BANK_CARD}", source)
            text_path = args.input_root / f"{kind}.{template_id}.txt"
            capture_path = args.capture_root / f"{kind}.{template_id}.mi1cap"
            if text_path.read_text(encoding="utf-8") != wrapped_text:
                raise ValueError(f"{kind}/{template_id}: exact wrapper mismatch")
            wrapped = MemoryBank.from_native_capture(
                capture_path,
                source_text=wrapped_text,
                model_sha256=host["gguf_sha256"],
                llama_commit=host["llama_cpp_commit"],
            )
            positions = descriptor_positions_in_wrapped_tokens(raw.token_ids, wrapped.token_ids)
            part = contextualized_descriptor(wrapped, raw.token_ids, wrapper_text=wrapped_text)
            if part.token_ids != raw.token_ids[1:]:
                raise ValueError(f"{kind}/{template_id}: retained descriptor IDs differ")
            parts.append(part)
            template_rows.append(
                {
                    "id": template_id,
                    "wrapper_text_sha256": sha(text_path),
                    "capture_sha256": sha(capture_path),
                    "capture_token_count_including_bos": len(wrapped.token_ids),
                    "retained_positions": list(positions),
                    "retained_token_count": len(part.token_ids),
                }
            )
        if len({len(part.token_ids) for part in parts}) != 1:
            raise ValueError(f"{kind}: contextual retained slots have unequal count")
        bank = concatenate_banks(concatenate_banks(parts[0], parts[1]), parts[2])
        expected_slots = 3 * len(raw.token_ids[1:])
        if bank.manifest.slot_count != expected_slots:
            raise ValueError(
                f"{kind}: expected {expected_slots} slots, got {bank.manifest.slot_count}"
            )
        npz_path = args.output_root / f"{kind}.npz"
        native_path = args.output_root / f"{kind}.mi1"
        npz_sha = bank.save(npz_path)
        native_sha = bank.save_native(native_path)
        bank_rows[kind] = {
            "descriptor_text": source,
            "descriptor_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "raw_token_ids_with_bos": list(raw.token_ids),
            "retained_descriptor_tokens": len(raw.token_ids) - 1,
            "templates": template_rows,
            "slot_count": bank.manifest.slot_count,
            "layer_ids": list(bank.manifest.layer_ids),
            "kv_heads_by_layer": list(bank.manifest.kv_heads_by_layer),
            "head_dim_by_layer": list(bank.manifest.head_dim_by_layer),
            "npz_path": str(npz_path),
            "npz_sha256": npz_sha,
            "native_path": str(native_path),
            "native_sha256": native_sha,
            "native_bank_fingerprint": native_bank_fingerprint(native_path),
        }

    if len({row["slot_count"] for row in bank_rows.values()}) != 1:
        raise ValueError("A/B/control bank slot counts are not equal")
    receipt = {
        "schema_version": 1,
        "protocol_sha256": sha(args.protocol),
        "encoder": host["mi1_encoder_path"],
        "model_sha256": host["gguf_sha256"],
        "llama_commit": host["llama_cpp_commit"],
        "bank_construction": construction,
        "banks": bank_rows,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
