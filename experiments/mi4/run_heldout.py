"""Execute the frozen 96-coordinate MI4 held-out matrix after bias freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import MI1CoordinateRunner, ResolvedBank
from experiments.mi4.coordinates import build_heldout_coordinates, validate_heldout_coordinate
from experiments.mi4.qwen_preflight import _request


class HeldoutBudget:
    """Durable held-out generation cap with MI4-only provenance."""

    def __init__(self, path: Path, *, hard_limit: int, protocol_sha256: str):
        self.path = path
        self.hard_limit = hard_limit
        self.protocol_sha256 = protocol_sha256
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            if (
                value.get("protocol_sha256") != protocol_sha256
                or value.get("hard_limit") != hard_limit
            ):
                raise ValueError("MI4 held-out budget contract mismatch")
        else:
            atomic_json_write(
                path,
                {
                    "schema_version": 1,
                    "protocol_sha256": protocol_sha256,
                    "hard_limit": hard_limit,
                    "reservations": [],
                },
            )

    def reserve(self, attempt_id: str, phase: str) -> None:
        if phase != "heldout":
            raise ValueError("MI4 held-out budget accepts heldout calls only")
        value = json.loads(self.path.read_text(encoding="utf-8"))
        reservations = value["reservations"]
        if any(row["attempt_id"] == attempt_id for row in reservations):
            raise FileExistsError(f"MI4 generation ID already reserved: {attempt_id}")
        if len(reservations) >= self.hard_limit:
            raise RuntimeError("frozen MI4 held-out call limit reached")
        reservations.append({"attempt_id": attempt_id, "phase": phase})
        atomic_json_write(self.path, value)

    def counts(self) -> dict[str, int]:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        count = len(value["reservations"])
        return {"total": count, "calibration": 0, "scored": count, "confirmation": 0}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_heldout(
    *,
    protocol_path: Path,
    selector_path: Path,
    variant_paths_path: Path,
    variant_manifest_path: Path,
    lifecycle_path: Path,
    calibration_freeze_path: Path,
    output_root: Path,
    base_url: str,
    blind_seed: int = 20261015,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    selector = json.loads(selector_path.read_text(encoding="utf-8"))
    variant_paths = json.loads(variant_paths_path.read_text(encoding="utf-8"))
    variants = json.loads(variant_manifest_path.read_text(encoding="utf-8"))
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    frozen = json.loads(calibration_freeze_path.read_text(encoding="utf-8"))
    if frozen.get("status") != "FROZEN":
        raise ValueError("MI4 held-out inference requires a frozen global calibration bias")
    bias = float(frozen["selected_bias"])
    if bias not in {0.5, 1.0}:
        raise ValueError("frozen MI4 bias must be one of the predeclared candidates")
    protocol_sha = _sha256(protocol_path)
    if frozen.get("protocol_sha256") != protocol_sha:
        raise ValueError("calibration freeze belongs to another MI4 protocol")
    if frozen.get("calibration_blind_seal_sha256") != _sha256(
        calibration_freeze_path.parent / "calibration-blind-seal.json"
    ):
        raise ValueError("calibration freeze does not bind the sealed blind score set")

    variant_rows = {(row["bank"], float(row["bias"])): row for row in variants["variants"]}
    selector_sha = _sha256(selector_path)
    plan = build_heldout_coordinates(protocol)
    if len(plan) != int(protocol["heldout"]["total_heldout_coordinates"]):
        raise ValueError("held-out plan differs from frozen coordinate count")
    for coordinate in plan:
        validate_heldout_coordinate(protocol, coordinate)
    plan_path = output_root / "heldout-plan.json"
    plan_value = {
        "schema_version": 1,
        "protocol_sha256": protocol_sha,
        "selected_bias": bias,
        "calibration_freeze_sha256": _sha256(calibration_freeze_path),
        "coordinates": plan,
    }
    if plan_path.exists() and json.loads(plan_path.read_text(encoding="utf-8")) != plan_value:
        raise ValueError("existing held-out plan differs from the frozen MI4 matrix")
    if not plan_path.exists():
        atomic_json_write(plan_path, plan_value)

    def resolve(source: str, _digest: str, config: dict[str, Any]) -> ResolvedBank:
        actual_bias = float(config["bias"])
        if actual_bias != bias:
            raise ValueError("held-out coordinate requested a non-frozen bank bias")
        key = f"{source}__bias-{bias:.1f}"
        row = variant_rows[(source, bias)]
        return ResolvedBank(
            path=Path(variant_paths[key]),
            native_sha256=row["sha256"],
            bank_fingerprint=lifecycle["variant_fingerprints"][key],
            selector_sha256=selector_sha,
            selector={"sites": selector["selected_query_sites"], "bias": bias},
        )

    journal = EvidenceJournal(output_root / "journal", hard_call_limit=96)
    index = journal._check_index()
    if index["attempts"]:
        raise RuntimeError("held-out journal is non-empty; do not replay calls")
    budget = HeldoutBudget(output_root / "budget.json", hard_limit=96, protocol_sha256=protocol_sha)
    runner = MI1CoordinateRunner(
        base_url=base_url, journal=journal, budget=budget, bank_resolver=resolve
    )
    start_bank_state = _request(base_url.rstrip("/") + "/mi1/bank")
    if start_bank_state.get("enabled"):
        raise RuntimeError("held-out matrix requires the side bank to start disabled")
    prompts_by_id = {row["id"]: row["user"] for row in protocol["heldout"]["prompts"]}

    order = list(range(len(plan)))
    random.Random(blind_seed).shuffle(order)
    blind_ids = {index: f"heldout_{rank + 1:03d}" for rank, index in enumerate(order)}
    blinded_outputs: list[dict[str, Any]] = []
    blind_map: dict[str, dict[str, Any]] = {}
    active_bank = False
    for index, coordinate in enumerate(plan):
        validate_heldout_coordinate(protocol, coordinate)
        bank = coordinate["bank"]
        action = "clear" if bank is None else ("replace" if active_bank else "attach")
        active_bank = bank is not None
        expected_bias = None if bank is None else bias
        source_hash = None if bank is None else variants["source_bank_hashes"][bank]
        call = {
            "coordinate_id": coordinate["coordinate_id"],
            "fixture_id": coordinate["fixture_id"],
            "condition": coordinate["condition"],
            "bank_action": action,
            "bank_source": bank,
            "bank_source_sha256": source_hash,
            "bank_config": {} if bank is None else {"bias": expected_bias},
            "request": coordinate["request"],
            "metadata": {
                "blind_id": blind_ids[index],
                "frozen_plan_sha256": _sha256(plan_path),
                "calibration_freeze_sha256": _sha256(calibration_freeze_path),
                "randomization_seed": blind_seed,
                "order_index": index,
            },
        }
        response = runner.execute(call, phase="heldout")
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        if choice.get("finish_reason") != "stop":
            raise RuntimeError(
                f"held-out coordinate {coordinate['coordinate_id']} finished abnormally; stopped"
            )
        blinded_outputs.append(
            {
                "blind_id": blind_ids[index],
                "fixture_id": coordinate["fixture_id"],
                "user_prompt": prompts_by_id[coordinate["fixture_id"]],
                "reasoning": message.get("reasoning_content", message.get("reasoning", "")),
                "final": message.get("content", ""),
                "finish_reason": choice["finish_reason"],
            }
        )
        blind_map[blind_ids[index]] = {
            "coordinate_id": coordinate["coordinate_id"],
            "fixture_id": coordinate["fixture_id"],
            "seed": coordinate["seed"],
            "thinking": coordinate["thinking"],
            "condition": coordinate["condition"],
            "bank": bank,
            "bias": expected_bias,
            "order_index": index,
        }
        atomic_json_write(output_root / "blind-heldout-outputs.json", blinded_outputs)
        atomic_json_write(output_root / "blind-map.json", blind_map)

    clear_response = _request(base_url.rstrip("/") + "/mi1/bank", {"operation": "clear"})
    final_bank_state = _request(base_url.rstrip("/") + "/mi1/bank")
    if (
        clear_response.get("enabled") is not False
        or final_bank_state.get("enabled") is not False
        or final_bank_state.get("bank_fingerprint")
    ):
        raise RuntimeError("held-out completion did not clear the side bank")

    receipt = {
        "schema_version": 1,
        "protocol_sha256": protocol_sha,
        "calibration_freeze_sha256": _sha256(calibration_freeze_path),
        "heldout_plan_sha256": _sha256(plan_path),
        "calls_expected": 96,
        "calls_completed": len(blinded_outputs),
        "blind_seed": blind_seed,
        "outputs_sha256": _sha256(output_root / "blind-heldout-outputs.json"),
        "mapping_sha256": _sha256(output_root / "blind-map.json"),
        "bank_state_before": start_bank_state,
        "bank_clear_response": clear_response,
        "bank_state_after": final_bank_state,
        "journal_path": str(output_root / "journal"),
        "interpretation": "Frozen held-out MI4 matrix; no developmental MNEME state used.",
    }
    atomic_json_write(output_root / "heldout-receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--variant-paths", type=Path, required=True)
    parser.add_argument("--variant-manifest", type=Path, required=True)
    parser.add_argument("--bank-lifecycle", type=Path, required=True)
    parser.add_argument("--calibration-freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18473")
    args = parser.parse_args()
    print(
        json.dumps(
            run_heldout(
                protocol_path=args.protocol,
                selector_path=args.selector,
                variant_paths_path=args.variant_paths,
                variant_manifest_path=args.variant_manifest,
                lifecycle_path=args.bank_lifecycle,
                calibration_freeze_path=args.calibration_freeze,
                output_root=args.output,
                base_url=args.base_url,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
