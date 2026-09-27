#!/usr/bin/env python3
# ruff: noqa: E501
"""Execute the frozen ten-thread SAA developmental comparison.

This runner is deliberately prospective.  It uses the frozen contract from
``run_p23_saa_ten_thread`` and the already qualified local Gemma, GLiNER,
DeBERTa, and shared Qwen services.  Historical runs are read-only evidence.
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

from mneme.controller import ResponseController, TurnIntent
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
from mneme.state.contracts import StoragePermissions
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_p23_f0_background_shared_interloper import (  # noqa: E402
    RemoteGlinerHost,
    RemoteLlamaHost,
    _call,
    _load_assessor_host,
    _trace,
)
from tools.run_p23_saa_ten_thread import (  # noqa: E402
    FIELD_SEEDS,
    GEMMA_READOUT_SEEDS,
    READOUT_PROBES,
    SAA_VERSION,
    THREAD_SCHEDULE,
    saa_contract,
    validate_saa_contract,
)

ROOT = Path(os.environ.get("MNEME_SAA_LAB", "/tmp/mneme-p23-saa-ten-thread-20260926"))
RUN_ID = os.environ.get("MNEME_SAA_RUN_ID", "p23-saa-ten-thread-20260926")
DEVELOPMENT_TURNS = 8
READOUT_TURNS = 4
READOUT_REPETITIONS = 3
MAX_OUTPUT_TOKENS = 300_000
PLANNED_CALLS = 380


def _permissions(slot: int) -> StoragePermissions:
    return StoragePermissions(
        store=True,
        export=True,
        interpret=slot == 0,
        recall=slot == 0,
        provider_reuse=True,
        learn=slot == 0,
    )


def _development_request(
    controller: ResponseController,
    *,
    participant: str,
    history: list[tuple[str, str]],
    seed: int,
    field_seed: int,
    operation_id: str,
    memory: str,
    selection_policy: str,
) -> tuple[Any, dict[str, Any]]:
    prepared = controller.prepare(
        TurnIntent(
            current_input=participant,
            mode="develop",
            memory=memory,
            session_messages=tuple(
                {"role": role, "content": content}
                for pair in history[-2:]
                for role, content in (("user", pair[0]), ("assistant", pair[1]))
            ),
            system=GEMMA_SYSTEM_PROMPT,
            parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
            seed=seed,
            operation_id=operation_id,
            selection_policy=selection_policy,
            field_seed=field_seed,
        )
    )
    field = prepared.field_result.to_dict() if prepared.field_result else None
    return prepared, {
        "policy": prepared.selection_policy,
        "memory": memory,
        "field_seed": field_seed,
        "selected": [item.to_dict() for item in prepared.selected],
        "applied": [item.to_dict() for item in prepared.applied],
        "field": field,
        "request": prepared.request.to_dict(),
    }


def _prepare_observe(
    controller: ResponseController,
    *,
    input_text: str,
    history: list[tuple[str, str]],
    seed: int,
    field_seed: int,
    operation_id: str,
    policy: str,
    memory: str,
) -> Any:
    return controller.prepare(
        TurnIntent(
            current_input=input_text,
            mode="observe",
            memory=memory,
            session_messages=tuple(
                {"role": role, "content": content}
                for pair in history[-2:]
                for role, content in (("user", pair[0]), ("assistant", pair[1]))
            ),
            system=GEMMA_SYSTEM_PROMPT,
            parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
            seed=seed,
            operation_id=operation_id,
            selection_policy=policy,
            field_seed=field_seed,
        )
    )


def _nonzero_edges(controller: ResponseController) -> list[Any]:
    pin = controller._pin()
    state = controller._learner_state(pin)
    return [item for item in state.edge_states if item.accessibility > 0 or item.support > 0]


def _measurement_field_check(
    readouts: list[dict[str, Any]],
    probes: list[dict[str, Any]],
    removal: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate SAA fields after development has produced eligible state.

    Development traces legitimately include cold-start coordinates before the
    first eligible association exists.  The treatment gate therefore checks
    actual SAA readouts, probes, and ON/RESTORED removal checks.  The OFF
    removal condition is intentionally field-free and is excluded.
    """

    rows = (
        [row for row in readouts if row.get("condition") == "SAA"]
        + [row for row in probes if row.get("condition") == "SAA"]
        + [
            row
            for row in removal
            if row.get("condition") in {"SAA_ON", "SAA_RESTORED"}
        ]
    )
    invalid: list[dict[str, Any]] = []
    for row in rows:
        field = row.get("field")
        if not isinstance(field, Mapping) or not bool(field.get("field_enabled")):
            invalid.append(
                {"condition": row.get("condition"), "coordinate": row.get("coordinate", row.get("probe"))}
            )
            continue
        try:
            pressure = float(field.get("total_pressure", 0))
        except (TypeError, ValueError):
            pressure = 0.0
        if pressure <= 0:
            invalid.append(
                {
                    "condition": row.get("condition"),
                    "coordinate": row.get("coordinate", row.get("probe")),
                    "total_pressure": pressure,
                }
            )
    return {"checked": len(rows), "invalid": invalid, "valid": bool(rows) and not invalid}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _record_measurement_unknown(
    pilot: PilotRun,
    *,
    call_id: str,
    coordinate: Mapping[str, Any],
    operation_id: str,
    validation_error: str | None,
) -> None:
    """Persist an assessor validation miss without mutating developmental state.

    The raw provider result and validator error are already retained by
    ``PilotRuntime.provider_call``.  This companion receipt makes the
    downstream disposition explicit: the episode remains conversational
    evidence, but it contributes neither learner credit nor absence evidence.
    In particular, do not pass ``None`` to the production publication adapter;
    that adapter correctly accepts only resolved semantic rows.
    """

    pilot.publish_artifact(
        "assessment",
        f"{call_id}-measurement-unknown.json",
        {
            "status": "measurement_unknown / interpretation_unavailable",
            "call_id": call_id,
            "coordinate": dict(coordinate),
            "operation_id": operation_id,
            "validation_error": validation_error,
            "admitted_relationships": 0,
            "learner_credit": 0,
            "absence_evidence": False,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="perform the authorized live run")
    args = parser.parse_args(argv)
    contract = saa_contract()
    if not args.execute:
        validate_saa_contract(contract)
        print(json.dumps({"status": "FROZEN_PLAN_ONLY", "contract_sha256": content_digest(contract), "provider_calls": 0}, indent=2))
        return 0
    validate_saa_contract(contract)
    if DEVELOPMENT_TURNS < 6 or DEVELOPMENT_TURNS > 10:
        raise RuntimeError("developmental runway drifted outside frozen bounds")
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
    store = ArtifactStore(ROOT)
    experiment = {
        "name": contract["name"],
        "contract_revision": contract["contract_revision"],
        "contract": contract,
        "live_runner": "run_p23_saa_ten_thread_live.py",
        "historical_evidence_unchanged": True,
        "model_fingerprints": {
            "gemma": gemma.fingerprint().to_dict(),
            "extractor": extractor.fingerprint().to_dict(),
            "interloper": interloper.fingerprint().to_dict(),
            "assessor": assessor.fingerprint().to_dict(),
        },
    }
    experiment["contract_sha256"] = content_digest(experiment)
    store.publish_run(
        experiment=experiment,
        preflight={"status": "READY", "contract_sha256": experiment["contract_sha256"]},
        study_plan={
            "development_calls": 9 * DEVELOPMENT_TURNS * 2,
            "extraction_calls": 9 * DEVELOPMENT_TURNS,
            "assessment_calls": 9 * DEVELOPMENT_TURNS,
            "shared_interloper_calls": 9 * (DEVELOPMENT_TURNS - 1) + READOUT_TURNS,
            "readout_calls": READOUT_TURNS * 2 + len(READOUT_PROBES) * READOUT_REPETITIONS * 2,
            "removal_restoration_calls": 3,
            "planned_calls": PLANNED_CALLS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        bindings={"subjects": [{"slot": 0, "label": "SAA"}, {"slot": 1, "label": "C"}], "historical_evidence_unchanged": True},
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
        metadata={"experiment": contract["name"], "mode": SAA_VERSION},
        role_bindings=role_bindings,
    )
    qualification = run_assessor_qualification(pilot, assessor_host=assessor, max_output_tokens=1536)
    if qualification.get("status") != "QUALIFIED":
        report = {
            "status": "INVALID_ASSESSOR_QUALIFICATION",
            "qualification": qualification,
            "historical_evidence_unchanged": True,
        }
        pilot.publish_artifact("contingent", "final-report.json", report)
        pilot.finish(summary=report)
        print(json.dumps(report, indent=2))
        return 2
    pilot.begin_pilot()

    subjects: dict[int, RuntimeSubject] = {}
    controllers: dict[int, ResponseController] = {}
    for slot, label in ((0, "SAA"), (1, "C")):
        path = ROOT / "subjects" / f"{label}.sqlite3"
        subject_store = SQLiteStore(path)
        instance = subject_store.create_root(
            instance_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{contract['name']}:{label}")),
            permissions=_permissions(slot),
            host_binding=gemma.fingerprint().to_dict(),
            controller_version="mneme-p2-saa-v1",
        )
        subjects[slot] = RuntimeSubject(slot, subject_store, instance, gemma)
        controllers[slot] = ResponseController(subject_store, instance, gemma)
    runtime = PilotRuntime(pilot, subjects)
    adapter = ProductionAssessmentAdapter(runtime, assessor)
    transcripts: list[dict[str, Any]] = []
    field_traces: list[dict[str, Any]] = []
    histories: dict[int, list[tuple[str, str]]] = {0: [], 1: []}
    global_turn = 0
    # Qualification is intentionally local and deterministic in the live path;
    # no oversized hosted assessor is used.
    prior_participant: str | None = None
    for thread_index, thread in enumerate(THREAD_SCHEDULE[:9]):
        histories = {0: [], 1: []}
        prior_participant = None
        participant = thread.opening
        for turn in range(DEVELOPMENT_TURNS):
            if turn > 0:
                participant = require_nonempty_message(
                    _call(
                        pilot,
                        interloper,
                        build_shared_interloper_request(
                            thread=thread.shared_interloper_spec(),
                            prior_participant=prior_participant,
                            responses={"A": histories[0][-1][1], "B": histories[1][-1][1]},
                            turn=turn,
                        ),
                        call_id=f"qwen-{thread.thread_id}-{turn}",
                        role="interloper",
                        coordinate={"thread": thread.thread_id, "turn": turn},
                        max_tokens=192,
                    ).content,
                    role="Qwen",
                )
            branch: dict[str, Any] = {}
            for slot, label in ((0, "SAA"), (1, "C")):
                seed = 100000 + thread_index * 100 + turn
                field_seed = FIELD_SEEDS[(global_turn + turn) % len(FIELD_SEEDS)] + global_turn
                policy = "field-saa-v1" if slot == 0 else "fixed-v2"
                memory = "graph" if slot == 0 else "off"
                operation_id = f"dev-{label}-{thread.thread_id}-{turn}"
                prepared, exposure = _development_request(
                    controllers[slot], participant=participant, history=histories[slot], seed=seed,
                    field_seed=field_seed, operation_id=operation_id, memory=memory,
                    selection_policy=policy,
                )
                outcome = runtime.execute_development(
                    slot=slot, call_id=operation_id,
                    coordinate={"thread": thread.thread_id, "turn": turn, "twin": label},
                    request=prepared.request, max_output_tokens=256,
                )
                response = require_nonempty_message(str(outcome.result.get("content", "")), role=f"Gemma {label}")
                row: dict[str, Any] = {"response": response, "seed": seed, "exposure": exposure}
                if slot == 0:
                    extraction = runtime.extract(
                        slot=0, call_id=f"extract-{thread.thread_id}-{turn}",
                        coordinate={"thread": thread.thread_id, "turn": turn, "twin": label},
                        episode_id=outcome.operation.episode_id, extractor_host=extractor,
                        max_output_tokens=768, extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
                    )
                    status = "excluded"
                    admitted = 0
                    if extraction.residue is not None:
                        plan = adapter(
                            0, DevelopmentFixture(global_turn, thread.thread_id, participant, f"shared-{thread.thread_id}-{turn}"),
                            outcome, extraction,
                        )
                        if plan.request is not None and plan.validator is not None:
                            assessed = runtime.provider_call(
                                call_id=f"assess-{thread.thread_id}-{turn}", role="assessor",
                                coordinate={"thread": thread.thread_id, "turn": turn}, host=assessor,
                                request=plan.request, max_output_tokens=1536, validator=plan.validator,
                                artifact_category="assessment",
                            )
                            if assessed.validation_error is None:
                                admitted = plan.publish(assessed.validated)
                                status = "complete"
                            else:
                                _record_measurement_unknown(
                                    pilot,
                                    call_id=f"assess-{thread.thread_id}-{turn}",
                                    coordinate={"thread": thread.thread_id, "turn": turn},
                                    operation_id=outcome.operation.operation_id,
                                    validation_error=assessed.validation_error,
                                )
                                status = "measurement_unknown"
                        else:
                            admitted = plan.publish(None)
                    row.update({"interpretation": status, "admitted": admitted, "trace": _trace(subjects[0].store, outcome.operation.operation_id)})
                    if prepared.field_result is not None:
                        field_traces.append({
                            "coordinate": f"{thread.thread_id}:{turn}", "subject": "SAA", "thread": thread.thread_id,
                            "turn": turn, "current_input": participant, "field_seed": field_seed,
                            "gemma_seed": seed, "field": prepared.field_result.to_dict(), "gemma_output": response,
                        })
                branch[label] = row
                histories[slot].append((participant, response))
            prior_participant = participant
            transcript = {"thread": thread.thread_id, "turn": turn, "global_turn": global_turn,
                          "shared_participant_message": participant, "SAA": branch["SAA"], "C": branch["C"]}
            transcripts.append(transcript)
            pilot.publish_artifact("contingent", f"transcript-{thread.thread_id}-{turn}.json", transcript)
            global_turn += 1
    nonzero = _nonzero_edges(controllers[0])
    gate = {
        "nonzero_edge_count": len(nonzero),
        "nonzero_edge_keys": [item.target_key for item in nonzero],
        "conceptual_neighborhood_count": len({item.target_key.split("::", 1)[0] for item in nonzero}),
        "adequate_nontrivial_field": len(nonzero) >= 2,
        "historical_evidence_unchanged": True,
    }
    pilot.publish_artifact("contingent", "development-gate.json", gate)
    if not gate["adequate_nontrivial_field"]:
        report = {"status": "INVALID_INSUFFICIENT_DEVELOPMENTAL_FIELD", "development_gate": gate, "accounting": pilot.reservations_report()}
        pilot.publish_artifact("contingent", "final-report.json", report)
        pilot.finish(summary=report)
        print(json.dumps(report, indent=2))
        return 2
    m_checkpoint = ROOT / "snapshots" / "SAA-developed.sqlite3"
    c_checkpoint = ROOT / "snapshots" / "C-developed.sqlite3"
    create_checkpoint(subjects[0].store, m_checkpoint, checkpoint_id=f"{RUN_ID}-SAA-developed")
    create_checkpoint(subjects[1].store, c_checkpoint, checkpoint_id=f"{RUN_ID}-C-developed")

    # Thread 10 is a frozen initial readout: its state is not learned from.
    thread = THREAD_SCHEDULE[9]
    histories = {0: [], 1: []}
    prior_participant = None
    participant = thread.opening
    readouts: list[dict[str, Any]] = []
    for turn in range(READOUT_TURNS):
        if turn > 0:
            participant = require_nonempty_message(
                _call(
                    pilot, interloper,
                    build_shared_interloper_request(thread=thread.shared_interloper_spec(), prior_participant=prior_participant,
                                                   responses={"A": histories[0][-1][1], "B": histories[1][-1][1]}, turn=turn),
                    call_id=f"qwen-T10-{turn}", role="interloper", coordinate={"thread": "T10", "turn": turn}, max_tokens=192,
                ).content,
                role="Qwen",
            )
        for slot, label, policy, memory in ((0, "SAA", "field-saa-v1", "graph"), (1, "C", "fixed-v2", "off")):
            seed = 81000 + turn
            field_seed = FIELD_SEEDS[turn % len(FIELD_SEEDS)]
            prepared = _prepare_observe(controllers[slot], input_text=participant, history=histories[slot], seed=seed,
                                        field_seed=field_seed, operation_id=f"t10-{label}-{turn}", policy=policy, memory=memory)
            checkpoint = m_checkpoint if slot == 0 else c_checkpoint
            result = runtime.evaluate(slot=slot, call_id=f"readout-T10-{label}-{turn}", coordinate={"thread": "T10", "turn": turn, "condition": label},
                                     checkpoint=checkpoint, private_snapshot=checkpoint, host=gemma, messages=prepared.request.messages,
                                     max_output_tokens=256, seed=seed, parameters=prepared.request.parameters, system=prepared.request.system)
            content = require_nonempty_message(str(result.result.get("content", "")), role=f"Gemma {label}")
            readouts.append({"thread": "T10", "turn": turn, "condition": label, "participant": participant, "seed": seed,
                             "field_seed": field_seed, "field": prepared.field_result.to_dict() if prepared.field_result else None,
                             "payload": prepared.request.system, "output": content})
            histories[slot].append((participant, content))
        prior_participant = participant
    probes: list[dict[str, Any]] = []
    for probe_index, probe in enumerate(READOUT_PROBES):
        for repetition, seed in enumerate(GEMMA_READOUT_SEEDS):
            for slot, label, policy, memory in ((0, "SAA", "field-saa-v1", "graph"), (1, "C", "fixed-v2", "off")):
                field_seed = FIELD_SEEDS[(probe_index + repetition) % len(FIELD_SEEDS)]
                prepared = _prepare_observe(controllers[slot], input_text=probe, history=[], seed=seed, field_seed=field_seed,
                                            operation_id=f"probe-{label}-{probe_index}-{repetition}", policy=policy, memory=memory)
                checkpoint = m_checkpoint if slot == 0 else c_checkpoint
                result = runtime.evaluate(slot=slot, call_id=f"probe-{label}-{probe_index}-{repetition}",
                                         coordinate={"probe": probe_index, "repetition": repetition, "condition": label}, checkpoint=checkpoint,
                                         private_snapshot=checkpoint, host=gemma, messages=prepared.request.messages, max_output_tokens=256,
                                         seed=seed, parameters=prepared.request.parameters, system=prepared.request.system)
                content = require_nonempty_message(str(result.result.get("content", "")), role=f"Gemma {label}")
                probes.append({"probe": probe_index, "repetition": repetition, "condition": label, "prompt": probe, "seed": seed,
                               "field_seed": field_seed, "field": prepared.field_result.to_dict() if prepared.field_result else None, "output": content})
    # One bounded removal/restoration coordinate, using the same frozen state,
    # input, field seed, and host seed.  This is a read-only causal check.
    removal: list[dict[str, Any]] = []
    probe = READOUT_PROBES[0]
    for label, policy, memory in (("SAA_ON", "field-saa-v1", "graph"), ("SAA_OFF", "fixed-v2", "off"), ("SAA_RESTORED", "field-saa-v1", "graph")):
        seed, field_seed = 82001, FIELD_SEEDS[0]
        prepared = _prepare_observe(controllers[0], input_text=probe, history=[], seed=seed, field_seed=field_seed,
                                    operation_id=f"removal-{label}", policy=policy, memory=memory)
        result = runtime.evaluate(slot=0, call_id=f"removal-{label}", coordinate={"removal": label}, checkpoint=m_checkpoint,
                                  private_snapshot=m_checkpoint, host=gemma, messages=prepared.request.messages, max_output_tokens=256,
                                  seed=seed, parameters=prepared.request.parameters, system=prepared.request.system)
        content = require_nonempty_message(str(result.result.get("content", "")), role=label)
        removal.append({"condition": label, "seed": seed, "field_seed": field_seed, "field": prepared.field_result.to_dict() if prepared.field_result else None, "output": content})

    pilot.publish_artifact("contingent", "transcripts.json", {"rows": transcripts})
    pilot.publish_artifact("evaluation", "saa-field-traces.json", {"rows": field_traces})
    pilot.publish_artifact("evaluation", "thread10-readouts.json", {"rows": readouts})
    pilot.publish_artifact("evaluation", "heldout-probes.json", {"rows": probes, "probe_bank": list(READOUT_PROBES)})
    pilot.publish_artifact("evaluation", "removal-restoration.json", {"rows": removal})
    by_coord: dict[tuple[int, int], dict[str, str]] = {}
    for row in probes:
        by_coord.setdefault((int(row["probe"]), int(row["repetition"])), {})[str(row["condition"])] = str(row["output"])
    comparisons = []
    for key, values in sorted(by_coord.items()):
        if "SAA" in values and "C" in values:
            comparisons.append({"probe": key[0], "repetition": key[1], "label_order": ["response_A", "response_B"],
                                "response_A": values["SAA"], "response_B": values["C"], "different": values["SAA"] != values["C"]})
    pilot.publish_artifact("evaluation", "blinded-stage1.json", {"stage": "mechanical-observable", "rows": comparisons})
    field_check = _measurement_field_check(readouts, probes, removal)
    valid_field = bool(field_check["valid"])
    report = {
        "status": "VALID_INTERPRETABLE_C_SAA" if valid_field else "INVALID_ZERO_FIELD_PRESSURE",
        "mode_definitions": {"C": "vanilla/no MNEME", "SAA": SAA_VERSION},
        "development_gate": gate,
        "treatment_gate": {"SAA_state_nonzero": bool(nonzero), "SAA_development_field_coordinates": len(field_traces), "SAA_measurement_field_check": field_check, "SAA_nonzero_pressure": valid_field, "control_influence": 0},
        "transcript_count": len(transcripts),
        "thread10_readouts": readouts,
        "probe_comparisons": comparisons,
        "removal_restoration": removal,
        "consequence_subtest": {"status": "deferred", "reason": "no primary-state mutation after frozen measurement"},
        "sibling_check": {"status": "deferred", "reason": "bounded ten-thread scope"},
        "accounting": pilot.reservations_report(),
        "historical_evidence_unchanged": True,
    }
    pilot.publish_artifact("contingent", "final-report.json", report)
    pilot.finish(summary={"status": report["status"], "treatment_gate": report["treatment_gate"]})
    _write_json(ROOT / "terminal-report.json", report)
    print(json.dumps({"run_id": RUN_ID, "root": str(ROOT), "status": report["status"], "calls": report["accounting"].get("counts", {})}, indent=2))
    return 0 if report["status"].startswith("VALID_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
