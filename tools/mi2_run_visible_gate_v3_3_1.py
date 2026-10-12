#!/usr/bin/env python3
"""Run the Root-approved MI2 v3.3.1 visible-guidance gate only.

This runner has no bank, selector, latent, or held-out dispatch path. It
supports a network-free dry run, a two-call baseline determinism preflight,
six baseline calls, a frozen baseline-headroom gate, and six conditional
visible-guidance calls followed by post-durability score annotation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import http_json, http_sse

PACKAGE_ID = "MI2-PAPER-GUIDANCE-20261011"
FREEZE_SHA256 = "40cc66141761ab50412800717497b12d5197288aa7930c74b93c4a6d6d8c3690"
APPROVAL_SHA256 = "7a6edf6d72983b541a7f4cd006154592d715a5e2d98d122f38ff9021a28b646f"
CANDIDATE_SHA256 = "f03023d72b9d3ac844cf22c84f156ef3ed30d1ef8c58b0938cf3a9f5fea445e1"
TASK_IDS = ("quantum/1-1041", "quantum/3-3025", "quantum/3-3047")
CONDITIONS = ("BASELINE", "VISIBLE_GUIDANCE")
SEEDS = (481001, 481019)
PREFLIGHT_IDS = (
    "v331_preflight_quantum_1_1041_baseline_481001_a",
    "v331_preflight_quantum_1_1041_baseline_481001_b",
)
MAX_CALLS = 14
MATRIX_COUNT = 12
TARGET_CARD_OPENING = (
    "Trigger: A prompt mixes states, operators, spectra, measurement, and time language"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def assert_no_forbidden_fields(value: Any, path: str = "execution") -> None:
    """Reject latent, held-out, and test material from execution projections."""
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if "heldout" in lowered or "latent" in lowered or lowered in {
                "test",
                "test_items",
                "heldout_embargo",
            }:
                raise ValueError(f"forbidden field in execution projection: {path}.{key}")
            assert_no_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_no_forbidden_fields(child, f"{path}[{index}]")


def load_frozen(
    plan_path: Path, approval_path: Path, candidate_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan_bytes = plan_path.read_bytes()
    approval_bytes = approval_path.read_bytes()
    candidate_bytes = candidate_path.read_bytes()
    if sha256_bytes(plan_bytes) != FREEZE_SHA256:
        raise ValueError("v3.3.1 freeze hash mismatch")
    if sha256_bytes(approval_bytes) != APPROVAL_SHA256:
        raise ValueError("v3.3.1 approval hash mismatch")
    if sha256_bytes(candidate_bytes) != CANDIDATE_SHA256:
        raise ValueError("v3.3.1 candidate hash mismatch")
    freeze = json.loads(plan_bytes)
    approval = json.loads(approval_bytes)
    candidate = json.loads(candidate_bytes)
    if (
        freeze.get("artifact_type") != "MI2_PREHELDOUT_VISIBLE_CALIBRATION_FREEZE"
        or freeze.get("package_id") != PACKAGE_ID
        or freeze.get("freeze_id") != "MI2-CAL-V3.3.1-20261012"
    ):
        raise ValueError("wrong package or candidate version")
    if freeze.get("candidate", {}).get("sha256") != CANDIDATE_SHA256:
        raise ValueError("freeze candidate hash reference mismatch")
    if freeze.get("frozen_candidate") != candidate:
        raise ValueError("embedded frozen candidate differs from canonical candidate file")
    if freeze.get("immutability", {}).get("candidate_content_frozen") is not True:
        raise ValueError("freeze does not mark its candidate content immutable")
    if approval.get("approval_status") != (
        "APPROVED_FOR_FROZEN_VISIBLE_GUIDANCE_CALIBRATION_ONLY_NOT_DISPATCHED"
    ):
        raise ValueError("Root visible-gate approval is missing")
    if (
        approval.get("candidate", {}).get("sha256") != CANDIDATE_SHA256
        or approval.get("freeze", {}).get("sha256") != FREEZE_SHA256
        or approval.get("authorized_limits", {}).get("maximum_calls") != MAX_CALLS
        or approval.get("authorized_limits", {}).get("preflight_calls") != 2
        or approval.get("authorized_limits", {}).get("baseline_calls") != 6
        or approval.get("authorized_limits", {}).get("conditional_visible_calls") != 6
        or approval.get("explicit_exclusions")
        != freeze.get("dispatch_boundary", {}).get("not_authorized")
    ):
        raise ValueError("approval does not match this exact v3.3.1 runner scope")
    if candidate.get("package_id") != PACKAGE_ID or candidate.get("candidate_version") != "v3.3.1":
        raise ValueError("candidate is not the approved v3.3.1 artifact")
    return freeze, approval, candidate


def execution_projection(plan: dict[str, Any]) -> dict[str, Any]:
    """Copy only the frozen calibration tasks and visible-gate request settings."""
    rows = plan.get("candidate_tasks")
    if not isinstance(rows, list) or tuple(row.get("id") for row in rows) != TASK_IDS:
        raise ValueError("candidate task IDs/order differ from approved v3.3.1 freeze")
    prompts = plan["prompt_contract"]
    runtime = prompts["runtime"]
    if (
        prompts.get("reasoning") != "ON"
        or prompts.get("cache_prompt") is not False
        or prompts.get("generation_seeds") != list(SEEDS)
        or runtime.get("model") != "google/gemma-4-E4B-it"
        or prompts.get("cache_prompt") is not False
        or runtime.get("max_tokens") != 8192
        or runtime.get("context_size") != 8192
        or runtime.get("gguf_sha256")
        != "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"
        or runtime.get("llama_cpp_commit")
        != "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0"
    ):
        raise ValueError("runtime settings differ from the approved frozen contract")
    source_card = plan["source_card_choice"]
    result = {
        "package_id": plan["package_id"],
        "candidate_version": plan["candidate_version"],
        "tasks": [
            {
                "id": row["id"],
                "question": row["question"],
                "question_sha256": row["question_sha256"],
                "process_score_criteria_binary": row["process_score_criteria_binary"],
                "answer_key_components": row["answer_key_components"],
                "answer_key_sha256": row["answer_key_sha256"],
            }
            for row in rows
        ],
        "conditions": list(CONDITIONS),
        "seeds": list(SEEDS),
        "baseline_system_text": source_card["baseline_system_text_exact"],
        "visible_system_text": source_card["visible_system_text_exact"],
        "reasoning": prompts["reasoning"],
        "cache_prompt": prompts["cache_prompt"],
        "runtime": {
            "model": runtime["model"],
            "gguf_sha256": runtime["gguf_sha256"],
            "llama_cpp_commit": runtime["llama_cpp_commit"],
            "temperature": runtime["temperature"],
            "top_k": runtime["top_k"],
            "top_p": runtime["top_p"],
            "min_p": runtime["min_p"],
            "max_tokens": runtime["max_tokens"],
            "context_size": runtime["context_size"],
            "reasoning_format": runtime["reasoning_format"],
            "gpu_layers": runtime["gpu_layers"],
            "batch_size": runtime["batch_size"],
            "ubatch_size": runtime["ubatch_size"],
            "threads": runtime["threads"],
            "threads_batch": runtime["threads_batch"],
            "parallel": runtime["parallel"],
        },
        "preflight": {
            "task_id": "quantum/1-1041",
            "condition": "BASELINE",
            "seed": SEEDS[0],
            "attempt_ids": list(PREFLIGHT_IDS),
        },
    }
    assert_no_forbidden_fields(result)
    if result["visible_system_text"] == result["baseline_system_text"]:
        raise ValueError("visible and baseline prompts must differ by the frozen guidance")
    return result


def safe_token(text: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in text).strip(
        "_"
    )


def matrix_coordinate_id(task_id: str, condition: str, seed: int) -> str:
    return f"v331_cal_{safe_token(task_id)}_{safe_token(condition)}_{seed}"


def build_matrix(execution: dict[str, Any]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for task in execution["tasks"]:
        for seed in execution["seeds"]:
            for condition in execution["conditions"]:
                system_text = (
                    execution["baseline_system_text"]
                    if condition == "BASELINE"
                    else execution["visible_system_text"]
                )
                messages = [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": task["question"]},
                ]
                matrix.append(
                    {
                        "coordinate_id": matrix_coordinate_id(task["id"], condition, seed),
                        "task_id": task["id"],
                        "condition": condition,
                        "seed": seed,
                        "request": make_request(execution, messages, seed),
                        "messages": messages,
                    }
                )
    ids = [row["coordinate_id"] for row in matrix]
    if len(matrix) != MATRIX_COUNT or len(set(ids)) != MATRIX_COUNT:
        raise ValueError("v3.3.1 matrix must contain exactly 12 unique coordinates")
    if any(row["condition"] not in CONDITIONS for row in matrix):
        raise ValueError("unexpected condition in matrix")
    if any("heldout" in row["coordinate_id"] or "latent" in row["coordinate_id"] for row in matrix):
        raise ValueError("forbidden coordinate entered matrix")
    return matrix


def condition_matrix(
    execution: dict[str, Any], condition: str
) -> list[dict[str, Any]]:
    if condition not in CONDITIONS:
        raise ValueError(f"condition is outside the v3.3.1 approval: {condition}")
    return [row for row in build_matrix(execution) if row["condition"] == condition]


def make_request(
    execution: dict[str, Any], messages: list[dict[str, str]], seed: int
) -> dict[str, Any]:
    runtime = execution["runtime"]
    return {
        "model": runtime["model"],
        "messages": messages,
        "temperature": runtime["temperature"],
        "top_k": runtime["top_k"],
        "top_p": runtime["top_p"],
        "min_p": runtime["min_p"],
        "max_tokens": runtime["max_tokens"],
        "seed": seed,
        "stream": True,
        "cache_prompt": False,
        "chat_template_kwargs": {"enable_thinking": True},
    }


def response_parts(response: dict[str, Any]) -> tuple[str, str, str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("response must contain exactly one choice")
    choice = choices[0]
    message = choice.get("message", {})
    reasoning = message.get("reasoning_content", "")
    answer = message.get("content", "")
    finish = choice.get("finish_reason", "")
    if not all(isinstance(value, str) for value in (reasoning, answer, finish)):
        raise ValueError("reasoning, answer, and finish reason must be strings")
    return reasoning, answer, finish


def response_digest(response: dict[str, Any]) -> str:
    values = response_parts(response)
    return sha256_bytes("\0".join(values).encode("utf-8"))


class V331Runner:
    """Small no-bank caller with request-before-call and event-level journaling."""

    def __init__(self, base_url: str, journal: EvidenceJournal, plan_sha: str, approval_sha: str):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base URL must use http(s)")
        self.base_url = base_url.rstrip("/")
        self.journal = journal
        self.plan_sha = plan_sha
        self.approval_sha = approval_sha

    def execute(self, coordinate: dict[str, Any], phase: str) -> dict[str, Any]:
        attempt_id = coordinate["coordinate_id"]
        messages = coordinate["messages"]
        request = dict(coordinate["request"])
        if request.get("cache_prompt") is not False or request.get("stream") is not True:
            raise ValueError("v3.3.1 requires cache_prompt=false and streaming")
        template_request = {
            "messages": messages,
            "add_generation_prompt": True,
            "chat_template_kwargs": request["chat_template_kwargs"],
        }
        template = http_json(self.base_url + "/apply-template", template_request)
        prompt = template.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("template endpoint did not return exact rendered prompt")
        if coordinate["condition"] == "BASELINE" and execution_target_card_in_prompt(prompt):
            raise ValueError("target guidance leaked into baseline prompt")
        if coordinate["condition"] == "VISIBLE_GUIDANCE" and not execution_target_card_in_prompt(
            prompt
        ):
            raise ValueError("visible prompt omitted frozen target guidance")
        journal_request = {
            **request,
            "model_visible_prompt": prompt,
            "model_visible_prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        }
        metadata = {
            "package_id": PACKAGE_ID,
            "phase": phase,
            "coordinate": {
                key: coordinate[key]
                for key in ("task_id", "condition", "seed", "coordinate_id")
            },
            "freeze_sha256": self.plan_sha,
            "approval_sha256": self.approval_sha,
            "template_request": template_request,
            "template_response": template,
            "stream_file": f"{attempt_id}.stream.jsonl",
        }
        self.journal.begin(attempt_id, journal_request, metadata)
        try:
            response = http_sse(
                self.base_url + "/v1/chat/completions",
                request,
                lambda raw_event: self.journal.append_stream_event(attempt_id, raw_event),
            )
        except Exception as exc:
            self.journal.fail(
                attempt_id,
                {"error_type": type(exc).__name__, "message": str(exc)},
                {"phase": phase, "stream": self.journal.stream_summary(attempt_id)},
            )
            raise
        reasoning, answer, finish = response_parts(response)
        self.journal.complete(
            attempt_id,
            response,
            {
                "phase": phase,
                "finish_reason": finish,
                "reasoning_sha256": sha256_bytes(reasoning.encode("utf-8")),
                "answer_sha256": sha256_bytes(answer.encode("utf-8")),
                "stream": self.journal.stream_summary(attempt_id),
            },
        )
        return response


def execution_target_card_in_prompt(prompt: str) -> bool:
    """Detect the card by its distinctive frozen quantum-guidance opening."""
    return TARGET_CARD_OPENING in prompt


def journal_attempts(journal_root: Path) -> dict[str, dict[str, Any]]:
    index = json.loads((journal_root / "index.json").read_text(encoding="utf-8"))
    return {row["attempt_id"]: row for row in index.get("attempts", [])}


def validate_scope(
    attempts: dict[str, dict[str, Any]], execution: dict[str, Any]
) -> None:
    expected = set(PREFLIGHT_IDS) | {
        row["coordinate_id"] for row in build_matrix(execution)
    }
    unexpected = set(attempts) - expected
    if unexpected:
        raise ValueError(f"journal contains calls outside v3.3.1 approval: {sorted(unexpected)}")
    if len(attempts) > MAX_CALLS:
        raise ValueError("journal exceeds approved 14-call maximum")


def preflight_result(journal_root: Path) -> dict[str, Any]:
    attempts = journal_attempts(journal_root)
    if set(PREFLIGHT_IDS) - set(attempts):
        raise ValueError("both preflight attempts must be durably present")
    if any(attempts[key]["status"] != "COMPLETE" for key in PREFLIGHT_IDS):
        raise ValueError("preflight includes failed or uncertain attempt; do not retry")
    responses: list[dict[str, Any]] = []
    for attempt_id in PREFLIGHT_IDS:
        envelope = json.loads(
            (journal_root / "attempts" / f"{attempt_id}.complete.json").read_text(
                encoding="utf-8"
            )
        )
        response = envelope.get("payload")
        if not isinstance(response, dict):
            raise ValueError(f"invalid preflight response envelope: {attempt_id}")
        responses.append(response)
    digests = [response_digest(response) for response in responses]
    finishes = [response_parts(response)[2] for response in responses]
    passed = digests[0] == digests[1] and finishes == ["stop", "stop"]
    return {
        "status": "PASS" if passed else "STOP_PREFLIGHT_MISMATCH_OR_ABNORMAL_FINISH",
        "attempt_ids": list(PREFLIGHT_IDS),
        "response_sha256": digests,
        "finish_reasons": finishes,
        "byte_identical": digests[0] == digests[1],
        "compared_fields": ["reasoning_content", "final content", "finish_reason"],
    }


def ensure_matrix_complete(
    execution: dict[str, Any], journal_root: Path
) -> list[str]:
    attempts = journal_attempts(journal_root)
    allowed = [row["coordinate_id"] for row in build_matrix(execution)]
    if set(attempts) != set(PREFLIGHT_IDS) | set(allowed):
        raise ValueError("scoring requires all 14 exact approved calls and no extras")
    if any(attempts[key]["status"] != "COMPLETE" for key in set(PREFLIGHT_IDS) | set(allowed)):
        raise ValueError("scoring requires every approved call to be durably COMPLETE")
    for attempt_id in set(PREFLIGHT_IDS) | set(allowed):
        outcome = json.loads(
            (journal_root / "attempts" / f"{attempt_id}.complete.json").read_text(
                encoding="utf-8"
            )
        )
        response = outcome.get("payload")
        if not isinstance(response, dict) or response_parts(response)[2] != "stop":
            raise ValueError(f"scoring cannot include abnormal finish: {attempt_id}")
    return allowed


def score_baseline_ceiling(
    execution: dict[str, Any], annotations: dict[str, Any], journal_root: Path
) -> dict[str, Any]:
    """Apply only the frozen baseline ceiling rule before visible calls dispatch."""
    attempts = journal_attempts(journal_root)
    matrix = condition_matrix(execution, "BASELINE")
    expected_ids = {row["coordinate_id"] for row in matrix}
    visible_ids = {
        row["coordinate_id"] for row in condition_matrix(execution, "VISIBLE_GUIDANCE")
    }
    if visible_ids & set(attempts):
        raise ValueError("baseline ceiling gate must be recorded before any visible call")
    if set(PREFLIGHT_IDS) - set(attempts):
        raise ValueError("both determinism preflight attempts must be durable")
    if any(attempts[key]["status"] != "COMPLETE" for key in PREFLIGHT_IDS):
        raise ValueError("preflight must be complete before baseline ceiling scoring")
    if expected_ids - set(attempts):
        raise ValueError("baseline ceiling scoring requires all six baseline outputs")
    if any(attempts[key]["status"] != "COMPLETE" for key in expected_ids):
        raise ValueError("baseline ceiling scoring requires six complete outputs")
    rows = annotations.get("coordinates")
    if not isinstance(rows, list):
        raise ValueError("baseline annotations must contain a coordinates list")
    expected = {
        (coordinate["task_id"], coordinate["seed"]): coordinate
        for coordinate in matrix
    }
    observed: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        key = (row.get("task_id"), row.get("seed"))
        if key not in expected or key in observed:
            raise ValueError(f"unexpected or duplicate baseline annotation: {key}")
        if row.get("condition") != "BASELINE":
            raise ValueError("baseline ceiling worksheet may contain BASELINE only")
        scores = row.get("process_criteria")
        if not isinstance(scores, list) or len(scores) != 3 or any(
            value not in (0, 1) for value in scores
        ):
            raise ValueError("baseline process criteria must be three binary scores")
        spans = row.get("evidence_spans")
        if not isinstance(spans, list) or not spans:
            raise ValueError("baseline scores require exact evidence spans")
        attempt_id = expected[key]["coordinate_id"]
        outcome = json.loads(
            (journal_root / "attempts" / f"{attempt_id}.complete.json").read_text(
                encoding="utf-8"
            )
        )
        reasoning, answer, finish = response_parts(outcome["payload"])
        if finish != "stop":
            raise ValueError(f"abnormal finish cannot be baseline-scored: {attempt_id}")
        for span in spans:
            if (
                not isinstance(span, dict)
                or span.get("field") not in {"reasoning_content", "content"}
                or not isinstance(span.get("quote"), str)
                or not span["quote"]
            ):
                raise ValueError("evidence spans require exact reasoning/content quotes")
            source = reasoning if span["field"] == "reasoning_content" else answer
            if span["quote"] not in source:
                raise ValueError(f"baseline evidence quote not found in durable output: {key}")
        observed[key] = row
    if set(observed) != set(expected):
        raise ValueError("baseline worksheet must annotate exactly six baseline coordinates")
    by_task: list[dict[str, Any]] = []
    for task in execution["tasks"]:
        scores = [
            float(sum(observed[(task["id"], seed)]["process_criteria"]))
            for seed in SEEDS
        ]
        by_task.append(
            {"task_id": task["id"], "seed_scores": scores, "mean": sum(scores) / len(scores)}
        )
    mean = sum(row["mean"] for row in by_task) / len(by_task)
    ceiling = mean > 2.5 or sum(row["mean"] == 3 for row in by_task) >= 2
    return {
        "status": "CEILING_LIMITED_STOP" if ceiling else "BASELINE_HEADROOM_GATE_PASS",
        "baseline_process_mean": mean,
        "ceiling_limited": ceiling,
        "rule": "Mean >2.5/3 or at least two item means equal 3/3.",
        "per_task": by_task,
        "visible_calls_authorized_by_existing_approval": not ceiling,
        "all_six_baseline_outputs_durable": True,
    }


def score_gate(
    execution: dict[str, Any],
    annotations: dict[str, Any],
    journal_root: Path,
) -> dict[str, Any]:
    """Apply only frozen 0..3 process annotations and separate answer scores."""
    ensure_matrix_complete(execution, journal_root)
    rows = annotations.get("coordinates")
    if not isinstance(rows, list):
        raise ValueError("annotations must contain a coordinates list")
    expected_keys = {
        (task["id"], condition, seed)
        for task in execution["tasks"]
        for condition in CONDITIONS
        for seed in SEEDS
    }
    indexed: dict[tuple[str, str, int], dict[str, Any]] = {}
    matrix_by_id = {
        matrix_coordinate_id(task["id"], condition, seed): (task["id"], condition, seed)
        for task in execution["tasks"]
        for condition in CONDITIONS
        for seed in SEEDS
    }
    for row in rows:
        key = (row.get("task_id"), row.get("condition"), row.get("seed"))
        if key not in expected_keys or key in indexed:
            raise ValueError(f"unexpected or duplicate score annotation: {key}")
        process = row.get("process_criteria")
        answer = row.get("answer_components")
        task = next(item for item in execution["tasks"] if item["id"] == key[0])
        if not isinstance(process, list) or len(process) != 3:
            raise ValueError("each process score must contain exactly three frozen criteria")
        if any(value not in (0, 1) for value in process):
            raise ValueError("process criteria are binary 0/1")
        if not isinstance(answer, list) or len(answer) != len(task["answer_key_components"]):
            raise ValueError("answer score count must match frozen answer-key components")
        if any(value not in (0, 0.5, 1) for value in answer):
            raise ValueError("answer components must be scored 0, 0.5, or 1")
        spans = row.get("evidence_spans")
        if not isinstance(spans, list) or not spans:
            raise ValueError("each score requires evidence spans")
        matching_id = next(
            (attempt_id for attempt_id, tuple_key in matrix_by_id.items() if tuple_key == key),
            None,
        )
        if matching_id is None:
            raise ValueError(f"score annotation has no frozen coordinate: {key}")
        outcome = json.loads(
            (journal_root / "attempts" / f"{matching_id}.complete.json").read_text(
                encoding="utf-8"
            )
        )
        response = outcome["payload"]
        reasoning, final_answer, _finish = response_parts(response)
        for span in spans:
            if not isinstance(span, dict) or span.get("field") not in {
                "reasoning_content",
                "content",
            } or not isinstance(span.get("quote"), str) or not span["quote"]:
                raise ValueError(
                    "evidence span must name reasoning_content/content and exact quote"
                )
            source = reasoning if span["field"] == "reasoning_content" else final_answer
            if span["quote"] not in source:
                raise ValueError(f"scoring evidence quote is not present in durable output: {key}")
        indexed[key] = row
    if set(indexed) != expected_keys:
        raise ValueError("score annotations must cover all 12 matrix coordinates")

    per_task: list[dict[str, Any]] = []
    for task in execution["tasks"]:
        condition_scores: dict[str, list[float]] = {condition: [] for condition in CONDITIONS}
        answer_scores: dict[str, list[float]] = {condition: [] for condition in CONDITIONS}
        for seed in SEEDS:
            for condition in CONDITIONS:
                row = indexed[(task["id"], condition, seed)]
                condition_scores[condition].append(float(sum(row["process_criteria"])))
                answer_scores[condition].append(
                    sum(row["answer_components"]) / len(row["answer_components"])
                )
        baseline = sum(condition_scores["BASELINE"]) / len(SEEDS)
        visible = sum(condition_scores["VISIBLE_GUIDANCE"]) / len(SEEDS)
        per_task.append(
            {
                "task_id": task["id"],
                "baseline_process_mean": baseline,
                "visible_process_mean": visible,
                "process_delta": visible - baseline,
                "baseline_answer_mean": sum(answer_scores["BASELINE"]) / len(SEEDS),
                "visible_answer_mean": sum(answer_scores["VISIBLE_GUIDANCE"]) / len(SEEDS),
            }
        )
    baseline_mean = sum(row["baseline_process_mean"] for row in per_task) / len(per_task)
    deltas = [row["process_delta"] for row in per_task]
    overall_delta = sum(deltas) / len(deltas)
    answer_harm = sum(
        row["baseline_answer_mean"] - row["visible_answer_mean"] for row in per_task
    ) / len(per_task)
    ceiling = baseline_mean > 2.5 or sum(
        row["baseline_process_mean"] == 3 for row in per_task
    ) >= 2
    gate_pass = (
        overall_delta >= 0.5
        and sum(delta > 0 for delta in deltas) >= 2
        and answer_harm <= 0.10
    )
    if ceiling:
        status = "CEILING_LIMITED"
    elif gate_pass:
        status = "VISIBLE_GATE_PASS_STOP_FOR_ROOT_REVIEW"
    else:
        status = "VISIBLE_GATE_FAIL_STOP"
    return {
        "status": status,
        "scored_after_durable_completion": True,
        "baseline_process_mean": baseline_mean,
        "visible_minus_baseline_process_delta": overall_delta,
        "positive_item_deltas": sum(delta > 0 for delta in deltas),
        "normalized_answer_score_harm": answer_harm,
        "per_task": per_task,
        "no_task_substitution": True,
        "next_authority_boundary": (
            "No latent/heldout/bank/selector work is authorized by a visible-gate pass."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18473")
    parser.add_argument(
        "--stage",
        choices=("dry-run", "preflight", "baseline", "baseline-gate", "visible", "score"),
        required=True,
    )
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--dry-run-output", type=Path)
    args = parser.parse_args()

    plan, _approval, candidate = load_frozen(args.plan, args.approval, args.candidate)
    execution = execution_projection(candidate)
    matrix = build_matrix(execution)
    plan_sha = sha256_file(args.plan)
    approval_sha = sha256_file(args.approval)

    if args.stage == "dry-run":
        output = {
            "status": "DRY_RUN_VALIDATED_NO_NETWORK_NO_GENERATION",
            "package_id": PACKAGE_ID,
            "freeze_id": plan["freeze_id"],
            "plan_sha256": plan_sha,
            "approval_sha256": approval_sha,
            "candidate_sha256": CANDIDATE_SHA256,
            "runner_script_sha256": sha256_file(Path(__file__)),
            "preflight_ids": list(PREFLIGHT_IDS),
            "matrix_count": len(matrix),
            "matrix_ids": [row["coordinate_id"] for row in matrix],
            "dispatch_stages": {
                "1": "two-call same-coordinate BASELINE determinism preflight",
                "2": "six BASELINE matrix calls",
                "3": "score frozen baseline ceiling rule; stop if ceiling-limited",
                "4": "six VISIBLE_GUIDANCE calls only after baseline gate passes",
                "5": (
                    "score frozen visible-minus-baseline process/answer gate "
                    "after all 14 outputs durable"
                ),
            },
            "task_ids": list(TASK_IDS),
            "conditions": list(CONDITIONS),
            "seeds": list(SEEDS),
            "max_total_calls": MAX_CALLS,
            "latent_coordinates": 0,
            "heldout_coordinates": 0,
            "bank_or_selector_calls": 0,
            "reasoning": "ON",
            "cache_prompt": False,
            "generation_dispatched": False,
            "execution_projection_sha256": canonical_sha256(execution),
        }
        output_path = args.dry_run_output or (
            args.journal_root.parent / "MI2_v3_3_1_Visible_Gate_Dry_Run.json"
        )
        atomic_json_write(output_path, output)
        print(json.dumps(output, indent=2))
        return 0

    journal = EvidenceJournal(args.journal_root, hard_call_limit=MAX_CALLS)
    runner = V331Runner(args.base_url, journal, plan_sha, approval_sha)
    attempts = journal_attempts(args.journal_root)
    validate_scope(attempts, execution)
    if args.stage == "preflight":
        preflight_task = next(
            task for task in execution["tasks"] if task["id"] == "quantum/1-1041"
        )
        coord = {
            "coordinate_id": PREFLIGHT_IDS[0],
            "task_id": preflight_task["id"],
            "condition": "BASELINE",
            "seed": SEEDS[0],
            "messages": [
                {"role": "system", "content": execution["baseline_system_text"]},
                {"role": "user", "content": preflight_task["question"]},
            ],
            "request": make_request(
                execution,
                [
                    {"role": "system", "content": execution["baseline_system_text"]},
                    {"role": "user", "content": preflight_task["question"]},
                ],
                SEEDS[0],
            ),
        }
        for attempt_id in PREFLIGHT_IDS:
            status = attempts.get(attempt_id, {}).get("status")
            if status is not None:
                if status != "COMPLETE":
                    raise RuntimeError(f"uncertain/failed preflight {attempt_id}; never retry")
                continue
            coord["coordinate_id"] = attempt_id
            response = runner.execute(coord, "preflight")
            attempts[attempt_id] = {"status": "COMPLETE"}
            if response_parts(response)[2] != "stop":
                result = {
                    "status": "STOP_ABNORMAL_FINISH",
                    "attempt_ids_completed": [attempt_id],
                    "finish_reason": response_parts(response)[2],
                    "second_preflight_call_dispatched": False,
                }
                atomic_json_write(
                    args.journal_root.parent / "MI2_v3_3_1_Determinism_Preflight.json", result
                )
                print(json.dumps(result, indent=2))
                return 2
        result = preflight_result(args.journal_root)
        result["freeze_sha256"] = plan_sha
        result["approval_sha256"] = approval_sha
        atomic_json_write(
            args.journal_root.parent / "MI2_v3_3_1_Determinism_Preflight.json", result
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS" else 2

    preflight_path = args.journal_root.parent / "MI2_v3_3_1_Determinism_Preflight.json"
    if (
        not preflight_path.exists()
        or json.loads(preflight_path.read_text()).get("status") != "PASS"
    ):
        raise RuntimeError("passing durable preflight is required before baseline/visible/score")
    preflight_receipt = json.loads(preflight_path.read_text(encoding="utf-8"))
    if (
        preflight_receipt.get("freeze_sha256") != plan_sha
        or preflight_receipt.get("approval_sha256") != approval_sha
    ):
        raise RuntimeError("preflight receipt belongs to a different freeze or approval")
    if args.stage == "baseline":
        visible_existing = any(
            row["condition"] == "VISIBLE_GUIDANCE" and row["coordinate_id"] in attempts
            for row in matrix
        )
        if visible_existing:
            raise RuntimeError(
                "visible call already exists before baseline stage; refusing reordering"
            )
        stage_coordinates = condition_matrix(execution, "BASELINE")
        for coordinate in stage_coordinates:
            attempt_id = coordinate["coordinate_id"]
            status = attempts.get(attempt_id, {}).get("status")
            if status is not None:
                if status != "COMPLETE":
                    raise RuntimeError(f"uncertain/failed coordinate {attempt_id}; never retry")
                continue
            runner.execute(coordinate, "baseline")
            finish = response_parts(
                json.loads(
                    (args.journal_root / "attempts" / f"{attempt_id}.complete.json").read_text()
                )["payload"]
            )[2]
            if finish != "stop":
                raise RuntimeError(f"abnormal finish reason {finish!r} for {attempt_id}; stop")
            attempts[attempt_id] = {"status": "COMPLETE"}
            journal.verify()
            print(
                json.dumps({"completed": attempt_id, "durable_attempts": len(attempts)}),
                flush=True,
            )
        print(
            json.dumps(
                {"journal_verified": journal.verify(), "baseline_count": len(stage_coordinates)},
                indent=2,
            )
        )
        return 0

    baseline_gate_path = args.journal_root.parent / "MI2_v3_3_1_Baseline_Ceiling_Gate.json"
    if args.stage == "baseline-gate":
        if baseline_gate_path.exists():
            raise FileExistsError(
                "baseline gate receipt already exists; do not overwrite scoring evidence"
            )
        if args.annotations is None:
            raise ValueError("--annotations is required for baseline ceiling scoring")
        annotation_value = json.loads(args.annotations.read_text(encoding="utf-8"))
        gate = score_baseline_ceiling(execution, annotation_value, args.journal_root)
        gate["plan_sha256"] = plan_sha
        gate["approval_sha256"] = approval_sha
        atomic_json_write(baseline_gate_path, gate)
        print(json.dumps(gate, indent=2))
        return 2 if gate["ceiling_limited"] else 0

    if args.stage == "visible":
        if not baseline_gate_path.exists():
            raise RuntimeError("visible calls require a durable baseline ceiling decision")
        baseline_gate = json.loads(baseline_gate_path.read_text(encoding="utf-8"))
        if baseline_gate.get("status") != "BASELINE_HEADROOM_GATE_PASS":
            raise RuntimeError("baseline ceiling gate failed; visible calls are prohibited")
        if (
            baseline_gate.get("plan_sha256") != plan_sha
            or baseline_gate.get("approval_sha256") != approval_sha
        ):
            raise RuntimeError("baseline gate receipt belongs to a different freeze/approval")
        baseline_ids = {
            row["coordinate_id"] for row in condition_matrix(execution, "BASELINE")
        }
        if baseline_ids - {
            attempt_id
            for attempt_id, record in attempts.items()
            if record.get("status") == "COMPLETE"
        }:
            raise RuntimeError("visible calls require all six baseline outputs durably complete")
        stage_coordinates = condition_matrix(execution, "VISIBLE_GUIDANCE")
        for coordinate in stage_coordinates:
            attempt_id = coordinate["coordinate_id"]
            status = attempts.get(attempt_id, {}).get("status")
            if status is not None:
                if status != "COMPLETE":
                    raise RuntimeError(f"uncertain/failed coordinate {attempt_id}; never retry")
                continue
            runner.execute(coordinate, "visible_gate")
            finish = response_parts(
                json.loads(
                    (args.journal_root / "attempts" / f"{attempt_id}.complete.json").read_text()
                )["payload"]
            )[2]
            if finish != "stop":
                raise RuntimeError(f"abnormal finish reason {finish!r} for {attempt_id}; stop")
            attempts[attempt_id] = {"status": "COMPLETE"}
            journal.verify()
            print(
                json.dumps({"completed": attempt_id, "durable_attempts": len(attempts)}),
                flush=True,
            )
        print(
            json.dumps(
                {"journal_verified": journal.verify(), "visible_count": len(stage_coordinates)},
                indent=2,
            )
        )
        return 0

    if args.annotations is None:
        raise ValueError("--annotations is required for frozen post-completion scoring")
    if not baseline_gate_path.exists():
        raise RuntimeError("visible scoring requires a durable passing baseline gate receipt")
    baseline_gate = json.loads(baseline_gate_path.read_text(encoding="utf-8"))
    if (
        baseline_gate.get("status") != "BASELINE_HEADROOM_GATE_PASS"
        or baseline_gate.get("plan_sha256") != plan_sha
        or baseline_gate.get("approval_sha256") != approval_sha
    ):
        raise RuntimeError("baseline gate receipt does not authorize this frozen visible score")
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    score = score_gate(execution, annotations, args.journal_root)
    score["plan_sha256"] = plan_sha
    score["approval_sha256"] = approval_sha
    atomic_json_write(args.journal_root.parent / "MI2_v3_3_1_Visible_Gate_Score.json", score)
    print(json.dumps(score, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
