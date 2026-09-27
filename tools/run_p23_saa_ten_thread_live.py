#!/usr/bin/env python3
# ruff: noqa: E501
"""Execute the frozen SAA ten-thread experiment when explicitly requested.

The default command is plan-only.  The live path is deliberately explicit
(``--execute``) and reuses the existing Phase Two PilotRuntime, local Gemma,
GLiNER2.5, pinned local DeBERTa assessor, and shared Qwen3-30B contract.  It
does not modify the controller or the historical F0 runs.  Development uses
the normal learned graph path; SAA is evaluated only against the frozen
post-Thread-9 state so Thread 10 cannot write into the primary readout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mneme.controller import ResponseController, TurnIntent
from mneme.development.learner import DevelopmentalLearner
from mneme.experiments.artifacts import ArtifactStore, content_digest
from mneme.experiments.pilot import PilotRun, host_role_binding
from mneme.experiments.pilot_runtime import PilotRuntime, RuntimeSubject
from mneme.experiments.pilot_study import DevelopmentFixture, ProductionAssessmentAdapter
from mneme.experiments.qualification import run_assessor_qualification
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    build_shared_interloper_request,
    require_nonempty_message,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.memory.interpretation import MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore
from tools.run_p23_f0_background_shared_interloper import (
    RemoteGlinerHost,
    RemoteLlamaHost,
    _call,
    _development_request,
    _load_assessor_host,
    _subject_permissions,
    _trace,
)
from tools.run_p23_saa_ten_thread import (
    CONTRACT_REVISION,
    DEVELOPMENT_TURNS_MAX,
    DEVELOPMENT_TURNS_MIN,
    DEVELOPMENT_TURNS_TARGET,
    EXPERIMENT,
    FIELD_SEEDS,
    GEMMA_READOUT_SEEDS,
    READOUT_PROBES,
    READOUT_REPETITIONS,
    THREAD_SCHEDULE,
    saa_contract,
    validate_saa_contract,
)

ROOT = Path(os.environ.get("MNEME_SAA_LAB", "/tmp/mneme-p23-saa-ten-thread-20260926"))
RUN_ID = os.environ.get("MNEME_SAA_RUN_ID", "p23-saa-ten-thread-20260926")
PLANNED_CALLS = 420
MAX_OUTPUT_TOKENS = 300_000


def _payload(result: Any) -> dict[str, Any]:
    value = result.to_dict()
    usage = value.get("token_usage")
    if isinstance(usage, Mapping):
        value["usage"] = usage
    value.pop("token_usage", None)
    return value


def _field_seed(index: int) -> int:
    """Use only the predeclared field stream, independent of administration."""

    return FIELD_SEEDS[index % len(FIELD_SEEDS)]


def _build_contract(gemma: Any, extractor: Any, interloper: Any, assessor: Any) -> dict[str, Any]:
    contract = saa_contract()
    contract["run_id"] = RUN_ID
    contract["implementation"] = {
        "runner": "tools/run_p23_saa_ten_thread_live.py",
        "runner_contract_revision": CONTRACT_REVISION,
        "historical_runs_unchanged": True,
        "development_turn_bounds": {
            "minimum": DEVELOPMENT_TURNS_MIN,
            "target": DEVELOPMENT_TURNS_TARGET,
            "maximum": DEVELOPMENT_TURNS_MAX,
        },
    }
    contract["hosts"] = {
        "gemma": gemma.fingerprint().to_dict(),
        "extractor": extractor.fingerprint().to_dict(),
        "interloper": interloper.fingerprint().to_dict(),
        "assessor": assessor.fingerprint().to_dict(),
    }
    validate_saa_contract(contract)
    contract["contract_sha256"] = content_digest(contract)
    return contract


def _publish_transcript(pilot: PilotRun, row: Mapping[str, Any], name: str) -> None:
    pilot.publish_artifact("contingent", name, dict(row))


def _development_gate(controller: ResponseController, exposures: list[Mapping[str, Any]], transcripts: list[Mapping[str, Any]]) -> dict[str, Any]:
    pin = controller._pin()
    state = controller._learner_state(pin)
    edges = [item for item in state.edge_states if item.accessibility > 0 or item.support > 0]
    neighborhoods = {item.target_key.split("::", 1)[0] for item in edges}
    return {
        "eligible_state": bool(exposures and any(item.get("eligible_state") for item in exposures)),
        "nonzero_edge_count": len(edges),
        "nonzero_edge_keys": [item.target_key for item in edges],
        "conceptual_neighborhood_count": len(neighborhoods),
        "development_interpretations": sum(
            int(item.get("M", {}).get("admitted", 0))
            for item in transcripts
            if isinstance(item.get("M"), Mapping)
        ),
        "adequate_nontrivial_field": len(edges) >= 2 and len(neighborhoods) >= 2,
        "historical_evidence_unchanged": True,
    }


def _saa_readout_request(
    controller: ResponseController,
    *,
    label: str,
    probe: str,
    seed: int,
    field_seed: int | None,
    operation_id: str,
) -> Any:
    policy = "field-saa-v1" if label in {"SAA", "SAA_RESTORED"} else "fixed-v2"
    memory = "graph" if label in {"SAA", "SAA_RESTORED"} else "off"
    return controller.prepare(
        TurnIntent(
            current_input=probe,
            mode="develop",
            memory=memory,
            system=GEMMA_SYSTEM_PROMPT,
            parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
            seed=seed,
            field_seed=field_seed,
            operation_id=operation_id,
            selection_policy=policy,
        )
    )


def _run_frozen_probe(
    runtime: PilotRuntime,
    pilot: PilotRun,
    controllers: Mapping[int, ResponseController],
    gemma: Any,
    checkpoints: Mapping[str, Path],
    probe_index: int,
    repetition: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seed = GEMMA_READOUT_SEEDS[repetition]
    field_seed = _field_seed(probe_index * READOUT_REPETITIONS + repetition)
    conditions = (
        ("C", 1, checkpoints["C"]),
        ("SAA", 0, checkpoints["M"]),
        ("SAA_OFF", 0, checkpoints["M"]),
        ("SAA_RESTORED", 0, checkpoints["M"]),
    )
    for label, slot, checkpoint in conditions:
        prepared = _saa_readout_request(
            controllers[slot],
            label=label,
            probe=READOUT_PROBES[probe_index],
            seed=seed,
            field_seed=field_seed if label in {"SAA", "SAA_RESTORED"} else None,
            operation_id=f"readout-prep-{label}-p{probe_index}-r{repetition}",
        )
        outcome = runtime.evaluate(
            slot=slot,
            call_id=f"readout-{label}-p{probe_index}-r{repetition}",
            coordinate={
                "boundary": "frozen-neutral-probe",
                "probe": probe_index,
                "repetition": repetition,
                "condition": label,
            },
            checkpoint=checkpoint,
            private_snapshot=checkpoint,
            host=gemma,
            messages=prepared.request.messages,
            max_output_tokens=256,
            seed=seed,
            parameters=prepared.request.parameters,
            system=prepared.request.system,
        )
        output = require_nonempty_message(str(outcome.result.get("content", "")), role=f"Gemma {label}")
        field = prepared.field_result.to_dict() if prepared.field_result is not None else None
        if label in {"SAA", "SAA_RESTORED"} and not prepared.field_result:
            raise RuntimeError(f"SAA field was not computed at {label}/p{probe_index}/r{repetition}")
        rows.append(
            {
                "probe": probe_index,
                "probe_text": READOUT_PROBES[probe_index],
                "repetition": repetition,
                "condition": label,
                "seed": seed,
                "field_seed": field_seed if label in {"SAA", "SAA_RESTORED"} else None,
                "policy": prepared.selection_policy,
                "field_trace": field,
                "request": prepared.request.to_dict(),
                "result": dict(outcome.result) | {"content": output},
            }
        )
    return rows


def _blinded_rows(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((int(row["probe"]), int(row["repetition"])), {})[
            str(row["condition"])
        ] = row
    output: list[dict[str, Any]] = []
    for ordinal, (coordinate, values) in enumerate(sorted(grouped.items())):
        for left, right in (("C", "SAA"), ("SAA", "SAA_OFF"), ("SAA", "SAA_RESTORED")):
            if left not in values or right not in values:
                continue
            ordered = [(left, values[left]), (right, values[right])]
            if (ordinal + len(left)) % 2:
                ordered.reverse()
            left_text = str(ordered[0][1]["result"]["content"])
            right_text = str(ordered[1][1]["result"]["content"])
            output.append(
                {
                    "probe": coordinate[0],
                    "repetition": coordinate[1],
                    "comparison": f"{left}-vs-{right}",
                    "label_order": ["response_A", "response_B"],
                    "response_A": left_text,
                    "response_B": right_text,
                    "observable": {
                        "A_characters": len(left_text),
                        "B_characters": len(right_text),
                        "A_words": len(left_text.split()),
                        "B_words": len(right_text.split()),
                        "identical": left_text == right_text,
                    },
                }
            )
    return output


def _run(args: argparse.Namespace) -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    gemma = RemoteLlamaHost()
    extractor = RemoteGlinerHost()
    interloper = DeepInfraQwenAssessorHost(
        token=None,
        model_id="Qwen/Qwen3-30B-A3B",
        model_family="Qwen3 30B A3B Instruct-role",
        upstream_model_id="Qwen/Qwen3-30B-A3B",
        quantization="provider-managed",
        context_length=40960,
    )
    assessor = _load_assessor_host()
    contract = _build_contract(gemma, extractor, interloper, assessor)
    store = ArtifactStore(ROOT)
    development_turns = DEVELOPMENT_TURNS_TARGET
    study_plan = {
        "development_gemma_calls": 9 * development_turns * 2,
        "development_extraction_calls": 9 * development_turns,
        "development_assessment_calls": 9 * development_turns,
        "shared_interloper_development_calls": 9 * (development_turns - 1),
        "thread10_gemma_calls": development_turns * 2,
        "thread10_interloper_calls": development_turns - 1,
        "frozen_probe_calls": len(READOUT_PROBES) * READOUT_REPETITIONS * 4,
        "qualification_calls": 3,
        "planned_calls": PLANNED_CALLS,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
    }
    published = store.publish_run(
        experiment=contract,
        preflight={"status": "READY", "contract_sha256": content_digest(contract), "hosts": contract["hosts"]},
        study_plan=study_plan,
        bindings={
            "subjects": [
                {"slot": 0, "label": "SAA", "treatment": "mneme-saa"},
                {"slot": 1, "label": "C", "treatment": "control"},
            ],
            "threads": [item.thread_id for item in THREAD_SCHEDULE],
            "historical_evidence_unchanged": True,
        },
        run_id=RUN_ID,
    )
    pilot = PilotRun(store, RUN_ID)
    role_bindings = {
        "developing": host_role_binding("developing", gemma),
        "development-response": host_role_binding("development-response", gemma),
        "development-extraction": host_role_binding("development-extraction", extractor),
        "interloper": host_role_binding("interloper", interloper),
        "assessor": host_role_binding("assessor", assessor),
        "evaluation": host_role_binding("evaluation", gemma),
    }
    pilot.prepare(
        planned_calls=PLANNED_CALLS,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        qualification_calls=3,
        pilot_calls=PLANNED_CALLS - 3,
        metadata={"experiment": EXPERIMENT, "revision": CONTRACT_REVISION, "published_run": str(published.path)},
        role_bindings=role_bindings,
    )
    qualification = run_assessor_qualification(pilot, assessor_host=assessor, max_output_tokens=1536)
    if qualification.get("status") != "QUALIFIED":
        report = {"status": "INVALID_ASSESSOR_QUALIFICATION", "qualification": qualification, "contract": contract}
        pilot.publish_artifact("qualification", "final-report.json", report)
        pilot.finish(summary=report)
        print(json.dumps(report, indent=2))
        return 2
    pilot.begin_pilot()

    subjects: dict[int, RuntimeSubject] = {}
    controllers: dict[int, ResponseController] = {}
    for slot, label in ((0, "SAA"), (1, "C")):
        path = ROOT / "subjects" / f"{label}.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        subject_store = SQLiteStore(path)
        instance = subject_store.create_root(
            instance_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{EXPERIMENT}:{label}")),
            permissions=_subject_permissions(0 if slot == 0 else 1),
            host_binding=gemma.fingerprint().to_dict(),
            controller_version="mneme-p2-saa-ten-thread-v1",
        )
        subjects[slot] = RuntimeSubject(slot, subject_store, instance, gemma)
        controllers[slot] = ResponseController(subject_store, instance, gemma)
        create_checkpoint(subject_store, ROOT / "snapshots" / f"{label}-ancestor.sqlite3", checkpoint_id=f"{RUN_ID}-{label}-ancestor")
    runtime = PilotRuntime(pilot, subjects)
    adapter = ProductionAssessmentAdapter(runtime, assessor)
    histories: dict[int, list[tuple[str, str]]] = {0: [], 1: []}
    transcripts: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    sanity_checked = False
    global_turn = 0
    try:
        for thread_index, thread in enumerate(THREAD_SCHEDULE[:9]):
            histories = {0: [], 1: []}
            participant = require_nonempty_message(thread.opening, role="Qwen opening")
            prior_participant: str | None = None
            for local_turn in range(development_turns):
                if local_turn > 0:
                    responses = {"A": histories[0][-1][1], "B": histories[1][-1][1]}
                    qwen_result = _call(
                        pilot,
                        interloper,
                        build_shared_interloper_request(thread=thread.shared_interloper_spec(), prior_participant=prior_participant, responses=responses, turn=local_turn),
                        call_id=f"shared-qwen-{thread.thread_id}-t{local_turn}",
                        role="interloper",
                        coordinate={"thread": thread.thread_id, "turn": local_turn},
                        max_tokens=192,
                    )
                    participant = require_nonempty_message(qwen_result.content, role="Qwen")
                branch_rows: dict[str, Any] = {}
                for slot, label in ((0, "SAA"), (1, "C")):
                    seed = 100000 + thread_index * 100 + local_turn
                    operation_id = f"development-{label}-{thread.thread_id}-t{local_turn}"
                    prepared, exposure = _development_request(
                        controllers[slot], participant=participant, history=histories[slot], seed=seed,
                        operation_id=operation_id, memory="graph" if slot == 0 else "off",
                        selection_policy="learned-v1" if slot == 0 else "fixed-v2",
                    )
                    development = runtime.execute_development(
                        slot=slot, call_id=operation_id,
                        coordinate={"experiment": EXPERIMENT, "thread": thread.thread_id, "turn": local_turn, "twin": label},
                        request=prepared.request, max_output_tokens=256,
                    )
                    response = require_nonempty_message(str(development.result.get("content", "")), role=f"Gemma {label}")
                    branch_rows[label] = {"response": response, "seed": seed, "exposure": exposure}
                    if slot == 0:
                        exposure_record = {
                            "coordinate": f"{thread.thread_id}:{local_turn}",
                            "eligible_state": bool(controllers[0]._learner_state(prepared.pinned).edge_states),
                            "selected_count": len(prepared.selected),
                            "applied_count": len(prepared.applied),
                            "control_influence": 0,
                            "selected": exposure["selected"],
                            "applied": exposure["applied"],
                            "request": prepared.request.to_dict(),
                        }
                        exposures.append(exposure_record)
                        pilot.publish_artifact("contingent", f"exposure-{thread.thread_id}-{local_turn}.json", exposure_record)
                        extraction = runtime.extract(
                            slot=0, call_id=f"extraction-SAA-{thread.thread_id}-t{local_turn}",
                            coordinate={"experiment": EXPERIMENT, "thread": thread.thread_id, "turn": local_turn, "twin": "SAA"},
                            episode_id=development.operation.episode_id, extractor_host=extractor,
                            max_output_tokens=768, extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
                        )
                        admitted = 0
                        interpretation = "excluded"
                        if extraction.residue is not None:
                            plan = adapter(0, DevelopmentFixture(global_turn, thread.thread_id, participant, f"saa-{thread.thread_id}-{local_turn}"), development, extraction)
                            if plan.request is not None and plan.validator is not None:
                                outcome = runtime.provider_call(
                                    call_id=f"assessment-SAA-{thread.thread_id}-t{local_turn}", role="assessor",
                                    coordinate={"experiment": EXPERIMENT, "thread": thread.thread_id, "turn": local_turn, "twin": "SAA"},
                                    host=assessor, request=plan.request, max_output_tokens=1536,
                                    validator=plan.validator, artifact_category="assessment",
                                )
                                if outcome.validation_error is None:
                                    admitted = plan.publish(outcome.validated)
                                    interpretation = "complete"
                                else:
                                    interpretation = "measurement_unknown"
                                    runtime.publish_interpretation(
                                        slot=0, operation_id=extraction.operation_id, residue=extraction.residue,
                                        observations=(), learner=DevelopmentalLearner(),
                                        development_operation_id=development.operation.operation_id,
                                        assessor_version="p2-assessor-v9",
                                    )
                            else:
                                admitted = plan.publish(None)
                        branch_rows[label].update({"interpretation": interpretation, "admitted": admitted, "trace": _trace(subjects[0].store, development.operation.operation_id)})
                    histories[slot].append((participant, response))
                if not sanity_checked:
                    if branch_rows["SAA"]["response"] != branch_rows["C"]["response"]:
                        raise RuntimeError("INVALID_MATCHING_CONTROL: pre-treatment Gemma calls diverged")
                    pilot.publish_artifact("contingent", "pre-treatment-sanity.json", {"status": "PASS", "seed": branch_rows["SAA"]["seed"], "identical": True})
                    sanity_checked = True
                row = {"thread": thread.thread_id, "turn": local_turn, "global_turn": global_turn, "shared_participant_message": participant, "SAA": branch_rows["SAA"], "C": branch_rows["C"]}
                transcripts.append(row)
                _publish_transcript(pilot, row, f"transcript-{thread.thread_id}-t{local_turn}.json")
                prior_participant = participant
                global_turn += 1
            for slot, label in ((0, "SAA"), (1, "C")):
                create_checkpoint(subjects[slot].store, ROOT / "snapshots" / f"{label}-{thread.thread_id}.sqlite3", checkpoint_id=f"{RUN_ID}-{label}-{thread.thread_id}")

        gate = _development_gate(controllers[0], exposures, transcripts)
        pilot.publish_artifact("contingent", "development-gate.json", gate)
        if not gate["adequate_nontrivial_field"]:
            report = {"status": "INVALID_INSUFFICIENT_DEVELOPMENTAL_FIELD", "development_gate": gate, "historical_evidence_unchanged": True}
            pilot.publish_artifact("contingent", "final-report.json", report)
            pilot.finish(summary=report)
            print(json.dumps(report, indent=2))
            return 2

        # Thread 10 is a frozen read-only conversational readout.  No
        # extraction, assessment, or learner update is performed here.
        checkpoints = {"SAA": ROOT / "snapshots" / "SAA-T09.sqlite3", "C": ROOT / "snapshots" / "C-T09.sqlite3", "M": ROOT / "snapshots" / "SAA-T09.sqlite3"}
        t10 = THREAD_SCHEDULE[9]
        histories = {0: [], 1: []}
        participant = require_nonempty_message(t10.opening, role="Qwen T10 opening")
        t10_rows: list[dict[str, Any]] = []
        prior_participant = None
        for turn in range(development_turns):
            if turn > 0:
                responses = {"A": histories[0][-1][1], "B": histories[1][-1][1]}
                qwen_result = _call(
                    pilot, interloper,
                    build_shared_interloper_request(thread=t10.shared_interloper_spec(), prior_participant=prior_participant, responses=responses, turn=turn),
                    call_id=f"shared-qwen-T10-t{turn}", role="interloper",
                    coordinate={"thread": "T10", "turn": turn}, max_tokens=192,
                )
                participant = require_nonempty_message(qwen_result.content, role="Qwen T10")
            branches: dict[str, Any] = {}
            field_seed = _field_seed(turn)
            for slot, label, checkpoint in ((0, "SAA", checkpoints["SAA"]), (1, "C", checkpoints["C"])):
                seed = 200000 + turn
                prepared = _saa_readout_request(controllers[slot], label=label, probe=participant, seed=seed, field_seed=field_seed if label == "SAA" else None, operation_id=f"t10-prep-{label}-t{turn}")
                outcome = runtime.evaluate(
                    slot=slot, call_id=f"t10-{label}-t{turn}", coordinate={"thread": "T10", "turn": turn, "condition": label},
                    checkpoint=checkpoint, private_snapshot=checkpoint, host=gemma,
                    messages=prepared.request.messages, max_output_tokens=256, seed=seed,
                    parameters=prepared.request.parameters, system=prepared.request.system,
                )
                output = require_nonempty_message(str(outcome.result.get("content", "")), role=f"Gemma T10 {label}")
                branches[label] = {"response": output, "seed": seed, "field_seed": field_seed if label == "SAA" else None, "field_trace": prepared.field_result.to_dict() if prepared.field_result else None, "request": prepared.request.to_dict()}
                histories[slot].append((participant, output))
            row = {"thread": "T10", "turn": turn, "shared_participant_message": participant, "SAA": branches["SAA"], "C": branches["C"]}
            t10_rows.append(row)
            _publish_transcript(pilot, row, f"transcript-T10-t{turn}.json")
            prior_participant = participant

        readouts: list[dict[str, Any]] = []
        for probe_index in range(len(READOUT_PROBES)):
            for repetition in range(READOUT_REPETITIONS):
                readouts.extend(_run_frozen_probe(runtime, pilot, controllers, gemma, checkpoints, probe_index, repetition))
        blinded = _blinded_rows(readouts)
        pilot.publish_artifact("evaluation", "paired-readouts.json", {"rows": readouts, "probes": list(READOUT_PROBES)})
        pilot.publish_artifact("evaluation", "blinded-comparison.json", {"rows": blinded, "stage": "deterministic-observable-only"})
        # This is a bounded post-primary hook.  It records the required
        # consequence operation without fabricating feedback or mutating the
        # primary frozen snapshots; a future adapter may attach an actual
        # external feedback episode here.
        consequence = {"status": "DEFERRED_EXTERNAL_FEEDBACK", "reason": "primary readout is frozen; no synthetic feedback is applied", "primary_snapshots_unchanged": True}
        pilot.publish_artifact("consequence", "subtest.json", consequence)
        report = {
            "status": "VALID_INTERPRETABLE_SAA_AB",
            "contract": contract,
            "development_gate": gate,
            "thread10": t10_rows,
            "readouts": readouts,
            "blinded_comparison": blinded,
            "removal_restoration": {"conditions": ["SAA", "SAA_OFF", "SAA_RESTORED"], "rows": [row for row in readouts if row["condition"] != "C"]},
            "consequence_subtest": consequence,
            "historical_evidence_unchanged": True,
            "accounting": pilot.reservations_report(),
            "limitations": [
                "SAA is a bounded text-mediated graph approximation, not a neural field.",
                "The consequence subtest is deferred rather than supplied synthetic feedback.",
                "No hidden reasoning or personality claim is inferred from observable text.",
            ],
        }
        pilot.publish_artifact("contingent", "final-report.json", report)
        pilot.finish(summary={"status": report["status"], "readouts": len(readouts), "threads": 10})
        (ROOT / "human-report.md").write_text(
            "# SAA ten-thread experiment\n\n"
            "Status: `VALID_INTERPRETABLE_SAA_AB`\n\n"
            f"Development threads: 10; frozen probe rows: {len(readouts)}.\n"
            "C, SAA, removal, and restoration raw outputs and field traces are in the evaluation artifacts.\n",
            encoding="utf-8",
        )
        print(json.dumps({"run_id": RUN_ID, "root": str(ROOT), "status": report["status"], "calls": pilot.reservations_report().get("counts", {})}, indent=2))
        return 0
    except Exception as exc:
        report = {"status": "INVALID_INSTRUMENTATION", "error": f"{type(exc).__name__}: {exc}", "historical_evidence_unchanged": True, "accounting": pilot.reservations_report()}
        pilot.publish_artifact("contingent", "final-report.json", report)
        pilot.finish(summary=report)
        print(json.dumps(report, indent=2))
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-plan", type=Path, help="emit the offline frozen contract")
    parser.add_argument("--execute", action="store_true", help="perform live calls; omitted by default")
    args = parser.parse_args(argv)
    if args.emit_plan is not None:
        from tools.run_p23_saa_ten_thread import emit_plan

        payload = emit_plan(args.emit_plan)
        print(json.dumps({"status": payload["status"], "path": str(args.emit_plan), "provider_calls": 0}, indent=2))
        if not args.execute:
            return 0
    if not args.execute:
        parser.error("live calls are disabled unless --execute is explicit")
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
