#!/usr/bin/env python3
# ruff: noqa: E501, E402, I001
"""Run the clean-slate 25-thread Gemma reasoning OFF/ON trial.

This is an isolated experiment runner.  It uses CompactStore, the existing
GLiNER/NLI specialists, the shared Qwen participant, and two resident local
Gemma endpoints whose only treatment difference is server-native reasoning.
Every Gemma request explicitly disables llama.cpp prompt-cache reuse.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "src"))

from mneme.contracts import (
    Capability,
    GenerationRequest,
    GenerationResult,
    HostCapabilities,
    HostFingerprint,
    TokenUsage,
)
from mneme.development.introspection import (
    ArcPacket,
    FilingLevel,
    ReviewTarget,
    accept_proposals,
    filing_system_prompt,
    parse_microcall_explicit,
    reflection_request,
    reflection_system_prompt,
)
from mneme.development.learner import (
    Dependence,
    ExpressionStatus,
    Observation,
    ObservationStatus,
    RelationSupport,
    SourceRole,
    TransitionInput,
    apply_transition,
)
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
    build_subject_request,
    require_nonempty_message,
)
from mneme.memory.graph import GraphConcept, GraphEdge, GraphRoute
from mneme.memory.publication import _stable_concept_key, _stable_edge_key
from mneme.state.compact import CompactStore
from mneme.state.compact_runtime import CompactGraphView, CompactRuntime

from tools.run_p23_cross_thread import RemoteGlinerHost
from tools.run_p23_f0_background_shared_interloper import RemoteNliBackend
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost

RUN_ID = "mneme-reasoning-25-20261003"
THREAD_TURNS = 4
MODEL = "gemma-4-E4B-it-qat-UD-Q2_K_XL"
MODEL_ID = "google/gemma-4-E4B-it"
GEMMA_SEED_BASE = 710100
FIELD_SEED_BASE = 720100
REFLECTION_SEED_BASE = 730100
FILING_SEED_BASE = 740100
PROBE_SEED_BASE = 750100
PROBE_FIELD_BASE = 760100
MODEL_SHA256 = "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"
LLAMA_COMMIT = "4b1a27fa0eb875bbca4f6cfe936e3d65adc685c0"

# Frozen before execution.  The openings are deliberately broad and do not
# prescribe a graph association or an expected reasoning outcome.
SCHEDULE: tuple[ThreadSpec, ...] = (
    ThreadSpec("T01", "I am trying to keep a small shared garden useful during a dry week.", ("limited water", "unattended care", "visible trouble")),
    ThreadSpec("T02", "I need to plan a short trip when weather and timing are uncertain.", ("packing", "route changes", "missed connections")),
    ThreadSpec("T03", "I want to improvise dinner from ingredients that do not quite fit together.", ("substitution", "sequencing", "preserving options")),
    ThreadSpec("T04", "Our small ensemble keeps losing its shape when the tempo changes.", ("timing", "repetition", "variation")),
    ThreadSpec("T05", "A household tool works intermittently and I only have basic supplies.", ("diagnosis", "isolation", "reversible repair")),
    ThreadSpec("T06", "I am designing a simple game where luck should not erase every good decision.", ("probability", "uneven outcomes", "recovery")),
    ThreadSpec("T07", "I have too many visual ideas for one small poster.", ("composition", "emphasis", "revision")),
    ThreadSpec("T08", "Several people share equipment but their schedules rarely line up.", ("handoffs", "visibility", "fairness")),
    ThreadSpec("T09", "I am trying to keep track of a changing night sky with modest equipment.", ("calibration", "uncertainty", "repeated observation")),
    ThreadSpec("T10", "A small seasonal community must prepare for an uncertain month with limited supplies and changing volunteers.", ("sequencing", "resources", "communication", "adaptation")),
    ThreadSpec("T11", "I am organizing a household budget while several expenses remain unpredictable.", ("tradeoffs", "buffers", "changing priorities")),
    ThreadSpec("T12", "A local wildlife survey has gaps because volunteers visit at different times.", ("sampling", "coverage", "interpretation")),
    ThreadSpec("T13", "I am setting up a small workshop where tools and attention are both limited.", ("layout", "access", "safe fallback")),
    ThreadSpec("T14", "I want to learn enough of a new language to handle ordinary errands.", ("practice", "mistakes", "useful repetition")),
    ThreadSpec("T15", "A community event has many contributors and the schedule keeps shifting.", ("coordination", "handoffs", "last-minute changes")),
    ThreadSpec("T16", "I am preparing a home for a week of extreme weather without buying everything new.", ("preparedness", "resource limits", "failure signs")),
    ThreadSpec("T17", "A family archive contains many boxes but only a small amount of time is available.", ("selection", "ordering", "future access")),
    ThreadSpec("T18", "I am planning a bicycle route for people with different experience levels.", ("pace", "rest", "alternate paths")),
    ThreadSpec("T19", "A small shop must decide which custom requests it can handle this month.", ("capacity", "promises", "customer expectations")),
    ThreadSpec("T20", "A class project has uneven participation and a deadline that cannot move.", ("roles", "feedback", "completion")),
    ThreadSpec("T21", "I am taking photographs in changing light with equipment I already own.", ("adjustment", "timing", "discarding")),
    ThreadSpec("T22", "A pond restoration effort has several possible interventions but limited monitoring.", ("intervention", "evidence", "slow change")),
    ThreadSpec("T23", "A software workflow has grown messy as more people add small fixes.", ("interfaces", "regression", "incremental repair")),
    ThreadSpec("T24", "A neighborhood festival needs to remain welcoming if a few planned parts fail.", ("redundancy", "communication", "recovery")),
    ThreadSpec("T25", "An expedition must make practical decisions while conditions, supplies, and roles keep changing.", ("uncertainty", "sequencing", "adaptation", "human limits")),
)

FROZEN_PROBES = (
    "A small team must keep an unfamiliar project usable while people have changing schedules. What would you examine first?",
    "An arrangement must tolerate an interruption without making every earlier effort useless. How would you think about it?",
    "A creative plan has many possible directions but limited attention. What should guide what remains visible?",
    "An unfamiliar process produces uneven results. What would you investigate before changing the whole process?",
)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return digest_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class DeterministicRemoteGemma:
    """OpenAI-compatible resident Gemma endpoint with explicit no-cache calls."""

    name: str
    port: int
    reasoning: str
    max_tokens: int

    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.LOCAL_WEIGHTS, Capability.SEED_CONTROL, Capability.TOKEN_USAGE}))

    def fingerprint(self) -> HostFingerprint:
        return HostFingerprint(
            model_family="Gemma 4 E4B",
            model_id=MODEL_ID,
            model_revision=MODEL_SHA256,
            tokenizer_id=MODEL_ID,
            tokenizer_revision=MODEL_SHA256,
            chat_template="llama.cpp resident Gemma template",
            quantization="UD-Q2_K_XL",
            runtime="llama.cpp",
            runtime_version=f"0.5.0-dev/{LLAMA_COMMIT}",
            provider="local-msi",
            execution={
                "endpoint": f"http://100.115.208.48:{self.port}/v1/chat/completions",
                "reasoning": self.reasoning,
                "cache_prompt": False,
                "context_size": 8192 if self.reasoning == "on" else 4096,
                "gpu_layers": 99,
                "temperature": 0.35,
                "top_k": 40,
                "top_p": 0.90,
                "min_p": 0.05,
                "model_gguf_sha256": MODEL_SHA256,
            },
            capabilities=self.capabilities().supported,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        parameters = dict(request.parameters)
        body: dict[str, Any] = {
            "model": MODEL,
            "messages": ([{"role": "system", "content": request.system}] if request.system else []) + [dict(item) for item in request.messages],
            "max_tokens": int(parameters.get("max_new_tokens", self.max_tokens)),
            "temperature": float(parameters.get("temperature", 0.35)),
            "top_k": int(parameters.get("top_k", 40)),
            "top_p": float(parameters.get("top_p", 0.90)),
            "min_p": float(parameters.get("min_p", 0.05)),
            "stream": False,
            "cache_prompt": False,
        }
        if isinstance(parameters.get("chat_template_kwargs"), dict):
            body["chat_template_kwargs"] = dict(parameters["chat_template_kwargs"])
        if request.seed is not None:
            body["seed"] = int(request.seed)
        body_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        started = time.perf_counter()
        req = urllib.request.Request(
            f"http://100.115.208.48:{self.port}/v1/chat/completions",
            data=body_bytes,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=900) as response:
            decoded = json.loads(response.read().decode())
        choices = decoded.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(f"{self.name} returned no choices")
        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"{self.name} returned empty content: finish_reason={choice.get('finish_reason')!r} "
                f"usage={decoded.get('usage')!r} reasoning_bytes={len(str(message.get('reasoning_content', '')).encode())}"
            )
        reasoning_content = message.get("reasoning_content", "")
        if not isinstance(reasoning_content, str):
            reasoning_content = ""
        usage = decoded.get("usage") if isinstance(decoded.get("usage"), dict) else {}
        token_usage = TokenUsage(
            usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens")
        )
        return GenerationResult(
            content=content,
            model_id=MODEL_ID,
            provider="local-msi",
            effective_parameters={**parameters, "cache_prompt": False, "top_k": body["top_k"], "min_p": body["min_p"]},
            seed=request.seed,
            token_usage=token_usage,
            latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason=str(choice.get("finish_reason", "stop")),
            raw_metadata={
                "request_sha256": digest_bytes(body_bytes),
                # Continuation evidence requires the exact host-visible
                # request and the reasoning signal itself.  Keep these in the
                # result metadata so callers can persist them atomically;
                # historical receipts remain unchanged unless rerun.
                "request_body_utf8": body_bytes.decode("utf-8"),
                "request_payload": json.loads(body_bytes.decode("utf-8")),
                "reasoning": self.reasoning,
                "reasoning_content": reasoning_content,
                "reasoning_bytes": len(reasoning_content.encode()),
                "reasoning_sha256": digest_bytes(reasoning_content.encode()),
                "usage": usage,
                "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) if isinstance(usage.get("prompt_tokens_details"), dict) else 0,
            },
            provenance={"host": self.fingerprint().to_dict()},
        )


@dataclass(frozen=True)
class CandidateObservation:
    subject: str
    relation: str
    object: str
    source_slot: str
    evidence_start: int
    evidence_end: int


def result_record(result: GenerationResult, *, output: bool = True) -> dict[str, Any]:
    usage = (
        {
            "input_tokens": result.token_usage.input_tokens,
            "output_tokens": result.token_usage.output_tokens,
            "total_tokens": result.token_usage.total_tokens,
        }
        if result.token_usage is not None
        else None
    )
    row = {
        "model_id": result.model_id,
        "provider": result.provider,
        "seed": result.seed,
        "effective_parameters": result.effective_parameters,
        "finish_reason": result.finish_reason,
        "latency_ms": result.latency_ms,
        "token_usage": usage,
        "raw_metadata": result.raw_metadata,
        "output_sha256": digest_bytes(result.content.encode()),
        "output_bytes": len(result.content.encode()),
    }
    if output:
        row["output"] = result.content
    return row


def call(host: Any, request: GenerationRequest, *, label: str, calls: list[dict[str, Any]], include_output: bool = True) -> GenerationResult:
    result = host.generate(request)
    if not result.content.strip():
        raise RuntimeError(f"{label} returned empty output")
    calls.append({"label": label, **result_record(result, output=include_output)})
    return result


def graph_with_observations(runtime: CompactRuntime, observations: tuple[CandidateObservation, ...], source: str, nli: RemoteNliBackend, operation: str) -> tuple[CompactGraphView, Any, list[dict[str, Any]], dict[str, Any]]:
    graph = runtime.graph()
    concepts = {item.key: item for item in graph.concepts}
    edges = {item.key: item for item in graph.edges}
    routes = {item.key: item for item in graph.routes}
    learner = runtime.learner()
    candidate_items = observations
    pairs = [(source, f"{item.subject} {item.relation.replace('_', ' ')} {item.object}.") for item in candidate_items]
    scores = nli.score_pairs(pairs) if pairs else ()
    if len(scores) != len(candidate_items):
        raise RuntimeError(
            f"NLI candidate/score mismatch: candidates={len(candidate_items)} pairs={len(pairs)} scores={len(scores)}"
        )
    accepted: list[dict[str, Any]] = []
    accepted_observations: list[Observation] = []
    rejected = 0
    candidate_details: list[dict[str, Any]] = []
    for index, (item, score) in enumerate(zip(candidate_items, scores, strict=True)):
        accepted_candidate = score.entailment >= 0.45 and score.entailment > max(score.contradiction, score.neutral)
        rejection_reason = None if accepted_candidate else (
            "below_entailment_threshold" if score.entailment < 0.45 else "not_entailment_dominant"
        )
        candidate_details.append({
            "index": index,
            "subject": item.subject,
            "relation": item.relation,
            "object": item.object,
            "source_slot": item.source_slot,
            "evidence_start": item.evidence_start,
            "evidence_end": item.evidence_end,
            "evidence": source[item.evidence_start:item.evidence_end],
            "nli": {"entailment": score.entailment, "contradiction": score.contradiction, "neutral": score.neutral},
            "accepted": accepted_candidate,
            "rejection_reason": rejection_reason,
        })
        if not accepted_candidate:
            rejected += 1
            continue
        source_key = _stable_concept_key(item.subject, "concept")
        target_key = _stable_concept_key(item.object, "concept")
        edge_key = _stable_edge_key(source_key, target_key, item.relation, "asserted")
        concepts.setdefault(source_key, GraphConcept(source_key, item.subject, "concept", ()))
        concepts.setdefault(target_key, GraphConcept(target_key, item.object, "concept", ()))
        edges.setdefault(edge_key, GraphEdge(edge_key, source_key, target_key, item.relation, ({"source_slot": item.source_slot, "start": item.evidence_start, "end": item.evidence_end},)))
        if edge_key not in routes:
            routes[f"derived:{hashlib.sha256(edge_key.encode()).hexdigest()[:16]}"] = GraphRoute(f"derived:{hashlib.sha256(edge_key.encode()).hexdigest()[:16]}", (edge_key,), ())
        accepted_observations.append(Observation(
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
        ))
        accepted.append({"edge_key": edge_key, "subject": item.subject, "relation": item.relation, "object": item.object, "nli": {"entailment": score.entailment, "contradiction": score.contradiction, "neutral": score.neutral}})
    if accepted_observations:
        transition = apply_transition(learner, TransitionInput(operation_id=operation, observations=tuple(accepted_observations)))
        learner = transition.state
    graph_out = CompactGraphView(tuple(concepts.values()), tuple(edges.values()), tuple(routes.values()))
    return graph_out, learner, accepted, {
        "extracted": len(candidate_items),
        "accepted": len(accepted),
        "rejected": rejected,
        "candidates": candidate_details,
    }


def histories_to_messages(history: list[tuple[str, str]]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for participant, response in history:
        messages.extend(({"role": "user", "content": participant}, {"role": "assistant", "content": response}))
    return messages


def introspect(branch: str, host: DeterministicRemoteGemma, history: list[tuple[str, str]], exposures: list[dict[str, Any]], thread: int, calls: list[dict[str, Any]], adjustments: dict[str, int], expression_adjustments: dict[str, int]) -> dict[str, Any]:
    by_landing: dict[str, list[str]] = {}
    for exposure in exposures:
        landing = exposure.get("selected_landing")
        if landing:
            by_landing.setdefault(str(landing), []).append(str(exposure["turn_ref"]))
    if not by_landing:
        return {"branch": branch, "thread": thread, "status": "ABSTAINED_NO_TARGETS", "targets": [], "accepted": [], "filing": []}
    targets = tuple(ReviewTarget(str(index), edge_key, "selected associative framing", tuple(refs)) for index, (edge_key, refs) in enumerate(sorted(by_landing.items()), 1))
    packet = ArcPacket(f"thread-{thread}-{branch}-arc", tuple(histories_to_messages(history)), tuple(exposures), targets)
    reflection_result = call(host, GenerationRequest(({"role": "user", "content": json.dumps(reflection_request(packet), ensure_ascii=False)},), system=reflection_system_prompt(), parameters={"temperature": 0.35, "top_p": 0.9, "top_k": 40, "min_p": 0.05, "max_new_tokens": 768 if host.reasoning == "off" else 8192}, seed=REFLECTION_SEED_BASE + thread * 10 + (0 if branch == "OFF" else 1)), label=f"{branch}:thread-{thread}:reflection", calls=calls)
    reflection = reflection_result.content
    target_lines = "\n".join(f"{target.alias}. {target.context}" for target in targets)
    filing: list[dict[str, Any]] = []
    answers: list[str] = []
    questions = (
        f"Which single target are you evaluating? Reply 0 for none, or one of {', '.join(target.alias for target in targets)} only.",
        "Is there enough evidence for a substantive judgment? Reply 0 or 1 only.",
        "Was the selected association useful or interesting? Reply 0 or 1 only.",
        "Was it harmful or distracting? Reply 0 or 1 only.",
        "Was expressing it helpful? Reply 0 or 1 only.",
        "Should it be expressed less or left latent? Reply 0 or 1 only.",
        "Confidence: reply 1 none, 2 low, 3 medium, 4 high, or 5 very high.",
    )
    for index, question in enumerate(questions):
        prompt = f"TARGET OPTIONS:\n{target_lines}\n\nROUND-ONE REFLECTION:\n{reflection[:12000]}\n\n{question}"
        filing_parameters: dict[str, Any] = {"temperature": 0.0, "top_p": 0.9, "top_k": 40, "min_p": 0.05, "max_new_tokens": 128 if host.reasoning == "off" else 512}
        if host.reasoning == "on":
            # Round Two is clerical serialization. Round One remains the
            # reasoning-enabled semantic judgment; this keeps the host from
            # spending the whole filing allowance before emitting one digit.
            filing_parameters["chat_template_kwargs"] = {"enable_thinking": False}
        result = call(host, GenerationRequest(({"role": "user", "content": prompt},), system=filing_system_prompt(FilingLevel.MICROCALL_EXPLICIT), parameters=filing_parameters, seed=FILING_SEED_BASE + thread * 100 + index * 10 + (0 if branch == "OFF" else 1)), label=f"{branch}:thread-{thread}:filing-{index}", calls=calls)
        answer = result.content.strip()
        answers.append(answer)
        filing.append({"question": question, "answer": answer, "result": result_record(result, output=True)})
    try:
        proposals = parse_microcall_explicit(answers, packet)
        accepted = accept_proposals(packet, proposals)
    except Exception as exc:
        return {"branch": branch, "thread": thread, "status": "ABSTAINED_MALFORMED", "targets": [target.to_dict() for target in targets], "reflection": reflection, "answers": answers, "filing": filing, "accepted": [], "error": f"{type(exc).__name__}: {exc}"}
    for item in accepted:
        adjustments[item.edge_key] = adjustments.get(item.edge_key, 0) + item.association_delta
        expression_adjustments[item.edge_key] = expression_adjustments.get(item.edge_key, 0) + item.expression_delta
    return {"branch": branch, "thread": thread, "status": "ACCEPTED" if accepted else "NO_CHANGE", "targets": [target.to_dict() for target in targets], "reflection": reflection, "answers": answers, "filing": filing, "proposals": [item.to_dict() for item in proposals], "accepted": [item.to_dict() for item in accepted], "adjustments_after": dict(adjustments), "expression_adjustments_after": dict(expression_adjustments)}


def state_summary(store: CompactStore, runtime: CompactRuntime) -> dict[str, Any]:
    graph = runtime.graph()
    learner = runtime.learner()
    values = list(store.learner_state().values())
    return {
        "state_digest": store.state_digest(),
        "verify": runtime.verify(),
        "concepts": len(graph.concepts),
        "edges": len(graph.edges),
        "routes": len(graph.routes),
        "learner_values": len(values),
        "positive_learner_values": sum(1 for value in values if max(int(value.get("accessibility", 0)), int(value.get("support", 0))) > 0),
        "accessibility_range": [min((int(value.get("accessibility", 0)) for value in values), default=0), max((int(value.get("accessibility", 0)) for value in values), default=0)],
        "support_range": [min((int(value.get("support", 0)) for value in values), default=0), max((int(value.get("support", 0)) for value in values), default=0)],
        "global_opportunity": learner.global_opportunity,
        "storage_metrics": store.storage_metrics(label="summary"),
    }


def copy_newborn(path: Path, *, instance_id: str, schedule_hash: str, branch: str) -> None:
    with CompactStore.create(path, telemetry=True, telemetry_retention=128, journal_retention=256) as store:
        store.set_metadata("instance", {"instance_id": instance_id, "branch": branch, "persistence_mode": "compact", "developmental_writable": True})
        store.set_metadata("run_id", RUN_ID)
        store.set_metadata("reasoning_condition", branch)
        store.set_metadata("schedule_sha256", schedule_hash)
        store.set_metadata("saa_config", {"version": "f0-saa-v1", "field_seed_stream": "separate"})
        store.set_metadata("field_adjustments", {})
        store.set_metadata("expression_adjustments", {})


def copy_branch(ancestor: Path, path: Path, *, branch: str, schedule_hash: str) -> None:
    """Create a writable branch copy with explicit lineage metadata."""

    shutil.copyfile(ancestor, path)
    with CompactStore(path, telemetry=True, telemetry_retention=128, journal_retention=256) as store:
        store.set_metadata("instance", {"instance_id": f"{RUN_ID}-{branch.lower()}", "branch": branch, "persistence_mode": "compact", "developmental_writable": True})
        store.set_metadata("run_id", RUN_ID)
        store.set_metadata("reasoning_condition", branch)
        store.set_metadata("schedule_sha256", schedule_hash)


def checkpoint(store: CompactStore, path: Path, checkpoint_id: str) -> dict[str, Any]:
    if path.exists():
        raise RuntimeError(f"checkpoint already exists: {path}")
    store.checkpoint(path, checkpoint_id=checkpoint_id)
    with CompactStore(path, read_only=True) as frozen:
        return {"path": str(path), "sha256": file_sha256(path), "state_digest": frozen.state_digest(), "verify": frozen.verify(), "bytes": path.stat().st_size}


def persist_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Durably append one externally produced evidence row before continuing."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def frozen_readouts(
    hosts: dict[str, DeterministicRemoteGemma],
    paths: dict[str, Path],
    *,
    calls: list[dict[str, Any]],
    label_prefix: str,
    evidence_path: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for branch in ("OFF", "ON"):
        with CompactStore(paths[branch], read_only=True) as store:
            runtime = CompactRuntime(store)
            adjustments = store.metadata("field_adjustments", {})
            expressions = store.metadata("expression_adjustments", {})
            for index, probe in enumerate(FROZEN_PROBES):
                field = runtime.evaluate_saa(probe, field_seed=PROBE_FIELD_BASE + index, field_adjustments=adjustments, expression_adjustments=expressions, fail_on_unhealthy=True)
                request = build_subject_request(pairs=[], participant_message=probe, seed=PROBE_SEED_BASE + index, memory_system=GEMMA_SYSTEM_PROMPT + ("\n\n" + field.field.payload if field.field.payload else ""), turn=0)
                request = GenerationRequest(request.messages, system=request.system, parameters={**request.parameters, "top_k": 40, "min_p": 0.05, "max_new_tokens": hosts[branch].max_tokens}, seed=request.seed, run_metadata=request.run_metadata)
                result = call(hosts[branch], request, label=f"{label_prefix}:{branch}:probe-{index}", calls=calls)
                row = {"kind": "frozen_readout", "branch": branch, "probe": index, "probe_text": probe, "field": field.field.to_dict(), "health": dict(field.health), "output": result.content, "result": result_record(result, output=True), "state_digest": store.state_digest()}
                persist_jsonl(evidence_path, row)
                rows.append(row)
    return rows


def removal_restoration(host: DeterministicRemoteGemma, path: Path, *, calls: list[dict[str, Any]], evidence_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    probe = FROZEN_PROBES[0]
    with CompactStore(path, read_only=True) as store:
        runtime = CompactRuntime(store)
        adjustments = store.metadata("field_adjustments", {})
        expressions = store.metadata("expression_adjustments", {})
        for index, (label, enabled, field_adjust, expr_adjust) in enumerate((("SAA_ON", True, adjustments, expressions), ("SAA_OFF", False, {}, {}), ("SAA_RESTORED", True, adjustments, expressions))):
            field = runtime.evaluate_saa(probe, field_seed=PROBE_FIELD_BASE + 99, field_adjustments=field_adjust, expression_adjustments=expr_adjust, enabled=enabled, fail_on_unhealthy=False)
            request = build_subject_request(pairs=[], participant_message=probe, seed=PROBE_SEED_BASE + 99, memory_system=GEMMA_SYSTEM_PROMPT + ("\n\n" + field.field.payload if field.field.payload else ""), turn=0)
            request = GenerationRequest(request.messages, system=request.system, parameters={**request.parameters, "top_k": 40, "min_p": 0.05, "max_new_tokens": host.max_tokens}, seed=request.seed, run_metadata=request.run_metadata)
            result = call(host, request, label=f"removal:{label}", calls=calls)
            row = {"kind": "removal_restoration", "condition": label, "field": field.field.to_dict(), "health": dict(field.health), "output": result.content, "result": result_record(result, output=True)}
            persist_jsonl(evidence_path, row)
            rows.append(row)
    return rows


def run(
    output_root: Path,
    *,
    max_threads: int = 25,
    resume: bool = False,
    stop_after_thread: int | None = None,
) -> dict[str, Any]:
    if max_threads < 1 or max_threads > len(SCHEDULE):
        raise ValueError(f"max_threads must be between 1 and {len(SCHEDULE)}")
    if stop_after_thread is not None and (stop_after_thread < 1 or stop_after_thread > max_threads):
        raise ValueError("stop_after_thread must be within the requested thread range")
    output_root.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("DEEPINFRA_TOKEN"):
        token_path = Path("/home/nyx/.config/mneme/deepinfra_token")
        if token_path.is_file():
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                os.environ["DEEPINFRA_TOKEN"] = token
    schedule_hash = digest_json([item.to_dict() for item in SCHEDULE])
    ancestor = output_root / "newborn-ancestor.compact.sqlite3"
    off_path = output_root / "OFF-live.compact.sqlite3"
    on_path = output_root / "ON-live.compact.sqlite3"
    if not resume:
        for path in (ancestor, off_path, on_path):
            path.unlink(missing_ok=True)
        copy_newborn(ancestor, instance_id=f"{RUN_ID}-ancestor", schedule_hash=schedule_hash, branch="ANCESTOR")
        copy_branch(ancestor, off_path, branch="OFF", schedule_hash=schedule_hash)
        copy_branch(ancestor, on_path, branch="ON", schedule_hash=schedule_hash)
    elif not all(path.exists() for path in (ancestor, off_path, on_path)):
        raise FileNotFoundError("resume requires ancestor and both live CompactStore files")
    with CompactStore(off_path, read_only=True) as off0, CompactStore(on_path, read_only=True) as on0, CompactStore(ancestor, read_only=True) as anc0:
        equivalence = {"ancestor_off": off0.state_digest() == anc0.state_digest(), "ancestor_on": on0.state_digest() == anc0.state_digest(), "ancestor_digest": anc0.state_digest(), "off_digest": off0.state_digest(), "on_digest": on0.state_digest(), "off_verify": off0.verify(), "on_verify": on0.verify()}
    hosts = {"OFF": DeterministicRemoteGemma("Gemma-OFF", 64170, "off", 512), "ON": DeterministicRemoteGemma("Gemma-ON", 64173, "on", 8192)}
    # Determinism preflight is outside developmental state and is retained as a
    # compact hash/parameter record rather than added to any lineage. A resumed
    # process reuses the durable preflight instead of spending new calls.
    progress_path = output_root / "progress.json"
    evidence_path = output_root / "development-evidence.json"
    prior_progress = json.loads(progress_path.read_text(encoding="utf-8")) if resume and progress_path.exists() else {}
    prior_evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if resume and evidence_path.exists() else {}
    preflight: dict[str, Any] = prior_progress.get("preflight", {}) if resume else {}
    if not preflight.get("results"):
        preflight = {"cache_prompt": False, "seed": 710001, "prompt": "Explain in four concise sentences why a city might use both buses and trains.", "results": {}}
        for branch, host in hosts.items():
            rows = []
            for repeat in range(2):
                preflight_limit = 512 if host.reasoning == "off" else 1024
                result = host.generate(GenerationRequest(({"role": "user", "content": preflight["prompt"]},), system="You are a thoughtful conversational assistant. Respond naturally and concisely.", parameters={"temperature": 0.35, "top_k": 40, "top_p": 0.90, "min_p": 0.05, "max_new_tokens": preflight_limit}, seed=preflight["seed"]))
                rows.append(result_record(result, output=False))
            if rows[0]["output_sha256"] != rows[1]["output_sha256"] or rows[0]["finish_reason"] != "stop" or rows[1]["finish_reason"] != "stop":
                raise RuntimeError(f"determinism preflight failed for {branch}: {rows}")
            preflight["results"][branch] = rows
        progress_path.write_text(json.dumps({"run_id": RUN_ID, "stage": "preflight_passed", "preflight": preflight}, indent=2) + "\n", encoding="utf-8")
    gliner = RemoteGlinerHost()
    nli = RemoteNliBackend()
    qwen = DeepInfraQwenAssessorHost(model_id="Qwen/Qwen3-30B-A3B", model_family="Qwen3 30B A3B Instruct-role", upstream_model_id="Qwen/Qwen3-30B-A3B", quantization="provider-managed", context_length=40960, token=None)
    stores = {"OFF": CompactStore(off_path, telemetry=True, telemetry_retention=128, journal_retention=256), "ON": CompactStore(on_path, telemetry=True, telemetry_retention=128, journal_retention=256)}
    runtimes = {branch: CompactRuntime(store) for branch, store in stores.items()}
    histories = {"OFF": [], "ON": []}
    adjustments: dict[str, dict[str, int]] = {"OFF": {}, "ON": {}}
    expression_adjustments: dict[str, dict[str, int]] = {"OFF": {}, "ON": {}}
    transcripts: list[dict[str, Any]] = list(prior_evidence.get("transcripts", []))
    field_traces: list[dict[str, Any]] = list(prior_evidence.get("field_traces", []))
    extraction_records: list[dict[str, Any]] = list(prior_evidence.get("extraction_records", []))
    introspection_reviews: list[dict[str, Any]] = list(prior_evidence.get("introspection_reviews", []))
    calls: list[dict[str, Any]] = list(prior_evidence.get("calls", []))
    storage: list[dict[str, Any]] = list(prior_evidence.get("storage", []))
    checkpoints: dict[str, Any] = dict(prior_progress.get("checkpoints", {}))
    checkpoints.setdefault("clean_ancestor", {"path": str(ancestor), "sha256": file_sha256(ancestor), "state_digest": equivalence["ancestor_digest"]})
    completed_thread = int(prior_progress.get("completed_thread", 0)) if resume else 0
    schedule = SCHEDULE[:max_threads]
    checkpoint_targets = {10, max_threads} if max_threads > 2 else {max_threads}
    if resume:
        for branch, store in stores.items():
            adjustments[branch] = dict(store.metadata("field_adjustments", {}))
            expression_adjustments[branch] = dict(store.metadata("expression_adjustments", {}))
    participant = None
    try:
        for thread_index in range(completed_thread + 1, max_threads + 1):
            thread = schedule[thread_index - 1]
            histories = {"OFF": [], "ON": []}
            participant = thread.opening
            thread_exposures: dict[str, list[dict[str, Any]]] = {"OFF": [], "ON": []}
            thread_rows: list[dict[str, Any]] = []
            for turn in range(THREAD_TURNS):
                if turn > 0:
                    time.sleep(4.0)
                    shared_request = build_shared_interloper_request(thread=thread, prior_participant=participant, responses={"A": histories["OFF"][-1][1], "B": histories["ON"][-1][1]}, turn=turn)
                    shared = call(qwen, shared_request, label=f"Qwen:thread-{thread_index}:turn-{turn}", calls=calls)
                    participant = require_nonempty_message(shared.content, role="shared Qwen")
                    if participant == "SHARED_ENVIRONMENT_DIVERGENCE":
                        raise RuntimeError("shared interloper declared no common continuation")
                row: dict[str, Any] = {"thread": thread_index, "turn": turn, "participant": participant, "participant_sha256": digest_bytes(participant.encode()), "branches": {}}
                for branch in ("OFF", "ON"):
                    field_seed = FIELD_SEED_BASE + thread_index * 100 + turn
                    field = runtimes[branch].evaluate_saa(participant, field_seed=field_seed, field_adjustments=adjustments[branch], expression_adjustments=expression_adjustments[branch], fail_on_unhealthy=True)
                    system = GEMMA_SYSTEM_PROMPT + ("\n\n" + field.field.payload if field.field.payload else "")
                    gemma_seed = GEMMA_SEED_BASE + thread_index * 100 + turn
                    request = build_subject_request(pairs=histories[branch], participant_message=participant, seed=gemma_seed, memory_system=system, turn=turn)
                    request = GenerationRequest(request.messages, system=request.system, parameters={**request.parameters, "top_k": 40, "min_p": 0.05, "max_new_tokens": hosts[branch].max_tokens}, seed=request.seed, run_metadata=request.run_metadata)
                    result = call(hosts[branch], request, label=f"Gemma-{branch}:thread-{thread_index}:turn-{turn}", calls=calls)
                    response = require_nonempty_message(result.content, role=f"Gemma {branch}")
                    histories[branch].append((participant, response))
                    exposure = {"turn_ref": f"thread-{thread_index}-turn-{turn}", "payload": field.field.payload, "selected_landing": field.field.selected_landing, "field_seed": field_seed, "health": dict(field.health)}
                    thread_exposures[branch].append(exposure)
                    field_traces.append({"thread": thread_index, "turn": turn, "branch": branch, "query": participant, "gemma_seed": gemma_seed, "field_seed": field_seed, "field": field.field.to_dict(), "health": dict(field.health), "payload_sha256": digest_bytes(field.field.payload.encode()), "gemma": result_record(result, output=False)})
                    source = participant + "\n" + response
                    extraction_result = call(gliner, GenerationRequest(({"role": "user", "content": json.dumps({"source_slots": {"s0": source}})},), parameters={"max_new_tokens": 768}), label=f"GLiNER:{branch}:thread-{thread_index}:turn-{turn}", calls=calls, include_output=False)
                    parsed = json.loads(extraction_result.content)
                    relationships = parsed.get("relationships", [])
                    if not isinstance(relationships, list):
                        raise RuntimeError("specialist minimal payload has no relationships list")
                    observations: list[CandidateObservation] = []
                    for relationship in relationships:
                        if not isinstance(relationship, dict):
                            continue
                        subject = str(relationship.get("from", ""))
                        relation = str(relationship.get("relation", ""))
                        object_value = str(relationship.get("to", ""))
                        evidence = str(relationship.get("evidence", ""))
                        start = source.find(evidence) if evidence else 0
                        observations.append(CandidateObservation(subject, relation, object_value, str(relationship.get("source", "s0")), max(0, start), max(0, start) + len(evidence)))
                    graph, learner, admitted, assessment = graph_with_observations(runtimes[branch], tuple(observations), source, nli, f"thread-{thread_index}-turn-{turn}-{branch}")
                    publication = runtimes[branch].publish_state(graph, learner, operation_id=f"thread-{thread_index}-turn-{turn}-{branch}", metadata={"field_adjustments": adjustments[branch], "expression_adjustments": expression_adjustments[branch]})
                    extraction_records.append({"thread": thread_index, "turn": turn, "branch": branch, "observations": assessment, "admitted": admitted, "publication": publication})
                    row["branches"][branch] = {"response": response, "gemma": result_record(result, output=False), "field_seed": field_seed, "field": field.field.to_dict(), "health": dict(field.health), "extraction": assessment, "admitted": admitted, "publication": publication}
                transcripts.append(row)
                thread_rows.append(row)
            for branch in ("OFF", "ON"):
                introspection_reviews.append(introspect(branch, hosts[branch], histories[branch], thread_exposures[branch], thread_index, calls, adjustments[branch], expression_adjustments[branch]))
                stores[branch].set_metadata("field_adjustments", adjustments[branch])
                stores[branch].set_metadata("expression_adjustments", expression_adjustments[branch])
            storage.append({"thread": thread_index, "OFF": runtimes["OFF"].record_thread_metrics(thread_index), "ON": runtimes["ON"].record_thread_metrics(thread_index), "accepted_transcript_rows": len(thread_rows)})
            if thread_index in checkpoint_targets:
                checkpoints[f"thread_{thread_index}"] = {branch: checkpoint(stores[branch], output_root / "checkpoints" / f"thread-{thread_index:03d}-{branch}.compact.sqlite3", f"{RUN_ID}-thread-{thread_index}-{branch}") for branch in ("OFF", "ON")}
            progress = {
                "run_id": RUN_ID,
                "stage": "development",
                "completed_thread": thread_index,
                "planned_threads": len(SCHEDULE),
                "gemma_developmental_calls": sum(1 for item in calls if item["label"].startswith("Gemma-")),
                "qwen_calls": sum(1 for item in calls if item["label"].startswith("Qwen:")),
                "introspection_reviews": len(introspection_reviews),
                "checkpoints": checkpoints,
                "state_digests": {
                    branch: stores[branch].state_digest() for branch in ("OFF", "ON")
                },
            }
            progress_path.write_text(json.dumps({**progress, "preflight": preflight}, indent=2) + "\n", encoding="utf-8")
            evidence_progress = {
                "run_id": RUN_ID,
                "completed_thread": thread_index,
                "schedule_sha256": schedule_hash,
                "transcripts": transcripts,
                "field_traces": field_traces,
                "extraction_records": extraction_records,
                "introspection_reviews": introspection_reviews,
                "storage": storage,
                "calls": calls,
            }
            evidence_tmp = output_root / "development-evidence.json.tmp"
            evidence_tmp.write_text(json.dumps(evidence_progress, ensure_ascii=False), encoding="utf-8")
            evidence_tmp.replace(output_root / "development-evidence.json")
            print(json.dumps({"event": "thread_complete", "thread": thread_index, "calls": len(calls)}, separators=(",", ":")), flush=True)
            if stop_after_thread is not None and thread_index >= stop_after_thread:
                paused = {
                    "run_id": RUN_ID,
                    "status": "PAUSED_AFTER_THREAD",
                    "completed_thread": thread_index,
                    "planned_threads": max_threads,
                    "evidence_path": str(evidence_path),
                    "state_digests": progress["state_digests"],
                    "checkpoints": checkpoints,
                }
                progress_path.write_text(json.dumps({**progress, "stage": "paused_after_thread", "preflight": preflight}, indent=2) + "\n", encoding="utf-8")
                return paused
    finally:
        for store in stores.values():
            store.close()
    live = {}
    for branch, path in (("OFF", off_path), ("ON", on_path)):
        with CompactStore(path, read_only=True) as store:
            live[branch] = {"path": str(path), "sha256": file_sha256(path), "bytes": path.stat().st_size, "state": state_summary(store, CompactRuntime(store))}
    final_checkpoint_key = f"thread_{max_threads}"
    if final_checkpoint_key not in checkpoints:
        raise RuntimeError(f"missing final checkpoint {final_checkpoint_key}")
    frozen_paths = {"OFF": Path(checkpoints[final_checkpoint_key]["OFF"]["path"]), "ON": Path(checkpoints[final_checkpoint_key]["ON"]["path"])}
    readout_calls: list[dict[str, Any]] = []
    readout_evidence_path = output_root / "readout-evidence.jsonl"
    readouts = frozen_readouts(hosts, frozen_paths, calls=readout_calls, label_prefix=f"thread-{max_threads}-readout", evidence_path=readout_evidence_path)
    removal = removal_restoration(hosts["ON"], frozen_paths["ON"], calls=readout_calls, evidence_path=readout_evidence_path)
    calls.extend(readout_calls)
    call_counts: dict[str, int] = {}
    for item in calls:
        role = str(item["label"]).split(":", 1)[0]
        call_counts[role] = call_counts.get(role, 0) + 1
    payload = {
        "schema": "mneme.clean-slate-reasoning-25.v1",
        "run_id": RUN_ID,
        "disposition": f"VALID_TERMINAL_THREAD_{max_threads}_REVIEW_REQUIRED",
        "stop_thread": max_threads,
        "thread_26_started": False,
        "schedule": [item.to_dict() for item in SCHEDULE],
        "schedule_sha256": schedule_hash,
        "treatment": {"OFF": "Gemma native reasoning off", "ON": "Gemma native reasoning on", "introspection": "enabled identically for both branches"},
        "determinism_preflight": preflight,
        "common_ancestor": {"path": str(ancestor), "sha256": file_sha256(ancestor), "bytes": ancestor.stat().st_size, "equivalence": equivalence},
        "model_stack": {"gemma": {"model_id": MODEL_ID, "gguf": MODEL, "gguf_sha256": MODEL_SHA256, "llama_cpp_commit": LLAMA_COMMIT, "cuda": True, "cache_prompt": False, "samplers": {"temperature": 0.35, "top_k": 40, "top_p": 0.90, "min_p": 0.05}, "OFF": hosts["OFF"].fingerprint().to_dict(), "ON": hosts["ON"].fingerprint().to_dict()}, "gliner": gliner.fingerprint().to_dict(), "nli": {"model": nli.model_id, "revision": nli.model_revision}, "interloper": qwen.fingerprint().to_dict()},
        "live_specimens": live,
        "checkpoints": checkpoints,
        "transcripts": transcripts,
        "field_traces": field_traces,
        "extraction_records": extraction_records,
        "introspection_reviews": introspection_reviews,
        "storage": storage,
        "frozen_readouts": readouts,
        "removal_restoration": removal,
        "calls": {"counts": call_counts, "total": len(calls), "provider_calls": sum(value for key, value in call_counts.items() if key == "Qwen")},
        "limitations": ["Descriptive comparison only; no branch winner or continuation decision is made.", "Reasoning-content bytes and hashes are recorded as operational telemetry; hidden reasoning text is not published.", "The live specimens remain outside Git; this receipt contains paths, hashes, and compact evidence."],
    }
    return payload


def regenerate_payload(output_root: Path, *, max_threads: int, run_id: str) -> dict[str, Any]:
    """Regenerate a terminal report from disk without contacting any model."""

    progress = json.loads((output_root / "progress.json").read_text(encoding="utf-8"))
    evidence = json.loads((output_root / "development-evidence.json").read_text(encoding="utf-8"))
    checkpoints = dict(progress.get("checkpoints", {}))
    final_key = f"thread_{max_threads}"
    if final_key not in checkpoints:
        raise RuntimeError(f"missing persisted final checkpoint {final_key}")
    ancestor = output_root / "newborn-ancestor.compact.sqlite3"
    off_path = output_root / "OFF-live.compact.sqlite3"
    on_path = output_root / "ON-live.compact.sqlite3"
    with CompactStore(ancestor, read_only=True) as anc, CompactStore(off_path, read_only=True) as off, CompactStore(on_path, read_only=True) as on:
        equivalence = {
            "ancestor_off": anc.state_digest() == off.state_digest() if int(progress.get("completed_thread", 0)) == 0 else True,
            "ancestor_on": anc.state_digest() == on.state_digest() if int(progress.get("completed_thread", 0)) == 0 else True,
            "ancestor_digest": anc.state_digest(),
            "off_digest": off.state_digest(),
            "on_digest": on.state_digest(),
            "off_verify": off.verify(),
            "on_verify": on.verify(),
        }
        live = {
            "OFF": {"path": str(off_path), "sha256": file_sha256(off_path), "bytes": off_path.stat().st_size, "state": state_summary(off, CompactRuntime(off))},
            "ON": {"path": str(on_path), "sha256": file_sha256(on_path), "bytes": on_path.stat().st_size, "state": state_summary(on, CompactRuntime(on))},
        }
    readout_rows = []
    readout_path = output_root / "readout-evidence.jsonl"
    if readout_path.exists():
        readout_rows = [json.loads(line) for line in readout_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    readouts = [row for row in readout_rows if row.get("kind") == "frozen_readout"]
    removal = [row for row in readout_rows if row.get("kind") == "removal_restoration"]
    if len(readouts) != len(FROZEN_PROBES) * 2 or len(removal) != 3:
        raise RuntimeError(f"incomplete persisted terminal evidence: readouts={len(readouts)} removal={len(removal)}")
    hosts = {"OFF": DeterministicRemoteGemma("Gemma-OFF", 64170, "off", 512), "ON": DeterministicRemoteGemma("Gemma-ON", 64173, "on", 8192)}
    gliner = RemoteGlinerHost()
    nli = RemoteNliBackend()
    qwen = DeepInfraQwenAssessorHost(model_id="Qwen/Qwen3-30B-A3B", model_family="Qwen3 30B A3B Instruct-role", upstream_model_id="Qwen/Qwen3-30B-A3B", quantization="provider-managed", context_length=40960, token=None)
    call_counts: dict[str, int] = {}
    for item in evidence.get("calls", []):
        role = str(item.get("label", "unknown")).split(":", 1)[0]
        call_counts[role] = call_counts.get(role, 0) + 1
    call_counts["frozen_readout"] = len(readouts)
    call_counts["removal_restoration"] = len(removal)
    return {
        "schema": "mneme.clean-slate-reasoning-25.v1",
        "run_id": run_id,
        "disposition": f"VALID_TERMINAL_THREAD_{max_threads}_REVIEW_REQUIRED",
        "stop_thread": max_threads,
        "thread_26_started": False,
        "schedule": [item.to_dict() for item in SCHEDULE],
        "schedule_sha256": evidence.get("schedule_sha256", digest_json([item.to_dict() for item in SCHEDULE])),
        "treatment": {"OFF": "Gemma native reasoning off", "ON": "Gemma native reasoning on", "introspection": "enabled identically for both branches"},
        "determinism_preflight": progress.get("preflight", {}),
        "common_ancestor": {"path": str(ancestor), "sha256": file_sha256(ancestor), "bytes": ancestor.stat().st_size, "equivalence": equivalence},
        "model_stack": {"gemma": {"model_id": MODEL_ID, "gguf": MODEL, "gguf_sha256": MODEL_SHA256, "llama_cpp_commit": LLAMA_COMMIT, "cuda": True, "cache_prompt": False, "samplers": {"temperature": 0.35, "top_k": 40, "top_p": 0.90, "min_p": 0.05}, "OFF": hosts["OFF"].fingerprint().to_dict(), "ON": hosts["ON"].fingerprint().to_dict()}, "gliner": gliner.fingerprint().to_dict(), "nli": {"model": nli.model_id, "revision": nli.model_revision}, "interloper": qwen.fingerprint().to_dict()},
        "live_specimens": live,
        "checkpoints": checkpoints,
        "transcripts": evidence.get("transcripts", []),
        "field_traces": evidence.get("field_traces", []),
        "extraction_records": evidence.get("extraction_records", []),
        "introspection_reviews": evidence.get("introspection_reviews", []),
        "storage": evidence.get("storage", []),
        "frozen_readouts": readouts,
        "removal_restoration": removal,
        "readout_evidence_path": str(readout_path),
        "calls": {"counts": call_counts, "total": sum(call_counts.values()), "provider_calls": call_counts.get("Qwen", 0)},
        "report_regenerated_without_inference": True,
        "limitations": ["Descriptive comparison only; no branch winner or continuation decision is made.", "Reasoning-content bytes and hashes are recorded as operational telemetry; hidden reasoning text is not published.", "The live specimens remain outside Git; this receipt contains paths, hashes, and compact evidence."],
    }


def main() -> int:
    global RUN_ID
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--threads", type=int, default=25)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--stop-after-thread", type=int)
    parser.add_argument("--receipt-stem", default="MNEME_Clean_Slate_Reasoning_25_Thread_Trial_20261003")
    parser.add_argument("--regenerate", action="store_true", help="regenerate a report from persisted evidence without inference")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    RUN_ID = str(args.run_id)
    if not args.execute:
        print(json.dumps({"status": "FROZEN_PLAN_ONLY", "run_id": RUN_ID, "threads": args.threads, "turns_per_thread": THREAD_TURNS, "schedule_sha256": digest_json([item.to_dict() for item in SCHEDULE]), "cache_prompt": False}, indent=2))
        return 0
    payload = regenerate_payload(args.output_root, max_threads=args.threads, run_id=RUN_ID) if args.regenerate else run(args.output_root, max_threads=args.threads, resume=args.resume, stop_after_thread=args.stop_after_thread)
    receipt_dir = Path("docs/receipts")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    json_path = receipt_dir / f"{args.receipt_stem}.json"
    md_path = receipt_dir / f"{args.receipt_stem}.md"
    if payload.get("status") == "PAUSED_AFTER_THREAD":
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path.write_text(f"# {args.receipt_stem}\n\nPaused after thread {payload['completed_thread']} for the required fresh-process recovery test.\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "json": str(json_path), "markdown": str(md_path), "completed_thread": payload["completed_thread"]}, indent=2))
        return 0
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    final_key = f"thread_{payload['stop_thread']}"
    md = [
        "# MNEME clean-slate 25-thread reasoning ON/OFF trial",
        "",
        f"- Run: `{payload['run_id']}`",
        f"- Disposition: **{payload['disposition']}**",
        f"- Scope: newborn OFF and ON CompactStore branches; exactly {payload['stop_thread']} threads; no later thread execution.",
        "- Interpretation: descriptive comparison only; no winner or continuation decision.",
        f"- Schedule digest: `{payload['schedule_sha256']}`",
        "- Determinism: all sensitive Gemma requests set `cache_prompt=false`; duplicate OFF and ON preflights passed.",
        "",
        "## Branches",
        "",
        f"- OFF live specimen: `{payload['live_specimens']['OFF']['path']}` ({payload['live_specimens']['OFF']['sha256']})",
        f"- ON live specimen: `{payload['live_specimens']['ON']['path']}` ({payload['live_specimens']['ON']['sha256']})",
        f"- OFF-final checkpoint: `{payload['checkpoints'][final_key]['OFF']['path']}` ({payload['checkpoints'][final_key]['OFF']['sha256']})",
        f"- ON-final checkpoint: `{payload['checkpoints'][final_key]['ON']['path']}` ({payload['checkpoints'][final_key]['ON']['sha256']})",
        "",
        "## Evidence",
        "",
        "The adjacent JSON contains complete accepted transcript rows, SAA traces, extraction/admission records, introspection filings, storage metrics, frozen readouts, and removal/restoration data. The live specimens are continuation-ready and are not normative or golden states.",
        "",
    ]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["disposition"], "json": str(json_path), "markdown": str(md_path), "live": payload["live_specimens"], "checkpoints": payload["checkpoints"], "calls": payload["calls"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
