#!/usr/bin/env python3
"""Fail-closed, resumable MI2 v3.4 visible-guidance prerequisite gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write
from experiments.mi1.runner import http_json, http_sse

FREEZE_SHA256 = "8b8963b99d2575276fc9ff7f070f1f8840f64fe0dbd6115382563f2006cac967"
APPROVAL_SHA256 = "87e95c00b04d8d5f84d28e759cb5e63b482478ed0f4520fc3d1da146f5d2339c"
CANDIDATE_SHA256 = "f1e26d775d7fdb2e35b2ce47ca572ab66ae137a3ec52e7b069f57ed8bfe4b23a"
FREEZE_ID = "MI2-CAL-V3.4-20261012"
CONDITIONS = ("BASELINE", "VISIBLE_GUIDANCE")
SEEDS = (482011, 482029, 482047)
PREFLIGHT_IDS = ("v34_preflight_baseline_a", "v34_preflight_baseline_b")
MAX_CALLS = 200
CARD_SENTINEL = "Trigger: A prompt mixes states, operators, spectra, measurement, and time language"


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def load_plan(
    candidate_path: Path, freeze_path: Path, approval_path: Path
) -> tuple[dict[str, Any], str, str]:
    candidate_bytes = candidate_path.read_bytes()
    freeze_bytes = freeze_path.read_bytes()
    approval_bytes = approval_path.read_bytes()
    if (sha256(candidate_bytes), sha256(freeze_bytes), sha256(approval_bytes)) != (
        CANDIDATE_SHA256,
        FREEZE_SHA256,
        APPROVAL_SHA256,
    ):
        raise ValueError("candidate/freeze/approval fingerprint mismatch")
    candidate = json.loads(candidate_bytes)
    freeze = json.loads(freeze_bytes)
    approval = json.loads(approval_bytes)
    tasks = candidate.get("tasks")
    if candidate.get("candidate_version") != "v3.4" or not isinstance(tasks, list):
        raise ValueError("wrong candidate version or task list")
    task_ids = [row.get("id") for row in tasks]
    if len(tasks) != 33 or len(set(task_ids)) != 33 or task_ids != sorted(task_ids):
        raise ValueError("frozen cohort must contain 33 unique sorted task IDs")
    if freeze.get("frozen_task_ids") != task_ids or freeze.get("freeze_id") != FREEZE_ID:
        raise ValueError("candidate and freeze cohort differ")
    if freeze.get("candidate", {}).get("sha256") != CANDIDATE_SHA256:
        raise ValueError("freeze does not bind the expected candidate")
    task_records_hash = sha256(canonical(tasks))
    if freeze.get("frozen_task_records_sha256") != task_records_hash:
        raise ValueError("frozen task-record digest mismatch")
    if freeze.get("max_calls") != MAX_CALLS:
        raise ValueError("frozen maximum call count mismatch")
    if approval.get("freeze", {}).get("sha256") != FREEZE_SHA256:
        raise ValueError("approval does not bind the expected freeze")
    limits = approval.get("authorized_limits", {})
    if (
        approval.get("approval_status") != "APPROVED_FOR_FROZEN_VISIBLE_GATE_ONLY"
        or limits.get("maximum_calls") != MAX_CALLS
        or limits.get("baseline_calls") != 99
        or limits.get("conditional_visible_calls") != 99
        or limits.get("preflight_calls") != 2
        or limits.get("conditions") != list(CONDITIONS)
        or limits.get("seeds") != list(SEEDS)
        or limits.get("cache_prompt") is not False
        or limits.get("reasoning") != "ON"
    ):
        raise ValueError("approval scope does not match v3.4 runner")
    if candidate.get("scope_boundary", {}).get("allowed") != [
        "BASELINE duplicate preflight",
        "BASELINE matrix",
        "VISIBLE_GUIDANCE matrix conditional on baseline gate",
        "offline scoring",
    ]:
        raise ValueError("candidate authorization boundary mismatch")
    return candidate, FREEZE_SHA256, APPROVAL_SHA256


def coordinate_id(task_id: str, condition: str, seed: int) -> str:
    token = task_id.replace("/", "_").replace("-", "_")
    return f"v34_{token}_{condition.lower()}_{seed}"


def make_request(
    candidate: dict[str, Any], messages: list[dict[str, str]], seed: int
) -> dict[str, Any]:
    runtime = candidate["prompt_contract"]["runtime"]
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


def build_matrix(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = []
    for task in candidate["tasks"]:
        for seed in SEEDS:
            for condition in CONDITIONS:
                system = candidate["prompt_contract"][
                    "baseline_system_text_exact"
                    if condition == "BASELINE"
                    else "visible_system_text_exact"
                ]
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": task["question"]},
                ]
                matrix.append(
                    {
                        "coordinate_id": coordinate_id(task["id"], condition, seed),
                        "task_id": task["id"],
                        "condition": condition,
                        "seed": seed,
                        "trigger_applicability": task["trigger_applicability"],
                        "messages": messages,
                        "request": make_request(candidate, messages, seed),
                    }
                )
    if len(matrix) != 198 or len({row["coordinate_id"] for row in matrix}) != 198:
        raise ValueError("v3.4 must contain exactly 198 unique matrix coordinates")
    return matrix


def parts(response: dict[str, Any]) -> tuple[str, str, str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("exactly one model choice is required")
    choice = choices[0]
    message = choice.get("message", {})
    reasoning = message.get("reasoning_content", "")
    answer = message.get("content", "")
    finish = choice.get("finish_reason", "")
    if not all(isinstance(value, str) for value in (reasoning, answer, finish)):
        raise ValueError("reasoning, answer, and finish reason must be strings")
    return reasoning, answer, finish


def response_hash(response: dict[str, Any]) -> str:
    return sha256("\0".join(parts(response)).encode())


def attempts_at(root: Path) -> dict[str, dict[str, Any]]:
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    return {row["attempt_id"]: row for row in index.get("attempts", [])}


def preflight_status(root: Path) -> dict[str, Any]:
    attempts = attempts_at(root)
    if any(attempts.get(key, {}).get("status") != "COMPLETE" for key in PREFLIGHT_IDS):
        return {"status": "INCOMPLETE_OR_UNCERTAIN", "attempt_ids": list(PREFLIGHT_IDS)}
    responses = []
    for attempt in PREFLIGHT_IDS:
        outcome = json.loads(
            (root / "attempts" / f"{attempt}.complete.json").read_text(encoding="utf-8")
        )
        responses.append(outcome.get("payload"))
    hashes = [response_hash(item) for item in responses]
    finishes = [parts(item)[2] for item in responses]
    return {
        "status": "PASS"
        if hashes[0] == hashes[1] and finishes == ["stop", "stop"]
        else "STOP_MISMATCH_OR_ABNORMAL_FINISH",
        "attempt_ids": list(PREFLIGHT_IDS),
        "response_hashes": hashes,
        "finish_reasons": finishes,
        "byte_identical": hashes[0] == hashes[1],
    }


def baseline_replay_status(candidate: dict[str, Any], root: Path) -> dict[str, Any]:
    """Compare the matrix's first baseline coordinate with both preflight calls."""
    matrix_coord = next(
        row
        for row in build_matrix(candidate)
        if row["condition"] == "BASELINE"
        and row["task_id"] == candidate["tasks"][0]["id"]
        and row["seed"] == SEEDS[0]
    )
    attempts = attempts_at(root)
    attempt_id = matrix_coord["coordinate_id"]
    if attempts.get(attempt_id, {}).get("status") != "COMPLETE":
        return {"status": "MATRIX_REPLAY_MISSING", "matrix_attempt_id": attempt_id}
    matrix_response = json.loads(
        (root / "attempts" / f"{attempt_id}.complete.json").read_text(encoding="utf-8")
    ).get("payload")
    preflight_responses = [
        json.loads(
            (root / "attempts" / f"{preflight_id}.complete.json").read_text(encoding="utf-8")
        ).get("payload")
        for preflight_id in PREFLIGHT_IDS
    ]
    digests = [response_hash(response) for response in [*preflight_responses, matrix_response]]
    finishes = [parts(response)[2] for response in [*preflight_responses, matrix_response]]
    return {
        "status": "PASS"
        if len(set(digests)) == 1 and finishes == ["stop"] * 3
        else "STOP_BASELINE_REPLAY_MISMATCH",
        "attempt_ids": [*PREFLIGHT_IDS, attempt_id],
        "response_hashes": digests,
        "finish_reasons": finishes,
        "byte_identical": len(set(digests)) == 1,
    }


class Runner:
    def __init__(
        self,
        base_url: str,
        journal: EvidenceJournal,
        candidate: dict[str, Any],
        freeze_sha: str,
        approval_sha: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.journal = journal
        self.candidate = candidate
        self.freeze_sha = freeze_sha
        self.approval_sha = approval_sha

    def execute(self, coordinate: dict[str, Any], phase: str) -> None:
        attempt_id = coordinate["coordinate_id"]
        request = coordinate["request"]
        if request.get("cache_prompt") is not False:
            raise ValueError("matched generation requires cache_prompt=false")
        template_request = {
            "messages": coordinate["messages"],
            "add_generation_prompt": True,
            "chat_template_kwargs": request["chat_template_kwargs"],
        }
        template_response = http_json(self.base_url + "/apply-template", template_request)
        prompt = template_response.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("chat-template endpoint did not return prompt text")
        condition = coordinate.get("condition", "BASELINE")
        if condition == "BASELINE" and CARD_SENTINEL in prompt:
            raise ValueError("target card leaked into baseline prompt")
        if condition == "VISIBLE_GUIDANCE" and CARD_SENTINEL not in prompt:
            raise ValueError("visible prompt omitted frozen card")
        journal_request = {
            **request,
            "model_visible_prompt": prompt,
            "model_visible_prompt_sha256": sha256(prompt.encode()),
        }
        metadata = {
            "package_id": "MI2-PAPER-GUIDANCE-20261011",
            "candidate_version": "v3.4",
            "phase": phase,
            "coordinate": {
                key: coordinate.get(key)
                for key in (
                    "task_id",
                    "condition",
                    "seed",
                    "coordinate_id",
                    "trigger_applicability",
                )
            },
            "freeze_sha256": self.freeze_sha,
            "approval_sha256": self.approval_sha,
            "template_request": template_request,
            "template_response": template_response,
            "stream_file": f"{attempt_id}.stream.jsonl",
        }
        self.journal.begin(attempt_id, journal_request, metadata)
        try:
            response = http_sse(
                self.base_url + "/v1/chat/completions",
                request,
                lambda event: self.journal.append_stream_event(attempt_id, event),
            )
        except Exception as exc:
            self.journal.fail(
                attempt_id,
                {"error_type": type(exc).__name__, "message": str(exc)},
                {"phase": phase, "stream": self.journal.stream_summary(attempt_id)},
            )
            raise
        reasoning, answer, finish = parts(response)
        self.journal.complete(
            attempt_id,
            response,
            {
                "phase": phase,
                "finish_reason": finish,
                "reasoning_sha256": sha256(reasoning.encode()),
                "answer_sha256": sha256(answer.encode()),
                "stream": self.journal.stream_summary(attempt_id),
            },
        )


def matrix_phase(candidate: dict[str, Any], condition: str) -> list[dict[str, Any]]:
    return [row for row in build_matrix(candidate) if row["condition"] == condition]


def run_phase(runner: Runner, root: Path, coords: list[dict[str, Any]], phase: str) -> None:
    attempts = attempts_at(root)
    for coordinate in coords:
        attempt_id = coordinate["coordinate_id"]
        existing = attempts.get(attempt_id)
        if existing:
            if existing.get("status") == "COMPLETE":
                continue
            raise RuntimeError(f"uncertain/failed coordinate {attempt_id}; do not retry")
        runner.execute(coordinate, phase)
        attempts = attempts_at(root)


def validate_annotations(
    rows: Any,
    expected: set[tuple[str, str, int]],
    candidate: dict[str, Any],
    root: Path,
    matrix: list[dict[str, Any]],
) -> dict[tuple[str, str, int], dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("annotation file must contain a coordinates array")
    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    attempts = attempts_at(root)
    task_by_id = {row["id"]: row for row in candidate["tasks"]}
    for annotation in rows:
        key = (annotation.get("task_id"), annotation.get("condition"), annotation.get("seed"))
        if key not in expected or key in by_key:
            raise ValueError(f"unexpected or duplicate annotation coordinate: {key}")
        process = annotation.get("process_criteria")
        task = task_by_id[key[0]]
        answer = annotation.get("answer_components")
        if (
            not isinstance(process, list)
            or len(process) != 3
            or any(x not in (0, 1) for x in process)
        ):
            raise ValueError("process criteria must be exactly three binary scores")
        if not isinstance(answer, list) or len(answer) != len(task["answer_components"]):
            raise ValueError("answer score count must match the frozen answer key")
        if any(x not in (0, 0.5, 1) for x in answer):
            raise ValueError("answer components must be 0, 0.5, or 1")
        spans = annotation.get("evidence_spans")
        if not isinstance(spans, list) or not spans:
            raise ValueError("every annotation needs exact evidence quotes")
        coordinate = next(
            (
                x
                for x in matrix
                if x["task_id"] == key[0] and x["condition"] == key[1] and x["seed"] == key[2]
            ),
            None,
        )
        if coordinate is None:
            raise ValueError(f"no matrix entry for {key}")
        attempt_id = coordinate["coordinate_id"]
        if attempts.get(attempt_id, {}).get("status") != "COMPLETE":
            raise ValueError(f"cannot annotate nondurable coordinate {attempt_id}")
        outcome = json.loads((root / "attempts" / f"{attempt_id}.complete.json").read_text())
        response = outcome.get("payload")
        reasoning, final, finish = parts(response)
        if finish != "stop":
            raise ValueError(f"cannot score abnormal finish {attempt_id}")
        for span in spans:
            if (
                span.get("field") not in {"reasoning_content", "content"}
                or not isinstance(span.get("quote"), str)
                or not span["quote"]
            ):
                raise ValueError("evidence span must name a text field and nonempty quote")
            source = reasoning if span["field"] == "reasoning_content" else final
            if span["quote"] not in source:
                raise ValueError(f"quote not found in raw response: {key}")
        by_key[key] = annotation
    if set(by_key) != expected:
        raise ValueError(f"annotation coverage mismatch missing={len(expected - set(by_key))}")
    return by_key


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def sign_test_p(positive: int, negative: int) -> float:
    n = positive + negative
    if n == 0:
        return 1.0
    tail_count = sum(math.comb(n, k) for k in range(positive, n + 1))
    return min(1.0, float(tail_count) / float(2**n))


def summarize_gate(
    candidate: dict[str, Any], root: Path, annotations: dict[str, Any], baseline_only: bool
) -> dict[str, Any]:
    matrix = build_matrix(candidate)
    expected_conditions = {"BASELINE"} if baseline_only else set(CONDITIONS)
    expected = {
        (task["id"], condition, seed)
        for task in candidate["tasks"]
        for condition in expected_conditions
        for seed in SEEDS
    }
    indexed = validate_annotations(
        annotations.get("coordinates"), expected, candidate, root, matrix
    )
    direct = [
        t for t in candidate["tasks"] if t["trigger_applicability"] == "direct_quantum_process"
    ]
    if not direct:
        raise ValueError("no directly triggered tasks in frozen cohort")

    def rowmean(task: dict[str, Any], condition: str) -> tuple[float, float]:
        vals = [indexed[(task["id"], condition, seed)] for seed in SEEDS]
        proc = average([float(sum(x["process_criteria"])) for x in vals])
        ans = average([average([float(s) for s in x["answer_components"]]) for x in vals])
        return proc, ans

    baseline_tasks = []
    for task in direct:
        process, answer = rowmean(task, "BASELINE")
        baseline_tasks.append(
            {"task_id": task["id"], "process_mean_0_to_3": process, "answer_mean_0_to_1": answer}
        )
    baseline_answer = average([r["answer_mean_0_to_1"] for r in baseline_tasks])
    baseline_process = average([r["process_mean_0_to_3"] for r in baseline_tasks])
    ceiling_fraction = sum(r["answer_mean_0_to_1"] == 1 for r in baseline_tasks) / len(
        baseline_tasks
    )
    if baseline_only:
        passed = baseline_answer <= 0.90 and ceiling_fraction < 0.20
        return {
            "status": "BASELINE_HEADROOM_PASS" if passed else "BASELINE_CEILING_STOP",
            "baseline_direct_task_count": len(direct),
            "baseline_answer_mean_0_to_1": baseline_answer,
            "baseline_process_mean_0_to_3": baseline_process,
            "exact_answer_ceiling_task_fraction": ceiling_fraction,
            "frozen_rule": (
                "Answer mean <=0.90 and <20% direct tasks score exactly 1.0; "
                "otherwise stop before visible calls."
            ),
            "visible_dispatch_permitted": passed,
            "all_baseline_coordinates_durable": True,
        }
    task_rows = []
    for task in candidate["tasks"]:
        bproc, bans = rowmean(task, "BASELINE")
        vproc, vans = rowmean(task, "VISIBLE_GUIDANCE")
        task_rows.append(
            {
                "task_id": task["id"],
                "trigger_applicability": task["trigger_applicability"],
                "baseline_process_mean": bproc,
                "visible_process_mean": vproc,
                "process_delta": vproc - bproc,
                "baseline_answer_mean": bans,
                "visible_answer_mean": vans,
            }
        )
    direct_rows = [r for r in task_rows if r["trigger_applicability"] == "direct_quantum_process"]
    deltas = [r["process_delta"] for r in direct_rows]
    positive = sum(delta > 0 for delta in deltas)
    negative = sum(delta < 0 for delta in deltas)
    p_value = sign_test_p(positive, negative)
    process_delta = average(deltas)
    answer_harm = average(
        [r["baseline_answer_mean"] - r["visible_answer_mean"] for r in direct_rows]
    )
    passed = (
        process_delta >= 0.25 and positive > negative and p_value <= 0.05 and answer_harm <= 0.05
    )
    return {
        "status": "VISIBLE_GATE_PASS_STOP_FOR_ROOT_REVIEW" if passed else "VISIBLE_GATE_FAIL_STOP",
        "direct_task_count": len(direct_rows),
        "broad_quantum_task_count": len(task_rows) - len(direct_rows),
        "mean_process_delta_direct_0_to_3": process_delta,
        "positive_direct_task_deltas": positive,
        "negative_direct_task_deltas": negative,
        "tied_direct_task_deltas": len(deltas) - positive - negative,
        "one_sided_exact_sign_test_p": p_value,
        "normalized_answer_score_harm_direct": answer_harm,
        "per_task": task_rows,
        "criteria": {
            "minimum_mean_process_delta": 0.25,
            "positive_items_must_exceed_negative": True,
            "one_sided_sign_test_p_max": 0.05,
            "maximum_answer_harm": 0.05,
        },
        "scored_after_durable_completion": True,
        "latent_or_bank_calls": 0,
        "freeze_sha256": FREEZE_SHA256,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:18473")
    parser.add_argument(
        "--stage",
        choices=("dry-run", "preflight", "baseline", "baseline-gate", "visible", "score"),
        required=True,
    )
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    candidate, freeze_sha, approval_sha = load_plan(args.candidate, args.freeze, args.approval)
    matrix = build_matrix(candidate)
    root = args.journal_root
    root.mkdir(parents=True, exist_ok=True)
    if args.stage == "dry-run":
        output = {
            "status": "VALIDATED_NO_NETWORK_NO_GENERATION",
            "candidate_sha256": CANDIDATE_SHA256,
            "freeze_sha256": freeze_sha,
            "approval_sha256": approval_sha,
            "runner_script_sha256": sha256(Path(__file__).read_bytes()),
            "candidate_builder_sha256": sha256(
                (
                    Path(__file__).resolve().parents[1] / "tools" / "mi2_freeze_v3_4_candidate.py"
                ).read_bytes()
            ),
            "task_count": len(candidate["tasks"]),
            "direct_task_count": sum(
                t["trigger_applicability"] == "direct_quantum_process" for t in candidate["tasks"]
            ),
            "matrix_count": len(matrix),
            "preflight_calls": 2,
            "conditional_visible_calls": 99,
            "maximum_calls": MAX_CALLS,
            "reasoning": "ON",
            "cache_prompt": False,
            "test_split_access": False,
            "latent_or_bank_calls": 0,
            "generation_dispatched": False,
        }
        atomic_json_write(args.output or root.parent / "MI2_v3_4_Dry_Run.json", output)
        print(json.dumps(output, indent=2))
        return 0

    journal = EvidenceJournal(root, hard_call_limit=MAX_CALLS)
    attempts = attempts_at(root)
    expected_ids = set(PREFLIGHT_IDS) | {row["coordinate_id"] for row in matrix}
    unexpected = set(attempts) - expected_ids
    if unexpected or len(attempts) > MAX_CALLS:
        raise ValueError(f"unexpected/excess journal calls: {sorted(unexpected)}")
    runner = Runner(args.base_url, journal, candidate, freeze_sha, approval_sha)
    if args.stage == "preflight":
        task = candidate["tasks"][0]
        for attempt_id in PREFLIGHT_IDS:
            if attempt_id in attempts:
                if attempts[attempt_id].get("status") != "COMPLETE":
                    raise RuntimeError("uncertain preflight exists; do not retry")
                continue
            messages = [
                {
                    "role": "system",
                    "content": candidate["prompt_contract"]["baseline_system_text_exact"],
                },
                {"role": "user", "content": task["question"]},
            ]
            runner.execute(
                {
                    "coordinate_id": attempt_id,
                    "task_id": task["id"],
                    "condition": "BASELINE",
                    "seed": SEEDS[0],
                    "trigger_applicability": task["trigger_applicability"],
                    "messages": messages,
                    "request": make_request(candidate, messages, SEEDS[0]),
                },
                "preflight",
            )
            attempts = attempts_at(root)
        result = preflight_status(root)
        atomic_json_write(root / "v34-preflight-result.json", result)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS" else 2
    preflight = json.loads((root / "v34-preflight-result.json").read_text())
    if preflight.get("status") != "PASS":
        raise RuntimeError("deterministic duplicate preflight has not passed")
    if args.stage == "baseline":
        run_phase(runner, root, matrix_phase(candidate, "BASELINE"), "baseline")
        return 0
    if args.stage == "baseline-gate":
        if args.annotations is None:
            raise ValueError("baseline-gate requires a frozen-rubric annotation file")
        replay = baseline_replay_status(candidate, root)
        atomic_json_write(root / "v34-baseline-replay-check.json", replay)
        if replay.get("status") != "PASS":
            result = {
                "status": "BASELINE_REPLAY_STOP",
                "visible_dispatch_permitted": False,
                "replay_check": replay,
            }
            atomic_json_write(root / "v34-baseline-gate.json", result)
            print(json.dumps(result, indent=2))
            return 2
        result = summarize_gate(candidate, root, json.loads(args.annotations.read_text()), True)
        result["baseline_replay_check"] = replay
        atomic_json_write(root / "v34-baseline-gate.json", result)
        print(json.dumps(result, indent=2))
        return 0 if result["visible_dispatch_permitted"] else 3
    if args.stage == "visible":
        gate = json.loads((root / "v34-baseline-gate.json").read_text())
        if gate.get("status") != "BASELINE_HEADROOM_PASS" or not gate.get(
            "visible_dispatch_permitted"
        ):
            raise RuntimeError("durable baseline headroom gate did not pass")
        run_phase(runner, root, matrix_phase(candidate, "VISIBLE_GUIDANCE"), "visible")
        return 0
    if args.stage == "score":
        if args.annotations is None:
            raise ValueError("score requires frozen-rubric annotations")
        result = summarize_gate(candidate, root, json.loads(args.annotations.read_text()), False)
        atomic_json_write(args.output or root.parent / "MI2_v3_4_Visible_Gate_Score.json", result)
        print(json.dumps(result, indent=2))
        return 0
    raise AssertionError(args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
