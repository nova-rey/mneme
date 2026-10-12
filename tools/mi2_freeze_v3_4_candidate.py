#!/usr/bin/env python3
"""Build the deterministic MI2 v3.4 visible-only PHYSICS-eval candidate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET = Path(
    "/home/nyx/mneme-artifacts/phase4-mi2/source/PHYSICS/PHYSICS/"
    "PHYSICS-eval/quantum_dataset_eval.jsonl"
)
OUT = ROOT / "docs/receipts/MI2_Calibration_v3_4_Candidate_20261012.json"
PREVIOUSLY_USED = {
    "quantum/1-1022",
    "quantum/1-1041",
    "quantum/3-3013",
    "quantum/3-3024",
    "quantum/3-3025",
    "quantum/3-3047",
    "quantum/4002",
    "quantum/5005",
    "quantum/5051",
    "quantum/6015",
    "quantum/6040",
    "quantum/6046",
}
NOT_DIRECT_TRIGGER = {"quantum/7024", "quantum/8001"}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def main() -> None:
    source_bytes = DATASET.read_bytes()
    rows = [json.loads(line) for line in source_bytes.splitlines()]
    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for row in rows:
        identifier = row["id"]
        question = row["questions"]
        if identifier in PREVIOUSLY_USED:
            continue
        if row.get("graphs") or re.search(r"\bfig(?:ure)?\b", question, flags=re.IGNORECASE):
            excluded.append({"id": identifier, "reason": "unavailable figure/diagram input"})
            continue
        answers = row.get("final_answers")
        if not isinstance(answers, list) or not answers:
            excluded.append({"id": identifier, "reason": "no component answer key"})
            continue
        eligible.append(
            {
                "id": identifier,
                "question": question,
                "question_sha256": sha256(question.encode("utf-8")),
                "answer_components": answers,
                "answer_key_sha256": sha256(canonical(answers)),
                "solution_sha256": sha256(row["solutions"].encode("utf-8")),
                "source_row_sha256": sha256(canonical(row)),
                "trigger_applicability": (
                    "broad_quantum"
                    if identifier in NOT_DIRECT_TRIGGER
                    else "direct_quantum_process"
                ),
            }
        )
    eligible.sort(key=lambda item: item["id"])
    excluded.sort(key=lambda item: item["id"])
    if len(rows) != 53 or len(eligible) != 33 or len(excluded) != 8:
        raise SystemExit(
            "source/count mismatch: "
            f"rows={len(rows)} eligible={len(eligible)} excluded={len(excluded)}"
        )
    previous_in_data = PREVIOUSLY_USED & {row["id"] for row in rows}
    if len(previous_in_data) != 12:
        raise SystemExit(f"prior-use inventory mismatch: {sorted(previous_in_data)}")

    prior = json.loads(
        (ROOT / "docs/receipts/MI2_Calibration_v3_3_1_Candidate_20261012.json").read_text()
    )
    baseline = prior["source_card_choice"]["baseline_system_text_exact"]
    card = prior["source_card_choice"]["paper_card_text_normalized"]
    visible = prior["source_card_choice"]["visible_system_text_exact"]
    runtime = prior["prompt_contract"]["runtime"]
    candidate = {
        "schema_version": 1,
        "artifact_type": "MI2_VISIBLE_ONLY_CANDIDATE",
        "candidate_version": "v3.4",
        "package_id": "MI2-PAPER-GUIDANCE-20261011",
        "created_utc": "2026-10-12T00:00:00Z",
        "purpose": (
            "Estimate whether the paper's same Quantum process card has a repeatable visible "
            "effect on a broader untouched PHYSICS-eval cohort before authorizing latent work."
        ),
        "source": {
            "dataset": "PHYSICS-eval Quantum subject, original paper benchmark split",
            "path": str(DATASET),
            "sha256": sha256(source_bytes),
            "row_count": len(rows),
            "license": "PHYSICS source repository MIT license",
        },
        "cohort_rule": {
            "previously_used_ids": sorted(previous_in_data),
            "excluded_other_ids": excluded,
            "eligibility": (
                "Every remaining quantum item with official final_answers, no attached "
                "graph/image, and no figure reference. No quality selection; no PHYSICS-test."
            ),
            "eligible_count": len(eligible),
            "task_ids": [item["id"] for item in eligible],
        },
        "guidance": {
            "source": ("Memory Inception arXiv:2605.06225v2, Appendix E, Table 5, Quantum row"),
            "card": card,
            "construction": (
                "Same verbatim paper card as v3.3.1; unchanged after its weak single-item result."
            ),
        },
        "scoring": {
            "answer_correctness": (
                "Score each official answer component: 0=incorrect/missing, "
                "0.5=partly correct/equivalent but incomplete, 1=correct/equivalent. "
                "Average components per response; report 0-1 and 0-5 separately from process."
            ),
            "process_rubric": [
                (
                    "Identifies the requested physical/mathematical object or operation, such as "
                    "spectrum, dynamics, measurement, perturbation, or approximation."
                ),
                (
                    "Chooses and applies a representation or procedure suited to that object "
                    "and the stated physical regime."
                ),
                (
                    "Keeps distinct requested objects/operations separate and avoids a category "
                    "substitution warned against by the card."
                ),
            ],
            "process_score": (
                "Three frozen binary criteria. Require exact evidence quotes from the saved "
                "reasoning or answer; repeating card wording alone does not count."
            ),
            "trigger_strata": (
                "Report direct_quantum_process items separately from two broad_quantum items; "
                "do not filter the cohort after outputs."
            ),
            "baseline_headroom_gate": (
                "Continue only if direct-item answer mean <=0.90/1 and fewer than 20% of "
                "direct-item means equal 1.0; otherwise stop for baseline ceiling."
            ),
            "visible_gate": (
                "Pass only if direct-item mean process delta >=0.25/3, positive task means "
                "exceed negative means with one-sided exact sign-test p<=0.05 (ties excluded), "
                "and answer-score harm <=0.05. Broad items cannot rescue a failed direct gate."
            ),
            "finish_policy": (
                "Do not retry abnormal, uncertain, or missing calls. Preserve failure and stop."
            ),
        },
        "prompt_contract": {
            "baseline_system_text_exact": baseline,
            "visible_system_text_exact": visible,
            "only_condition_difference": (
                "Only the fixed card changes the system text; user text and runtime fields "
                "are identical for each matched item and seed."
            ),
            "user_message": (
                "Use the exact question as the only user message; do not include the solution "
                "or answer key."
            ),
            "reasoning": "ON",
            "cache_prompt": False,
            "generation_seeds": [482011, 482029, 482047],
            "runtime": {
                key: runtime[key]
                for key in (
                    "model",
                    "gguf_path",
                    "gguf_sha256",
                    "llama_cpp_commit",
                    "temperature",
                    "top_k",
                    "top_p",
                    "min_p",
                    "max_tokens",
                    "context_size",
                    "reasoning_format",
                    "gpu_layers",
                    "batch_size",
                    "ubatch_size",
                    "threads",
                    "threads_batch",
                    "parallel",
                )
            },
        },
        "tasks": eligible,
        "scope_boundary": {
            "allowed": [
                "BASELINE duplicate preflight",
                "BASELINE matrix",
                "VISIBLE_GUIDANCE matrix conditional on baseline gate",
                "offline scoring",
            ],
            "forbidden": [
                "side-memory bank build",
                "K/V capture",
                "selector",
                "latent",
                "irrelevant bank",
                "held-out evaluation",
                "PHYSICS-test",
                "MNEME/SAA state",
                "other model family",
                "Quinn scoring calls",
            ],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUT),
                "sha256": sha256(OUT.read_bytes()),
                "eligible": len(eligible),
                "excluded": excluded,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
