#!/usr/bin/env python3
"""Validate v3.1 Atomic-only query captures and freeze its Gemma site selector.

This tool deliberately does not discover prompts from prior v1/v2 plans.  Its
calibration inputs come only from the v3.1 freeze's ``calibration.items`` and
all captured artifacts must live under the isolated v3.1 run directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.query_capture import read_query_capture
from experiments.mi1.native.selector import attention_mass
from experiments.mi1.site_calibration import select_query_sites


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def calibration_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only v3.1 calibration rows; never traverse heldout rows."""
    if plan.get("calibration_version") != "v3.1":
        raise ValueError("selector accepts only calibration_version=v3.1")
    rows = plan.get("calibration", {}).get("items")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("v3.1 selector requires exactly three frozen calibration items")
    ids = [row.get("id") for row in rows]
    if ids != ["atomic/1-48", "atomic/1-12", "atomic/1-41"]:
        raise ValueError(f"unexpected v3.1 calibration IDs: {ids}")
    return rows


def assert_v3_1_inputs(paths: Iterable[Path], run_root: Path) -> None:
    """Require selector inputs to be v3.1-local and reject prior-run artifacts."""
    resolved_root = run_root.resolve()
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_relative_to(resolved_root):
            raise ValueError(f"selector input is outside v3.1 run root: {resolved}")
        if any(
            part in {"v1", "v2", "calibration-run-v1", "calibration-run-v2"}
            for part in resolved.parts
        ):
            raise ValueError(f"prior MI2 artifact forbidden as selector input: {resolved}")


def expected_target_text(plan: dict[str, Any]) -> str:
    card = plan["paper_card"]
    expected = (
        f"Trigger: {card['trigger']}\nAction: {card['action']}\nTrap Check: {card['trap_check']}"
    )
    source = plan["target_bank_source_text"]
    if source["exact_text_utf8"] != expected:
        raise ValueError("target bank text does not match frozen card fields")
    if sha_bytes(expected.encode("utf-8")) != source["text_sha256"]:
        raise ValueError("target bank frozen exact-text SHA-256 mismatch")
    return expected


def composed_bank_source_text(plan: dict[str, Any], card_text: str) -> str:
    templates = plan["bank_construction"]["templates"]
    rendered = [template["text"].replace("{BANK_CARD}", card_text) for template in templates]
    if any("{BANK_CARD}" in row for row in rendered):
        raise ValueError("a frozen bank template is missing its card substitution")
    if len(rendered) != 3:
        raise ValueError("v3.1 requires exactly three frozen bank contextualizations")
    return "\n\n".join(rendered)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_bank(
    bank: MemoryBank,
    *,
    expected_card_text: str,
    expected_source_text: str,
    expected_text_sha256: str,
    label: str,
    freeze: dict[str, Any],
) -> None:
    if sha_bytes(expected_card_text.encode("utf-8")) != expected_text_sha256:
        raise ValueError(f"{label}: frozen exact-text SHA-256 mismatch")
    if bank.source_text != expected_source_text:
        raise ValueError(f"{label}: bank contextual source text differs from v3.1 freeze")
    if bank.manifest.model_sha256 != freeze["seed_and_runtime"]["gguf_sha256"]:
        raise ValueError(f"{label}: model hash differs from frozen host")
    if bank.manifest.llama_commit != freeze["seed_and_runtime"]["llama_commit"]:
        raise ValueError(f"{label}: llama.cpp commit differs from frozen host")
    if bank.manifest.layer_ids != tuple(range(24)):
        raise ValueError(f"{label}: expected Gemma4 KV source layers 0..23")
    if bank.manifest.kv_heads_by_layer != (2,) * 24:
        raise ValueError(f"{label}: expected two KV heads on each source layer")
    bank.validate()


def load_v3_1_banks(
    plan: dict[str, Any],
    target_path: Path,
    reference_path: Path,
    run_root: Path,
) -> tuple[MemoryBank, MemoryBank]:
    """Guard provenance before reading either bank payload or sidecar."""
    target_manifest = target_path.with_suffix(target_path.suffix + ".json")
    reference_manifest = reference_path.with_suffix(reference_path.suffix + ".json")
    assert_v3_1_inputs(
        (
            target_path,
            target_manifest,
            target_path.with_suffix(".mi1"),
            reference_path,
            reference_manifest,
            reference_path.with_suffix(".mi1"),
        ),
        run_root,
    )
    target = MemoryBank.load(target_path)
    reference = MemoryBank.load(reference_path)
    target_text = expected_target_text(plan)
    reference_text = plan["reference_control_bank"]["exact_text_utf8"]
    validate_bank(
        target,
        expected_card_text=target_text,
        expected_source_text=composed_bank_source_text(plan, target_text),
        expected_text_sha256=plan["target_bank_source_text"]["text_sha256"],
        label="target",
        freeze=plan,
    )
    validate_bank(
        reference,
        expected_card_text=reference_text,
        expected_source_text=composed_bank_source_text(plan, reference_text),
        expected_text_sha256=plan["reference_control_bank"]["text_sha256"],
        label="reference",
        freeze=plan,
    )
    if target.manifest.slot_count != len(target.token_ids) or reference.manifest.slot_count != len(
        reference.token_ids
    ):
        raise ValueError("bank manifest slot count differs from token IDs")
    if set(target.manifest.layer_ids) != set(reference.manifest.layer_ids):
        raise ValueError("target/reference bank layers differ")
    return target, reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--target-bank", type=Path, required=True)
    parser.add_argument("--reference-bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan_bytes = args.plan.read_bytes()
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    if plan_sha != args.approved_plan_sha256:
        raise ValueError("v3.1 plan hash differs from the approved freeze hash")
    plan = json.loads(plan_bytes)
    items = calibration_items(plan)

    target_manifest = args.target_bank.with_suffix(args.target_bank.suffix + ".json")
    reference_manifest = args.reference_bank.with_suffix(args.reference_bank.suffix + ".json")
    run_inputs = [
        args.target_bank,
        target_manifest,
        args.target_bank.with_suffix(".mi1"),
        args.reference_bank,
        reference_manifest,
        args.reference_bank.with_suffix(".mi1"),
    ]
    captures_by_id: dict[str, Path] = {}
    rendered_by_id: dict[str, Path] = {}
    for item in items:
        name = item["id"].replace("/", "_")
        captures_by_id[item["id"]] = args.run_root / "captures" / "query" / f"query_{name}.mi1qry"
        rendered_by_id[item["id"]] = args.run_root / "rendered" / f"{name}.json"
        run_inputs.extend((captures_by_id[item["id"]], rendered_by_id[item["id"]]))
    assert_v3_1_inputs(run_inputs, args.run_root)

    target, reference = load_v3_1_banks(plan, args.target_bank, args.reference_bank, args.run_root)

    captures: dict[str, Any] = {}
    target_banks: dict[str, MemoryBank] = {}
    records: dict[str, Any] = {}
    for item in items:
        item_id = item["id"]
        capture_path = captures_by_id[item_id]
        rendered_path = rendered_by_id[item_id]
        capture = read_query_capture(capture_path)
        rendered = json.loads(rendered_path.read_text(encoding="utf-8"))
        expected_tokens = tuple(row["id"] for row in rendered["server_tokenization"])
        if capture.token_ids != expected_tokens:
            raise ValueError(f"{item_id}: native capture token IDs differ from server /tokenize")
        if set(capture.layers) != set(range(42)):
            raise ValueError(f"{item_id}: expected query layers 0..41")
        capacities: set[int] = set()
        for layer, row in capture.layers.items():
            if row.query.shape[0] != len(expected_tokens) or row.query.shape[1] != 8:
                raise ValueError(f"{item_id}: unexpected query shape at layer {layer}")
            if row.attention.shape[0:2] != (len(expected_tokens), 8):
                raise ValueError(f"{item_id}: unexpected attention shape at layer {layer}")
            if not np.isfinite(row.query).all() or not np.isfinite(row.attention).all():
                raise ValueError(f"{item_id}: non-finite query/attention at layer {layer}")
            capacity = row.attention.shape[-1] - target.manifest.slot_count
            if capacity < len(expected_tokens):
                raise ValueError(f"{item_id}: cache capacity shorter than exact prompt")
            attention_mass(
                row.attention[-1].T,
                prompt_slots=len(expected_tokens),
                bank_slots=target.manifest.slot_count,
            )
            capacities.add(capacity)
        if len(capacities) != 1:
            raise ValueError(f"{item_id}: attention layers disagree on cache capacity")
        captures[item_id] = capture
        target_banks[item_id] = target
        records[item_id] = {
            "query_capture_sha256": sha(capture_path),
            "rendered_prompt_sha256": rendered["rendered_sha256"],
            "server_token_ids_sha256": hashlib.sha256(
                json.dumps(expected_tokens, separators=(",", ":")).encode()
            ).hexdigest(),
            "token_id_parity": "EXACT",
            "prompt_tokens": len(expected_tokens),
            "target_bank_slots": target.manifest.slot_count,
            "reference_bank_slots": reference.manifest.slot_count,
            "reserved_prompt_cache_capacity": next(iter(capacities)),
            "query_layers": len(capture.layers),
            "query_heads_per_layer": 8,
            "head_dims_by_layer": [
                int(capture.layers[layer].query.shape[-1]) for layer in range(42)
            ],
            "attention_keys_by_layer": [
                int(capture.layers[layer].attention.shape[-1]) for layer in range(42)
            ],
        }

    selected = select_query_sites(captures, target_banks, reference, top_layers=4)
    payload = {
        "schema_version": 1,
        "status": "V3_1_ATOMIC_SELECTOR_FROZEN_BEFORE_GENERATION",
        "plan_sha256": plan_sha,
        "target_bank_npz_sha256": sha(args.target_bank),
        "target_bank_native_sha256": sha(args.target_bank.with_suffix(".mi1")),
        "target_bank_native_fingerprint": native_bank_fingerprint(
            args.target_bank.with_suffix(".mi1")
        ),
        "target_bank_manifest_sha256": sha(target_manifest),
        "reference_bank_npz_sha256": sha(args.reference_bank),
        "reference_bank_native_sha256": sha(args.reference_bank.with_suffix(".mi1")),
        "reference_bank_native_fingerprint": native_bank_fingerprint(
            args.reference_bank.with_suffix(".mi1")
        ),
        "reference_bank_manifest_sha256": sha(reference_manifest),
        "calibration_query_records": records,
        "query_to_kv_source_mapping": [list(row) for row in selected.source_kv_by_query_layer],
        "alignment_margin_by_layer_group": selected.alignment.tolist(),
        "target_attention_mass_by_layer_group": selected.bank_mass.tolist(),
        "prompt_attention_mass_by_layer_group": selected.prompt_mass.tolist(),
        "selected_kv_groups": [list(row) for row in selected.sparse_groups],
        "selected_query_sites": [list(row) for row in selected.sparse_query_sites],
        "selection_rule": (
            "Fresh v3.1 Atomic calibration queries only; Appendix-C Eq.3 target/reference "
            "pre-RoPE K alignment; per-layer top-1 KV group, target-bank attention tie-break, "
            "global top-4 query layers; selected group expands to its four associated Q heads."
        ),
        "prior_version_capture_or_generation_inputs_used": False,
        "heldout_queries_used": False,
        "target_bank_attached_to_query_prefill": True,
        "reference_bank_attached_to_query_prefill": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": sha(args.output),
                "groups": payload["selected_kv_groups"],
                "sites": payload["selected_query_sites"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
