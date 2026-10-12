#!/usr/bin/env python3
"""Build frozen MI2 target/reference/irrelevant Gemma K/V banks from captures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.bank import MemoryBank
from experiments.mi1.native.contextual_bank import (
    concatenate_banks,
    contextualized_descriptor,
    descriptor_positions_in_wrapped_tokens,
)

MODEL_SHA = "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"
LLAMA_COMMIT = "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0"
KINDS = ("target", "reference", "irrelevant")
TEMPLATES = ("raw", "internal_principles", "private_reasoning_note")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    source_rows: dict[str, dict[str, Any]] = {}
    args.output_root.mkdir(parents=True, exist_ok=True)
    for kind in KINDS:
        raw_path = args.capture_root / f"{kind}__raw.mi1cap"
        raw_text_path = args.input_root / f"{kind}__raw.txt"
        raw_text = raw_text_path.read_text(encoding="utf-8")
        raw = MemoryBank.from_native_capture(
            raw_path,
            source_text=raw_text,
            model_sha256=MODEL_SHA,
            llama_commit=LLAMA_COMMIT,
            tokenization="llama_tokenize(add_special=true,parse_special=false)",
        )
        expected_layers = tuple(range(24))
        if raw.manifest.layer_ids != expected_layers:
            raise ValueError(f"{kind}: expected KV source layers 0..23")
        if raw.manifest.kv_heads_by_layer != (2,) * 24:
            raise ValueError(f"{kind}: expected two KV heads per source layer")

        components: list[MemoryBank] = []
        template_rows: list[dict[str, Any]] = []
        for template in TEMPLATES:
            text_path = args.input_root / f"{kind}__{template}.txt"
            capture_path = args.capture_root / f"{kind}__{template}.mi1cap"
            text = text_path.read_text(encoding="utf-8")
            captured = MemoryBank.from_native_capture(
                capture_path,
                source_text=text,
                model_sha256=MODEL_SHA,
                llama_commit=LLAMA_COMMIT,
                tokenization="llama_tokenize(add_special=true,parse_special=false)",
            )
            if template == "raw":
                retained = descriptor_positions_in_wrapped_tokens(raw.token_ids, raw.token_ids)
                component = contextualized_descriptor(captured, raw.token_ids, wrapper_text=text)
            else:
                retained = descriptor_positions_in_wrapped_tokens(raw.token_ids, captured.token_ids)
                component = contextualized_descriptor(captured, raw.token_ids, wrapper_text=text)
            if component.token_ids != raw.token_ids[1:]:
                raise ValueError(f"{kind}/{template}: retained token IDs differ from raw card")
            components.append(component)
            template_rows.append(
                {
                    "template": template,
                    "text_path": str(text_path),
                    "text_sha256": sha(text_path),
                    "capture_path": str(capture_path),
                    "capture_sha256": sha(capture_path),
                    "full_token_ids": list(captured.token_ids),
                    "retained_positions_excluding_bos": list(retained),
                    "retained_token_ids": list(component.token_ids),
                    "retained_slot_count": len(component.token_ids),
                    "key_relative_rope_phase": 0,
                }
            )
        if not (components[0].token_ids == components[1].token_ids == components[2].token_ids):
            raise ValueError(f"{kind}: contextual token slots do not align")
        bank = concatenate_banks(concatenate_banks(components[0], components[1]), components[2])
        bank.validate()
        if bank.manifest.slot_count != 3 * len(raw.token_ids[1:]):
            raise ValueError(f"{kind}: expected exactly three card-content slot copies")
        if bank.manifest.layer_ids != expected_layers:
            raise ValueError(f"{kind}: output layer set changed")
        for layer in expected_layers:
            if not (bank.keys[layer].shape == bank.values[layer].shape):
                raise ValueError(f"{kind}: K/V shape mismatch at layer {layer}")
        out = args.output_root / f"{kind}.npz"
        npz_sha = bank.save(out)
        native_path = out.with_suffix(".mi1")
        source_rows[kind] = {
            "raw_card_text": raw_text,
            "raw_card_sha256": hashlib.sha256(raw_text.encode()).hexdigest(),
            "raw_card_token_ids_with_bos": list(raw.token_ids),
            "raw_card_content_token_count": len(raw.token_ids[1:]),
            "templates": template_rows,
            "slots": bank.manifest.slot_count,
            "layers": list(bank.manifest.layer_ids),
            "kv_heads_by_layer": list(bank.manifest.kv_heads_by_layer),
            "head_dim_by_layer": list(bank.manifest.head_dim_by_layer),
            "npz_path": str(out),
            "npz_sha256": npz_sha,
            "native_path": str(native_path),
            "native_sha256": sha(native_path),
            "bank_fingerprint": bank.manifest.__dict__.get("bank_fingerprint"),
        }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "host_model_sha256": MODEL_SHA,
                "llama_commit": LLAMA_COMMIT,
                "tokenization": "llama_tokenize(add_special=true,parse_special=false)",
                "retention": (
                    "raw card content only; wrappers and BOS excluded; "
                    "exact positions retained"
                ),
                "composition_order": list(TEMPLATES),
                "banks": source_rows,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                name: {
                    "slots": row["slots"],
                    "layers": len(row["layers"]),
                    "native_sha256": row["native_sha256"],
                    "shape_layer0": [
                        row["slots"],
                        row["kv_heads_by_layer"][0],
                        row["head_dim_by_layer"][0],
                    ],
                }
                for name, row in source_rows.items()
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
