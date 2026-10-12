#!/usr/bin/env python3
"""Run only the Root-approved v3.1 MI2 calibration calls.

The runner projects the approved freeze onto the three calibration rows and
never builds execution coordinates from the heldout section. Requests and SSE
events are persisted by EvidenceJournal before the next call is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.bank import MemoryBank, native_bank_fingerprint
from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.native.variant import configure_bank
from experiments.mi1.runner import (
    MI1CoordinateRunner,
    ResolvedBank,
    load_completed_response,
)

PACKAGE_ID = "MI2-PAPER-GUIDANCE-20261011"
PLAN_SHA256 = "6e5ffbc17e2185e99e3dfdfb4d0245cb007c8950ae2461472b8a37b518ab7af1"
SELECTOR_SHA256 = "b370695dbfa0bc94ab705fc204dd51dde19b460a15326ad49d70eecfe66cbe15"
APPROVAL_SHA256 = "cac5ae26e3ad0eaa4876e0f6e20e7283be909f8968b7c418d479f35b92cf4efc"
CALIBRATION_IDS = ("atomic/1-48", "atomic/1-12", "atomic/1-41")
CONDITIONS = (
    "BASELINE",
    "VISIBLE_GUIDANCE",
    "LATENT_TARGET_BANK_BIAS_0.0",
    "LATENT_TARGET_BANK_BIAS_0.5",
    "LATENT_TARGET_BANK_BIAS_1.0",
)
SEEDS = (481001, 481019)
PREFLIGHT_IDS = (
    "v31_preflight_atomic_1-48_baseline_481001_a",
    "v31_preflight_atomic_1-48_baseline_481001_b",
)
MAX_CALLS = 32


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def atomic_json(path: Path, value: Any) -> None:
    atomic_json_write(path, value)


def card_text(plan: dict[str, Any]) -> str:
    card = plan["paper_card"]
    return (
        f"Trigger: {card['trigger']}\nAction: {card['action']}\n"
        f"Trap Check: {card['trap_check']}"
    )


def frozen_execution_inputs(plan: dict[str, Any]) -> dict[str, Any]:
    """Project only calibration fields needed to create authorized requests."""
    calibration = plan["calibration"]
    rows = calibration["items"]
    ids = tuple(row["id"] for row in rows)
    if ids != CALIBRATION_IDS:
        raise ValueError(f"unexpected calibration IDs: {ids}")
    if tuple(calibration["conditions"]) != CONDITIONS:
        raise ValueError("calibration conditions differ from Root authorization")
    if tuple(calibration["seeds"]) != SEEDS:
        raise ValueError("calibration seeds differ from Root authorization")
    sampler = plan["seed_and_runtime"]["sampler"]
    if tuple(sampler["seed_values"]) != SEEDS:
        raise ValueError("sampler seed list differs from Root authorization")
    result = {
        "package_id": plan["package_id"],
        "calibration_version": plan["calibration_version"],
        "items": [
            {
                "id": row["id"],
                "question_utf8": row["question_utf8"],
                "question_sha256": row["question_sha256"],
                "process_score_criteria": row["process_score_criteria"],
                "official_answer_component_count": row[
                    "official_answer_component_count"
                ],
                "official_answers_sha256": row["official_answers_sha256"],
            }
            for row in rows
        ],
        "conditions": list(CONDITIONS),
        "seeds": list(SEEDS),
        "sampler": {
            "temperature": sampler["temperature"],
            "top_k": sampler["top_k"],
            "top_p": sampler["top_p"],
            "min_p": sampler["min_p"],
            "max_tokens": sampler["max_tokens"],
            "stream": sampler["stream"],
        },
        "system_baseline": plan["prompt_contract"]["system_baseline"],
        "visible_system": plan["prompt_contract"]["visible_system"],
        "target_card": card_text(plan),
        "model": plan["seed_and_runtime"]["name"],
        "reasoning": plan["seed_and_runtime"]["reasoning"],
        "cache_prompt": plan["seed_and_runtime"]["prompt_cache"],
        "context_size": plan["seed_and_runtime"]["context_size"],
    }
    if result["package_id"] != PACKAGE_ID or result["calibration_version"] != "v3.1":
        raise ValueError("wrong package or freeze version")
    if result["model"] != "google/gemma-4-E4B-it" or result["reasoning"] != "ON":
        raise ValueError("model or reasoning mode differs from frozen contract")
    if result["cache_prompt"] is not False or result["sampler"]["max_tokens"] != 8192:
        raise ValueError("cache or output allowance differs from frozen contract")
    return result


def assert_no_heldout_fields(value: Any, path: str = "execution") -> None:
    """Fail closed if execution payloads contain heldout material or metadata."""
    if isinstance(value, dict):
        for key, child in value.items():
            if "heldout" in key.lower() or key.lower() in {"test", "test_items"}:
                raise ValueError(f"heldout field leaked into execution inputs: {path}.{key}")
            assert_no_heldout_fields(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_no_heldout_fields(child, f"{path}[{index}]")


def matrix_ids(execution: dict[str, Any]) -> list[str]:
    rows = execution["items"]
    return [
        coordinate_id(row["id"], condition, seed)
        for row in rows
        for seed in execution["seeds"]
        for condition in execution["conditions"]
    ]


def safe_token(text: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in text).strip("_")


def coordinate_id(item_id: str, condition: str, seed: int) -> str:
    return f"v31_cal_{safe_token(item_id)}_{safe_token(condition)}_{seed}"


def response_parts(response: dict[str, Any]) -> tuple[str, str, str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("generation response must contain exactly one choice")
    choice = choices[0]
    message = choice.get("message", {})
    reasoning = message.get("reasoning_content", "")
    answer = message.get("content", "")
    finish = choice.get("finish_reason", "")
    if not all(isinstance(value, str) for value in (reasoning, answer, finish)):
        raise ValueError("reasoning, final answer, or finish reason has invalid type")
    return reasoning, answer, finish


class V31Budget:
    """Atomic call reservation ledger bounded to exactly the approved 32 calls."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        contract = {
            "schema_version": 1,
            "package_id": PACKAGE_ID,
            "plan_sha256": PLAN_SHA256,
            "approval_sha256": APPROVAL_SHA256,
            "max_total_calls": MAX_CALLS,
        }
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if any(existing.get(key) != value for key, value in contract.items()):
                raise ValueError("v3.1 generation budget contract mismatch")
        else:
            atomic_json(path, {**contract, "reservations": []})

    def reserve(self, attempt_id: str, phase: str) -> None:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        reservations = value["reservations"]
        if any(row["attempt_id"] == attempt_id for row in reservations):
            raise FileExistsError(f"generation ID already reserved: {attempt_id}")
        if len(reservations) >= MAX_CALLS:
            raise RuntimeError("Root-approved v3.1 32-call ceiling reached")
        reservations.append({"attempt_id": attempt_id, "phase": phase})
        atomic_json(self.path, value)

    def counts(self) -> dict[str, int]:
        reservations = json.loads(self.path.read_text(encoding="utf-8"))["reservations"]
        return {
            "total": len(reservations),
            "preflight": sum(row["phase"] == "preflight" for row in reservations),
            "matrix": sum(row["phase"] == "matrix" for row in reservations),
        }


def load_approved(
    plan_path: Path, selector_path: Path, approval_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan_bytes = plan_path.read_bytes()
    selector_bytes = selector_path.read_bytes()
    approval_bytes = approval_path.read_bytes()
    for label, data, expected in (
        ("plan", plan_bytes, PLAN_SHA256),
        ("selector", selector_bytes, SELECTOR_SHA256),
        ("approval", approval_bytes, APPROVAL_SHA256),
    ):
        if sha_bytes(data) != expected:
            raise ValueError(f"approved {label} hash mismatch")
    plan = json.loads(plan_bytes)
    selector = json.loads(selector_bytes)
    approval = json.loads(approval_bytes)
    if plan.get("calibration_version") != "v3.1":
        raise ValueError("plan is not v3.1")
    if selector.get("plan_sha256") != PLAN_SHA256 or selector.get(
        "status"
    ) != "V3_1_ATOMIC_SELECTOR_FROZEN_BEFORE_GENERATION":
        raise ValueError("selector is not the approved v3.1 selector")
    if approval.get("status") != "APPROVED_CALIBRATION_GENERATION_ONLY":
        raise ValueError("Root calibration-generation approval is missing")
    if approval.get("authorized_scope", {}).get("matrix_call_count") != 30:
        raise ValueError("approval does not authorize exactly 30 matrix calls")
    if approval.get("authorized_scope", {}).get("total_generation_call_cap") != 32:
        raise ValueError("approval does not authorize the 32-call total cap")
    if approval.get("authorized_scope", {}).get("calibration_items") != list(
        CALIBRATION_IDS
    ):
        raise ValueError("approval calibration IDs differ from frozen v3.1 IDs")
    if approval.get("authorized_scope", {}).get("conditions") != list(CONDITIONS):
        raise ValueError("approval conditions differ from frozen v3.1 conditions")
    if approval.get("authorized_scope", {}).get("seeds") != list(SEEDS):
        raise ValueError("approval seeds differ from frozen v3.1 seeds")
    execution = frozen_execution_inputs(plan)
    assert_no_heldout_fields(execution)
    return plan, selector, approval, execution


class V31CoordinateRunner(MI1CoordinateRunner):
    def __init__(self, *args: Any, execution: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.execution = execution
        self.current_coordinate: dict[str, Any] = {}

    def _post(
        self, route: str, payload: dict[str, Any], *, base_url: str | None = None
    ) -> dict[str, Any]:
        result = super()._post(route, payload, base_url=base_url)
        if route == "/apply-template":
            prompt = result.get("prompt")
            if not isinstance(prompt, str):
                raise ValueError("apply-template omitted exact rendered prompt")
            condition = self.current_coordinate["metadata"]["condition"]
            secret = self.execution["target_card"]
            if condition.startswith("LATENT") and secret in prompt:
                raise ValueError("latent target card leaked into model-visible prompt")
            if condition == "BASELINE" and secret in prompt:
                raise ValueError("target card leaked into baseline prompt")
        return result

    def execute(
        self,
        coordinate: dict[str, Any],
        *,
        phase: str,
        messages: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        assert_no_heldout_fields(coordinate)
        self.current_coordinate = coordinate
        response = super().execute(coordinate, phase=phase, messages=messages)
        _, _, finish = response_parts(response)
        if finish == "length":
            stop = {
                "status": "STOP_TRUNCATED_OUTPUT",
                "attempt_id": coordinate["coordinate_id"],
                "finish_reason": finish,
                "reason": "Frozen 8192-token allowance ended before a complete answer.",
            }
            atomic_json(
                self.journal.root.parent / "MI2_v3_1_Stop_Receipt.json", stop
            )
            raise RuntimeError("v3.1 coordinate truncated; stop without retry")
        return response


def make_coordinate(
    execution: dict[str, Any],
    selector: dict[str, Any],
    plan_sha: str,
    selector_sha: str,
    row: dict[str, Any],
    condition: str,
    seed: int,
) -> dict[str, Any]:
    if condition not in CONDITIONS or row["id"] not in CALIBRATION_IDS:
        raise ValueError("coordinate is outside the approved calibration matrix")
    latent = condition.startswith("LATENT_TARGET_BANK_BIAS_")
    visible = condition == "VISIBLE_GUIDANCE"
    bias = float(condition.removeprefix("LATENT_TARGET_BANK_BIAS_")) if latent else None
    system = execution["visible_system"] if visible else execution["system_baseline"]
    request = {
        "model": execution["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": row["question_utf8"]},
        ],
        "stream": True,
        "cache_prompt": False,
        "seed": seed,
        "temperature": execution["sampler"]["temperature"],
        "top_k": execution["sampler"]["top_k"],
        "top_p": execution["sampler"]["top_p"],
        "min_p": execution["sampler"]["min_p"],
        "max_tokens": execution["sampler"]["max_tokens"],
        "chat_template_kwargs": {"enable_thinking": True},
    }
    target_card = execution["target_card"]
    coordinate = {
        "coordinate_id": coordinate_id(row["id"], condition, seed),
        "request": request,
        "bank_action": "attach" if latent else "clear",
        "bank_source": target_card if latent else None,
        "bank_source_sha256": sha_bytes(target_card.encode("utf-8")) if latent else None,
        "bank_config": {"bank_logit_bias": bias} if latent else {},
        "metadata": {
            "server_role": "mi1_server",
            "phase": "calibration",
            "package_id": PACKAGE_ID,
            "item_id": row["id"],
            "condition": condition,
            "seed": seed,
            "bank_logit_bias": bias,
            "frozen_plan_sha256": plan_sha,
            "selector_sha256": selector_sha,
            "reasoning": "ON",
            "process_score_criteria": row["process_score_criteria"],
            "official_answer_component_count": row[
                "official_answer_component_count"
            ],
            "official_answers_sha256": row["official_answers_sha256"],
        },
    }
    assert_no_heldout_fields(coordinate)
    if request["cache_prompt"] is not False or request["seed"] != seed:
        raise ValueError("matched request control invariant failed")
    if latent and len(selector["selected_query_sites"]) != 16:
        raise ValueError("latent coordinate has unexpected selector site count")
    return coordinate


def response_digest(response: dict[str, Any]) -> str:
    return sha_bytes(
        json.dumps(response_parts(response), ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--bank-root", type=Path, required=True)
    parser.add_argument("--remote-bank-root", required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    parser.add_argument("--budget-path", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18473")
    parser.add_argument("--stage", choices=("dry-run", "preflight", "matrix"), required=True)
    args = parser.parse_args()

    plan, selector, approval, execution = load_approved(
        args.plan, args.selector, args.approval
    )
    plan_sha = sha_file(args.plan)
    selector_sha = sha_file(args.selector)
    target_bank = MemoryBank.load(args.bank_root / "target.npz")
    if execution["target_card"] not in target_bank.source_text:
        raise ValueError("fresh target bank does not carry exact frozen card text")
    sites = tuple(tuple(site) for site in selector["selected_query_sites"])
    if len(sites) != 16 or len(set(sites)) != 16:
        raise ValueError("selector must contain 16 unique Q-head sites")
    variants: dict[float, Path] = {}
    variant_root = args.bank_root / "variants"
    for bias in (0.0, 0.5, 1.0):
        configured = configure_bank(
            target_bank, query_sites=sites, bank_logit_bias=bias
        )
        path = variant_root / f"target-sites-b{bias:.1f}.npz"
        configured.save(path)
        variants[bias] = path.with_suffix(".mi1")

    def resolve(bank_text: str, bank_sha: str, config: dict[str, Any]) -> ResolvedBank:
        if bank_text != execution["target_card"] or bank_sha != sha_bytes(
            execution["target_card"].encode("utf-8")
        ):
            raise ValueError("only exact frozen target card may resolve to a bank")
        bias = float(config["bank_logit_bias"])
        local_path = variants[bias]
        return ResolvedBank(
            path=Path(posixpath.join(args.remote_bank_root, local_path.name)),
            native_sha256=sha_file(local_path),
            bank_fingerprint=native_bank_fingerprint(local_path),
            selector_sha256=selector_sha,
            selector={
                "selected_kv_groups": selector["selected_kv_groups"],
                "selected_query_sites": selector["selected_query_sites"],
                "selection_rule": selector["selection_rule"],
            },
        )

    matrix = [
        make_coordinate(execution, selector, plan_sha, selector_sha, row, condition, seed)
        for row in execution["items"]
        for seed in execution["seeds"]
        for condition in execution["conditions"]
    ]
    if len(matrix) != 30 or len({row["coordinate_id"] for row in matrix}) != 30:
        raise ValueError("v3.1 matrix must contain exactly 30 unique coordinates")
    if args.stage == "dry-run":
        manifest = {
            "status": "DRY_RUN_VALIDATED_NO_GENERATION",
            "package_id": PACKAGE_ID,
            "base_commit": "42084b99912f59c29e70694c5d697660345ec536",
            "runner_script_sha256": sha_file(Path(__file__)),
            "plan_sha256": plan_sha,
            "selector_sha256": selector_sha,
            "approval_sha256": sha_file(args.approval),
            "preflight_ids": list(PREFLIGHT_IDS),
            "matrix_count": len(matrix),
            "matrix_ids": [row["coordinate_id"] for row in matrix],
            "calibration_ids": list(CALIBRATION_IDS),
            "frozen_item_order": list(CALIBRATION_IDS),
            "conditions": list(CONDITIONS),
            "seeds": list(SEEDS),
            "total_call_cap": MAX_CALLS,
            "heldout_fields_in_execution_inputs": False,
            "generation_dispatched": False,
            "variant_banks": {
                str(bias): {
                    "path": str(path),
                    "sha256": sha_file(path),
                    "fingerprint": native_bank_fingerprint(path),
                }
                for bias, path in variants.items()
            },
        }
        atomic_json(args.journal_root.parent / "MI2_v3_1_Generation_Dry_Run.json", manifest)
        print(json.dumps(manifest, indent=2), flush=True)
        return 0

    journal = EvidenceJournal(args.journal_root, hard_call_limit=MAX_CALLS)
    budget = V31Budget(args.budget_path)
    runner = V31CoordinateRunner(
        base_url=args.base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
        execution=execution,
    )
    current = journal.verify()
    print(
        json.dumps({"stage": args.stage, "journal": current, "budget": budget.counts()}),
        flush=True,
    )

    if args.stage == "preflight":
        row = execution["items"][0]
        statuses = {
            record["attempt_id"]: record["status"]
            for record in json.loads((args.journal_root / "index.json").read_text())["attempts"]
        }
        for attempt_id in PREFLIGHT_IDS:
            if attempt_id in statuses and statuses[attempt_id] != "COMPLETE":
                raise RuntimeError(f"uncertain or failed preflight {attempt_id}; do not retry")
        for attempt_id in PREFLIGHT_IDS:
            if attempt_id not in statuses:
                coordinate = make_coordinate(
                    execution, selector, plan_sha, selector_sha, row, "BASELINE", SEEDS[0]
                )
                coordinate["coordinate_id"] = attempt_id
                runner.execute(coordinate, phase="calibration")
                statuses[attempt_id] = "COMPLETE"
        responses = [
            load_completed_response(args.journal_root, attempt_id)
            for attempt_id in PREFLIGHT_IDS
        ]
        digests = [response_digest(value) for value in responses]
        equal = digests[0] == digests[1]
        preflight = {
            "status": "PASS" if equal else "STOP_NONDETERMINISTIC",
            "attempt_ids": list(PREFLIGHT_IDS),
            "response_content_sha256": digests,
            "outputs_byte_identical": equal,
            "compared_fields": ["reasoning_content UTF-8", "final content UTF-8", "finish_reason"],
            "generation_calls_used": budget.counts()["total"],
        }
        out = args.journal_root.parent / "MI2_v3_1_Determinism_Preflight_20261012.json"
        atomic_json(out, preflight)
        print(json.dumps(preflight, indent=2), flush=True)
        return 0 if equal else 2

    preflight_path = args.journal_root.parent / "MI2_v3_1_Determinism_Preflight_20261012.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("outputs_byte_identical") is not True:
        raise RuntimeError("same-condition determinism preflight has not passed")
    statuses = {
        record["attempt_id"]: record["status"]
        for record in json.loads((args.journal_root / "index.json").read_text())["attempts"]
    }
    for coordinate in matrix:
        attempt_id = coordinate["coordinate_id"]
        status = statuses.get(attempt_id)
        if status == "COMPLETE":
            continue
        if status is not None:
            raise RuntimeError(f"coordinate {attempt_id} is uncertain/failed; do not retry")
        runner.execute(coordinate, phase="calibration")
        statuses[attempt_id] = "COMPLETE"
        print(
            json.dumps(
                {
                    "completed": attempt_id,
                    "matrix_complete": sum(
                        1 for key in statuses if key.startswith("v31_cal_")
                    ),
                    "budget": budget.counts(),
                }
            ),
            flush=True,
        )
    print(json.dumps({"journal_verified": journal.verify(), "budget": budget.counts()}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
