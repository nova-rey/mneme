"""Frozen, non-scored site/exposure calibration coordinates for MI1."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

CALIBRATION_SEEDS = (34111, 34133)
CALIBRATION_SYSTEM = (
    "You are solving a small fictional rule task. Use only the relationships "
    "provided in the current context. Do not invent missing rules. Give the "
    "chosen label first, then the complete directed path; if the facts do not "
    "determine a choice, answer unknown."
)

TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "CAL-REL-01",
        "recipient": (
            "Initially only Aster is active. Which of Deyu or Falen can become "
            "active? Give the complete path or say unknown."
        ),
        "bank": (
            "Aster activates Beryl.\n"
            "Beryl activates Corda.\n"
            "Corda makes Deyu available.\n"
            "Only the stated direction applies."
        ),
        "answer": "Deyu",
        "path": ("Aster", "Beryl", "Corda", "Deyu"),
    },
    {
        "task_id": "CAL-REL-02",
        "recipient": (
            "Only Moro is active at the beginning. Does Jori or Keme become "
            "available? Give the complete path or say unknown."
        ),
        "bank": (
            "Moro unlocks Pavi.\n"
            "Pavi enables Wela.\n"
            "Wela releases Jori.\n"
            "Tazu releases Keme."
        ),
        "answer": "Jori",
        "path": ("Moro", "Pavi", "Wela", "Jori"),
    },
    {
        "task_id": "CAL-REL-03",
        "recipient": (
            "Neri is the only starting label. Which of Garo or Tena can be "
            "reached? Give the complete path or say unknown."
        ),
        "bank": (
            "Neri prepares Sulo.\n"
            "Sulo clears Vemi.\n"
            "Vemi permits Garo.\n"
            "Rudo permits Tena."
        ),
        "answer": "Garo",
        "path": ("Neri", "Sulo", "Vemi", "Garo"),
    },
)

IRRELEVANT_BANK = (
    "Fenu marks Vato.\n"
    "Vato records Seki.\n"
    "Seki stores Domi.\n"
    "Domi tags Leri."
)

# The manifest's logit bias is added to every selected bank-slot attention
# logit. Thus exp(bias) is the relative per-slot bank-prior multiplier.
GAIN_LEVELS = {
    "low": {"relative_prior": 0.5, "logit_bias": math.log(0.5)},
    "moderate": {"relative_prior": 1.0, "logit_bias": 0.0},
    "strong": {"relative_prior": 2.0, "logit_bias": math.log(2.0)},
}

CONDITIONS = (
    "no_bank",
    "visible_bank",
    "latent_sparse_low",
    "latent_sparse_moderate",
    "latent_sparse_strong",
    "latent_broad_moderate",
    "latent_irrelevant_sparse_moderate",
)

CALIBRATION_SYSTEM_REVISION_2 = (
    "You are solving a fictional directed-reachability task. The reference relationships "
    "are directed: follow them only from an initially active label, and a label is "
    "reachable only when a complete directed chain connects an initial label to it. "
    "A relationship whose source is not reachable cannot activate its destination. "
    "Use no unstated relationships. Return exactly two lines: "
    "ANSWER: <reachable candidate label, or unknown> and "
    "PATH: <complete label chain separated by ->, or none if unknown>. "
    "Do not omit the path when a candidate is reachable."
)


def build_calibration_framing_revision(
    parent_plan: dict[str, Any], *, parent_sha256: str
) -> dict[str, Any]:
    """Freeze a generic output-format clarification without changing stimuli."""
    coordinates = copy.deepcopy(parent_plan["coordinates"])
    mapping = {
        row["coordinate_id"]: row["coordinate_id"].replace("C1-", "C2-", 1)
        for row in coordinates
    }
    if len(coordinates) != 44 or any(old == new for old, new in mapping.items()):
        raise ValueError("framing revision expects the frozen 44-coordinate C1 plan")
    for row in coordinates:
        old_id = row["coordinate_id"]
        row["coordinate_id"] = mapping[old_id]
        row["metadata"]["parent_coordinate_id"] = old_id
        duplicate_of = row["metadata"].get("duplicate_of")
        if duplicate_of is not None:
            row["metadata"]["duplicate_of"] = mapping[duplicate_of]
        row["request"]["messages"][0]["content"] = CALIBRATION_SYSTEM_REVISION_2
        row["request_sha256"] = hashlib.sha256(canonical_bytes(row["request"])).hexdigest()

    determinism_ids = {
        "primary_no_bank": "C2-CAL-REL-01-no_bank-34111",
        "same_server_replay": "C2-CAL-REL-01-no_bank-34111-duplicate",
        "base_server_replay": "C2-CAL-REL-01-no_bank-34111-base-server",
    }
    return {
        "schema_version": 1,
        "status": "FROZEN_CALIBRATION_REVISION",
        "correction_revision": 2,
        "parent_plan_path": "docs/receipts/MNEME_Phase_4_MI1_Calibration_Correction_20261010.json",
        "parent_plan_sha256": parent_sha256,
        "variant_source_plan_sha256": parent_plan.get("parent_plan_sha256"),
        "reason": (
            "C1 visible-bank controls passed only 1/6. This second bounded calibration "
            "revision clarifies directed reachability and requires an explicit final-answer "
            "path. It changes only the generic system framing; tasks, banks, expected answers, "
            "seeds, sampler, cache policy, exposure candidates, score rubric, and thresholds "
            "are unchanged. C1 outputs remain preserved and exploratory."
        ),
        "correction": {
            "type": "generic_task_framing_revision",
            "system_prompt": CALIBRATION_SYSTEM_REVISION_2,
            "changed_coordinate_count": len(coordinates),
            "unchanged": [
                "recipient task text",
                "visible and latent bank source text",
                "expected labels and directed paths",
                "generation seeds and sampler configuration",
                "bank variants, selectors, and exposure levels",
                "scoring rubric and pass thresholds",
            ],
            "coordinate_mapping": mapping,
            "determinism_coordinate_ids": determinism_ids,
        },
        "generation_budget": {
            "prior_calibration_calls": 8,
            "preserved_failed_call": 1,
            "c1_corrected_matrix_calls": 44,
            "c2_revision_calls": 44,
            "calibration_calls_after_c2": 97,
            "calibration_ceiling": 120,
            "test_a": 144,
            "test_b": 108,
            "test_c": 16,
            "untouched_confirmation_reserve": 48,
            "projected_total_if_gate_passes": 413,
            "hard_total_ceiling": 800,
            "retry_policy": "No automatic retry; every attempted call remains charged.",
        },
        "coordinates": coordinates,
    }


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def variant_key(source_sha256: str, config: dict[str, Any]) -> str:
    """Stable key for a source-bank plus frozen selector/exposure configuration."""
    return hashlib.sha256(
        canonical_bytes({"source_sha256": source_sha256, "config": config})
    ).hexdigest()


def build_calibration_coordinates(suite: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand the frozen 3-task x 2-seed grid plus two exact replay controls.

    The MI1 duplicate checks same-server determinism; the base-server copy
    compares the disabled patch path with the unmodified pinned server. Neither
    replay is a new semantic coordinate.
    """
    generation = suite["generation_config"]
    coordinates: list[dict[str, Any]] = []

    def add(
        *,
        coordinate_id: str,
        task: dict[str, Any],
        seed: int,
        condition: str,
        bank_text: str | None,
        expected: str,
        selector: str,
        gain_name: str | None,
        visible_bank_text: str | None = None,
        duplicate_of: str | None = None,
        server_role: str = "mi1_server",
    ) -> None:
        user_text = task["recipient"]
        if visible_bank_text is not None:
            user_text = (
                f"Reference relationships:\n{visible_bank_text}\n\nQuestion:\n{user_text}"
            )
        messages = [
            {"role": "system", "content": CALIBRATION_SYSTEM},
            {"role": "user", "content": user_text},
        ]
        request = {
            "model": suite["host_model"],
            "messages": messages,
            "stream": True,
            "cache_prompt": False,
            "seed": seed,
            "max_tokens": generation["max_tokens"],
            "chat_template_kwargs": generation["chat_template_kwargs"],
            **generation["sampler"],
        }
        gain = GAIN_LEVELS[gain_name] if gain_name is not None else None
        metadata = {
            "suite": "calibration",
            "task_id": task["task_id"],
            "condition": condition,
            "seed": seed,
            "selector": selector,
            "gain_name": gain_name,
            "gain": gain,
            "visible_bank_sha256": (
                source_hash(visible_bank_text) if visible_bank_text is not None else None
            ),
            "expected_answer": expected,
            "expected_path": list(task["path"])
            if expected == task["answer"]
            else [],
            "duplicate_of": duplicate_of,
            "server_role": server_role,
        }
        config: dict[str, Any] = {"selector": selector, "gain": gain}
        coordinate = {
            "coordinate_id": coordinate_id,
            "suite": "calibration",
            "metadata": metadata,
            "request": request,
            "request_sha256": hashlib.sha256(canonical_bytes(request)).hexdigest(),
            "bank_source": bank_text,
            "bank_source_sha256": source_hash(bank_text) if bank_text is not None else None,
            "bank_action": "attach" if bank_text is not None else "clear",
            "bank_config": config,
            "expected": {
                "answer": expected,
                "path": metadata["expected_path"],
            },
        }
        coordinates.append(coordinate)

    for task in TASKS:
        for condition in CONDITIONS:
            for seed in CALIBRATION_SEEDS:
                if condition == "no_bank":
                    add(
                        coordinate_id=f"{task['task_id']}-{condition}-{seed}",
                        task=task,
                        seed=seed,
                        condition=condition,
                        bank_text=None,
                        expected="unknown",
                        selector="none",
                        gain_name=None,
                    )
                elif condition == "visible_bank":
                    add(
                        coordinate_id=f"{task['task_id']}-{condition}-{seed}",
                        task=task,
                        seed=seed,
                        condition=condition,
                        bank_text=None,
                        expected=task["answer"],
                        selector="none",
                        gain_name=None,
                        visible_bank_text=task["bank"],
                    )
                elif condition == "latent_irrelevant_sparse_moderate":
                    add(
                        coordinate_id=f"{task['task_id']}-{condition}-{seed}",
                        task=task,
                        seed=seed,
                        condition=condition,
                        bank_text=IRRELEVANT_BANK,
                        expected="unknown",
                        selector="sparse",
                        gain_name="moderate",
                    )
                else:
                    selector = "broad" if condition == "latent_broad_moderate" else "sparse"
                    gain_name = condition.rsplit("_", 1)[-1]
                    add(
                        coordinate_id=f"{task['task_id']}-{condition}-{seed}",
                        task=task,
                        seed=seed,
                        condition=condition,
                        bank_text=task["bank"],
                        expected=task["answer"],
                        selector=selector,
                        gain_name=gain_name,
                    )

    # Replay the exact no-bank request once through the MI1 server and once
    # through the untouched base server. These are separate from a repeated
    # MI1-server request so that both patch no-op behavior and same-condition
    # reproducibility are observable.
    duplicate_source = next(
        row
        for row in coordinates
        if row["coordinate_id"] == "CAL-REL-01-no_bank-34111"
    )
    duplicate = json.loads(json.dumps(duplicate_source))
    duplicate["coordinate_id"] = "CAL-REL-01-no_bank-34111-duplicate"
    duplicate["metadata"]["duplicate_of"] = duplicate_source["coordinate_id"]
    coordinates.append(duplicate)

    base_server = json.loads(json.dumps(duplicate_source))
    base_server["coordinate_id"] = "CAL-REL-01-no_bank-34111-base-server"
    base_server["metadata"]["duplicate_of"] = duplicate_source["coordinate_id"]
    base_server["metadata"]["server_role"] = "base_server"
    coordinates.append(base_server)

    if len(coordinates) != 44:
        raise ValueError(f"MI1 calibration matrix must contain 44 calls, got {len(coordinates)}")
    ids = [row["coordinate_id"] for row in coordinates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate MI1 calibration coordinate IDs")
    if any(row["request"]["cache_prompt"] is not False for row in coordinates):
        raise ValueError("all MI1 calibration calls require cache_prompt=false")
    return coordinates
