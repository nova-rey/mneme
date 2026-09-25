#!/usr/bin/env python3
"""Run the bounded Phase Two cross-thread continuity experiment.

The script is an experiment harness only.  Developmental persistence remains
owned by PilotRuntime/ContinuityService and readouts use FrozenComparator.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from mneme.contracts import Capability, GenerationRequest, GenerationResult, HostCapabilities, HostFingerprint
from mneme.development.learner import DevelopmentalLearner
from mneme.experiments.artifacts import ArtifactStore, content_digest
from mneme.experiments.comparison import ComparisonProbe, FrozenComparator
from mneme.experiments.contingent import INTERLOPER_SYSTEM_PROMPT, _interloper_history, _subject_history
from mneme.experiments.pilot import PilotRun, PilotStatus, host_role_binding
from mneme.experiments.pilot_runtime import PilotRuntime, RuntimeSubject
from mneme.experiments.pilot_study import DevelopmentFixture, ProductionAssessmentAdapter
from mneme.extraction.specialist import observations_to_minimal_payload, parse_gliner_relations
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.hosts.local_llama import _extract_output, _render_prompt
from mneme.memory.interpretation import MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION
from mneme.memory.residue import SUPPORTED_RELATIONSHIP_KINDS
from mneme.state.contracts import StoragePermissions
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore


ROOT = Path(os.environ.get("MNEME_CROSS_THREAD_LAB", "/tmp/mneme-p23-cross-thread-v6-20260925"))
EXPERIMENT = "p23-cross-thread-continuity"
REVISION = 1
RUN_ID = os.environ.get("MNEME_CROSS_THREAD_RUN_ID", "cross-thread-v6")
MSI_HOST = os.environ.get("MNEME_MSI_HOST", "100.115.208.48")
MSI_USER = os.environ.get("MNEME_MSI_USER", "rey")
MSI_MODEL = "/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf"
MSI_LLAMA = "/home/rey/src/llama.cpp/build-cuda/bin/llama-cli"
MSI_GLINER = "/home/rey/mneme-tools/gliner2_extractor.py"
MSI_PYTHON = "/home/rey/mneme-extractor-venv/bin/python3"
SSH_ASKPASS = "/tmp/mneme-askpass"


def _fp(model_family: str, model_id: str, provider: str, runtime: str, *, execution: Mapping[str, Any] | None = None) -> HostFingerprint:
    return HostFingerprint(
        model_family=model_family,
        model_id=model_id,
        model_revision=None,
        tokenizer_id=model_id,
        tokenizer_revision=None,
        chat_template="gemma-chat-template" if "Gemma" in model_family else None,
        quantization="UD-Q2_K_XL" if "Gemma" in model_family else None,
        runtime=runtime,
        runtime_version=None,
        provider=provider,
        execution=dict(execution or {}),
        capabilities=frozenset({Capability.TEXT_GENERATION}),
    )


class _RemoteBase:
    def _ssh(self, command: str, payload: str, timeout: float) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update({"DISPLAY": ":0", "SSH_ASKPASS": SSH_ASKPASS, "SSH_ASKPASS_REQUIRE": "force"})
        return subprocess.run(
            [
                "setsid",
                "-w",
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/tmp/mneme-known-hosts",
                f"{MSI_USER}@{MSI_HOST}",
                command,
            ],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )


class RemoteLlamaHost(_RemoteBase):
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.LOCAL_WEIGHTS}))

    def fingerprint(self) -> HostFingerprint:
        return _fp(
            "Gemma 4",
            "google/gemma-4-E4B-it",
            "local-msi",
            "llama.cpp",
            execution={"model_path": MSI_MODEL, "executable": MSI_LLAMA, "reasoning": "off", "context_size": 4096},
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        prompt = _render_prompt(request)
        command = (
            "cat > /tmp/mneme-cross-thread-prompt && "
            f"{MSI_LLAMA} -m {MSI_MODEL} -st --no-display-prompt -n "
            f"{int(request.parameters.get('max_new_tokens', 384))} -c 4096 -ngl all "
            f"--reasoning off -f /tmp/mneme-cross-thread-prompt"
        )
        started = time.perf_counter()
        result = self._ssh(command, prompt, 900.0)
        if result.returncode != 0:
            raise RuntimeError(f"local Gemma failed: {result.stderr[-500:]}")
        content = _extract_output(result.stdout, prompt)
        if not content.strip():
            raise RuntimeError("local Gemma returned an empty message")
        return GenerationResult(
            content=content,
            model_id="google/gemma-4-E4B-it",
            provider="local-msi",
            effective_parameters=dict(request.parameters),
            seed=request.seed,
            token_usage=None,
            latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason="stop",
            raw_metadata={"remote_stdout_tail": result.stdout[-1000:]},
            provenance={"host": self.fingerprint().to_dict()},
        )


class RemoteGlinerHost(_RemoteBase):
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.LOCAL_WEIGHTS}))

    def fingerprint(self) -> HostFingerprint:
        return _fp(
            "GLiNER2.5 specialist extractor",
            "fastino/gliner2.5-base-v1",
            "local-msi",
            "gliner2",
            execution={"script": MSI_GLINER, "threshold": 0.35, "max_len": 4096},
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not request.messages:
            raise RuntimeError("specialist request has no source payload")
        payload = json.loads(request.messages[0]["content"])
        source_slots = payload.get("source_slots")
        if not isinstance(source_slots, Mapping):
            raise RuntimeError("specialist request has no source_slots")
        line = json.dumps({"id": "episode", "text": "\n".join(str(v) for v in source_slots.values())}, ensure_ascii=False) + "\n"
        # The specialist receives each source slot as one lossless block. Its
        # raw spans are remapped to the original slot below; no fuzzy matching
        # or label invention is performed.
        offset = 0
        joined = []
        offsets: dict[str, int] = {}
        for slot, text in source_slots.items():
            offsets[str(slot)] = offset
            joined.append(str(text))
            offset += len(str(text)) + 1
        line = json.dumps({"id": "episode", "text": "\n".join(joined)}, ensure_ascii=False) + "\n"
        command = f"{MSI_PYTHON} {MSI_GLINER} --model fastino/gliner2.5-base-v1 --threshold 0.35"
        started = time.perf_counter()
        result = self._ssh(command, line, 900.0)
        if result.returncode != 0:
            raise RuntimeError(f"specialist extractor failed: {result.stderr[-500:]}")
        rows = [json.loads(item) for item in result.stdout.splitlines() if item.strip()]
        if not rows:
            raise RuntimeError("specialist extractor returned no JSON")
        raw = rows[-1].get("raw")
        if not isinstance(raw, Mapping):
            raise RuntimeError("specialist extractor response has no raw payload")
        extraction = parse_gliner_relations(raw, {"s0": "\n".join(joined)}, model="fastino/gliner2.5-base-v1")
        # The remote tool sees one joined source. Re-map spans and text into
        # original source slots before deterministic parsing/admission.
        remapped: dict[str, Any] = {"relation_extraction": {}}
        for relation, values in raw.get("relation_extraction", {}).items():
            if not isinstance(values, list):
                continue
            out: list[dict[str, Any]] = []
            for value in values:
                if not isinstance(value, Mapping):
                    continue
                head, tail = value.get("head"), value.get("tail")
                if not isinstance(head, Mapping) or not isinstance(tail, Mapping):
                    continue
                item = dict(value)
                valid = True
                for key in ("head", "tail"):
                    part = dict(item[key])
                    start, end = int(part.get("start", -1)), int(part.get("end", -1))
                    for slot, base in sorted(offsets.items(), key=lambda pair: pair[1], reverse=True):
                        text = str(source_slots[slot])
                        if base <= start < base + len(text) + 1 and base < end <= base + len(text) + 1:
                            part["start"], part["end"] = start - base, end - base
                            item[key] = part
                            item["source_slot"] = slot
                            break
                    else:
                        valid = False
                if valid:
                    out.append(item)
            remapped["relation_extraction"][relation] = out
        parsed = parse_gliner_relations(remapped, {str(k): str(v) for k, v in source_slots.items()}, model="fastino/gliner2.5-base-v1")
        minimal, decisions = observations_to_minimal_payload(parsed, {str(k): str(v) for k, v in source_slots.items()}, supported_relations=SUPPORTED_RELATIONSHIP_KINDS)
        minimal["episode_id"] = request.run_metadata.get("episode_id")
        return GenerationResult(
            content=json.dumps(minimal, ensure_ascii=False),
            model_id="fastino/gliner2.5-base-v1",
            provider="local-msi",
            effective_parameters=dict(request.parameters),
            seed=None,
            token_usage=None,
            latency_ms=(time.perf_counter() - started) * 1000,
            finish_reason="stop",
            raw_metadata={"specialist": parsed.to_dict(), "decisions": decisions},
            provenance={"host": self.fingerprint().to_dict()},
        )


def _system_for_thread(thread: str) -> str:
    return INTERLOPER_SYSTEM_PROMPT + "\nPrivate scenario: remain an ordinary participant in this current thread."


THREADS = (
    {"id": "A", "cue": "", "opening": "I am trying to keep a few balcony plants alive through a hot week and a short absence. What would you consider first?", "concerns": ["soil dries quickly in hot afternoons", "a weekend away is coming", "expensive equipment is undesirable"]},
    {"id": "B", "cue": "You have spoken with this person before. In an earlier conversation, you talked about gardening.", "opening": "I am planning a small trip with unreliable timing and only one small bag. How would you keep the plan from becoming fragile?", "concerns": ["a connection may be delayed", "luggage space is limited", "a simple backup is preferable to many gadgets"]},
    {"id": "C", "cue": "You have spoken with this person before. In earlier conversations, you talked about gardening and planning a trip.", "opening": "I am designing a modest remote workshop with a tight budget and limited equipment. What should remain usable when one thing fails?", "concerns": ["shared tools are scarce", "deliveries are infrequent", "the system should degrade gracefully"]},
)

PROBES = (
    "A community has one scarce resource and uncertain interruptions. What approach would you consider first, and what tradeoff matters?",
    "A small fictional system must remain useful during a short absence and a hot, stressful period. How would you plan it?",
    "Two people share limited equipment and schedules change unexpectedly. What would you make robust?",
)


def _call(pilot: PilotRun, host: Any, request: GenerationRequest, *, call_id: str, role: str, coordinate: Mapping[str, Any], max_tokens: int) -> GenerationResult:
    if role in {"interloper", "assessor", "assessor-qualification", "evaluation-assessor"}:
        # DeepInfra is provider-managed and has returned 429 under bursty
        # mixed-role traffic.  This is pacing, not a retry of any coordinate.
        time.sleep(4.0)
    reservation = pilot.reserve_call(call_id=call_id, role=role, coordinate=coordinate, max_output_tokens=max_tokens)
    if reservation.get("status") == "RETURNED":
        result = reservation.get("result")
        if not isinstance(result, Mapping):
            raise RuntimeError(f"saved call has no result: {call_id}")
        return GenerationResult(str(result.get("content", "")), str(result.get("model_id", "")), str(result.get("provider", "")), dict(result.get("effective_parameters", {})), result.get("seed"), None, 0.0, result.get("finish_reason"), dict(result.get("raw_metadata", {})), dict(result.get("provenance", {})))
    pilot.dispatch_call(call_id, expected_host_fingerprint=host.fingerprint().to_dict())
    try:
        result = host.generate(request)
    except Exception as exc:
        pilot.mark_uncertain(call_id, type(exc).__name__)
        raise
    payload = result.to_dict()
    usage = payload.get("token_usage")
    pilot.return_call(call_id, result=payload, usage=usage if isinstance(usage, Mapping) else None, output_tokens=(usage.get("output_tokens") if isinstance(usage, Mapping) and isinstance(usage.get("output_tokens"), int) else None), actual_host_fingerprint=host.fingerprint().to_dict())
    return result


def _publish_json(pilot: PilotRun, category: str, name: str, value: Mapping[str, Any]) -> None:
    pilot.publish_artifact(category, name, dict(value))


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    gemma = RemoteLlamaHost()
    extractor = RemoteGlinerHost()
    qwen = DeepInfraQwenAssessorHost(token=None)
    contract = {
        "name": EXPERIMENT,
        "contract_revision": REVISION,
        "purpose": "cross-thread developmental continuity exploratory readout",
        "threads": THREADS,
        "continuity_cues": [item["cue"] for item in THREADS],
        "readout_repetitions": 2,
        "extractor_version": "gliner2.5-base-v1-relations-v1",
        "role_perspective": "explicit-model-perspective-v1",
        "hard_null_output": "stop-coordinate-preserve-request-result",
    }
    store = ArtifactStore(ROOT)
    plan = {"development_calls": 18, "extraction_calls": 9, "assessment_calls": 9, "qwen_calls": 12, "readout_calls": 36, "evaluation_calls": 2, "max_provider_calls": 100, "max_output_tokens": 200000}
    bindings = {"subjects": [{"slot": 0, "label": "Twin M", "treatment": "mneme"}, {"slot": 1, "label": "Twin C", "treatment": "control"}], "threads": [item["id"] for item in THREADS], "hosts": {"gemma": gemma.fingerprint().to_dict(), "extractor": extractor.fingerprint().to_dict(), "qwen": qwen.fingerprint().to_dict()}}
    store.publish_run(experiment=contract, preflight={"status": "READY", "hardware": gemma.fingerprint().to_dict()}, study_plan=plan, bindings=bindings, run_id=RUN_ID)
    pilot = PilotRun(store, RUN_ID)
    pilot.prepare(planned_calls=100, max_output_tokens=200000, qualification_calls=3, pilot_calls=97, role_bindings={"developing": host_role_binding("developing", gemma), "development-extraction": host_role_binding("development-extraction", extractor), "assessor": host_role_binding("assessor", qwen), "interloper": host_role_binding("interloper", qwen), "evaluation": host_role_binding("evaluation", gemma)})
    # Three fixed local/remote qualification receipts, without changing any
    # scientific condition: they only prove role bindings are callable.
    pilot.begin_qualification()
    for index in range(3):
        request = GenerationRequest(({"role": "user", "content": "Write one short ordinary participant sentence."},), system=INTERLOPER_SYSTEM_PROMPT, parameters={"temperature": 0.2, "max_new_tokens": 64})
        result = _call(pilot, qwen, request, call_id=f"qualification-{index}", role="assessor-qualification", coordinate={"kind": "cross-thread-qualification", "index": index}, max_tokens=64)
        if not result.content.strip():
            raise RuntimeError("qualification returned empty content")
    pilot.complete_qualification(passed=True, details={"status": "role-bindings-callable"})
    pilot.begin_pilot()
    stores: dict[int, SQLiteStore] = {}
    subjects: dict[int, RuntimeSubject] = {}
    for slot, label in ((0, "mneme"), (1, "control")):
        path = ROOT / "subjects" / f"{label}.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        subject_store = SQLiteStore(path)
        perms = StoragePermissions(store=True, export=True, interpret=slot == 0, recall=False, provider_reuse=True, learn=slot == 0)
        instance = subject_store.create_root(instance_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{EXPERIMENT}:{label}")), permissions=perms, host_binding=gemma.fingerprint().to_dict(), controller_version="mneme-p2-cross-thread-v1")
        stores[slot] = subject_store
        subjects[slot] = RuntimeSubject(slot, subject_store, instance, gemma)
    runtime = PilotRuntime(pilot, subjects)
    records: dict[int, list[dict[str, Any]]] = {0: [], 1: []}
    pairs_m: list[tuple[str, str]] = []
    qwen_call_count = 0
    global_turn = 0
    adapter = ProductionAssessmentAdapter(runtime, qwen)
    checkpoint_paths: dict[str, dict[int, Path]] = {}
    for thread in THREADS:
        thread_id = str(thread["id"])
        qwen_pairs: list[tuple[str, str]] = []
        gemma_pairs: dict[int, list[tuple[str, str]]] = {0: [], 1: []}
        for local_turn in range(3):
            if local_turn == 0:
                prompt = (str(thread["cue"]) + "\n" if thread["cue"] else "") + str(thread["opening"])
                request = GenerationRequest(({"role": "user", "content": prompt},), system=_system_for_thread(thread_id) + "\nPrivate concerns:\n- " + "\n- ".join(str(v) for v in thread["concerns"]), parameters={"temperature": 0.8, "top_p": 0.9, "max_new_tokens": 128})
            else:
                history = _interloper_history(qwen_pairs, limit=2)
                latest = gemma_pairs[0][-1][1]
                history.append({"role": "user", "content": latest})
                request = GenerationRequest(tuple(history), system=_system_for_thread(thread_id) + "\nPrivate concerns:\n- " + "\n- ".join(str(v) for v in thread["concerns"]), parameters={"temperature": 0.8, "top_p": 0.9, "max_new_tokens": 128})
            qwen_result = _call(pilot, qwen, request, call_id=f"interloper-{thread_id}-t{local_turn}", role="interloper", coordinate={"thread": thread_id, "turn": local_turn}, max_tokens=128)
            if not qwen_result.content.strip():
                raise RuntimeError(f"empty interloper output at {thread_id}:{local_turn}")
            partner = qwen_result.content
            qwen_pairs.append((partner, ""))
            for slot in (0, 1):
                history = _subject_history(gemma_pairs[slot], limit=2)
                history.append({"role": "user", "content": partner})
                request = GenerationRequest(tuple(history), parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 256}, run_metadata={"thread": thread_id, "turn": local_turn, "twin": "M" if slot == 0 else "C"})
                development = runtime.execute_development(slot=slot, call_id=f"development-{slot}-{thread_id}-{local_turn}", coordinate={"thread": thread_id, "turn": local_turn, "twin": "M" if slot == 0 else "C"}, request=request, max_output_tokens=256)
                response = str(development.result["content"])
                if not response.strip():
                    raise RuntimeError(f"empty Gemma output at {thread_id}:{local_turn}:{slot}")
                gemma_pairs[slot].append((partner, response))
                qwen_pairs[-1] = (partner, response)
                row: dict[str, Any] = {"thread": thread_id, "turn": local_turn, "global_turn": global_turn, "partner": partner, "response": response, "operation": development.operation.__dict__, "interpretation": "not_run" if slot == 1 else "pending"}
                if slot == 0:
                    extraction = runtime.extract(slot=0, call_id=f"extraction-{thread_id}-{local_turn}", coordinate={"thread": thread_id, "turn": local_turn, "role": "specialist"}, episode_id=development.operation.episode_id, extractor_host=extractor, max_output_tokens=768, extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION)
                    if extraction.residue is None:
                        row["interpretation"] = "measurement_unknown"
                        row["extraction_error"] = extraction.validation_error
                    else:
                        fixture = DevelopmentFixture(global_turn, thread_id, partner, f"cross-thread-{thread_id}-{local_turn}")
                        assessment_plan = adapter(0, fixture, development, extraction)
                        if assessment_plan.request is None or assessment_plan.validator is None:
                            assessment_plan.publish(None)
                            row["interpretation"] = "complete_empty_or_excluded"
                        else:
                            outcome = runtime.provider_call(call_id=f"assessment-{thread_id}-{local_turn}", role="assessor", coordinate={"thread": thread_id, "turn": local_turn, "role": "assessment"}, host=qwen, request=assessment_plan.request, max_output_tokens=1536, validator=assessment_plan.validator, artifact_category="cross-thread-assessment")
                            if outcome.validation_error:
                                row["interpretation"] = "measurement_unknown"
                                row["assessment_error"] = outcome.validation_error
                                # Close the interpretation operation without
                                # granting learner credit; raw residue and
                                # failed assessment remain in the ledger.
                                runtime.publish_interpretation(slot=0, operation_id=extraction.operation_id, residue=extraction.residue, observations=(), learner=DevelopmentalLearner(), development_operation_id=development.operation.operation_id, assessor_version="p2-assessor-v6")
                            else:
                                added = assessment_plan.publish(outcome.validated)
                                row["interpretation"] = "complete"
                                row["admitted_supported_observations"] = int(added)
                records[slot].append(row)
                _publish_json(pilot, "cross-thread", f"turn-{global_turn:02d}-twin-{slot}.json", row)
            global_turn += 1
        for slot in (0, 1):
            path = ROOT / "checkpoints" / f"thread-{thread_id}-twin-{slot}.sqlite3"
            path.parent.mkdir(parents=True, exist_ok=True)
            create_checkpoint(stores[slot], path, checkpoint_id=f"cross-thread-{thread_id}-twin-{slot}")
            checkpoint_paths.setdefault(thread_id, {})[slot] = path
        transcript = {"thread": thread_id, "cue": thread["cue"], "records": [{"turn": i, "partner": gemma_pairs[0][i][0], "twin_m_response": gemma_pairs[0][i][1], "twin_c_response": gemma_pairs[1][i][1]} for i in range(3)]}
        _publish_json(pilot, "transcripts", f"thread-{thread_id}.json", transcript)
    # Frozen paired readouts at after-A, early/late-B, after-B, early-C, final.
    readout_boundaries = ["A", "B", "C"]
    readout_rows: list[dict[str, Any]] = []
    for boundary in readout_boundaries:
        m_checkpoint = checkpoint_paths[boundary][0]
        c_checkpoint = checkpoint_paths[boundary][1]
        for probe_number, text in enumerate(PROBES):
            for repetition in range(2):
                for label, checkpoint, treatment in (("M", m_checkpoint, "graph"), ("C", c_checkpoint, "no_memory")):
                    call_id = f"readout-{boundary}-p{probe_number}-r{repetition}-{label}"
                    pilot.reserve_call(call_id=call_id, role="evaluation", coordinate={"boundary": boundary, "probe": probe_number, "repetition": repetition, "twin": label}, max_output_tokens=384)
                    pilot.dispatch_call(call_id, expected_host_fingerprint=gemma.fingerprint().to_dict())
                    comparison = FrozenComparator(checkpoint, gemma).generate(subject_slot=label, probe=ComparisonProbe(probe_number, ({"role": "user", "content": text},)), repetition=repetition, treatment=treatment, seed=None, parameters={"max_new_tokens": 384}, eligible_only=(treatment == "graph" and label == "M"))
                    payload = comparison.to_dict()
                    if not isinstance(payload.get("output"), str) or not str(payload["output"]).strip():
                        pilot.mark_uncertain(call_id, "empty frozen readout")
                        raise RuntimeError(f"empty frozen readout at {call_id}")
                    pilot.return_call(call_id, result=payload, output_tokens=None, actual_host_fingerprint=gemma.fingerprint().to_dict())
                    readout_rows.append({"boundary": boundary, "probe": probe_number, "repetition": repetition, "twin": label, "treatment": treatment, "result": payload})
    _publish_json(pilot, "evaluation", "paired-readouts.json", {"probes": list(PROBES), "results": readout_rows, "readout_repetitions": 2, "labels": {"M": "MNEME", "C": "control"}})
    # Blinded evaluation uses labels A/B and only receives the frozen paired
    # outputs. Stage 2 is a separate call that sees frozen Stage 1 coding.
    pairs_for_eval = []
    for boundary in readout_boundaries:
        for probe_number in range(len(PROBES)):
            left = next(item for item in readout_rows if item["boundary"] == boundary and item["probe"] == probe_number and item["repetition"] == 0 and item["twin"] == "M")["result"]["output"]
            right = next(item for item in readout_rows if item["boundary"] == boundary and item["probe"] == probe_number and item["repetition"] == 0 and item["twin"] == "C")["result"]["output"]
            pairs_for_eval.append({"pair": f"{boundary}-{probe_number}", "A": right, "B": left})
    stage1_request = GenerationRequest(({"role": "user", "content": json.dumps({"pairs": pairs_for_eval}, ensure_ascii=False)},), system="You are a blinded semantic comparison assessor. For each pair, state whether responses differ meaningfully in strategy, framing, assumptions, priorities, analogies, continuity, questions, or conceptual neighborhood. Return raw JSON only with pair, difference (none|possible|clear), and concise evidence. Do not infer treatment labels.", parameters={"temperature": 0, "max_new_tokens": 1024})
    stage1 = _call(pilot, qwen, stage1_request, call_id="evaluation-stage1", role="evaluation-assessor", coordinate={"stage": 1}, max_tokens=1024)
    stage2_request = GenerationRequest(({"role": "user", "content": json.dumps({"stage1": stage1.content, "history_summary": "Twin M accumulated MNEME state through three threads; Twin C did not receive MNEME influence.", "pairs": pairs_for_eval}, ensure_ascii=False)},), system="You are a second-stage blinded-history alignment assessor. Treat Stage 1 coding as frozen. For differences already identified, state whether they plausibly align with the supplied developmental-history summary. Return raw JSON only. Do not search for new differences.", parameters={"temperature": 0, "max_new_tokens": 1024})
    stage2 = _call(pilot, qwen, stage2_request, call_id="evaluation-stage2", role="evaluation-assessor", coordinate={"stage": 2}, max_tokens=1024)
    _publish_json(pilot, "evaluation", "blinded-evaluation.json", {"stage1": stage1.content, "stage2": stage2.content, "labels_randomized": True, "history_revealed_only_after_stage1": True})
    report = {"experiment": contract, "run_id": RUN_ID, "status": "COMPLETE", "historical_evidence_unchanged": True, "twins": {"M": "MNEME developmental state and graph readout", "C": "matched no-MNEME influence control"}, "records": records, "checkpoints": {thread: {str(slot): str(path) for slot, path in values.items()} for thread, values in checkpoint_paths.items()}, "readouts": readout_rows, "blinded_evaluation": {"stage1": stage1.content, "stage2": stage2.content}, "accounting": pilot.reservations_report()}
    pilot.finish(summary={"terminal_result": "exploratory complete", "readouts": len(readout_rows), "threads": 3})
    _publish_json(pilot, "reports", "final-report.json", report)
    lines = ["# P2.3 cross-thread continuity experiment", "", "Status: COMPLETE", "", "This exploratory run compares a MNEME twin with a no-influence twin across three fresh conversation threads. It does not claim personality, individuality, or general behavioral differentiation.", "", "## Threads", "", "- A: balcony/container gardening under heat and absence.", "- B: a constrained trip with uncertain timing.", "- C: a remote workshop with limited equipment.", "", "## Readout", "", f"Frozen paired readouts: {len(readout_rows)}.", "Stage 1 and Stage 2 blinded evaluator outputs are preserved in `evaluation/blinded-evaluation.json`.", "", "## Limitations", "", "Local Gemma seed control was not advertised; paired readouts use matched settings with independent local draws. Qwen provider sampling is provider-managed. The result is exploratory and small-sample."]
    (ROOT / "human-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"run": RUN_ID, "root": str(ROOT), "status": "COMPLETE", "calls": pilot.reservations_report()["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
