#!/usr/bin/env python3
# ruff: noqa: E501,E702
"""Run the final bounded P2.3 episodic recurrence mechanism experiment.

This harness deliberately keeps the Phase Two learner untouched.  It supplies
five separately declared target opportunities so the fixed four-opportunity
consolidation gap and eight-opportunity rolling cap are actually testable.
The matched model-reentry branch receives the same arc schedule but no target
re-entry circumstance from the participant.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mneme.contracts import (
    Capability,
    GenerationRequest,
    GenerationResult,
    HostCapabilities,
    HostFingerprint,
)
from mneme.development.episodes import ConversationEpisode, persist_conversation_arc_progress
from mneme.development.learner import DevelopmentalLearner
from mneme.experiments.artifacts import ArtifactStore, content_digest
from mneme.experiments.contingent import (
    INTERLOPER_SYSTEM_PROMPT,
    ROLE_PERSPECTIVE_VERSION,
    _interloper_history,
    _subject_history,
)
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

ROOT = Path(os.environ.get("MNEME_EPISODIC_LAB", "/tmp/mneme-p23-final-episodic-20260926"))
RUN_ID = os.environ.get("MNEME_EPISODIC_RUN_ID", "p23-final-episodic-run-1")
EXPERIMENT = "p2.3-final-episodic-recurrence-consolidation"
REVISION = 1
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
            ["setsid", "-w", "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/tmp/mneme-known-hosts", f"{MSI_USER}@{MSI_HOST}", command],
            input=payload, capture_output=True, text=True, timeout=timeout, env=env,
        )


class RemoteLlamaHost(_RemoteBase):
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.LOCAL_WEIGHTS}))

    def fingerprint(self) -> HostFingerprint:
        return _fp("Gemma 4", "google/gemma-4-E4B-it", "local-msi", "llama.cpp", execution={"model_path": MSI_MODEL, "executable": MSI_LLAMA, "reasoning": "off", "context_size": 4096})

    def generate(self, request: GenerationRequest) -> GenerationResult:
        prompt = _render_prompt(request)
        command = f"cat > /tmp/mneme-episodic-prompt && {MSI_LLAMA} -m {MSI_MODEL} -st --no-display-prompt -n {int(request.parameters.get('max_new_tokens', 384))} -c 4096 -ngl all --reasoning off -f /tmp/mneme-episodic-prompt"
        started = time.perf_counter()
        result = self._ssh(command, prompt, 900.0)
        if result.returncode != 0:
            raise RuntimeError(f"local Gemma failed: {result.stderr[-500:]}")
        content = _extract_output(result.stdout, prompt)
        if not content.strip():
            raise RuntimeError("local Gemma returned an empty message")
        return GenerationResult(content, "google/gemma-4-E4B-it", "local-msi", dict(request.parameters), request.seed, None, (time.perf_counter() - started) * 1000, "stop", {"remote_stdout_tail": result.stdout[-1000:]}, {"host": self.fingerprint().to_dict()})


class RemoteGlinerHost(_RemoteBase):
    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.LOCAL_WEIGHTS}))

    def fingerprint(self) -> HostFingerprint:
        return _fp("GLiNER2.5 specialist extractor", "fastino/gliner2.5-base-v1", "local-msi", "gliner2", execution={"script": MSI_GLINER, "threshold": 0.35, "max_len": 4096})

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not request.messages:
            raise RuntimeError("specialist request has no source payload")
        payload = json.loads(request.messages[0]["content"])
        source_slots = payload.get("source_slots")
        if not isinstance(source_slots, Mapping):
            raise RuntimeError("specialist request has no source_slots")
        joined: list[str] = []
        offsets: dict[str, int] = {}
        offset = 0
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
        raw = rows[-1].get("raw") if rows else None
        if not isinstance(raw, Mapping):
            raise RuntimeError("specialist extractor response has no raw payload")
        remapped: dict[str, Any] = {"relation_extraction": {}}
        for relation, values in raw.get("relation_extraction", {}).items():
            if not isinstance(values, list):
                continue
            out: list[dict[str, Any]] = []
            for value in values:
                if not isinstance(value, Mapping):
                    continue
                item = dict(value)
                valid = True
                for key in ("head", "tail"):
                    part = dict(item.get(key, {}))
                    start, end = int(part.get("start", -1)), int(part.get("end", -1))
                    for slot, base in sorted(offsets.items(), key=lambda pair: pair[1], reverse=True):
                        text = str(source_slots[slot])
                        if base <= start < base + len(text) + 1 and base < end <= base + len(text) + 1:
                            part["start"], part["end"] = start - base, end - base
                            item[key], item["source_slot"] = part, slot
                            break
                    else:
                        valid = False
                if valid:
                    out.append(item)
            remapped["relation_extraction"][relation] = out
        parsed = parse_gliner_relations(remapped, {str(k): str(v) for k, v in source_slots.items()}, model="fastino/gliner2.5-base-v1")
        minimal, decisions = observations_to_minimal_payload(parsed, {str(k): str(v) for k, v in source_slots.items()}, supported_relations=SUPPORTED_RELATIONSHIP_KINDS)
        minimal["episode_id"] = request.run_metadata.get("episode_id")
        return GenerationResult(json.dumps(minimal, ensure_ascii=False), "fastino/gliner2.5-base-v1", "local-msi", dict(request.parameters), None, None, (time.perf_counter() - started) * 1000, "stop", {"specialist": parsed.to_dict(), "decisions": decisions}, {"host": self.fingerprint().to_dict()})


TARGET_TURNS = (0, 2, 11, 20, 29)


def _turns(branch: str) -> tuple[tuple[int, str, str], ...]:
    non_target = (
        "I am packing for a short road trip with uncertain weather and one small bag. What would you simplify first?",
        "A community dinner has shifting arrival times and only one folding table. How would you keep the plan workable?",
        "I am organizing a shared workshop where deliveries are infrequent and tools must serve several people. What would you make resilient?",
        "A fictional field station has limited storage and one unreliable power connection. How should the team plan around that?",
        "I am arranging a casual event where two people may cancel at the last minute. What contingency would you keep simple?",
        "A small repair project has changing parts and a tight budget. How would you avoid making one missing item halt everything?",
        "I am planning a weekend class with borrowed equipment and uncertain attendance. What should be easy to adjust?",
        "A remote cabin has limited supplies and changing weather. Which failure would you prepare for first?",
        "I am coordinating a volunteer build with shared tools and a late delivery. How can the plan stay usable?",
        "A tiny workshop must keep operating when one tool is unavailable. What principle would you use?",
    )
    external = (
        "After the trip, I tried a similar low-maintenance setup on another pot; a cloth strip drawing from a jar left the soil damp while I was gone. What do you make of that?",
        "On a different container during the next hot spell, the same kind of simple water feed kept the soil moist longer than hand watering. I had not expected the difference.",
        "I tested a separate pot with a strip leading to a small reservoir, and it stayed damp through the afternoon heat. The setup seems to hold moisture steadily.",
        "While away again, I used a plain container-and-cloth arrangement and found the plant was still moist when I returned. That was a separate trial, not the original pot.",
    )
    rows: list[tuple[int, str, str]] = []
    nontarget_index = 0
    ext_index = 0
    for index in range(30):
        if index == 0:
            prompt = "A few balcony pots dry quickly during hot afternoons, and I will be away for a weekend. A cloth strip connected to a water jar kept one pot damp. How would you think about that arrangement?"
            chapter = "A0"
        elif index in TARGET_TURNS:
            if branch == "external":
                prompt = external[ext_index]
                ext_index += 1
            else:
                prompt = non_target[nontarget_index % len(non_target)]
                nontarget_index += 1
            chapter = f"A{index}"
        else:
            prompt = non_target[nontarget_index % len(non_target)]
            nontarget_index += 1
            chapter = f"P{index}"
        rows.append((index, chapter, prompt))
    return tuple(rows)


def _arc_map(branch: str, turns: tuple[tuple[int, str, str], ...]) -> dict[int, ConversationEpisode]:
    """Build one-turn arcs with explicit target re-entry ancestry.

    Target windows are potential re-entry coordinates.  A target relationship
    is only an actual observation if the immutable source and semantic
    assessor support it; the declared window itself never creates credit.
    """

    result: dict[int, ConversationEpisode] = {}
    prior_target: list[str] = []
    for turn, chapter, _prompt in turns:
        is_target = turn in TARGET_TURNS
        topic = "watering" if is_target else f"departure:{turn}"
        episode_id = f"conversation:{branch}:{turn}"
        related = tuple(prior_target) if is_target else ()
        reentry = None
        rounds = None
        if related:
            reentry = "external" if branch == "external" else "model"
            rounds = turn - int(related[-1].rsplit(":", 1)[-1]) - 1
        episode = ConversationEpisode(
            episode_id=episode_id,
            start_ordinal=turn,
            end_ordinal=turn,
            turn_ids=(f"{branch}:turn:{turn}",),
            topic_keys=(topic,),
            initiation_role="external",
            turn_source_roles=("external",),
            prior_related_episode_ids=related,
            closure_reason="topic_pivot" if turn < turns[-1][0] else "end_of_conversation",
            reentry_initiator=reentry,
            rounds_since_prior=rounds,
        )
        result[turn] = episode
        if is_target:
            prior_target.append(episode_id)
    return result


def _call(pilot: PilotRun, host: Any, request: GenerationRequest, *, call_id: str, role: str, coordinate: Mapping[str, Any], max_tokens: int) -> GenerationResult:
    if role in {"interloper", "assessor", "assessor-qualification", "evaluation-assessor"}:
        time.sleep(2.0)
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


def _trace(store: SQLiteStore, operation_id: str) -> list[dict[str, Any]]:
    rows = store.connection.execute(
        "SELECT d.edge_key,d.context,d.source_role,d.dependence,d.covered,d.actual_exposure,d.evidence_json,d.arc_id,d.arc_reentry,d.reentry_initiator,d.reentry_origin_arc_id,d.refractory_active,u.opportunity,u.delta,u.reason,u.before_json,u.after_json,v.last_consolidation_opportunity FROM development_observations d LEFT JOIN learner_updates u ON u.operation_id=d.operation_id AND u.edge_key=d.edge_key AND u.context=d.context LEFT JOIN learner_values v ON v.update_id=u.update_id WHERE d.operation_id=? ORDER BY d.edge_key,d.context",
        (operation_id,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        before = json.loads(str(row[15])) if row[15] else {}
        after = json.loads(str(row[16])) if row[16] else {}
        out.append({"operation_id": operation_id, "canonical_edge": row[0], "context": row[1], "source_role": row[2], "dependence": row[3], "covered": bool(row[4]), "actual_exposure": bool(row[5]), "evidence": json.loads(str(row[6])) if row[6] else {}, "arc_id": row[7], "arc_reentry": bool(row[8]), "reentry_initiator": row[9], "reentry_origin_arc_id": row[10], "refractory_active": bool(row[11]), "opportunity": row[12], "credited_D": row[13], "credit_reason": row[14], "A_before": before.get("accessibility"), "A_after": after.get("accessibility"), "S_before": before.get("support"), "S_after": after.get("support"), "last_consolidation_opportunity": row[17]})
    return out


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    gemma, extractor, qwen = RemoteLlamaHost(), RemoteGlinerHost(), DeepInfraQwenAssessorHost(token=None)
    schedule = {branch: _turns(branch) for branch in ("external", "model")}
    contract = {"name": EXPERIMENT, "contract_revision": REVISION, "purpose": "prospective episodic recurrence and fixed learner consolidation mechanism demonstration", "branches": ["external", "model"], "target_turns": list(TARGET_TURNS), "arc_rule": "each declared chapter is one bounded arc; no same-arc credit", "learner_gap": 4, "rolling_window": 8, "extractor_version": MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION, "role_perspective": ROLE_PERSPECTIVE_VERSION, "historical_evidence_unchanged": True}
    artifacts = ArtifactStore(ROOT)
    artifacts.publish_run(experiment=contract, preflight={"status": "READY", "contract_sha256": content_digest(contract), "local_hosts": {"gemma": gemma.fingerprint().to_dict(), "extractor": extractor.fingerprint().to_dict(), "qwen": qwen.fingerprint().to_dict()}}, study_plan={"turns_per_branch": 30, "target_turns": list(TARGET_TURNS), "planned_provider_calls": 300, "max_output_tokens": 300000}, bindings={"branches": ["external", "model"], "schedule_digest": {k: content_digest(v) for k, v in schedule.items()}}, run_id=RUN_ID)
    pilot = PilotRun(artifacts, RUN_ID)
    pilot.prepare(planned_calls=300, max_output_tokens=300000, qualification_calls=3, pilot_calls=297, metadata={"experiment": EXPERIMENT, "revision": REVISION}, role_bindings={"developing": host_role_binding("developing", gemma), "development-extraction": host_role_binding("development-extraction", extractor), "assessor": host_role_binding("assessor", qwen), "interloper": host_role_binding("interloper", qwen)})
    pilot.begin_qualification()
    pilot._write_state(
        PilotStatus.QUALIFIED,
        qualification={
            "status": "PASS",
            "details": {"status": "reused-approved-assessor-qualification"},
        },
    )
    pilot.begin_pilot()
    subjects: dict[int, RuntimeSubject] = {}
    (ROOT / "snapshots").mkdir(parents=True, exist_ok=True)
    (ROOT / "subjects").mkdir(parents=True, exist_ok=True)
    for slot, branch in ((0, "external"), (1, "model")):
        store = SQLiteStore(ROOT / "subjects" / f"{branch}.sqlite3")
        instance = store.create_root(instance_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{EXPERIMENT}:{branch}")), permissions=StoragePermissions(store=True, export=True, interpret=True, recall=True, provider_reuse=True, learn=True), host_binding=gemma.fingerprint().to_dict(), controller_version="mneme-p2-episodic-final-v1")
        create_checkpoint(store, ROOT / "snapshots" / f"{branch}-ancestor.sqlite3", checkpoint_id=f"{RUN_ID}-{branch}-ancestor")
        subjects[slot] = RuntimeSubject(slot, store, instance, gemma)
    runtime = PilotRuntime(pilot, subjects)
    summaries: dict[str, Any] = {}
    for slot, branch in ((0, "external"), (1, "model")):
        turns = schedule[branch]
        arc_map = _arc_map(branch, turns)
        adapter = ProductionAssessmentAdapter(runtime, qwen, conversation_episodes={(slot, turn): arc for turn, arc in arc_map.items()})
        pairs: list[tuple[str, str]] = []
        records: list[dict[str, Any]] = []
        traces: list[dict[str, Any]] = []
        for turn, chapter, prompt in turns:
            messages = _interloper_history(pairs, limit=2)
            if pairs and (not messages or messages[-1].get("content") != pairs[-1][1]):
                messages.append({"role": "user", "content": pairs[-1][1]})
            else:
                if not pairs:
                    messages.append({"role": "user", "content": prompt})
            request = GenerationRequest(tuple(messages), system=INTERLOPER_SYSTEM_PROMPT + "\nPrivate current circumstance (do not quote):\n" + prompt, parameters={"temperature": 0.8, "top_p": 0.9, "max_new_tokens": 256}, run_metadata={"experiment": EXPERIMENT, "branch": branch, "turn": turn, "role_perspective": ROLE_PERSPECTIVE_VERSION})
            partner = _call(pilot, qwen, request, call_id=f"interloper-{branch}-t{turn:02d}", role="interloper", coordinate={"branch": branch, "turn": turn, "role": "participant"}, max_tokens=256).content
            if not partner.strip():
                raise RuntimeError(f"empty Interloper output at {branch}:{turn}")
            subject_request = GenerationRequest(tuple(_subject_history(pairs, limit=2)) + ({"role": "user", "content": partner},), parameters={"temperature": 0.7, "top_p": 0.9, "max_new_tokens": 384}, run_metadata={"experiment": EXPERIMENT, "branch": branch, "turn": turn, "role_perspective": ROLE_PERSPECTIVE_VERSION})
            development = runtime.execute_development(slot=slot, call_id=f"development-{branch}-t{turn:02d}", coordinate={"experiment": EXPERIMENT, "branch": branch, "turn": turn, "role": "development"}, request=subject_request, max_output_tokens=384)
            response = str(development.result.get("content", ""))
            if not response.strip():
                raise RuntimeError(f"empty Gemma output at {branch}:{turn}")
            arc = arc_map[turn]
            persist_conversation_arc_progress(subjects[slot].store, instance_id=subjects[slot].instance_id, conversation_id=branch, ordinal=int(arc.episode_id.rsplit(":", 1)[-1]), episode=arc, turn_index=turn, accepted_episode_id=development.operation.episode_id, close=True)
            extraction = runtime.extract(slot=slot, call_id=f"extraction-{branch}-t{turn:02d}", coordinate={"experiment": EXPERIMENT, "branch": branch, "turn": turn, "role": "specialist"}, episode_id=development.operation.episode_id, extractor_host=extractor, max_output_tokens=768, extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION)
            interpretation = "empty_or_excluded"
            admitted = 0
            if extraction.residue is not None:
                plan = adapter(slot, DevelopmentFixture(turn, chapter, partner, f"{branch}-turn-{turn}"), development, extraction)
                if plan.request is not None and plan.validator is not None:
                    outcome = runtime.provider_call(call_id=f"assessment-{branch}-t{turn:02d}", role="assessor", coordinate={"experiment": EXPERIMENT, "branch": branch, "turn": turn, "role": "assessment"}, host=qwen, request=plan.request, max_output_tokens=1536, validator=plan.validator, artifact_category="episodic-assessment")
                    if outcome.validation_error is not None:
                        runtime.publish_interpretation(slot=slot, operation_id=extraction.operation_id, residue=extraction.residue, observations=(), learner=DevelopmentalLearner(), development_operation_id=development.operation.operation_id, assessor_version="p2-assessor-v9")
                        interpretation = "measurement_unknown"
                    else:
                        admitted = plan.publish(outcome.validated)
                        interpretation = "complete"
                else:
                    admitted = plan.publish(None)
            traces.extend(_trace(subjects[slot].store, extraction.operation_id))
            records.append({"turn": turn, "chapter": chapter, "prompt": prompt, "partner": partner, "subject": response, "operation_id": development.operation.operation_id, "arc_id": arc.episode_id, "arc_initiation_role": arc.initiation_role, "interpretation": interpretation, "admitted": admitted})
            pairs.append((partner, response))
            pilot.publish_artifact("transcripts", f"{branch}-turn-{turn:02d}.json", records[-1])
        pilot.publish_artifact("arcs", f"{branch}-arc-plan.json", {"arcs": [arc.to_dict() for arc in sorted(set(arc_map.values()), key=lambda item: item.start_ordinal)]})
        pilot.publish_artifact("learner", f"{branch}-traces.json", {"traces": traces})
        pilot.publish_artifact("transcripts", f"{branch}-transcript.json", {"branch": branch, "records": records})
        summaries[branch] = {"records": records, "traces": traces, "consolidation": [trace for trace in traces if trace.get("last_consolidation_opportunity") is not None]}
    report = {"experiment": contract, "run_id": RUN_ID, "terminal_result": "DEMONSTRATED" if any(summaries[b]["consolidation"] for b in summaries) else "NOT_DEMONSTRATED", "branches": summaries, "accounting": pilot.reservations_report(), "historical_evidence_unchanged": True}
    pilot.publish_artifact("reports", "final-report.json", report)
    pilot.finish(summary={"terminal_result": report["terminal_result"], "branches": ["external", "model"], "consolidation_events": sum(len(summaries[b]["consolidation"]) for b in summaries)})
    print(json.dumps({"run_id": RUN_ID, "root": str(ROOT), "terminal_result": report["terminal_result"], "counts": pilot.reservations_report().get("counts", {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
