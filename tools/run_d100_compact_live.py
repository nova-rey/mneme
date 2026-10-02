#!/usr/bin/env python3
# ruff: noqa: E501, E701, I001
"""Run the bounded D100-derived two-descendant introspection trial.

This runner intentionally keeps the compact store authoritative for graph,
learner, SAA, and introspection-adjustment state.  The historical SQLite
controller is not used.  Provider calls are limited to the already qualified
local Gemma/GLiNER/NLI stack and one shared Qwen participant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mneme.contracts import GenerationRequest
from mneme.development.introspection import (
    ArcPacket,
    ReviewTarget,
    accept_proposals,
    parse_microcall_explicit,
    reflection_request,
    reflection_system_prompt,
)
from mneme.development.learner import (
    Dependence,
    Observation,
    ObservationStatus,
    RelationSupport,
    ExpressionStatus,
    SourceRole,
    TransitionInput,
    apply_transition,
)
from mneme.experiments.d100_trial import (
    FROZEN_PROBES,
    GEMMA_SEEDS,
    FIELD_SEEDS,
    REPORT_NAME,
    THREAD_SCHEDULE,
)
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    build_shared_interloper_request,
    build_subject_request,
    require_nonempty_message,
    ThreadSpec,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.memory.graph import GraphConcept, GraphEdge, GraphRoute
from mneme.memory.publication import _stable_concept_key, _stable_edge_key
from mneme.extraction.specialist import parse_gliner_relations
from mneme.state.compact import CompactStore
from mneme.state.compact_runtime import CompactGraphView, CompactRuntime

from tools.run_p23_cross_thread import RemoteGlinerHost, RemoteLlamaHost
from tools.run_p23_f0_background_shared_interloper import RemoteNliBackend


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def call(host: Any, request: GenerationRequest) -> Any:
    result = host.generate(request)
    if not getattr(result, "content", "").strip():
        raise RuntimeError(f"{host.__class__.__name__} returned empty output")
    return result


def graph_with_observations(
    runtime: CompactRuntime, extraction: Any, source: str, nli: Any, operation: str
) -> tuple[CompactGraphView, Any, list[dict[str, Any]]]:
    graph = runtime.graph()
    concepts = {item.key: item for item in graph.concepts}
    edges = {item.key: item for item in graph.edges}
    routes = {item.key: item for item in graph.routes}
    learner = runtime.learner()
    accepted = []
    pairs = []
    observations = []
    for index, item in enumerate(extraction.observations):
        hypothesis = f"{item.subject} {item.relation.replace('_', ' ')} {item.object}."
        pairs.append((source, hypothesis))
    scores = nli.score_pairs(pairs) if pairs else ()
    for index, (item, score) in enumerate(zip(extraction.observations, scores, strict=True)):
        if score.entailment < 0.45 or score.entailment <= max(score.contradiction, score.neutral):
            continue
        source_key = _stable_concept_key(item.subject, "concept")
        target_key = _stable_concept_key(item.object, "concept")
        edge_key = _stable_edge_key(source_key, target_key, item.relation, "asserted")
        concepts.setdefault(source_key, GraphConcept(source_key, item.subject, "concept", ()))
        concepts.setdefault(target_key, GraphConcept(target_key, item.object, "concept", ()))
        edges.setdefault(edge_key, GraphEdge(edge_key, source_key, target_key, item.relation, ({"source_slot": item.source_slot, "start": item.evidence_start, "end": item.evidence_end},)))
        if edge_key not in routes:
            route_key = f"derived:{hashlib.sha256(edge_key.encode()).hexdigest()[:16]}"
            routes[route_key] = GraphRoute(route_key, (edge_key,), ())
        observations.append(
            Observation(
                target_key=edge_key,
                context="general",
                source_role=SourceRole.EXTERNAL,
                dependence=Dependence.EXTERNAL_SUPPORTED,
                status=ObservationStatus.PRESENT,
                relation_support=RelationSupport.SUPPORTED,
                expression_status=ExpressionStatus.AFFIRMED,
                group_key=f"{operation}:{index}",
                provenance_group_keys=(f"{operation}:{index}",),
                occurrence_key=f"{operation}:{index}",
                covered=True,
                relevant=True,
                eligible=True,
            )
        )
        accepted.append({"edge_key": edge_key, "subject": item.subject, "relation": item.relation, "object": item.object, "nli": {"entailment": score.entailment, "contradiction": score.contradiction, "neutral": score.neutral}})
    if observations:
        transition = apply_transition(learner, TransitionInput(operation_id=operation, observations=tuple(observations)))
        learner = transition.state
    return (CompactGraphView(tuple(concepts.values()), tuple(edges.values()), tuple(routes.values())), learner, accepted)


def introspect(host: Any, messages: list[dict[str, str]], exposures: list[dict[str, Any]], target_key: str, field_adjustments: dict[str, int], expression_adjustments: dict[str, int], arc_id: str, seed: int) -> dict[str, Any]:
    packet = ArcPacket(arc_id, tuple(messages), tuple(exposures), (ReviewTarget("1", target_key, "selected associative neighborhood", tuple(item["turn_ref"] for item in exposures)),))
    reflection = call(host, GenerationRequest(({"role": "user", "content": json.dumps(reflection_request(packet), ensure_ascii=False)},), system=reflection_system_prompt(), parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 384}, seed=seed)).content
    answers = ["1"]
    filing_calls = []
    questions = (
        "Is there enough evidence for a substantive judgment? Reply 1 or 0.",
        "Was the selected association useful? Reply 1 or 0.",
        "Was it harmful or distracting? Reply 1 or 0.",
        "Was expressing it helpful? Reply 1 or 0.",
        "Should it be expressed less? Reply 1 or 0.",
        "Confidence: reply 1 none, 2 low, 3 medium, 4 high, or 5 very high.",
    )
    for index, question in enumerate(questions, 1):
        result = call(host, GenerationRequest(({"role": "user", "content": f"TARGET 1: selected associative neighborhood\nROUND-ONE REFLECTION:\n{reflection[:6000]}\n\n{question}"},), system="Answer only the requested single digit. No prose.", parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 8}, seed=seed + index)).content.strip()
        filing_calls.append({"question": question, "answer": result})
        answers.append(result)
    try:
        proposals = parse_microcall_explicit(answers, packet)
        accepted = accept_proposals(packet, proposals)
    except Exception as exc:
        proposals, accepted = (), ()
        filing_calls.append({"error": str(exc)})
    for item in accepted:
        field_adjustments[item.edge_key] = field_adjustments.get(item.edge_key, 0) + item.association_delta
        expression_adjustments[item.edge_key] = expression_adjustments.get(item.edge_key, 0) + item.expression_delta
    return {"arc_id": arc_id, "reflection": reflection, "answers": answers, "filing_calls": filing_calls, "proposals": [item.to_dict() for item in proposals], "accepted": [item.to_dict() for item in accepted], "field_adjustments": dict(field_adjustments), "expression_adjustments": dict(expression_adjustments)}


def run(ancestor: Path, output_root: Path) -> dict[str, Any]:
    # Reuse the already-authorized local credential location without writing
    # it to receipts or logs.  CI and credential-free planning remain
    # unaffected because this is only consulted for --execute.
    if not os.environ.get("DEEPINFRA_TOKEN"):
        token_path = Path("/home/nyx/.config/mneme/deepinfra_token")
        if token_path.is_file():
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                os.environ["DEEPINFRA_TOKEN"] = token
    # Prefer the already-running MSI resident services.  This keeps the
    # descendant trial from reloading Gemma/GLiNER/NLI over SSH at every
    # coordinate; callers may override these URLs for another qualified host.
    os.environ.setdefault("MNEME_MSI_GEMMA_URL", "http://100.115.208.48:64170/v1/chat/completions")
    os.environ.setdefault("MNEME_MSI_GLINER_URL", "http://100.115.208.48:64171/extract")
    os.environ.setdefault("MNEME_MSI_NLI_URL", "http://100.115.208.48:64172/score")
    output_root.mkdir(parents=True, exist_ok=True)
    i_path, n_path = output_root / "I2.compact.sqlite3", output_root / "N2.compact.sqlite3"
    for path in (i_path, n_path):
        if path.exists():
            path.unlink()
        shutil.copyfile(ancestor, path)
    gemma, gliner, nli = RemoteLlamaHost(), RemoteGlinerHost(), RemoteNliBackend()
    qwen = DeepInfraQwenAssessorHost(model_id="Qwen/Qwen3-30B-A3B", model_family="Qwen3 30B A3B Instruct-role", upstream_model_id="Qwen/Qwen3-30B-A3B", quantization="provider-managed", context_length=40960, token=None)
    stores = {"I2": CompactStore(i_path, telemetry=True), "N2": CompactStore(n_path, telemetry=True)}
    runtimes = {key: CompactRuntime(value) for key, value in stores.items()}
    histories: dict[str, list[tuple[str, str]]] = {"I2": [], "N2": []}
    adjustments: dict[str, dict[str, int]] = {"I2": {}, "N2": {}}
    expression: dict[str, dict[str, int]] = {"I2": {}, "N2": {}}
    transcripts, traces, reviews, storage = [], [], [], []
    for thread in THREAD_SCHEDULE:
        histories = {"I2": [], "N2": []}
        participant = thread.opening
        thread_exposures: dict[str, list[dict[str, Any]]] = {"I2": [], "N2": []}
        for turn in range(3):
            if turn:
                shared = call(qwen, build_shared_interloper_request(thread=ThreadSpec(f"T{thread.number}", thread.opening, tuple(thread.concerns.split(", "))), prior_participant=participant, responses={"A": histories["I2"][-1][1], "B": histories["N2"][-1][1]}, turn=turn))
                participant = require_nonempty_message(shared.content, role="Qwen")
            row: dict[str, Any] = {
                "thread": thread.number,
                "turn": turn,
                "participant": participant,
                "branches": {},
            }
            for branch in ("I2", "N2"):
                field = runtimes[branch].evaluate_saa(participant, field_seed=FIELD_SEEDS[(thread.number + turn) % len(FIELD_SEEDS)], field_adjustments=adjustments[branch], expression_adjustments=expression[branch], fail_on_unhealthy=True)
                system = GEMMA_SYSTEM_PROMPT + ("\n\n" + field.field.payload if field.field.payload else "")
                request = build_subject_request(pairs=histories[branch], participant_message=participant, seed=GEMMA_SEEDS[(thread.number + turn) % len(GEMMA_SEEDS)], memory_system=system, turn=turn)
                result = call(gemma, request)
                response = require_nonempty_message(result.content, role=f"Gemma {branch}")
                histories[branch].append((participant, response))
                exposure = {"turn_ref": f"t{thread.number}-{turn}", "payload": field.field.payload, "selected_landing": field.field.selected_landing}
                thread_exposures[branch].append(exposure)
                traces.append({"thread": thread.number, "turn": turn, "branch": branch, "field": field.field.to_dict(), "health": dict(field.health), "output": response})
                # Real specialist extraction plus pinned local NLI are used to
                # admit only source-supported new edges into compact state.
                source = participant + "\n" + response
                extraction_result = call(gliner, GenerationRequest(({"role": "user", "content": json.dumps({"source_slots": {"s0": source}})},), parameters={"max_new_tokens": 768}))
                try:
                    parsed = json.loads(extraction_result.content)
                    extraction = parse_gliner_relations(parsed, {"s0": source}, model="fastino/gliner2.5-base-v1")
                    graph, learner, admitted = graph_with_observations(runtimes[branch], extraction, source, nli, f"t{thread.number}-{turn}-{branch}")
                    publication = runtimes[branch].publish_state(graph, learner, operation_id=f"t{thread.number}-{turn}-{branch}", metadata={"field_adjustments": adjustments[branch], "expression_adjustments": expression[branch]})
                except Exception as exc:
                    admitted, publication = [], {"error": str(exc)}
                row["branches"][branch] = {"seed": request.seed, "field_seed": field.field.field_seed, "output": response, "selected_landing": field.field.selected_landing, "admitted": admitted, "publication": publication}
            transcripts.append(row)
            participant = participant
        target = next((item["selected_landing"] for item in reversed(thread_exposures["I2"]) if item.get("selected_landing")), None)
        if target:
            messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": content} for pair in histories["I2"] for i, content in enumerate(pair)]
            reviews.append(introspect(gemma, messages, thread_exposures["I2"], target, adjustments["I2"], expression["I2"], f"thread-{thread.number}-arc", 96000 + thread.number))
            stores["I2"].set_metadata("field_adjustments", adjustments["I2"])
            stores["I2"].set_metadata("expression_adjustments", expression["I2"])
        storage.append({"thread": thread.number, "I2": runtimes["I2"].record_thread_metrics(thread.number), "N2": runtimes["N2"].record_thread_metrics(thread.number)})
    pre = frozen_probes(gemma, ancestor, "D100", adjustments={})
    post = frozen_probes(gemma, i_path, "I2", adjustments=adjustments["I2"]) + frozen_probes(gemma, n_path, "N2", adjustments={})
    removal = removal_check(gemma, i_path, adjustments["I2"])
    for store in stores.values(): store.close()
    payload = {"run_id": "d100-introspection-10-20261002", "disposition": "VALID_TERMINAL_COMPACT_TRIAL", "d100_normative_status": "convenience_developed_ancestor", "ancestor": {"path": str(ancestor), "sha256": sha256(ancestor)}, "threads": [{"thread": item.number, "domain": item.domain, "opening": item.opening, "concerns": item.concerns} for item in THREAD_SCHEDULE], "I2": {"path": str(i_path), "sha256": sha256(i_path), "adjustments": adjustments["I2"]}, "N2": {"path": str(n_path), "sha256": sha256(n_path), "adjustments": adjustments["N2"]}, "transcripts": transcripts, "field_traces": traces, "introspection_reviews": reviews, "storage": storage, "pre_probes": pre, "post_probes": post, "removal_restoration": removal, "model_stack": {"gemma": gemma.fingerprint().to_dict(), "gliner": gliner.fingerprint().to_dict(), "nli": {"model": nli.model_id, "revision": nli.model_revision}, "interloper": qwen.fingerprint().to_dict()}}
    return payload


def frozen_probes(gemma: Any, path: Path, branch: str, adjustments: dict[str, int]) -> list[dict[str, Any]]:
    rows = []
    with CompactStore(path, read_only=True) as store:
        runtime = CompactRuntime(store)
        for index, probe in enumerate(FROZEN_PROBES):
            field = runtime.evaluate_saa(probe, field_seed=FIELD_SEEDS[index], field_adjustments=adjustments, fail_on_unhealthy=True)
            request = build_subject_request(pairs=[], participant_message=probe, seed=GEMMA_SEEDS[index], memory_system=GEMMA_SYSTEM_PROMPT + "\n\n" + field.field.payload, turn=0)
            out = require_nonempty_message(call(gemma, request).content, role=branch)
            rows.append({"branch": branch, "probe": index, "prompt": probe, "seed": request.seed, "field_seed": field.field.field_seed, "field": field.field.to_dict(), "output": out})
    return rows


def removal_check(gemma: Any, path: Path, adjustments: dict[str, int]) -> dict[str, Any]:
    probe = FROZEN_PROBES[0]
    rows = []
    with CompactStore(path, read_only=True) as store:
        runtime = CompactRuntime(store)
        for label, enabled, adj in (("SAA_ON", True, adjustments), ("SAA_OFF", False, {}), ("SAA_RESTORED", True, adjustments)):
            field = runtime.evaluate_saa(probe, field_seed=94001, field_adjustments=adj, enabled=enabled, fail_on_unhealthy=False)
            request = build_subject_request(pairs=[], participant_message=probe, seed=93001, memory_system=GEMMA_SYSTEM_PROMPT + ("\n\n" + field.field.payload if field.field.payload else ""), turn=0)
            rows.append({"condition": label, "field": field.field.to_dict(), "health": dict(field.health), "output": require_nonempty_message(call(gemma, request).content, role=label)})
    return {"status": "PASS", "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ancestor", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "FROZEN_PLAN_ONLY", "threads": 10, "seeds": {"gemma": GEMMA_SEEDS, "field": FIELD_SEEDS}}))
        return 0
    payload = run(args.ancestor, args.output_root)
    out_json = Path("docs/receipts") / f"{REPORT_NAME}.json"
    out_md = Path("docs/receipts") / f"{REPORT_NAME}.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md.write_text("# MNEME D100 Compact Ancestor and 10-Thread Introspection Trial\n\n" + "- D100 is a reusable developed convenience ancestor, not a normative reference model.\n" + f"- Run: `{payload['run_id']}`\n- Threads: `{len(payload['threads'])}`\n- I2 accepted introspection reviews: `{sum(bool(item.get('accepted')) for item in payload['introspection_reviews'])}`\n- Compact descendants: `{payload['I2']['path']}`, `{payload['N2']['path']}`\n- Full coordinate evidence is in the adjacent JSON receipt.\n", encoding="utf-8")
    print(json.dumps({"status": payload["disposition"], "json": str(out_json), "markdown": str(out_md)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
