#!/usr/bin/env python3
"""Execute only the frozen MI2 calibration matrix with a durable call journal."""

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
from experiments.mi1.native.evidence import EvidenceJournal
from experiments.mi1.native.variant import configure_bank
from experiments.mi1.runner import (
    GenerationBudget,
    MI1CoordinateRunner,
    ResolvedBank,
    load_completed_response,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class MI2Runner(MI1CoordinateRunner):
    def execute(self, coordinate: dict[str, Any], *, phase: str, messages=None):
        self._current_coordinate = coordinate
        return super().execute(coordinate, phase=phase, messages=messages)

    def _post(self, route: str, payload: dict[str, Any], *, base_url=None):
        result = super()._post(route, payload, base_url=base_url)
        if route == "/apply-template":
            prompt = result.get("prompt")
            if not isinstance(prompt, str):
                raise ValueError("apply-template omitted exact prompt")
            coordinate = getattr(self, "_current_coordinate", {})
            condition = coordinate.get("metadata", {}).get("condition")
            if condition and condition.startswith("LATENT"):
                secret = coordinate.get("metadata", {}).get("secret_card")
                if not isinstance(secret, str) or secret in prompt:
                    raise ValueError("secret bank card leaked into the model-visible prompt")
            if condition in {"BASELINE", "VISIBLE_GUIDANCE"} and condition == "BASELINE":
                if "Trigger: " in prompt or "Trap Check: " in prompt:
                    raise ValueError("bank card marker unexpectedly appears in baseline prompt")
        return result


def response_text(response: dict[str, Any]) -> tuple[str, str, str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("generation response did not contain exactly one choice")
    choice = choices[0]
    message = choice.get("message", {})
    reasoning = message.get("reasoning_content", "")
    answer = message.get("content", "")
    finish = choice.get("finish_reason", "")
    if not isinstance(reasoning, str) or not isinstance(answer, str) or not isinstance(finish, str):
        raise ValueError("reasoning, answer, or finish reason has unexpected type")
    return reasoning, answer, finish


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--selector", type=Path, required=True)
    parser.add_argument("--bank-root", type=Path, required=True)
    parser.add_argument("--remote-bank-root", required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    parser.add_argument("--budget-path", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18473")
    parser.add_argument("--stage", choices=("preflight", "matrix"), required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    selector = json.loads(args.selector.read_text(encoding="utf-8"))
    if selector.get("heldout_queries_used") is not False:
        raise ValueError("selector must be calibration-only")
    if selector.get("status") != "CALIBRATION_SELECTOR_FROZEN_BEFORE_GENERATION":
        raise ValueError("selector freeze status is missing")
    sites = tuple(tuple(site) for site in selector["selected_query_sites"])
    if len(sites) != 16:
        raise ValueError("selector must expand four KV groups into sixteen Q sites")

    target_bank = MemoryBank.load(args.bank_root / "target.npz")
    target_text = plan["guidance_source"]["bank_card"]
    secret_card = (
        f"Trigger: {target_text['trigger']}\nAction: {target_text['action']}\n"
        f"Trap Check: {target_text['trap_check']}"
    )
    if target_bank.source_text.count(secret_card) == 0:
        raise ValueError("target bank does not carry the exact frozen card")
    variants: dict[float, Path] = {}
    selector_record = {
        "selection_rule": selector["selection_rule"],
        "selected_kv_groups": selector["selected_kv_groups"],
        "selected_query_sites": selector["selected_query_sites"],
        "source_kv_mapping": selector["query_to_kv_source_mapping"],
    }
    selector_sha = sha(
        json.dumps(
            selector_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    for bias in (0.0, 0.5, 1.0):
        variant = configure_bank(target_bank, query_sites=sites, bank_logit_bias=bias)
        path = args.bank_root / f"target-sites-b{bias:.1f}.npz"
        variant.save(path)
        variants[bias] = path.with_suffix(".mi1")

    def resolve(bank_text: str, bank_sha: str, config: dict[str, Any]) -> ResolvedBank:
        if sha(bank_text.encode("utf-8")) != bank_sha or bank_sha != sha(
            secret_card.encode("utf-8")
        ):
            raise ValueError("requested bank text/hash is not the frozen target card")
        bias = float(config["bank_logit_bias"])
        local_path = variants[bias]
        # The llama.cpp server resolves bank paths on the MSI, while this
        # coordinator and its durable journal run locally. Keep both identities
        # explicit; the remote copy is hash-verified before dispatch.
        path = Path(posixpath.join(args.remote_bank_root, local_path.name))
        return ResolvedBank(
            path=path,
            native_sha256=sha(local_path.read_bytes()),
            bank_fingerprint=native_bank_fingerprint(local_path),
            selector_sha256=selector_sha,
            selector=selector_record,
        )

    journal = EvidenceJournal(args.journal_root, hard_call_limit=42)
    budget = GenerationBudget(
        args.budget_path,
        prior_calibration_calls=0,
        calibration_limit=42,
        hard_limit=42,
    )
    runner = MI2Runner(
        base_url=args.base_url,
        journal=journal,
        budget=budget,
        bank_resolver=resolve,
    )
    sampler = plan["seed_and_runtime"]["sampler"]

    def coordinate(
        identifier: str, item: dict[str, Any], seed: int, condition: str, bias: float | None
    ):
        if condition == "VISIBLE_GUIDANCE":
            system = plan["prompt_contract"]["visible_system"]
            action, bank_config, bank_source = "clear", {}, None
        else:
            system = plan["prompt_contract"]["system_baseline"]
            if condition.startswith("LATENT"):
                action, bank_config, bank_source = "attach", {"bank_logit_bias": bias}, secret_card
            else:
                action, bank_config, bank_source = "clear", {}, None
        request = {
            "model": plan["seed_and_runtime"]["name"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": item["question"]},
            ],
            "stream": True,
            "cache_prompt": False,
            "seed": seed,
            "temperature": sampler["temperature"],
            "top_k": sampler["top_k"],
            "top_p": sampler["top_p"],
            "min_p": sampler["min_p"],
            "max_tokens": sampler["max_tokens"],
            "chat_template_kwargs": {"enable_thinking": True},
        }
        return {
            "coordinate_id": identifier,
            "request": request,
            "bank_action": action,
            "bank_source": bank_source,
            "bank_source_sha256": None if bank_source is None else sha(bank_source.encode()),
            "bank_config": bank_config,
            "metadata": {
                "server_role": "mi1_server",
                "phase": "calibration",
                "item_id": item["id"],
                "condition": condition,
                "seed": seed,
                "bank_logit_bias": bias,
                "secret_card": secret_card,
                "frozen_plan_sha256": sha(args.plan.read_bytes()),
                "selector_sha256": sha(args.selector.read_bytes()),
            },
        }

    index = journal.verify()
    print(
        json.dumps({"stage": args.stage, "existing_statuses": index, "budget": budget.counts()}),
        flush=True,
    )
    if args.stage == "preflight":
        item = plan["splits"]["calibration"][0]
        ids = ("determinism_preflight_a_4002_481001", "determinism_preflight_b_4002_481001")
        existing = {
            row["attempt_id"]: row["status"]
            for row in json.loads((args.journal_root / "index.json").read_text())["attempts"]
        }
        if any(existing.get(identifier) == "FAILED" for identifier in ids) or any(
            identifier in existing and existing[identifier] != "COMPLETE" for identifier in ids
        ):
            raise RuntimeError("a prior preflight call is uncertain/failed; do not retry")
        for identifier in ids:
            if identifier not in existing:
                runner.execute(
                    coordinate(identifier, item, 481001, "BASELINE", None), phase="calibration"
                )
        a, b = [load_completed_response(args.journal_root, identifier) for identifier in ids]
        equal = response_text(a) == response_text(b)
        record = {
            "status": "PASS" if equal else "STOP_NONDETERMINISTIC",
            "attempt_ids": list(ids),
            "outputs_byte_identical": equal,
            "compared_sha256": [
                sha(
                    json.dumps(
                        response_text(row), ensure_ascii=False, separators=(",", ":")
                    ).encode()
                )
                for row in (a, b)
            ],
        }
        out = args.journal_root.parent / "MI2_Determinism_Preflight_20261011.json"
        out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2), flush=True)
        if not equal:
            return 2
        return 0

    # Do not enter the matrix before both deterministic preflight attempts pass.
    preflight_path = args.journal_root.parent / "MI2_Determinism_Preflight_20261011.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("determinism preflight has not passed")
    existing = {
        row["attempt_id"]: row["status"]
        for row in json.loads((args.journal_root / "index.json").read_text())["attempts"]
    }
    for item in plan["splits"]["calibration"]:
        item_short = item["id"].replace("/", "_")
        for seed in sampler["seed_values"]:
            for condition, bias in (
                ("BASELINE", None),
                ("VISIBLE_GUIDANCE", None),
                ("LATENT_BIAS_0.0", 0.0),
                ("LATENT_BIAS_0.5", 0.5),
                ("LATENT_BIAS_1.0", 1.0),
            ):
                identifier = f"cal_{item_short}_{condition.lower().replace('.', '_')}_{seed}"
                status = existing.get(identifier)
                if status == "COMPLETE":
                    continue
                if status is not None:
                    raise RuntimeError(
                        f"coordinate {identifier} is {status}; do not retry uncertainty"
                    )
                runner.execute(
                    coordinate(identifier, item, seed, condition, bias), phase="calibration"
                )
                existing[identifier] = "COMPLETE"
                print(
                    json.dumps(
                        {"completed": identifier, "count": len(existing), "budget": budget.counts()}
                    ),
                    flush=True,
                )
    print(json.dumps({"journal_verified": journal.verify(), "budget": budget.counts()}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
