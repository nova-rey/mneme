"""Build frozen Qwen3 MI4 banks from descriptor/context K/V captures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.mi1.native.bank import MemoryBank
from experiments.mi1.native.contextual_bank import (
    concatenate_banks,
    contextualized_descriptor,
    descriptor_positions_in_wrapped_tokens,
)

MODEL_SHA256 = "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5"
LLAMA_COMMIT = "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0"
ARCHITECTURE = "qwen3-4b"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_banks(
    protocol: dict[str, Any], *, capture_dir: Path, output_dir: Path
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: dict[str, Any] = {}
    for bank_name, bank_spec in protocol["neighborhoods"].items():
        descriptor = bank_spec["descriptor_text"]
        raw_path = capture_dir / f"{bank_name}__raw.mi1cap"
        raw = MemoryBank.from_native_capture(
            raw_path,
            source_text=descriptor,
            model_sha256=MODEL_SHA256,
            llama_commit=LLAMA_COMMIT,
            architecture=ARCHITECTURE,
            tokenizer="Qwen3-4B Qwen BPE via pinned llama.cpp",
            tokenization="llama_tokenize(add_special=true,parse_special=false)",
        )
        banks = [raw]
        variants: dict[str, Any] = {
            "raw": {
                "path": str(raw_path),
                "sha256": _sha256(raw_path),
                "slots": raw.manifest.slot_count,
            }
        }
        for template in protocol["bank_construction"]["contextualization"][1:]:
            wrapped_text = template["text"].replace("{BANK_CARD}", descriptor)
            capture_path = capture_dir / f"{bank_name}__{template['id']}.mi1cap"
            wrapped = MemoryBank.from_native_capture(
                capture_path,
                source_text=wrapped_text,
                model_sha256=MODEL_SHA256,
                llama_commit=LLAMA_COMMIT,
                architecture=ARCHITECTURE,
                tokenizer="Qwen3-4B Qwen BPE via pinned llama.cpp",
                tokenization="llama_tokenize(add_special=true,parse_special=false)",
            )
            aligned = contextualized_descriptor(
                wrapped, raw.token_ids, wrapper_text=wrapped_text
            )
            positions = descriptor_positions_in_wrapped_tokens(
                raw.token_ids, wrapped.token_ids
            )
            banks.append(aligned)
            variants[template["id"]] = {
                "path": str(capture_path),
                "sha256": _sha256(capture_path),
                "wrapped_slots": wrapped.manifest.slot_count,
                "descriptor_token_positions": list(positions),
                "retained_descriptor_slots": aligned.manifest.slot_count,
            }
        combined = concatenate_banks(concatenate_banks(banks[0], banks[1]), banks[2])
        output_path = output_dir / f"{bank_name}.npz"
        digest = combined.save(output_path)
        native_path = output_path.with_suffix(".mi1")
        rows[bank_name] = {
            "descriptor_sha256": hashlib.sha256(descriptor.encode("utf-8")).hexdigest(),
            "components": variants,
            "component_slot_counts": [bank.manifest.slot_count for bank in banks],
            "total_slots": combined.manifest.slot_count,
            "layer_ids": list(combined.manifest.layer_ids),
            "head_dim_by_layer": list(combined.manifest.head_dim_by_layer),
            "kv_heads_by_layer": list(combined.manifest.kv_heads_by_layer),
            "npz_path": str(output_path),
            "npz_sha256": digest,
            "native_path": str(native_path),
            "native_sha256": _sha256(native_path),
        }
    slot_counts = {row["total_slots"] for row in rows.values()}
    result = {
        "schema_version": 1,
        "model_sha256": MODEL_SHA256,
        "llama_commit": LLAMA_COMMIT,
        "architecture": ARCHITECTURE,
        "contextualization_recipe": (
            "raw descriptor + descriptor-aligned tokens from internal_principles and "
            "private_reasoning_note"
        ),
        "banks": rows,
        "equal_total_slot_count": len(slot_counts) == 1,
    }
    manifest = output_dir / "bank-build-manifest.json"
    tmp = manifest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(manifest)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    result = build_banks(
        protocol, capture_dir=args.capture_dir, output_dir=args.output_dir
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
