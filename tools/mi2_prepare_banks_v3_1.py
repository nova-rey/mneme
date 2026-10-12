#!/usr/bin/env python3
"""Build only the freshly frozen v3.1 target/reference Gemma KV banks."""

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


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def card_text(plan: dict[str, Any], kind: str) -> tuple[str, str]:
    if kind == "target":
        card = plan["paper_card"]
        text = (
            f"Trigger: {card['trigger']}\nAction: {card['action']}\n"
            f"Trap Check: {card['trap_check']}"
        )
        digest = plan["target_bank_source_text"]["text_sha256"]
        frozen = plan["target_bank_source_text"]["exact_text_utf8"]
    elif kind == "reference":
        text = plan["reference_control_bank"]["exact_text_utf8"]
        digest = plan["reference_control_bank"]["text_sha256"]
        frozen = text
    else:
        raise ValueError("v3.1 builder accepts only target and reference banks")
    if text != frozen or sha_bytes(text.encode("utf-8")) != digest:
        raise ValueError(f"{kind}: exact frozen source-text hash mismatch")
    return text, digest


def assert_local_v3_1_path(path: Path, run_root: Path) -> None:
    resolved = path.resolve()
    root = run_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"v3.1 artifact is outside its run root: {resolved}")
    if any(
        part in {"v1", "v2", "calibration-run-v1", "calibration-run-v2"} for part in resolved.parts
    ):
        raise ValueError(f"prior-version artifact forbidden: {resolved}")


def build_bank(
    plan: dict[str, Any],
    *,
    kind: str,
    input_root: Path,
    capture_root: Path,
    output_root: Path,
    run_root: Path,
) -> dict[str, Any]:
    source, source_digest = card_text(plan, kind)
    raw_text_path = input_root / f"{kind}__raw.txt"
    raw_capture_path = capture_root / f"{kind}__raw.mi1cap"
    for path in (raw_text_path, raw_capture_path):
        assert_local_v3_1_path(path, run_root)
    if raw_text_path.read_text(encoding="utf-8") != source:
        raise ValueError(f"{kind}: raw source bytes differ from the approved freeze")
    raw = MemoryBank.from_native_capture(
        raw_capture_path,
        source_text=source,
        model_sha256=plan["seed_and_runtime"]["gguf_sha256"],
        llama_commit=plan["seed_and_runtime"]["llama_commit"],
        tokenization="llama_tokenize(add_special=true,parse_special=false)",
    )
    if raw.manifest.layer_ids != tuple(range(24)) or raw.manifest.kv_heads_by_layer != (2,) * 24:
        raise ValueError(f"{kind}: native K/V source layer shape differs from freeze")

    components: list[MemoryBank] = []
    template_records: list[dict[str, Any]] = []
    templates = plan["bank_construction"]["templates"]
    if [row["id"] for row in templates] != ["raw", "internal_principles", "private_reasoning_note"]:
        raise ValueError("v3.1 bank template list or order differs from freeze")
    for template in templates:
        template_id = template["id"]
        template_text = template["text"].replace("{BANK_CARD}", source)
        text_path = input_root / f"{kind}__{template_id}.txt"
        capture_path = capture_root / f"{kind}__{template_id}.mi1cap"
        for path in (text_path, capture_path):
            assert_local_v3_1_path(path, run_root)
        if text_path.read_text(encoding="utf-8") != template_text:
            raise ValueError(f"{kind}/{template_id}: wrapper text differs from frozen template")
        captured = MemoryBank.from_native_capture(
            capture_path,
            source_text=template_text,
            model_sha256=plan["seed_and_runtime"]["gguf_sha256"],
            llama_commit=plan["seed_and_runtime"]["llama_commit"],
            tokenization="llama_tokenize(add_special=true,parse_special=false)",
        )
        retained = descriptor_positions_in_wrapped_tokens(raw.token_ids, captured.token_ids)
        component = contextualized_descriptor(captured, raw.token_ids, wrapper_text=template_text)
        if component.token_ids != raw.token_ids[1:]:
            raise ValueError(f"{kind}/{template_id}: retained descriptor token IDs are not aligned")
        components.append(component)
        template_records.append(
            {
                "id": template_id,
                "text_sha256": sha(text_path),
                "capture_sha256": sha(capture_path),
                "full_token_ids": list(captured.token_ids),
                "retained_positions_excluding_bos": list(retained),
                "retained_token_ids": list(component.token_ids),
                "slots": len(component.token_ids),
            }
        )
    if not (components[0].token_ids == components[1].token_ids == components[2].token_ids):
        raise ValueError(f"{kind}: contextualized retained token slots do not align")
    bank = concatenate_banks(concatenate_banks(components[0], components[1]), components[2])
    expected_source_text = "\n\n".join(
        row["text"].replace("{BANK_CARD}", source) for row in templates
    )
    if bank.source_text != expected_source_text:
        raise ValueError(f"{kind}: assembled source text differs from exact v3.1 wrappers")
    if bank.manifest.slot_count != 3 * len(raw.token_ids[1:]):
        raise ValueError(f"{kind}: expected three aligned descriptor-slot copies")

    output_path = output_root / f"{kind}.npz"
    assert_local_v3_1_path(output_path, run_root)
    bank_sha = bank.save(output_path)
    return {
        "kind": kind,
        "source_text_sha256": source_digest,
        "raw_capture_sha256": sha(raw_capture_path),
        "raw_token_ids_with_bos": list(raw.token_ids),
        "raw_content_token_count": len(raw.token_ids[1:]),
        "templates": template_records,
        "slots": bank.manifest.slot_count,
        "layers": list(bank.manifest.layer_ids),
        "head_dim_by_layer": list(bank.manifest.head_dim_by_layer),
        "kv_heads_by_layer": list(bank.manifest.kv_heads_by_layer),
        "npz_path": str(output_path),
        "npz_sha256": bank_sha,
        "native_path": str(output_path.with_suffix(".mi1")),
        "native_sha256": sha(output_path.with_suffix(".mi1")),
        "manifest_path": str(output_path.with_suffix(output_path.suffix + ".json")),
        "manifest_sha256": sha(output_path.with_suffix(output_path.suffix + ".json")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    plan_path = args.plan.resolve()
    plan_sha = sha(plan_path)
    if plan_sha != args.approved_plan_sha256:
        raise ValueError("v3.1 plan differs from approved freeze")
    assert_local_v3_1_path(args.output, run_root)
    if plan_path == run_root or plan_path.is_relative_to(run_root):
        raise ValueError("freeze plan must remain immutable outside the run root")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("calibration_version") != "v3.1":
        raise ValueError("bank builder accepts only v3.1")
    results = {
        kind: build_bank(
            plan,
            kind=kind,
            input_root=run_root / "inputs",
            capture_root=run_root / "captures" / "bank_kv",
            output_root=run_root / "banks",
            run_root=run_root,
        )
        for kind in ("target", "reference")
    }
    payload = {
        "schema_version": 1,
        "status": "FRESH_V3_1_TARGET_REFERENCE_BANKS_BUILT_NO_GENERATION",
        "plan_sha256": plan_sha,
        "prior_version_artifacts_used": False,
        "heldout_items_loaded": False,
        "banks": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"output": str(args.output), "sha256": sha(args.output), "banks": results}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
