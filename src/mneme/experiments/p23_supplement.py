"""One-shot P2.3 separated-support adequacy supplement.

This is a thin laboratory runner around the existing contingent request
builders, P2.0 runtime, relationships-v1 extractor, assessor, and learner.
It adds no developmental semantics.  The schedule is immutable and the
result is either a recorded consolidation transition or a bounded negative
result.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts import GenerationRequest
from ..host import Host
from ..memory.interpretation import MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION
from ..state.contracts import StoragePermissions
from ..state.snapshots import create_checkpoint
from ..state.storage import SQLiteStore
from .artifacts import ArtifactStore, content_digest
from .contingent import (
    ContingentSchedule,
    ContingentStudy,
    ContingentStudyError,
    ContingentTurn,
)
from .pilot import PilotRun, PilotStatus, host_role_binding
from .pilot_runtime import RuntimeSubject
from .pilot_study import DevelopmentFixture, ProductionAssessmentAdapter

SUPPLEMENT_ID = "p2.3-separated-support-adequacy-20260925"
SUPPLEMENT_CONTRACT_REVISION = 3
SUPPLEMENT_TURNS = 12
SUPPLEMENT_PLANNED_CALLS = 75
SUPPLEMENT_MAX_OUTPUT_TOKENS = 50_000


class SupplementError(RuntimeError):
    """The bounded supplement cannot safely advance."""


@dataclass(frozen=True)
class SupplementSchedule(ContingentSchedule):
    """Frozen one-lineage practical gardening trajectory."""

    @classmethod
    def fixed(cls) -> SupplementSchedule:
        prompts = (
            (
                "I am trying to keep several balcony pots alive through a hot spell, "
                "and I will be away for a weekend. What would you look at first?"
            ),
            (
                "The small containers dry quickly while I am away, but I do not want "
                "to drown the roots before leaving. How would you make the setup less fragile?"
            ),
            (
                "After the same hot afternoon, a deeper ceramic pot stayed damp longer "
                "than a shallow plastic one. I am deciding whether the container setup "
                "matters more than a fixed watering schedule."
            ),
            (
                "The basil gets afternoon sun while the mint is shaded, so the pots are "
                "behaving differently. I am comparing what I should change before the next absence."
            ),
            (
                "A friend suggested using a saucer, but I worry about keeping the roots "
                "too wet. What practical detail would you check before trying that?"
            ),
            (
                "After another hot day, one container was still moist below the surface "
                "while the shallow pot was dry. I am trying to understand what the "
                "arrangement is doing."
            ),
            (
                "I am preparing another planter for a short trip and want a simple check "
                "I can do before leaving without buying much equipment."
            ),
            (
                "The shaded pot and the larger container are differing again, and I need "
                "to decide which change to make first."
            ),
            (
                "I replaced one shallow pot with a deeper container and will watch what "
                "happens during the next hot afternoon."
            ),
            (
                "Before I leave, I need a low-maintenance watering plan that will not "
                "leave the roots soaked."
            ),
            (
                "The new setup stayed damp after a hot afternoon while the old pot needed "
                "water, so I am comparing the two observations."
            ),
            (
                "I am deciding which arrangement to keep for the next absence and what "
                "I should record while I am away."
            ),
        )
        turns = tuple(ContingentTurn(index, "B", prompt) for index, prompt in enumerate(prompts))
        return cls(turns)


def _trace(store: SQLiteStore, operation_id: str) -> list[dict[str, Any]]:
    rows = store.connection.execute(
        "SELECT o.edge_key,o.context,o.source_role,o.dependence,o.covered,"
        "o.actual_exposure,o.evidence_json,u.opportunity,u.delta,u.reason,"
        "u.before_json,u.after_json,v.last_consolidation_opportunity "
        "FROM development_observations o "
        "LEFT JOIN learner_updates u ON u.operation_id=o.operation_id "
        "AND u.edge_key=o.edge_key AND u.context=o.context "
        "LEFT JOIN learner_values v ON v.update_id=u.update_id "
        "WHERE o.operation_id=? ORDER BY o.edge_key,o.context",
        (operation_id,),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        before = json.loads(str(row[10])) if row[10] else None
        after = json.loads(str(row[11])) if row[11] else None
        result.append(
            {
                "source_episode": operation_id,
                "canonical_edge": row[0],
                "context": row[1],
                "source_role": row[2],
                "dependence_root": row[3],
                "covered": bool(row[4]),
                "actual_exposure": bool(row[5]),
                "evidence": json.loads(str(row[6])) if row[6] else {},
                "opportunity": row[7],
                "credited_D": row[8],
                "A_before": None
                if not isinstance(before, Mapping)
                else before.get("accessibility"),
                "A_after": None if not isinstance(after, Mapping) else after.get("accessibility"),
                "S_before": None if not isinstance(before, Mapping) else before.get("support"),
                "S_after": None if not isinstance(after, Mapping) else after.get("support"),
                "consolidation_disposition": row[9],
                "last_consolidation_opportunity": row[12],
            }
        )
    return result


class P23SupplementStudy(ContingentStudy):
    """Execute exactly one fixed one-lineage adequacy trajectory."""

    def __init__(
        self, *args: Any, schedule: SupplementSchedule | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, schedule=schedule or SupplementSchedule.fixed(), **kwargs)
        self.schedule = schedule or SupplementSchedule.fixed()
        # Keep supplemental receipts inside the verified Phase Two contingent
        # artifact category; ArtifactStore intentionally rejects new top-level
        # run directories.
        self.supplement_root = self.pilot.run_path / "contingent"
        self.supplement_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(
        cls,
        lab: Path,
        developing_host: Host,
        interloper_host: Host,
        assessor_host: Host,
        extractor_host: Host,
        evidence_reviewer_host: Host | None = None,
        *,
        run_id: str = "p23-supplement-run-1",
    ) -> P23SupplementStudy:
        lab = Path(lab)
        artifacts = ArtifactStore(lab)
        schedule = SupplementSchedule.fixed()
        experiment = {
            "name": SUPPLEMENT_ID,
            "experiment_name": "p2.3-separated-support-adequacy",
            "contract_revision": SUPPLEMENT_CONTRACT_REVISION,
            "purpose": (
                "one bounded adequacy demonstration of separated live support and consolidation"
            ),
            "historical_p2_3_disposition": "COMPLETED_INADEQUATE",
            "schedule_sha256": content_digest(schedule.to_dict()),
            "relationships_version": MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
            "no_new_condition": True,
        }
        plan = {
            "supplement_id": SUPPLEMENT_ID,
            "schedule": schedule.to_dict(),
            "turn_count": SUPPLEMENT_TURNS,
            "budgets": {
                "planned_calls": SUPPLEMENT_PLANNED_CALLS,
                "max_output_tokens": SUPPLEMENT_MAX_OUTPUT_TOKENS,
                "call_formula": (
                    "3 fit + 12*(interloper + development + extraction + assessment) "
                    "+ at most 12 extraction repairs"
                ),
            },
        }
        bindings = {
            "subjects": [{"slot": 0, "condition": "supplement-interactive"}],
            "checkpoints": {},
            "historical_run_preserved": True,
        }
        artifacts.publish_run(
            experiment=experiment,
            preflight={"status": "OFFLINE_PREPARED", "contract_sha256": content_digest(experiment)},
            study_plan=plan,
            bindings=bindings,
            run_id=run_id,
        )
        role_bindings = {
            "developing": host_role_binding("developing", developing_host),
            "assessor": host_role_binding("assessor", assessor_host),
            "interloper": host_role_binding("interloper", interloper_host),
            "development-response": host_role_binding("development-response", developing_host),
            "development-extraction": host_role_binding("development-extraction", extractor_host),
        }
        pilot = PilotRun(artifacts, run_id)
        pilot.prepare(
            planned_calls=SUPPLEMENT_PLANNED_CALLS,
            max_output_tokens=SUPPLEMENT_MAX_OUTPUT_TOKENS,
            qualification_calls=3,
            pilot_calls=SUPPLEMENT_PLANNED_CALLS - 3,
            metadata={"supplement": SUPPLEMENT_ID, "version": SUPPLEMENT_CONTRACT_REVISION},
            role_bindings=role_bindings,
        )
        path = lab / "subjects" / "p23-supplement.sqlite3"
        store = SQLiteStore(path)
        instance = store.create_root(
            instance_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{SUPPLEMENT_ID}:{run_id}")),
            permissions=StoragePermissions(
                store=True,
                export=True,
                interpret=True,
                recall=True,
                provider_reuse=True,
                learn=True,
            ),
            host_binding=developing_host.fingerprint().to_dict(),
            controller_version="mneme-p2-p23-supplement-v1",
        )
        create_checkpoint(
            store, lab / "ancestors" / "p23-supplement.sqlite3", checkpoint_id=f"{run_id}-ancestor"
        )
        study = cls(
            lab,
            pilot,
            {0: RuntimeSubject(0, store, instance, developing_host)},
            developing_host,
            interloper_host,
            assessor_host,
            extractor_host,
            schedule=schedule,
        )
        # This is the pre-dispatch role audit artifact.  It contains exact
        # provider-visible message arrays but no provider output or secret.
        pairs = [("Earlier participant message", "Earlier Gemma response")]
        gemma_request = study._subject_request(pairs, "Newest participant message", "supplement", 1)
        qwen_request = study._interloper_request("supplement", 1, pairs)
        pilot.publish_artifact(
            "receipts",
            "role-serialization-preflight.json",
            {
                "role_perspective_version": "explicit-model-perspective-v1",
                "gemma_request": gemma_request.to_dict(),
                "qwen_request": qwen_request.to_dict(),
                "assertions": {
                    "gemma_user_is_interloper": gemma_request.messages[-1]["role"] == "user",
                    "gemma_assistant_is_gemma": gemma_request.messages[-2]["role"] == "assistant",
                    "qwen_user_is_gemma": qwen_request.messages[-2]["role"] == "user",
                    "qwen_assistant_is_interloper": qwen_request.messages[-1]["role"]
                    == "assistant",
                },
            },
        )
        return study

    def _publish_supplement_transcript(self, records: list[dict[str, Any]]) -> None:
        lines = [
            "# P2.3 separated-support adequacy supplement transcript",
            "",
            f"Experiment: `{SUPPLEMENT_ID}`  ",
            f"Run: `{self.pilot.run_id}`  ",
            "Condition: `supplement-interactive`",
            "",
            (
                "Exact conversational text is preserved; credentials and provider "
                "headers are excluded."
            ),
            "",
        ]
        for record in records:
            lines.extend(
                [
                    f"## Turn {record['turn']}",
                    "",
                    "**Interloper message**",
                    "",
                    record.get("partner", ""),
                    "",
                    "**Gemma response**",
                    "",
                    record.get("subject", ""),
                    "",
                    f"Development accepted: `{record.get('development_accepted', False)}`  ",
                    f"Interpretation: `{record.get('downstream_status', 'unknown')}`",
                    "",
                ]
            )
            if record.get("interloper_recovery_attempts"):
                lines.extend(
                    [
                        "Interloper recovery attempts: "
                        f"`{record.get('interloper_recovery_attempts')}`",
                        "Initial Interloper failure: "
                        f"`{record.get('interloper_initial_failure', 'unavailable')}`",
                        "",
                    ]
                )
            if record.get("failure_reason"):
                lines.extend([f"Reason: {record['failure_reason']}", ""])
        self.pilot.publish_artifact(
            "contingent", "supplement-transcript.json", {"records": records}
        )
        path = self.supplement_root / "supplement-transcript.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def execute(self) -> dict[str, Any]:
        state = self.pilot.status()
        if state["status"] == PilotStatus.PREPARED.value:
            self.pilot.begin_qualification()
            self.pilot._write_state(
                PilotStatus.QUALIFIED,
                qualification={
                    "status": "PASS",
                    "kind": "reused-approved-assessor-qualification",
                    "live_fit_checks": 0,
                },
            )
            self.pilot.begin_pilot()
        elif state["status"] == PilotStatus.PAUSED.value:
            self.pilot.resume()
        elif state["status"] != PilotStatus.RUNNING.value:
            if state["status"] == PilotStatus.COMPLETE.value:
                return self.pilot.artifacts._read_json(
                    self.pilot.run_path / "receipts" / "p23-supplement-report.json"
                )
            raise SupplementError(f"supplement is not executable: {state['status']}")

        subject = self.subjects[0]
        adapter = ProductionAssessmentAdapter(self.runtime, self.assessor_host)
        pairs: list[tuple[str, str]] = []
        records: list[dict[str, Any]] = []
        traces: list[dict[str, Any]] = []
        environment_failures = 0
        recovery_attempts = 0
        hard_stop_reason: str | None = None
        for turn in self.schedule.turns:
            recovered_interloper = False
            interloper_failure: str | None = None
            request = self._interloper_request(
                "supplement",
                turn.turn,
                pairs,
                initial_prompt=turn.prompt,
                current_prompt=turn.prompt,
                latest_user_message=pairs[-1][1] if pairs else None,
            )
            try:
                partner = self._partner_call("supplement", turn.turn, request)
            except ContingentStudyError as exc:
                if "blank interloper generation" not in str(exc):
                    raise
                environment_failures += 1
                recovery_attempts += 1
                recovered_interloper = True
                interloper_failure = str(exc)
                recovery_request = GenerationRequest(
                    request.messages,
                    system=(request.system or "")
                    + "\n\nRECOVERY: Your previous generation did not contain a "
                    "participant message. Produce one non-empty ordinary conversational "
                    "message for the same participant state. Do not advance the scenario "
                    "or invent an intervening reply.",
                    parameters=dict(request.parameters),
                    seed=request.seed,
                    response_format=request.response_format,
                    run_metadata=dict(request.run_metadata)
                    | {
                        "recovery_attempt": 1,
                        "recovery_of": f"interloper-supplement-t{turn.turn:02d}",
                    },
                )
                try:
                    partner = self._partner_call(
                        "supplement", turn.turn, recovery_request, attempt=1
                    )
                except ContingentStudyError as recovery_exc:
                    hard_stop_reason = (
                        f"empty Interloper output persisted at turn {turn.turn}; "
                        f"one same-coordinate recovery was also unusable: {recovery_exc}"
                    )
                    records.append(
                        {
                            "turn": turn.turn,
                            "chapter": turn.chapter,
                            "partner": "",
                            "subject": "",
                            "operation_id": None,
                            "development_accepted": False,
                            "downstream_status": "invalid_environment_empty_interloper",
                            "trustworthy_interpretation": False,
                            "failure_reason": hard_stop_reason,
                            "extraction_repairs": 0,
                            "interloper_recovery_attempts": 1,
                        }
                    )
                    self._publish_supplement_transcript(records)
                    break
            if hard_stop_reason is not None:
                break
            if not partner.strip():
                hard_stop_reason = f"empty Interloper output at turn {turn.turn}"
                break
            development = self.runtime.execute_development(
                slot=0,
                call_id=f"development-supplement-t{turn.turn:02d}",
                coordinate={"study": SUPPLEMENT_ID, "turn": turn.turn, "role": "development"},
                request=self._subject_request(pairs, partner, "supplement", turn.turn),
                max_output_tokens=384,
            )
            extraction = self.runtime.extract(
                slot=0,
                call_id=f"extraction-supplement-t{turn.turn:02d}",
                coordinate={
                    "study": SUPPLEMENT_ID,
                    "turn": turn.turn,
                    "role": "extraction",
                    "attempt": 0,
                },
                episode_id=development.operation.episode_id,
                extractor_host=self.extractor_host,
                max_output_tokens=768,
                extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
            )
            repairs = 0
            if extraction.residue is None:
                repairs = 1
                extraction = self.runtime.extract(
                    slot=0,
                    call_id=f"extraction-supplement-t{turn.turn:02d}-repair",
                    coordinate={
                        "study": SUPPLEMENT_ID,
                        "turn": turn.turn,
                        "role": "extraction",
                        "attempt": 1,
                    },
                    episode_id=development.operation.episode_id,
                    extractor_host=self.extractor_host,
                    max_output_tokens=768,
                    repair=True,
                    operation_id=extraction.operation_id,
                    extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
                )
            status = "complete"
            failure: str | None = None
            if extraction.residue is not None:
                fixture = DevelopmentFixture(
                    turn.turn, "balcony-plants", partner, f"supplement-event-{turn.turn}"
                )
                plan = adapter(0, fixture, development, extraction)
                if plan.request is None or plan.validator is None:
                    plan.publish(None)
                else:
                    outcome = self.runtime.provider_call(
                        call_id=f"assessment-supplement-t{turn.turn:02d}",
                        role="assessor",
                        coordinate={
                            "study": SUPPLEMENT_ID,
                            "turn": turn.turn,
                            "role": "assessment",
                        },
                        host=plan.host,
                        request=plan.request,
                        max_output_tokens=1536,
                        validator=plan.validator,
                        artifact_category="contingent-assessment",
                    )
                    if outcome.validation_error is not None:
                        status = "measurement_unknown / interpretation_unavailable"
                        failure = outcome.validation_error
                    else:
                        plan.publish(outcome.validated)
                turn_trace = _trace(subject.store, extraction.operation_id)
                traces.extend(turn_trace)
            else:
                status = "measurement_unknown / interpretation_unavailable"
                failure = extraction.validation_error or "extraction unavailable after one repair"
            response = str(development.result.get("content", ""))
            records.append(
                {
                    "turn": turn.turn,
                    "chapter": turn.chapter,
                    "partner": partner,
                    "subject": response,
                    "operation_id": development.operation.operation_id,
                    "development_accepted": True,
                    "downstream_status": status,
                    "trustworthy_interpretation": status == "complete",
                    "failure_reason": failure,
                    "extraction_repairs": repairs,
                    "interloper_recovery_attempts": 1 if recovered_interloper else 0,
                    "interloper_initial_failure": interloper_failure,
                }
            )
            pairs.append((partner, response))
            self._publish_supplement_transcript(records)

        consolidation = [
            item for item in traces if item.get("last_consolidation_opportunity") is not None
        ]
        result = (
            "INVALID"
            if hard_stop_reason is not None
            else "DEMONSTRATED"
            if consolidation
            else "NOT_DEMONSTRATED"
        )
        summary = {
            "experiment": SUPPLEMENT_ID,
            "contract_revision": SUPPLEMENT_CONTRACT_REVISION,
            "run_id": self.pilot.run_id,
            "terminal_result": result,
            "turn_count": len(records),
            "trustworthy_interpretations": sum(
                bool(item["trustworthy_interpretation"]) for item in records
            ),
            "environment_failures": environment_failures,
            "interloper_recovery_attempts": recovery_attempts,
            "hard_stop_reason": hard_stop_reason,
            "systematic_environment_failure": hard_stop_reason is not None,
            "records": records,
            "learner_traces": traces,
            "consolidation_traces": consolidation,
            "relationships_version": MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
            "historical_p2_3_preserved": True,
            "reservations": self.pilot.reservations_report(),
        }
        self.pilot.finish(
            summary={
                "terminal_result": result,
                "turn_count": len(records),
                "consolidation_count": len(consolidation),
            }
        )
        self.pilot.publish_artifact("receipts", "p23-supplement-report.json", summary)
        return summary


__all__ = ["P23SupplementStudy", "SupplementSchedule", "SUPPLEMENT_ID"]
