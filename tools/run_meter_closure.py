#!/usr/bin/env python3
"""Bounded closure recorder; imports no meters and changes no production behavior."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.development.episodes import declared_conversation_arcs
from mneme.development.field import _strength
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.state.compact import CompactStore
from mneme.state.compact_runtime import CompactRuntime
from tools.run_p23_cross_thread import RemoteLlamaHost
from tools.run_three_pressure_v2 import (
    GEMMA_URL,
    STATE_SHA,
    CallBudget,
    RecordingGlinerHost,
    RecordingHost,
    bounded_request,
    export_records,
    extraction_record,
    file_digest,
    native_preprocess,
    read_json,
    write_json,
)

Json = dict[str, Any]


def public_message(ledger: Json) -> str:
    """The private ledger's complete allowed public content, without labels."""
    return " ".join([*ledger["required_facts"], ledger["question"]])


def fact_gate(text: str, ledger: Json) -> list[str]:
    # Permit whitespace formatting only. A changed negation, unit, question,
    # extra result, or leaked instruction is rejected before Gemma dispatch.
    expected = " ".join(public_message(ledger).split())
    return (
        []
        if " ".join(text.split()) == expected
        else ["public message differs from complete private factual/action ledger"]
    )


def quinn_request(
    opening: str,
    ledger: Json,
    turn: int,
    pairs: list[tuple[str, str]],
) -> GenerationRequest:
    thread = ThreadSpec(
        "current-task",
        opening,
        (
            "Continue the same practical task using the complete factual/action ledger below.",
            "Output exactly this public message, with no preface, quotation marks, or additions: "
            + json.dumps(public_message(ledger)),
            "Do not add observations, constraints, questions, results, or private instructions.",
        ),
    )
    request = build_shared_interloper_request(
        thread=thread,
        prior_participant=pairs[-1][0],
        responses={"A": pairs[-1][1], "B": pairs[-1][1]},
        turn=turn,
    )
    return replace(request, parameters={**request.parameters, "max_new_tokens": 384}, seed=None)


def run(
    output: Path,
    state: Path,
    plan: Json,
    *,
    budget_path: Path,
    hosts: Mapping[str, Any],
    preprocess: Callable[[list[Json]], Json],
    expected_sha: str = STATE_SHA,
    replacement: str | None = None,
    selected_ids: tuple[str, ...] | None = None,
    run_key: str = "main",
) -> Json:
    if output.exists():
        raise RuntimeError("output must be a fresh directory; uncertain attempts cannot resume")
    if file_digest(state) != expected_sha:
        raise RuntimeError("frozen state SHA mismatch")
    schedules = plan["trajectories"]
    if replacement:
        schedules = [row for row in schedules if row["id"] == replacement]
        if len(schedules) != 1:
            raise ValueError("replacement must identify exactly one planned trajectory")
    if selected_ids is not None:
        if replacement or run_key == "main" or not budget_path.exists():
            raise ValueError("untouched continuation needs prior ledger and distinct run key")
        if not selected_ids or len(set(selected_ids)) != len(selected_ids):
            raise ValueError("continuation requires distinct selected trajectory IDs")
        prior = read_json(budget_path)
        attempted = {row["coordinate"].split("/")[1].split("-t")[0] for row in prior["calls"]}
        if attempted.intersection(selected_ids):
            raise RuntimeError("refusing to repeat any previously attempted trajectory")
        schedules = [row for row in schedules if row["id"] in selected_ids]
        if len(schedules) != len(selected_ids):
            raise ValueError("unknown selected trajectory")
    elif run_key != "main":
        raise ValueError("distinct run key only permitted for untouched continuation")
    replacement_index = int(replacement is not None)
    budget = CallBudget(budget_path, plan["budget"])
    budget.register_run(f"replacement-{replacement_index}" if replacement else run_key, output)
    write_json(output / "construction.json", plan)
    wrapped = {
        role: RecordingHost(hosts[role], output / "calls", role, budget)
        for role in ("gemma", "extractor", "quinn")
    }
    records: list[Json] = []
    rejections: list[Json] = []
    manifests = []
    store = CompactStore(state, read_only=True)
    before = store.state_digest()
    runtime = CompactRuntime(store)
    graph, learner = runtime.graph(), runtime.learner()
    strengths = {edge.key: _strength(edge, learner)[0] for edge in graph.edges}
    # The promoted chat/runtime do not implicitly read introspection adjustments.
    # Preserve observed metadata for review; do not silently invent/apply a key.
    metadata_keys = [row[0] for row in store.connection.execute("SELECT key FROM compact_meta")]
    write_json(
        output / "state_before.json",
        {
            "file_sha256": expected_sha,
            "state_digest": before,
            "metadata_keys": metadata_keys,
            "applied_accessibility_adjustments": {},
        },
    )
    try:
        for index, schedule in enumerate(schedules):
            domain, pattern = schedule["domain"], schedule["environment"]
            conversation = "p005" if replacement else schedule["id"]
            prefix = conversation
            manifests.append(
                {
                    "conversation": conversation,
                    "domain": domain,
                    "environment": pattern,
                    "planned_opportunity": schedule["planned_opportunity"],
                    "replaces": replacement,
                    "replacement_index": replacement_index,
                }
            )
            pairs: list[tuple[str, str]] = []
            opening = schedule["opening"]
            domain_index = schedule["seed_domain_index"]
            seed_offset = plan["seed_rule"]["replacement_offsets"][0] if replacement else 0
            for turn in range(1, int(schedule["turns"]) + 1):
                coordinate = f"{prefix}-t{turn:02d}"
                attempt: Json = {
                    "conversation": conversation,
                    "turn": turn,
                    "coordinate": coordinate,
                }
                try:
                    if turn == 1:
                        participant = opening
                    else:
                        ledger = schedule["ledger"][turn - 2]
                        request = quinn_request(opening, ledger, turn, pairs)
                        partner = wrapped["quinn"].generate(request, coordinate)
                        participant = partner.content.strip()
                        reasons = fact_gate(participant, ledger)
                        if reasons:
                            rejections.append(
                                {
                                    **attempt,
                                    "kind": "quinn_fidelity",
                                    "reasons": reasons,
                                    "participant_text": participant,
                                }
                            )
                            break
                    seed = (
                        domain_index * int(plan["seed_rule"]["domain_stride"]) + turn + seed_offset
                    )
                    evaluation = runtime.evaluate_saa(
                        participant, field_seed=int(plan["seed_rule"]["field_base"]) + seed
                    )
                    field = evaluation.field
                    system = GEMMA_SYSTEM_PROMPT + (
                        "\n\n" + field.payload.strip() if field.payload.strip() else ""
                    )
                    request, context = bounded_request(
                        pairs,
                        participant,
                        system,
                        int(plan["seed_rule"]["gemma_base"]) + seed,
                        plan["context_policy"],
                        plan["settings"]["gemma"],
                        preprocess,
                    )
                    write_json(
                        output / "contexts" / f"{coordinate}.json", context, root=budget_path.parent
                    )
                    response = wrapped["gemma"].generate(request, coordinate)
                    if not response.content.strip():
                        raise ValueError("Gemma returned empty text")
                    sources = {"s0": participant, "s1": response.content}
                    extract_request = GenerationRequest(
                        ({"role": "user", "content": json.dumps({"source_slots": sources})},),
                        parameters={"temperature": 0, "max_new_tokens": 768},
                        run_metadata={"episode_id": coordinate},
                    )
                    extraction: Json = {
                        "residue": None,
                        "extraction_coverage": {"s0": None, "s1": None},
                    }
                    try:
                        result = wrapped["extractor"].generate(extract_request, coordinate)
                        extraction = extraction_record(result, sources)
                    except Exception as exc:
                        extraction["error"] = f"{type(exc).__name__}: {exc}"
                    arc = declared_conversation_arcs(
                        [(i, domain) for i in range(1, turn + 1)],
                        conversation_id=conversation,
                    )[turn]
                    row = {
                        **attempt,
                        "ordinal": turn,
                        "accepted_turn_id": arc.turn_ids[-1],
                        "arc_id": arc.episode_id,
                        "arc": arc.to_dict(),
                        "opening_task": opening,
                        "participant_text": participant,
                        "gemma_text": response.content,
                        "sources": sources,
                        "source_roles": {"s0": "participant", "s1": "gemma"},
                        **extraction,
                        "field": field.to_dict(),
                        "historical_strengths": {
                            key: strengths[key] for key, _ in field.accessibility_distribution
                        },
                        "accessibility_adjustments": {},
                        "context": context,
                        "length": {
                            "gemma_words": len(response.content.split()),
                            "participant_words": len(participant.split()),
                            "finish_reason": response.finish_reason,
                            "token_usage": response.to_dict()["token_usage"],
                            "usage": response.raw_metadata.get("usage"),
                            "capped": response.finish_reason == "length",
                        },
                    }
                    records.append(row)
                    pairs.append((participant, response.content))
                except Exception as exc:
                    rejections.append(
                        {
                            **attempt,
                            "kind": "runtime_failure",
                            "reasons": [f"{type(exc).__name__}: {exc}"],
                        }
                    )
                    break
                finally:
                    write_json(output / "records.json", records, root=budget_path.parent)
                    write_json(output / "rejections.json", rejections, root=budget_path.parent)
                    write_json(
                        output / "condition_manifest.json", manifests, root=budget_path.parent
                    )
                    export_records(records, output, root=budget_path.parent)
    finally:
        after = store.state_digest()
        store.close()
        actual_sha = file_digest(state)
        receipt = {
            "before": before,
            "after": after,
            "file_sha_before": expected_sha,
            "file_sha_after": actual_sha,
            "unchanged": before == after and actual_sha == expected_sha,
            "accepted_turns": len(records),
            "rejections": len(rejections),
            "measurement_calls": 0,
        }
        write_json(output / "run_receipt.json", receipt, root=budget_path.parent)
        if not receipt["unchanged"]:
            raise RuntimeError("frozen state changed")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan", type=Path, default=Path("docs/experiments/meter_closure/construction.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--state", type=Path, default=Path("/tmp/mneme-d100-migration/I100-D100.compact.sqlite3")
    )
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--replace")
    parser.add_argument("--quinn-review", type=Path)
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--run-key", default="main")
    args = parser.parse_args()
    plan = read_json(args.plan)
    if args.replace:
        if not args.quinn_review:
            parser.error("replacement requires Root Quinn-only fidelity review")
        review = read_json(args.quinn_review)
        invalid = [row["conversation"] for row in review["trajectories"] if not row["quinn_valid"]]
        if not invalid or args.replace != invalid[0]:
            parser.error("only first Quinn-invalid trajectory is eligible for replacement")
    os.environ["MNEME_MSI_GEMMA_URL"] = GEMMA_URL
    if not os.environ.get("DEEPINFRA_TOKEN"):
        os.environ["DEEPINFRA_TOKEN"] = (
            Path("/home/nyx/.config/mneme/deepinfra_token").read_text().strip()
        )
    hosts = {
        "gemma": RemoteLlamaHost(),
        "extractor": RecordingGlinerHost(),
        "quinn": DeepInfraQwenAssessorHost(
            model_id="Qwen/Qwen3-30B-A3B",
            model_family="Qwen3 30B A3B",
            upstream_model_id="Qwen/Qwen3-30B-A3B",
            quantization="unknown/provider-managed",
        ),
    }
    print(
        json.dumps(
            run(
                args.output,
                args.state,
                plan,
                budget_path=args.budget,
                hosts=hosts,
                preprocess=native_preprocess,
                replacement=args.replace,
                selected_ids=tuple(args.only) if args.only else None,
                run_key=args.run_key,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
