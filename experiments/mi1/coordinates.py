"""Expand the frozen MI1 suite into exact, auditable generation coordinates."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _bank_text(statements: list[str]) -> str:
    return "\n".join(f"- {statement}" for statement in statements)


def _messages(system: str, user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _coordinate(
    suite: dict[str, Any],
    *,
    coordinate_id: str,
    suite_name: str,
    messages: list[dict[str, str]] | None,
    metadata: dict[str, Any],
    bank_text: str | None,
    bank_action: str,
    expected: dict[str, Any],
    dependency: str | None = None,
) -> dict[str, Any]:
    generation = suite["generation_config"]
    request = {
        "model": suite["host_model"],
        "messages": messages,
        "stream": False,
        "cache_prompt": suite["cache_prompt"],
        "seed": metadata["seed"],
        "max_tokens": generation["max_tokens"],
        "chat_template_kwargs": generation["chat_template_kwargs"],
        **generation["sampler"],
    }
    return {
        "coordinate_id": coordinate_id,
        "suite": suite_name,
        "metadata": metadata,
        "request": request,
        "request_sha256": hashlib.sha256(
            json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        if messages is not None
        else None,
        "bank_source": bank_text,
        "bank_source_sha256": hashlib.sha256(bank_text.encode("utf-8")).hexdigest()
        if bank_text is not None
        else None,
        "bank_action": bank_action,
        "expected": expected,
        "depends_on_attempt": dependency,
    }


def build_scored_coordinates(suite: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the frozen 268 Test-A/B/C requests in stable execution order."""
    coordinates: list[dict[str, Any]] = []
    test_a = suite["test_a"]
    for fixture in test_a["fixtures"]:
        banks = {
            "latent_A": fixture["bank_A"]["statements"],
            "latent_B": fixture["bank_B"]["statements"],
            "latent_irrelevant": fixture["irrelevant_bank"]["statements"],
        }
        for condition in test_a["conditions"]:
            bank_text = _bank_text(banks[condition]) if condition in banks else None
            user = fixture["recipient_request"]
            if condition in {"visible_A", "visible_B"}:
                user = test_a["condition_wrappers"][condition].format(
                    bank_A=_bank_text(fixture["bank_A"]["statements"]),
                    bank_B=_bank_text(fixture["bank_B"]["statements"]),
                    recipient_request=user,
                )
            for seed in test_a["seeds"]:
                coordinate_id = f"A-{fixture['fixture_id']}-{condition}-{seed}"
                coordinates.append(
                    _coordinate(
                        suite,
                        coordinate_id=coordinate_id,
                        suite_name="test_a",
                        messages=_messages(test_a["system_prompt"], user),
                        metadata={
                            "suite": "test_a",
                            "fixture_id": fixture["fixture_id"],
                            "condition": condition,
                            "seed": seed,
                        },
                        bank_text=bank_text,
                        bank_action="attach" if bank_text is not None else "clear",
                        expected={
                            "answer": fixture["expected_by_condition"][condition],
                            "path": fixture["checks"]["bank_A_path"]
                            if fixture["expected_by_condition"][condition]
                            == fixture["bank_A"]["expected_answer"]
                            else fixture["checks"]["bank_B_path"]
                            if fixture["expected_by_condition"][condition]
                            == fixture["bank_B"]["expected_answer"]
                            else [],
                        },
                    )
                )

    test_b = suite["test_b"]
    irrelevant = test_b["irrelevant_pack"]["statements"]
    for pack in test_b["packs"]:
        for task in pack["tasks"]:
            bank_by_condition = {
                "latent_correct": pack["statements"],
                "latent_irrelevant": irrelevant,
                "latent_topology_altered": pack["topology_altered"],
            }
            for condition in test_b["conditions"]:
                bank_text = (
                    _bank_text(bank_by_condition[condition])
                    if condition in bank_by_condition
                    else None
                )
                user = task["prompt"]
                if condition in {"visible_pack", "text_C"}:
                    user = test_b["condition_wrappers"][condition].format(
                        pack=_bank_text(pack["statements"]), task_prompt=user
                    )
                for seed in test_b["seeds"]:
                    coordinates.append(
                        _coordinate(
                            suite,
                            coordinate_id=f"B-{pack['pack_id']}-{task['task_id']}-{condition}-{seed}",
                            suite_name="test_b",
                            messages=_messages(test_b["system_prompt"], user),
                            metadata={
                                "suite": "test_b",
                                "pack_id": pack["pack_id"],
                                "task_id": task["task_id"],
                                "condition": condition,
                                "seed": seed,
                                "task_native_overlap": task["task_native_overlap"],
                            },
                            bank_text=bank_text,
                            bank_action="attach" if bank_text is not None else "clear",
                            expected={"qualitative_rubric": test_b["rubric"]},
                        )
                    )

    test_c = suite["test_c"]
    test_a_by_id = {fixture["fixture_id"]: fixture for fixture in test_a["fixtures"]}
    first_seed = test_c["seed"]
    for fixture_id in test_c["fixtures"]:
        fixture = test_a_by_id[fixture_id]
        for condition, action, bank_key in (
            ("bank_A", "attach", "bank_A"),
            ("bank_B", "replace", "bank_B"),
            ("disabled", "clear", None),
            ("restored_A", "attach", "bank_A"),
        ):
            bank_text = (
                _bank_text(fixture[bank_key]["statements"]) if bank_key is not None else None
            )
            coordinates.append(
                _coordinate(
                    suite,
                    coordinate_id=f"C-FRESH-{fixture_id}-{condition}-{first_seed}",
                    suite_name="test_c_fresh",
                    messages=_messages(test_a["system_prompt"], fixture["recipient_request"]),
                    metadata={
                        "suite": "test_c",
                        "mode": "fresh_context",
                        "fixture_id": fixture_id,
                        "condition": condition,
                        "seed": first_seed,
                    },
                    bank_text=bank_text,
                    bank_action=action,
                    expected={
                        "answer": fixture["expected_by_condition"][
                            "latent_A"
                            if bank_key == "bank_A"
                            else "latent_B"
                            if bank_key == "bank_B"
                            else "no_bank"
                        ]
                    },
                )
            )

    exchange = test_c["ongoing_exchange"]
    exchange_fixture = test_a_by_id[exchange["fixture_id"]]
    first_id = f"C-ONGOING-{exchange['fixture_id']}-turn-1"
    coordinates.append(
        _coordinate(
            suite,
            coordinate_id=first_id,
            suite_name="test_c_ongoing",
            messages=_messages(test_a["system_prompt"], exchange["turn1_user_prompt"]),
            metadata={
                "suite": "test_c",
                "mode": "ongoing",
                "fixture_id": exchange["fixture_id"],
                "turn": 1,
                "seed": first_seed,
            },
            bank_text=_bank_text(exchange_fixture["bank_A"]["statements"]),
            bank_action="attach",
            expected={"answer": exchange_fixture["bank_A"]["expected_answer"]},
        )
    )
    coordinates.append(
        _coordinate(
            suite,
            coordinate_id=f"C-ONGOING-{exchange['fixture_id']}-turn-2",
            suite_name="test_c_ongoing",
            messages=None,
            metadata={
                "suite": "test_c",
                "mode": "ongoing",
                "fixture_id": exchange["fixture_id"],
                "turn": 2,
                "seed": first_seed,
            },
            bank_text=_bank_text(exchange_fixture["bank_B"]["statements"]),
            bank_action="replace",
            expected={"answer": exchange_fixture["bank_B"]["expected_answer"]},
            dependency=first_id,
        )
    )

    new_bank = test_c["new_bank"]
    new_bank_text = _bank_text(new_bank["source_text"])
    for index, recipient in enumerate(new_bank["recipient_contexts"], start=1):
        coordinates.append(
            _coordinate(
                suite,
                coordinate_id=f"C-NEW-BANK-{index}-{first_seed}",
                suite_name="test_c_new_bank",
                messages=_messages(test_a["system_prompt"], recipient),
                metadata={
                    "suite": "test_c",
                    "mode": "new_bank",
                    "context": index,
                    "seed": first_seed,
                },
                bank_text=new_bank_text,
                bank_action="encode_and_attach",
                expected={"path": new_bank["expected_path"]},
            )
        )

    expected_count = (
        test_a["generation_count"] + test_b["generation_count"] + test_c["generation_count"]
    )
    if len(coordinates) != expected_count:
        raise ValueError(f"coordinate count mismatch: {len(coordinates)} != {expected_count}")
    ids = [row["coordinate_id"] for row in coordinates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate frozen coordinate IDs")
    return coordinates
