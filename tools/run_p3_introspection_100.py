#!/usr/bin/env python3
# ruff: noqa: E501
"""Run the authorized P3-INTROSPECT-100 two-lineage study."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.controller import ResponseController, TurnIntent
from mneme.development import (
    ArcPacket,
    IntrospectionLedger,
    ReviewTarget,
    accept_proposals,
    parse_proposals,
    review_request,
    review_system_prompt,
)
from mneme.experiments.artifacts import ArtifactStore, content_digest
from mneme.experiments.pilot import PilotRun, host_role_binding
from mneme.experiments.pilot_runtime import PilotRuntime, RuntimeSubject
from mneme.experiments.pilot_study import DevelopmentFixture, ProductionAssessmentAdapter
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
    require_nonempty_message,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.memory.interpretation import MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION
from mneme.state.contracts import StoragePermissions
from mneme.state.snapshots import create_checkpoint, fork_from_checkpoint
from mneme.state.storage import SQLiteStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_p23_f0_background_shared_interloper import (
    RemoteGlinerHost,
    RemoteLlamaHost,
    _call,
    _load_assessor_host,
    _trace,
)
from tools.run_p23_saa_ten_thread_live import _development_request

ROOT = Path(os.environ.get("MNEME_P3_INTROSPECT_LAB", "docs/receipts/MNEME_P3_Introspection_100_Thread_Run_20260927"))
RUN_ID = os.environ.get("MNEME_P3_INTROSPECT_RUN_ID", "p3-introspect-100-20260927-r1")
TOPIC_BANK = Path("docs/experiments/p3_introspection_100_topic_bank_v1.json")
R8_CHECKPOINT = Path(
    "docs/receipts/MNEME_P2_SAA_Ten_Thread_Run_r8_20260927/snapshots/SAA-developed.sqlite3"
)
THREAD_TURNS = 8
CHECKPOINTS = (0, 10, 25, 50, 75, 100)
PROBE_SEEDS = (61001, 61002, 61003)
FIELD_SEEDS = (71001, 71004, 71007, 71010, 71013, 71016, 71019, 71022)
PROBES = (
    "A small team must keep a remote project usable while people have changing schedules. What would you notice first?",
    "A fictional station must remain useful when one supply route fails. How would you organize the design?",
    "Explain a new everyday mechanism to someone who wants both simplicity and room to recover from mistakes.",
    "A group is choosing between a very efficient plan and a more forgiving one. What tradeoff would you examine?",
    "A creative project has many possible directions but limited attention. How might you decide what to preserve?",
    "An unfamiliar process produces uneven results. What would you investigate before changing everything?",
    "A shared resource is sometimes available and sometimes absent. What kind of arrangement might help?",
    "Plan a modest event whose timing, people, and materials are all somewhat uncertain.",
)


def _permissions() -> StoragePermissions:
    return StoragePermissions(
        store=True, export=True, interpret=True, recall=True, provider_reuse=True, learn=True
    )


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _topics() -> list[ThreadSpec]:
    value = json.loads(TOPIC_BANK.read_text(encoding="utf-8"))
    rows = value.get("topics")
    if not isinstance(rows, list) or len(rows) != 100:
        raise RuntimeError("frozen topic bank must contain exactly 100 topics")
    result = []
    for row in rows:
        result.append(
            ThreadSpec(
                f"P3-{int(row['thread']):03d}",
                str(row["opening"]),
                (str(row["private_concerns"]),),
            )
        )
    return result


def _review_json(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _packet(thread_id: str, history: list[tuple[str, str]], exposures: list[dict[str, Any]]) -> ArcPacket:
    targets: list[ReviewTarget] = []
    refs: list[dict[str, Any]] = []
    for item in exposures:
        edge_key = str(item.get("edge_key", ""))
        if not edge_key or any(target.edge_key == edge_key for target in targets):
            continue
        ref = str(item.get("turn_ref", ""))
        targets.append(ReviewTarget(f"{thread_id.lower()}-{len(targets)}", edge_key, str(item.get("context", "general")), (ref,)))
        refs.append(item)
        if len(targets) >= 8:
            break
    if not targets:
        targets = [ReviewTarget(f"{thread_id.lower()}-none", "none", "general")]
    messages = tuple(
        {"role": role, "content": text}
        for participant, response in history
        for role, text in (("user", participant), ("assistant", response))
    )
    return ArcPacket(thread_id, messages, tuple(refs), tuple(targets), missing_aftermath=True)


def _review(
    pilot: PilotRun,
    host: Any,
    packet: ArcPacket,
    *,
    call_id: str,
    coordinate: Mapping[str, Any],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    request = GenerationRequest(
        messages=(
            {"role": "user", "content": json.dumps(review_request(packet), ensure_ascii=False)},
        ),
        system=review_system_prompt(),
        parameters={"temperature": 0.1, "top_p": 0.9, "max_new_tokens": 512},
    )
    result = _call(pilot, host, request, call_id=call_id, role="introspection", coordinate=coordinate, max_tokens=512)
    raw = _review_json(result.content)
    try:
        proposals = parse_proposals(raw, packet, valid_evidence_refs={str(item.get("turn_ref")) for item in packet.exposures})
        return proposals, {"status": "COMPLETE", "raw": result.content, "parsed": [item.to_dict() for item in proposals]}
    except Exception as first_error:
        repair_request = GenerationRequest(
            messages=({"role": "user", "content": raw},),
            system=(
                "Return only valid JSON with an assessments list using exactly the supplied target aliases, "
                "numeric effects in [-1,1], confidence in [0,1], and supplied evidence references. "
                "Do not invent an assessment."
            ),
            parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 512},
        )
        repaired = _call(pilot, host, repair_request, call_id=f"{call_id}-repair", role="introspection", coordinate=coordinate, max_tokens=512)
        try:
            proposals = parse_proposals(_review_json(repaired.content), packet, valid_evidence_refs={str(item.get("turn_ref")) for item in packet.exposures})
        except Exception as second_error:
            raise RuntimeError(f"introspection review malformed after one repair: {first_error}; {second_error}") from second_error
        return proposals, {"status": "REPAIRED", "raw": result.content, "repair": repaired.content, "parsed": [item.to_dict() for item in proposals]}


def _prepare_observe(controller: ResponseController, prompt: str, seed: int, field_seed: int, policy: str, memory: str, operation: str) -> Any:
    return controller.prepare(
        TurnIntent(
            current_input=prompt,
            mode="observe",
            memory=memory,
            session_messages=(),
            system=GEMMA_SYSTEM_PROMPT,
            parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
            seed=seed,
            operation_id=operation,
            selection_policy=policy,
            field_seed=field_seed,
        )
    )


def _make_pilot(gemma: Any, extractor: Any, assessor: Any, interloper: Any) -> tuple[ArtifactStore, PilotRun]:
    contract = {
        "name": "p3-introspect-100",
        "contract_revision": 1,
        "methodology": "arc-bound-introspection-two-lineage",
        "topic_bank_sha256": content_digest(json.loads(TOPIC_BANK.read_text(encoding="utf-8"))),
        "r8_parent": str(R8_CHECKPOINT),
        "threads": 100,
        "exchanges_per_thread": THREAD_TURNS,
        "checkpoints": list(CHECKPOINTS),
        "probe_count": len(PROBES),
        "probe_seeds": list(PROBE_SEEDS),
        "introspection_version": "p3-introspection-v1",
    }
    contract["contract_sha256"] = content_digest(contract)
    store = ArtifactStore(ROOT)
    bindings = {
        "subjects": [{"slot": 0, "label": "I"}, {"slot": 1, "label": "N"}],
        "historical_evidence_unchanged": True,
    }
    experiment = {
        **contract,
        "model_fingerprints": {
            "gemma": gemma.fingerprint().to_dict(),
            "extractor": extractor.fingerprint().to_dict(),
            "assessor": assessor.fingerprint().to_dict(),
            "interloper": interloper.fingerprint().to_dict(),
        },
    }
    experiment.pop("contract_sha256", None)
    experiment["contract_sha256"] = content_digest(experiment)
    planned = 6200
    store.publish_run(
        experiment=experiment,
        preflight={"status": "READY", "topic_bank_sha256": contract["topic_bank_sha256"]},
        study_plan={"planned_calls": planned, "max_output_tokens": 2_000_000, "schedule": contract},
        bindings=bindings,
        run_id=RUN_ID,
    )
    pilot = PilotRun(store, RUN_ID)
    pilot.prepare(
        planned_calls=planned,
        max_output_tokens=2_000_000,
        qualification_calls=3,
        pilot_calls=planned - 3,
        metadata={"experiment": "p3-introspect-100", "version": "p3-introspection-v1"},
        role_bindings={
            "developing": host_role_binding("developing", gemma),
            "development-response": host_role_binding("development-response", gemma),
            "development-extraction": host_role_binding("development-extraction", extractor),
            "assessor": host_role_binding("assessor", assessor),
            "interloper": host_role_binding("interloper", interloper),
            "introspection": host_role_binding("introspection", gemma),
            "evaluation": host_role_binding("evaluation", gemma),
        },
    )
    return store, pilot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "FROZEN_PLAN_ONLY", "topic_count": 100, "checkpoints": CHECKPOINTS}, indent=2))
        return 0
    ROOT.mkdir(parents=True, exist_ok=True)
    topics = _topics()
    if not R8_CHECKPOINT.is_file():
        raise RuntimeError(f"missing immutable R8 checkpoint: {R8_CHECKPOINT}")
    gemma = RemoteLlamaHost()
    extractor = RemoteGlinerHost()
    assessor = _load_assessor_host()
    interloper = DeepInfraQwenAssessorHost(
        token=None,
        model_id="Qwen/Qwen3-30B-A3B",
        model_family="Qwen3 30B A3B Instruct-role",
        upstream_model_id="Qwen/Qwen3-30B-A3B",
        quantization="provider-managed",
        context_length=40960,
    )
    store, pilot = _make_pilot(gemma, extractor, assessor, interloper)
    # Three local qualification calls are required by the durable pilot
    # envelope.  They test the real local host binding but do not enter study
    # data or learner state.
    pilot.begin_qualification()
    for index in range(3):
        request = GenerationRequest(
            ({"role": "user", "content": "Return the JSON object {\"ok\":true}."},),
            system="Return only the requested JSON.",
            parameters={"temperature": 0.0, "max_new_tokens": 16},
        )
        _call(pilot, gemma, request, call_id=f"qualify-{index}", role="assessor-qualification", coordinate={"qualification": index}, max_tokens=16)
    pilot.complete_qualification(passed=True, details={"local_gemma": "reachable", "introspection": "offline-qualified"})
    pilot.begin_pilot()

    branches = {"I": ROOT / "subjects" / "I.sqlite3", "N": ROOT / "subjects" / "N.sqlite3", "V": ROOT / "subjects" / "V.sqlite3"}
    for path in branches.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not branches["I"].exists():
        fork_from_checkpoint(R8_CHECKPOINT, branches["I"], child_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{RUN_ID}:I")))
        fork_from_checkpoint(R8_CHECKPOINT, branches["N"], child_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{RUN_ID}:N")))
        fork_from_checkpoint(R8_CHECKPOINT, branches["V"], child_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{RUN_ID}:V")))
    stores = {label: SQLiteStore(path) for label, path in branches.items()}
    subjects = {slot: RuntimeSubject(slot, stores[label], stores[label].current()["active_instance_id"], gemma) for slot, label in ((0, "I"), (1, "N"))}
    runtime = PilotRuntime(pilot, subjects)
    adapter = ProductionAssessmentAdapter(runtime, assessor)
    controllers = {label: ResponseController(stores[label], stores[label].current()["active_instance_id"], gemma) for label in ("I", "N")}
    ledgers = {label: IntrospectionLedger(ROOT / "introspection" / f"{label}.json", parent_digest=content_digest({"parent": str(R8_CHECKPOINT), "label": label})) for label in ("I", "N")}
    transcripts: list[dict[str, Any]] = []
    progress = {"threads_completed": 0, "checkpoints": {}, "introspection_reviews": 0}
    for thread_index, thread in enumerate(topics, 1):
        histories = {"I": [], "N": []}
        exposure_rows = []
        participant: str | None = None
        for turn in range(THREAD_TURNS):
            if turn == 0:
                participant = thread.opening
            else:
                participant = require_nonempty_message(
                    _call(
                        pilot,
                        interloper,
                        build_shared_interloper_request(
                            thread=thread,
                            prior_participant=participant,
                            responses={"A": histories["I"][-1][1], "B": histories["N"][-1][1]},
                            turn=turn,
                        ),
                        call_id=f"qwen-{thread.thread_id}-{turn}",
                        role="interloper",
                        coordinate={"thread": thread.thread_id, "turn": turn},
                        max_tokens=192,
                    ).content,
                    role="Qwen",
                )
            branch_rows: dict[str, Any] = {}
            for slot, label in ((0, "I"), (1, "N")):
                seed = 200000 + thread_index * 100 + turn
                field_seed = FIELD_SEEDS[(thread_index + turn) % len(FIELD_SEEDS)] + thread_index
                prepared, exposure = _development_request(
                    controllers[label], participant=participant, history=histories[label], seed=seed,
                    field_seed=field_seed, operation_id=f"dev-{label}-{thread.thread_id}-{turn}",
                    memory="graph", selection_policy="field-saa-v1",
                )
                if label == "I":
                    prepared = controllers[label].prepare(
                        TurnIntent(
                            current_input=participant, mode="develop", memory="graph",
                            session_messages=prepared.request.messages[:-1], system=GEMMA_SYSTEM_PROMPT,
                            parameters=prepared.request.parameters, seed=seed,
                            operation_id=f"dev-{label}-{thread.thread_id}-{turn}",
                            selection_policy="field-saa-v1", field_seed=field_seed,
                            field_adjustments=ledgers["I"].accessibility_adjustments(),
                        )
                    )
                    exposure["field_adjustments"] = ledgers["I"].accessibility_adjustments()
                outcome = runtime.execute_development(
                    slot=slot, call_id=f"dev-{label}-{thread.thread_id}-{turn}",
                    coordinate={"thread": thread.thread_id, "turn": turn, "lineage": label},
                    request=prepared.request, max_output_tokens=256,
                )
                response = require_nonempty_message(str(outcome.result.get("content", "")), role=f"Gemma {label}")
                extraction = runtime.extract(
                    slot=slot, call_id=f"extract-{label}-{thread.thread_id}-{turn}",
                    coordinate={"thread": thread.thread_id, "turn": turn, "lineage": label},
                    episode_id=outcome.operation.episode_id, extractor_host=extractor,
                    max_output_tokens=768, extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
                )
                plan = adapter(slot, DevelopmentFixture(thread_index * 100 + turn, thread.thread_id, participant, f"p3-{thread.thread_id}-{turn}"), outcome, extraction)
                status = "excluded"
                admitted = 0
                if plan.request is not None and plan.validator is not None:
                    assessed = runtime.provider_call(
                        call_id=f"assess-{label}-{thread.thread_id}-{turn}", role="assessor",
                        coordinate={"thread": thread.thread_id, "turn": turn, "lineage": label}, host=assessor,
                        request=plan.request, max_output_tokens=1536, validator=plan.validator,
                        artifact_category="assessment",
                    )
                    if assessed.validation_error is None:
                        admitted = plan.publish(assessed.validated)
                        status = "complete"
                    else:
                        status = "measurement_unknown"
                        plan.publish(None)
                else:
                    admitted = plan.publish(None)
                row = {"response": response, "seed": seed, "exposure": exposure, "interpretation": status, "admitted": admitted, "trace": _trace(stores[label], outcome.operation.operation_id)}
                branch_rows[label] = row
                histories[label].append((participant, response))
                if label == "I":
                    field = exposure.get("field") or {}
                    for contribution in field.get("contributions", []):
                        exposure_rows.append({"turn_ref": f"{thread.thread_id}:turn:{turn}", "edge_key": contribution.get("edge_key"), "context": contribution.get("relationship", "general"), "payload": field.get("payload", "")})
            transcripts.append({"thread": thread.thread_id, "turn": turn, "participant": participant, "I": branch_rows["I"], "N": branch_rows["N"]})
        packet = _packet(thread.thread_id, histories["I"], exposure_rows)
        proposals, review = _review(pilot, gemma, packet, call_id=f"introspect-{thread.thread_id}", coordinate={"thread": thread.thread_id, "boundary": "closed"})
        accepted = accept_proposals(packet, proposals, existing_dedup=ledgers["I"].dedup_keys)
        ledgers["I"].record_review(packet, proposals, accepted=accepted, status=review["status"])
        ledgers["I"].save()
        pilot.publish_artifact("introspection", f"review-{thread.thread_id}.json", {"packet": packet.to_dict(), "review": review, "accepted": [item.to_dict() for item in accepted]})
        progress["threads_completed"] = thread_index
        progress["introspection_reviews"] += 1
        if thread_index in CHECKPOINTS[1:]:
            for label in ("I", "N"):
                checkpoint = ROOT / "snapshots" / f"{label}-{thread_index}.sqlite3"
                create_checkpoint(stores[label], checkpoint, checkpoint_id=f"{RUN_ID}-{label}-{thread_index}")
                progress["checkpoints"][str(thread_index)] = progress["checkpoints"].get(str(thread_index), {}) | {label: str(checkpoint)}
        _atomic_json(ROOT / "progress.json", progress)
        pilot.publish_artifact("development", f"transcript-{thread.thread_id}.json", transcripts[-THREAD_TURNS:])

    # Frozen checkpoint readouts: the two developing lineages plus a vanilla
    # fork of the immutable R8 state.  Readouts never update any lineage.
    vanilla_controller = ResponseController(stores["V"], stores["V"].current()["active_instance_id"], gemma)
    checkpoints = {0: R8_CHECKPOINT, **{number: Path(path) for number, rows in progress["checkpoints"].items() for path in []}}
    for number in CHECKPOINTS[1:]:
        checkpoints[number] = ROOT / "snapshots" / f"I-{number}.sqlite3"
    readouts: list[dict[str, Any]] = []
    for checkpoint_number, checkpoint in checkpoints.items():
        for probe_index, prompt in enumerate(PROBES):
            for repetition, seed in enumerate(PROBE_SEEDS):
                for label, controller, policy, memory in (("I", controllers["I"], "field-saa-v1", "graph"), ("N", controllers["N"], "field-saa-v1", "graph"), ("V", vanilla_controller, "fixed-v2", "off")):
                    prepared = _prepare_observe(controller, prompt, seed, FIELD_SEEDS[(probe_index + repetition) % len(FIELD_SEEDS)], policy, memory, f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}")
                    result = pilot.reserve_call(call_id=f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}", role="evaluation", coordinate={"checkpoint": checkpoint_number, "probe": probe_index, "repetition": repetition, "condition": label}, max_output_tokens=256)
                    if result.get("status") == "RETURNED":
                        content = str(result["result"].get("content", ""))
                    else:
                        pilot.dispatch_call(f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}", expected_host_fingerprint=gemma.fingerprint().to_dict())
                        generated = gemma.generate(prepared.request)
                        content = require_nonempty_message(generated.content, role=f"Gemma {label}")
                        pilot.return_call(f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}", result={"content": content, "model_id": generated.model_id, "provider": generated.provider, "effective_parameters": generated.effective_parameters, "seed": generated.seed, "finish_reason": generated.finish_reason, "provenance": generated.provenance}, actual_host_fingerprint=gemma.fingerprint().to_dict())
                    readouts.append({"checkpoint": checkpoint_number, "probe": probe_index, "repetition": repetition, "condition": label, "seed": seed, "field_seed": FIELD_SEEDS[(probe_index + repetition) % len(FIELD_SEEDS)], "prompt": prompt, "output": content, "payload": prepared.request.system})
    _atomic_json(ROOT / "transcripts.json", {"rows": transcripts})
    _atomic_json(ROOT / "readouts.json", {"rows": readouts, "probes": list(PROBES), "seeds": list(PROBE_SEEDS)})
    _atomic_json(ROOT / "introspection-ledger.json", {label: ledgers[label].accessibility_adjustments() for label in ledgers})
    report = {
        "status": "VALID_INTERPRETABLE_P3_INTROSPECT_100",
        "run_id": RUN_ID,
        "historical_r8_unchanged": True,
        "threads_completed": len(topics),
        "transcript_rows": len(transcripts),
        "readout_rows": len(readouts),
        "introspection_reviews": progress["introspection_reviews"],
        "checkpoint_numbers": list(CHECKPOINTS),
        "model_stack": {"gemma": gemma.fingerprint().to_dict(), "extractor": extractor.fingerprint().to_dict(), "assessor": assessor.fingerprint().to_dict(), "interloper": interloper.fingerprint().to_dict()},
        "phase_four_recommendation": "planning_only_after_owner_review",
        "limitations": ["two related adaptive lineages are not 100 independent subjects", "introspection is a bounded text-mediated review path", "no Phase Four neural backend was started"],
        "accounting": pilot.reservations_report(),
    }
    pilot.publish_artifact("final", "final-report.json", report)
    pilot.finish(summary={"status": report["status"], "threads": len(topics), "readouts": len(readouts)})
    _atomic_json(ROOT / "terminal-report.json", report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
