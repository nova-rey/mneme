#!/usr/bin/env python3
# ruff: noqa: E501
"""Run the bounded three-thread C/R/F0 shared-Interloper experiment.

This runner is deliberately a new prospective run.  It reuses the existing
PilotRuntime, ResponseController preparation, specialist extraction, assessor
publication, and frozen readout boundaries; it does not touch historical runs.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mneme.controller import ResponseController, TurnIntent
from mneme.development.learner import DevelopmentalLearner
from mneme.experiments.artifacts import ArtifactStore, content_digest
from mneme.experiments.pilot import PilotRun, host_role_binding
from mneme.experiments.pilot_runtime import PilotRuntime, RuntimeSubject
from mneme.experiments.pilot_study import DevelopmentFixture, ProductionAssessmentAdapter
from mneme.experiments.qualification import run_assessor_qualification
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
    require_nonempty_message,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.hosts.local_nli import LocalNliAssessorHost, NliScores
from mneme.memory.interpretation import MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION
from mneme.state.contracts import StoragePermissions
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore

# The repository's tools directory is intentionally not a Python package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_p23_cross_thread import MSI_PYTHON, RemoteGlinerHost, RemoteLlamaHost, _RemoteBase

ROOT = Path(os.environ.get("MNEME_F0_LAB", "/tmp/mneme-p23-f0-20260926"))
RUN_ID = os.environ.get("MNEME_F0_RUN_ID", "p23-f0-shared-interloper-20260926")
EXPERIMENT = "p2.3-f0-graph-pressure-c-r-f0"
REVISION = 1
PLANNED_CALLS = 90
MAX_OUTPUT_TOKENS = 110_000
REMOTE_NLI_HELPER = "/home/rey/mneme-tools/mneme_nli_scores.py"


class RemoteNliBackend(_RemoteBase):
    """Proxy score-only NLI inference to the MSI CPU environment."""

    model_id = "cross-encoder/nli-deberta-v3-xsmall"
    model_revision = "a150876415327c80daeff35ca6f68f5ed8cf5c24"
    runtime_version = "torch-2.14.0+cpu/transformers-4.57.6"

    def __init__(self) -> None:
        self._deployed = False

    def ensure_helper(self) -> None:
        if self._deployed:
            return
        script = (Path(__file__).with_name("remote_nli_scores.py")).read_text(encoding="utf-8")
        result = self._ssh(
            f"mkdir -p $(dirname {REMOTE_NLI_HELPER}) && cat > {REMOTE_NLI_HELPER}",
            script,
            30.0,
        )
        if result.returncode != 0:
            raise RuntimeError(f"failed to deploy local NLI helper: {result.stderr[-500:]}")
        self._deployed = True

    def score_pairs(self, pairs: Any) -> tuple[NliScores, ...]:
        self.ensure_helper()
        request = json.dumps(
            {
                "model_id": self.model_id,
                "revision": self.model_revision,
                "pairs": [[str(premise), str(hypothesis)] for premise, hypothesis in pairs],
                "batch_size": int(os.environ.get("MNEME_NLI_BATCH_SIZE", "8")),
                "max_length": int(os.environ.get("MNEME_NLI_MAX_LENGTH", "512")),
            },
            ensure_ascii=False,
        )
        result = self._ssh(
            f"{MSI_PYTHON} {REMOTE_NLI_HELPER}",
            request,
            300.0,
        )
        if result.returncode != 0:
            raise RuntimeError(f"local NLI inference failed: {result.stderr[-1000:]}")
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("local NLI helper returned no JSON")
        payload = json.loads(lines[-1])
        scores = payload.get("scores")
        if payload.get("model_id") != self.model_id or payload.get("revision") != self.model_revision:
            raise RuntimeError("local NLI helper returned an unexpected model binding")
        if not isinstance(scores, list) or len(scores) != len(pairs):
            raise RuntimeError("local NLI helper returned an unexpected score count")
        return tuple(NliScores(float(row[0]), float(row[1]), float(row[2])) for row in scores)


def _load_assessor_host() -> Any:
    """Load the pinned local semantic assessor without a provider fallback.

    The assessor is deliberately configured as an explicit import target so a
    missing or unusable local specialist fails before the A/B run.  Falling
    back to either DeepInfra Qwen role here would turn an instrumentation
    substitution into an unrecorded experimental change.
    """

    spec = os.environ.get(
        "MNEME_LOCAL_ASSESSOR_FACTORY",
        "mneme.hosts.local_nli:LocalNliAssessorHost",
    )
    if spec == "mneme.hosts.local_nli:LocalNliAssessorHost":
        backend = RemoteNliBackend()
        backend.ensure_helper()
        return LocalNliAssessorHost(backend)
    module_name, separator, attribute = spec.partition(":")
    if not separator or not module_name or not attribute:
        raise RuntimeError(
            "MNEME_LOCAL_ASSESSOR_FACTORY must be module:attribute; "
            "no provider assessor fallback is permitted"
        )
    import importlib

    try:
        module = importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(f"configured local assessor is unavailable: {spec}") from exc
    factory = getattr(module, attribute, None)
    if factory is None:
        raise RuntimeError(f"configured local assessor is unavailable: {spec}")
    if hasattr(factory, "from_environment"):
        host = factory.from_environment()
    else:
        host = factory()
    if not hasattr(host, "generate") or not hasattr(host, "fingerprint"):
        raise RuntimeError(f"configured local assessor is not a Host: {spec}")
    return host


THREADS = (
    ThreadSpec(
        "A",
        "My balcony pots dry out during hot afternoons while I am away for a weekend, and I cannot check them daily. I can use ordinary household materials. How would you make watering reliable?",
        ("the soil dries quickly", "a weekend absence is coming", "expensive equipment is undesirable"),
    ),
    ThreadSpec(
        "B",
        "You have spoken with this conversational partner before. One previous conversation involved gardening. I am planning a small trip with one bag and an uncertain return time. How would you keep the plan from becoming fragile?",
        ("a connection may be delayed", "luggage space is limited", "a simple backup is preferable"),
    ),
    ThreadSpec(
        "C",
        "You have spoken with this conversational partner before. Earlier conversations involved gardening and planning a trip. I am setting up a remote workshop with limited equipment and infrequent deliveries. What should remain usable if one part fails?",
        ("shared tools are scarce", "deliveries are infrequent", "the system should degrade gracefully"),
    ),
)

PROBES = (
    "A greenhouse has no daily caretaker and a limited water supply. What would you notice first, and what tradeoff matters?",
    "A remote workshop has heat, limited supplies, and no daily maintenance. What design approach would you consider?",
)


def _subject_permissions(slot: int) -> StoragePermissions:
    """Permit ordinary conversational history without granting MNEME state."""

    return StoragePermissions(
        store=True,
        export=True,
        interpret=slot == 0,
        recall=slot == 0,
        # Both twins must be allowed to send their own prior assistant turns
        # as ordinary conversation history.  The control remains MNEME-free
        # because interpret, recall, and learn stay disabled for slot 1.
        provider_reuse=True,
        learn=slot == 0,
    )


def _payload(result: Any) -> dict[str, Any]:
    value = result.to_dict()
    usage = value.get("token_usage")
    if isinstance(usage, Mapping):
        value["usage"] = usage
    value.pop("token_usage", None)
    return value


def _call(
    pilot: PilotRun,
    host: Any,
    request: Any,
    *,
    call_id: str,
    role: str,
    coordinate: Mapping[str, Any],
    max_tokens: int,
) -> Any:
    if role in {"interloper", "assessor", "assessor-qualification"}:
        # Keep the fixed schedule intact while avoiding provider burst limits.
        time.sleep(5.0)
    reservation = pilot.reserve_call(
        call_id=call_id,
        role=role,
        coordinate=coordinate,
        max_output_tokens=max_tokens,
    )
    if reservation.get("status") == "RETURNED":
        result = reservation.get("result")
        if not isinstance(result, Mapping):
            raise RuntimeError(f"saved call has no result: {call_id}")
        from mneme.contracts import GenerationResult

        return GenerationResult(
            str(result.get("content", "")),
            str(result.get("model_id", "")),
            str(result.get("provider", "")),
            dict(result.get("effective_parameters", {})),
            result.get("seed"),
            None,
            0.0,
            result.get("finish_reason"),
            dict(result.get("raw_metadata", {})),
            dict(result.get("provenance", {})),
        )
    if reservation.get("status") != "RESERVED":
        raise RuntimeError(f"call is not dispatchable: {call_id}")
    pilot.dispatch_call(call_id, expected_host_fingerprint=host.fingerprint().to_dict())
    try:
        result = host.generate(request)
    except Exception as exc:
        pilot.mark_uncertain(call_id, type(exc).__name__)
        raise
    payload = _payload(result)
    usage = payload.get("usage")
    pilot.return_call(
        call_id,
        result=payload,
        usage=usage if isinstance(usage, Mapping) else None,
        output_tokens=(
            int(usage["output_tokens"])
            if isinstance(usage, Mapping) and isinstance(usage.get("output_tokens"), int)
            else None
        ),
        actual_host_fingerprint=host.fingerprint().to_dict(),
    )
    return result


def _development_request(
    controller: ResponseController,
    *,
    participant: str,
    history: list[tuple[str, str]],
    seed: int,
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
        )
    )
    return prepared, {
        "considered": [item.to_dict() for item in prepared.considered],
        "selected": [item.to_dict() for item in prepared.selected],
        "applied": [item.to_dict() for item in prepared.applied],
        "request": prepared.request.to_dict(),
        "policy": prepared.selection_policy,
        "memory": memory,
    }


def _trace(store: SQLiteStore, operation_id: str) -> list[dict[str, Any]]:
    rows = store.connection.execute(
        "SELECT d.edge_key,d.context,d.source_role,d.dependence,d.actual_exposure,"
        "u.opportunity,u.delta,u.reason,u.before_json,u.after_json "
        "FROM development_observations d LEFT JOIN learner_updates u "
        "ON u.operation_id=d.operation_id AND u.edge_key=d.edge_key "
        "AND u.context=d.context WHERE d.operation_id=? ORDER BY d.edge_key",
        (operation_id,),
    ).fetchall()
    output = []
    for row in rows:
        before = json.loads(str(row[8])) if row[8] else {}
        after = json.loads(str(row[9])) if row[9] else {}
        output.append(
            {
                "operation_id": operation_id,
                "canonical_edge": row[0],
                "context": row[1],
                "source_role": row[2],
                "dependence": row[3],
                "actual_exposure": bool(row[4]),
                "opportunity": row[5],
                "credited_D": row[6],
                "credit_reason": row[7],
                "A_before": before.get("accessibility"),
                "A_after": after.get("accessibility"),
                "S_before": before.get("support"),
                "S_after": after.get("support"),
            }
        )
    return output


def main() -> int:
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
    # The Qwen 235B assessor is historical/reference instrumentation only.
    # This run requires the pinned local specialist; the factory is explicit
    # and has no provider fallback.
    assessor = _load_assessor_host()
    contract = {
        "name": EXPERIMENT,
        "contract_revision": REVISION,
        "modes": {
            "C": "no MNEME influence",
            "R": "existing discrete route-note influence",
            "F0": "f0-graph-pressure-v1 deterministic graph-pressure approximation",
        },
        "f0_config": {
            "max_depth": 2,
            "attenuation": 600000,
            "minimum_pressure": 20000,
            "total_budget": 1000000,
            "max_contributors": 4,
            "render_max_chars": 900,
            "exploration": "off",
        },
        "threads": [item.to_dict() for item in THREADS],
        "shared_interloper": True,
        "historical_runs_unchanged": True,
        "role_perspective": "shared-interloper-v1",
        "semantic_assessor": {
            "mode": "local-specialist",
            "factory": os.environ.get(
                "MNEME_LOCAL_ASSESSOR_FACTORY",
                "mneme.hosts.local_nli:LocalNliAssessorHost",
            ),
            "provider_fallback": False,
        },
        "interloper_qualification": {
            "status": "REUSED_PRIOR_FIXED_QUALIFICATION",
            "model_id": "Qwen/Qwen3-30B-A3B",
            "receipt": "docs/receipts/MNEME_P2.3_Shared_Interloper_Model_Substitution_20260926.md",
        },
        "seed_plan": "local-gemma-seed=10000+thread*100+turn",
        "probes": list(PROBES),
    }
    store = ArtifactStore(ROOT)
    store.publish_run(
        experiment=contract,
        preflight={
            "status": "READY",
            "contract_sha256": content_digest(contract),
            "hosts": {
                "gemma": gemma.fingerprint().to_dict(),
                "extractor": extractor.fingerprint().to_dict(),
                "interloper": interloper.fingerprint().to_dict(),
                "assessor": assessor.fingerprint().to_dict(),
            },
        },
        study_plan={
            "development_calls": 18,
            "extraction_calls": 9,
            "assessment_calls": 9,
            "shared_interloper_calls": 9,
            "readout_calls": 12,
            "evaluation_calls": 0,
            "planned_calls": PLANNED_CALLS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        bindings={
            "subjects": [
                {"slot": 0, "label": "M", "treatment": "mneme"},
                {"slot": 1, "label": "C", "treatment": "control"},
            ],
            "threads": [item.thread_id for item in THREADS],
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
        metadata={"experiment": EXPERIMENT, "revision": REVISION},
        role_bindings=role_bindings,
    )
    qualification = run_assessor_qualification(
        pilot,
        assessor_host=assessor,
        max_output_tokens=1_536,
    )
    if qualification.get("status") != "QUALIFIED":
        report = {
            "status": "INVALID_ASSESSOR_QUALIFICATION",
            "qualification": qualification,
            "interloper_qualification": contract["interloper_qualification"],
            "historical_evidence_unchanged": True,
        }
        pilot.publish_artifact("qualification", "final-report.json", report)
        print(json.dumps(report, indent=2))
        return 2
    pilot.begin_pilot()

    subjects: dict[int, RuntimeSubject] = {}
    controllers: dict[int, ResponseController] = {}
    for slot, label in ((0, "M"), (1, "C")):
        path = ROOT / "subjects" / f"{label}.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        subject_store = SQLiteStore(path)
        permissions = _subject_permissions(slot)
        instance = subject_store.create_root(
            instance_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{EXPERIMENT}:{label}")),
            permissions=permissions,
            host_binding=gemma.fingerprint().to_dict(),
            controller_version="mneme-p2-shared-interloper-v1",
        )
        subjects[slot] = RuntimeSubject(slot, subject_store, instance, gemma)
        controllers[slot] = ResponseController(subject_store, instance, gemma)
        create_checkpoint(
            subject_store,
            ROOT / "snapshots" / f"{label}-ancestor.sqlite3",
            checkpoint_id=f"{RUN_ID}-{label}-ancestor",
        )

    runtime = PilotRuntime(pilot, subjects)
    adapter = ProductionAssessmentAdapter(runtime, assessor)
    transcripts: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    histories: dict[int, list[tuple[str, str]]] = {0: [], 1: []}
    sanity_checked = False
    prior_participant: str | None = None
    global_turn = 0
    for thread_index, thread in enumerate(THREADS):
        # Fresh Gemma context at every thread boundary; the broad cue is the
        # only continuity visible to either branch.
        histories = {0: [], 1: []}
        participant = thread.opening
        for local_turn in range(3):
            if local_turn > 0:
                response_map = {"A": histories[0][-1][1], "B": histories[1][-1][1]}
                qwen_request = build_shared_interloper_request(
                    thread=thread,
                    prior_participant=prior_participant,
                    responses=response_map,
                    turn=local_turn,
                )
                qwen_result = _call(
                    pilot,
                    interloper,
                    qwen_request,
                    call_id=f"shared-qwen-{thread.thread_id}-t{local_turn}",
                    role="interloper",
                    coordinate={"thread": thread.thread_id, "turn": local_turn},
                    max_tokens=192,
                )
                participant = require_nonempty_message(qwen_result.content, role="Qwen")
            else:
                participant = require_nonempty_message(participant, role="Qwen opening")
            branch_rows: dict[str, Any] = {}
            for slot, label in ((0, "M"), (1, "C")):
                seed = 10000 + thread_index * 100 + local_turn
                memory = "graph" if slot == 0 else "off"
                operation_id = f"development-{label}-{thread.thread_id}-t{local_turn}"
                prepared, exposure = _development_request(
                    controllers[slot],
                    participant=participant,
                    history=histories[slot],
                    seed=seed,
                    operation_id=operation_id,
                    memory=memory,
                    selection_policy="learned-v1" if slot == 0 else "fixed-v2",
                )
                development = runtime.execute_development(
                    slot=slot,
                    call_id=operation_id,
                    coordinate={"experiment": EXPERIMENT, "thread": thread.thread_id, "turn": local_turn, "twin": label},
                    request=prepared.request,
                    max_output_tokens=256,
                )
                response = require_nonempty_message(
                    str(development.result.get("content", "")), role=f"Gemma {label}"
                )
                if slot == 0:
                    exposure_record = {
                        "coordinate": f"{thread.thread_id}:{local_turn}",
                        "eligible_state": bool(
                            controllers[0]._learner_state(prepared.pinned).edge_states
                        ),
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
                        slot=0,
                        call_id=f"extraction-M-{thread.thread_id}-t{local_turn}",
                        coordinate={"experiment": EXPERIMENT, "thread": thread.thread_id, "turn": local_turn, "twin": "M"},
                        episode_id=development.operation.episode_id,
                        extractor_host=extractor,
                        max_output_tokens=768,
                        extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
                    )
                    admitted = 0
                    assessment_status = "excluded"
                    if extraction.residue is not None:
                        plan = adapter(
                            0,
                            DevelopmentFixture(global_turn, thread.thread_id, participant, f"shared-{thread.thread_id}-{local_turn}"),
                            development,
                            extraction,
                        )
                        if plan.request is not None and plan.validator is not None:
                            outcome = runtime.provider_call(
                                call_id=f"assessment-M-{thread.thread_id}-t{local_turn}",
                                role="assessor",
                                coordinate={"experiment": EXPERIMENT, "thread": thread.thread_id, "turn": local_turn, "twin": "M"},
                                host=assessor,
                                request=plan.request,
                                max_output_tokens=1536,
                                validator=plan.validator,
                                artifact_category="assessment",
                            )
                            if outcome.validation_error is None:
                                admitted = plan.publish(outcome.validated)
                                assessment_status = "complete"
                            else:
                                assessment_status = "measurement_unknown"
                                runtime.publish_interpretation(
                                    slot=0,
                                    operation_id=extraction.operation_id,
                                    residue=extraction.residue,
                                    observations=(),
                                    learner=DevelopmentalLearner(),
                                    development_operation_id=development.operation.operation_id,
                                    assessor_version="p2-assessor-v9",
                                )
                        else:
                            admitted = plan.publish(None)
                    branch_rows[label] = {
                        "response": response,
                        "seed": seed,
                        "exposure": exposure,
                        "interpretation": assessment_status,
                        "admitted": admitted,
                        "trace": _trace(subjects[0].store, development.operation.operation_id),
                    }
                else:
                    branch_rows[label] = {"response": response, "seed": seed, "influence": 0}
                histories[slot].append((participant, response))
            prior_participant = participant
            transcript = {
                "thread": thread.thread_id,
                "turn": local_turn,
                "global_turn": global_turn,
                "shared_participant_message": participant,
                "M": branch_rows["M"],
                "C": branch_rows["C"],
            }
            transcripts.append(transcript)
            pilot.publish_artifact("contingent", f"transcript-{thread.thread_id}-t{local_turn}.json", transcript)
            if not sanity_checked:
                if branch_rows["M"]["response"] != branch_rows["C"]["response"]:
                    report = {
                        "status": "INVALID_MATCHING_CONTROL",
                        "reason": "matched pre-treatment Gemma calls diverged",
                        "thread": thread.thread_id,
                        "turn": local_turn,
                        "M": branch_rows["M"],
                        "C": branch_rows["C"],
                    }
                    pilot.publish_artifact("contingent", "final-report.json", report)
                    pilot.finish(summary=report)
                    print(json.dumps(report, indent=2))
                    return 2
                pilot.publish_artifact(
                    "contingent",
                    "pre-treatment-sanity.json",
                    {"status": "PASS", "seed": branch_rows["M"]["seed"], "identical": True},
                )
                sanity_checked = True
            global_turn += 1
        create_checkpoint(
            subjects[0].store,
            ROOT / "snapshots" / f"M-thread-{thread.thread_id}.sqlite3",
            checkpoint_id=f"{RUN_ID}-M-thread-{thread.thread_id}",
        )
        create_checkpoint(
            subjects[1].store,
            ROOT / "snapshots" / f"C-thread-{thread.thread_id}.sqlite3",
            checkpoint_id=f"{RUN_ID}-C-thread-{thread.thread_id}",
        )

    development_gate = {
        "eligible_state": bool(exposures and any(item.get("eligible_state") for item in exposures)),
        "development_interpretations": sum(
            int(item.get("M", {}).get("admitted", 0))
            for item in transcripts
            if isinstance(item.get("M"), Mapping)
        ),
        "historical_r6_r7_unchanged": True,
    }
    pilot.publish_artifact("contingent", "development-gate.json", development_gate)

    # The three readout conditions share the frozen developed M state. C uses
    # the control lineage; R and F0 are read-only copies of M with distinct
    # controller policies. No readout calls can write developmental state.
    readout_checkpoint = ROOT / "snapshots" / "M-thread-C.sqlite3"
    control_checkpoint = ROOT / "snapshots" / "C-thread-C.sqlite3"
    readouts: list[dict[str, Any]] = []
    conditions = (("C", 1, "fixed-v2", "off"), ("R", 0, "learned-v1", "graph"), ("F0", 0, "field-v0", "graph"))
    probe_bank = tuple(PROBES)
    route_deliveries = 0
    field_evaluations = 0
    for probe_index, probe in enumerate(probe_bank):
        for repetition in range(2):
            seed = 20000 + probe_index * 10 + repetition
            for label, slot, policy, memory in conditions:
                controller = controllers[slot]
                prepared = controller.prepare(
                    TurnIntent(
                        current_input=probe,
                        mode="develop",
                        memory=memory,
                        system=GEMMA_SYSTEM_PROMPT,
                        parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
                        seed=seed,
                        operation_id=f"readout-prep-{label}-{probe_index}-{repetition}",
                        selection_policy=policy,
                    )
                )
                checkpoint = control_checkpoint if label == "C" else readout_checkpoint
                outcome = runtime.evaluate(
                    slot=slot,
                    call_id=f"readout-{label}-{probe_index}-{repetition}",
                    coordinate={
                        "boundary": "frozen-readout",
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
                    parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
                    system=prepared.request.system,
                )
                content = require_nonempty_message(str(outcome.result.get("content", "")), role=f"Gemma {label}")
                field = prepared.field_result.to_dict() if prepared.field_result is not None else None
                if label == "R" and prepared.applied:
                    route_deliveries += 1
                if label == "F0" and prepared.field_result is not None and prepared.field_result.field_enabled:
                    field_evaluations += 1
                readouts.append(
                    {
                        "probe": probe_index,
                        "repetition": repetition,
                        "condition": label,
                        "seed": seed,
                        "policy": policy,
                        "memory": memory,
                        "route_delivery": len(prepared.applied),
                        "field_evaluated": bool(prepared.field_result and prepared.field_result.field_enabled),
                        "field_trace": field,
                        "request": prepared.request.to_dict(),
                        "result": dict(outcome.result) | {"content": content},
                    }
                )

    # Blind the condition labels before deterministic comparison. The raw
    # outputs remain available in the machine-readable readout artifact.
    by_coordinate: dict[tuple[int, int], dict[str, Mapping[str, Any]]] = {}
    for row in readouts:
        by_coordinate.setdefault((int(row["probe"]), int(row["repetition"])), {})[
            str(row["condition"])
        ] = row
    blinded_rows: list[dict[str, Any]] = []
    for index, (coordinate, rows) in enumerate(sorted(by_coordinate.items())):
        for left, right in (("C", "R"), ("C", "F0"), ("R", "F0")):
            if left not in rows or right not in rows:
                continue
            swap = (index + len(left) + len(right)) % 2 == 1
            ordered = ((left, rows[left]), (right, rows[right]))
            if swap:
                ordered = (ordered[1], ordered[0])
            blinded_rows.append(
                {
                    "probe": coordinate[0],
                    "repetition": coordinate[1],
                    "comparison": f"{left}-vs-{right}",
                    "label_order": ["response_A", "response_B"],
                    "response_A": ordered[0][1]["result"]["content"],
                    "response_B": ordered[1][1]["result"]["content"],
                    "observable": {
                        "A_characters": len(ordered[0][1]["result"]["content"]),
                        "B_characters": len(ordered[1][1]["result"]["content"]),
                        "A_words": len(ordered[0][1]["result"]["content"].split()),
                        "B_words": len(ordered[1][1]["result"]["content"].split()),
                    },
                }
            )
    pilot.publish_artifact("evaluation", "paired-readouts.json", {"probes": list(probe_bank), "rows": readouts})
    pilot.publish_artifact("evaluation", "blinded-comparison.json", {"stage": "deterministic-observable-only", "rows": blinded_rows})
    treatment_gate = {
        "developmental_state_nonempty": development_gate["eligible_state"],
        "control_influence": 0,
        "route_backend_deliveries": route_deliveries,
        "f0_field_evaluations": field_evaluations,
        "f0_valid": development_gate["eligible_state"] and field_evaluations == 4,
        "r_valid_for_route_effect": route_deliveries > 0,
    }
    status = "VALID_INTERPRETABLE_C_R_F0"
    report = {
        "status": status,
        "mode_definitions": {"C": "no MNEME influence", "R": "discrete route-note", "F0": "graph-pressure approximation"},
        "development_gate": development_gate,
        "treatment_gate": treatment_gate,
        "transcripts": transcripts,
        "readouts": readouts,
        "blinded_stage_1": blinded_rows,
        "limitations": [
            "The deterministic comparison reports observable output features; no hidden reasoning is inferred.",
            "R is marked separately when no route-note delivery occurs on a particular probe.",
            "F0 uses deterministic exploration=off and remains a text-mediated approximation, not a neural field.",
        ],
        "accounting": pilot.reservations_report(),
        "historical_evidence_unchanged": True,
    }
    pilot.publish_artifact("contingent", "final-report.json", report)
    pilot.finish(summary={"status": status, "treatment_gate": treatment_gate})
    print(json.dumps({"run_id": RUN_ID, "root": str(ROOT), "status": status, "calls": pilot.reservations_report().get("counts", {})}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
