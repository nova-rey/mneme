"""Run the frozen, 18-call MI4 Qwen bias calibration with durable evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
)
from experiments.mi4.qwen_preflight import build_generation_request

CONDITIONS = (
    ("no_bank", None, None),
    ("visible_A_resilience", None, None),
    ("visible_B_simplicity", None, None),
    ("latent_A_bias_0.5", "A_resilience", 0.5),
    ("latent_A_bias_1.0", "A_resilience", 1.0),
    ("latent_B_bias_0.5", "B_simplicity", 0.5),
    ("latent_B_bias_1.0", "B_simplicity", 1.0),
    ("latent_irrelevant_bias_0.5", "irrelevant_visual_composition", 0.5),
    ("latent_irrelevant_bias_1.0", "irrelevant_visual_composition", 1.0),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _visible_messages(protocol: dict[str, Any], prompt: dict[str, Any], condition: str):
    user = prompt["user"]
    if condition in {"visible_A_resilience", "visible_B_simplicity"}:
        neighborhood = "A_resilience" if condition.endswith("A_resilience") else "B_simplicity"
        descriptor = protocol["neighborhoods"][neighborhood]["descriptor_text"]
        wrapper = protocol["calibration"]["visible_prompt_wrapper"]
        user = wrapper["prefix"] + descriptor + wrapper["suffix"] + user
    return [
        {"role": "system", "content": protocol["generation"]["system"]},
        {"role": "user", "content": user},
    ]


def build_plan(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand only the frozen D1/D2 × nine-condition × thinking-ON matrix."""
    output: list[dict[str, Any]] = []
    for prompt in protocol["calibration"]["prompts"]:
        for condition, bank, bias in CONDITIONS:
            messages = _visible_messages(protocol, prompt, condition)
            request = build_generation_request(
                messages=messages,
                seed=int(protocol["calibration"]["seed"]),
                thinking=True,
                sampler=protocol["generation"]["sampler"],
            )
            output.append(
                {
                    "coordinate_id": f"cal_{prompt['id']}__{condition}",
                    "fixture_id": prompt["id"],
                    "prompt": prompt["user"],
                    "condition": condition,
                    "bank": bank,
                    "bias": bias,
                    "thinking": True,
                    "request": request,
                }
            )
    if len(output) != protocol["calibration"]["call_count"]:
        raise ValueError("MI4 calibration plan cardinality differs from frozen protocol")
    if any(row["request"]["cache_prompt"] is not False for row in output):
        raise ValueError("MI4 calibration requires cache_prompt=false")
    return output


def run_calibration(
    *,
    protocol_path: Path,
    selector_path: Path,
    variants_path: Path,
    variants_manifest_path: Path,
    lifecycle_path: Path,
    output_root: Path,
    base_url: str,
    blind_seed: int = 20261014,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    selector = json.loads(selector_path.read_text(encoding="utf-8"))
    variants = json.loads(variants_manifest_path.read_text(encoding="utf-8"))
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    variant_files = json.loads(variants_path.read_text(encoding="utf-8"))
    variant_rows = {(row["bank"], float(row["bias"])): row for row in variants["variants"]}
    fingerprints = lifecycle["variant_fingerprints"]
    selector_sha = _sha256(selector_path)
    plan = build_plan(protocol)
    plan_bytes = (json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    output_root.mkdir(parents=True, exist_ok=True)
    plan_path = output_root / "calibration-plan.json"
    plan_value = json.loads(plan_bytes)
    if plan_path.exists() and json.loads(plan_path.read_text(encoding="utf-8")) != plan_value:
        raise ValueError("existing MI4 calibration plan differs from frozen plan")
    if not plan_path.exists():
        atomic_json_write(plan_path, plan_value)

    def resolve(source: str, _digest: str, config: dict[str, Any]) -> ResolvedBank:
        bias = float(config["bias"])
        row = variant_rows[(source, bias)]
        key = f"{source}__bias-{bias:.1f}"
        remote_path = Path(variant_files[key])
        return ResolvedBank(
            path=remote_path,
            native_sha256=row["sha256"],
            bank_fingerprint=fingerprints[key],
            selector_sha256=selector_sha,
            selector={"sites": selector["selected_query_sites"], "bias": bias},
        )

    journal = EvidenceJournal(output_root / "journal", hard_call_limit=18)
    budget = GenerationBudget(
        output_root / "budget.json",
        prior_calibration_calls=0,
        calibration_limit=18,
        hard_limit=18,
    )
    runner = MI1CoordinateRunner(
        base_url=base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    index = journal._check_index()
    if index["attempts"]:
        raise RuntimeError("calibration journal is non-empty; do not rerun coordinates")
    blind_order = list(range(len(plan)))
    random.Random(blind_seed).shuffle(blind_order)
    blind_ids = {index: f"blind_{rank + 1:02d}" for rank, index in enumerate(blind_order)}
    blind_map: dict[str, dict[str, Any]] = {}
    blind_data: list[dict[str, Any]] = []
    for index, coordinate in enumerate(plan):
        bank = coordinate["bank"]
        action = "clear" if bank is None else "attach"
        journal_coordinate = {
            "coordinate_id": coordinate["coordinate_id"],
            "fixture_id": coordinate["fixture_id"],
            "condition": coordinate["condition"],
            "bank_action": action,
            "bank_source": bank,
            "bank_source_sha256": None if bank is None else variants["source_bank_hashes"][bank],
            "bank_config": {} if bank is None else {"bias": coordinate["bias"]},
            "request": coordinate["request"],
            "metadata": {"blind_id": blind_ids[index], "frozen_plan_sha256": plan_sha},
        }
        response = runner.execute(journal_coordinate, phase="calibration")
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        finish = choice.get("finish_reason")
        if finish != "stop":
            raise RuntimeError(
                f"calibration coordinate {coordinate['coordinate_id']} did not finish normally"
            )
        blind_map[blind_ids[index]] = {
            "coordinate_id": coordinate["coordinate_id"],
            "fixture_id": coordinate["fixture_id"],
            "condition": coordinate["condition"],
            "bank": bank,
            "bias": coordinate["bias"],
        }
        blind_data.append(
            {
                "blind_id": blind_ids[index],
                "fixture_id": coordinate["fixture_id"],
                "user_prompt": coordinate["prompt"],
                "reasoning": message.get("reasoning_content", message.get("reasoning", "")),
                "final": message.get("content", ""),
                "finish_reason": finish,
            }
        )
        atomic_json_write(output_root / "blind-calibration-outputs.json", blind_data)
        atomic_json_write(output_root / "blind-map.json", blind_map)

    receipt = {
        "schema_version": 1,
        "protocol_sha256": _sha256(protocol_path),
        "selector_sha256": selector_sha,
        "calibration_plan_sha256": plan_sha,
        "calls_expected": len(plan),
        "calls_completed": len(blind_data),
        "blind_seed": blind_seed,
        "coordinates": [
            {
                "blind_id": blind_ids[index],
                "coordinate_id": row["coordinate_id"],
                "fixture_id": row["fixture_id"],
                "condition": row["condition"],
                "bank": row["bank"],
                "bias": row["bias"],
                "request_sha256": hashlib.sha256(
                    json.dumps(row["request"], ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest(),
            }
            for index, row in enumerate(plan)
        ],
        "journal_path": str(output_root / "journal"),
        "blinded_outputs_path": str(output_root / "blind-calibration-outputs.json"),
        "blinding_map_path": str(output_root / "blind-map.json"),
        "interpretation": "Calibration only; no held-out outputs included.",
    }
    atomic_json_write(output_root / "calibration-receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--variant-paths", type=Path, required=True)
    parser.add_argument("--variant-manifest", type=Path, required=True)
    parser.add_argument("--bank-lifecycle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18473")
    args = parser.parse_args()
    print(
        json.dumps(
            run_calibration(
                protocol_path=args.protocol,
                selector_path=args.selector,
                variants_path=args.variant_paths,
                variants_manifest_path=args.variant_manifest,
                lifecycle_path=args.bank_lifecycle,
                output_root=args.output,
                base_url=args.base_url,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
