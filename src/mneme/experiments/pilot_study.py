"""The fixed, resumable P2.3 pilot schedule.

The pilot plan is deliberately data driven.  :class:`PilotRuntime` remains the
only owner of provider reservations and developmental state transitions; this
module supplies the frozen coordinates and the small amount of orchestration
needed to run them in order.  Semantic extraction, assessment, and publication
are supplied by adapters so this module cannot invent a second interpretation
or learner path.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts import GenerationRequest
from ..development.assessment import (
    ASSESSOR_SCHEMA_VERSION,
    AssessorMonitor,
    AssessorRequest,
    AssessorSource,
    ResolvedAssessment,
    assessor_generation_request,
    validate_and_resolve_assessor_result,
)
from ..development.learner import DevelopmentalLearner, Observation
from ..host import Host
from ..memory.publication import PublicationError
from .evaluation import EvaluationError
from .pilot import PilotError, PilotRun, PilotStatus
from .pilot_runtime import (
    DevelopmentOutcome,
    ExtractionOutcome,
    PilotRuntime,
    PilotRuntimeError,
)

SUBJECT_SLOTS = (0, 1)
EPISODES_PER_SUBJECT = 24
EVALUATION_PROBES = 12
EVALUATION_REPETITIONS = 6
EXPECTED_DEVELOPMENT_CALLS = 48
EXPECTED_EXTRACTION_CALLS = 48
EXPECTED_ASSESSMENT_CALLS = 48
EXPECTED_EVALUATION_CALLS = 144
MAX_EXTRACTION_REPAIRS = 8
MIN_VALID_EXTRACTIONS = 44
MIN_ADMITTED_RELATIONSHIPS = 12


class PilotStudyError(RuntimeError):
    """The fixed P2.3 schedule cannot safely advance."""


@dataclass(frozen=True)
class DevelopmentFixture:
    """One frozen external input in the approved 24-episode fixture."""

    ordinal: int
    family: str
    text: str
    event_root: str
    dependent_recurrence: bool = False
    suppress_practice_reminder: bool = False

    @property
    def coordinate(self) -> dict[str, Any]:
        return {"subject": None, "episode": self.ordinal}


@dataclass(frozen=True)
class EvaluationProbe:
    """One held-out probe, repeated at a fixed coordinate per subject."""

    ordinal: int
    family: str
    text: str


@dataclass(frozen=True)
class PilotSchedule:
    """Immutable fixed schedule shared by both sibling subjects."""

    episodes: tuple[DevelopmentFixture, ...]
    probes: tuple[EvaluationProbe, ...]
    subject_slots: tuple[int, ...] = SUBJECT_SLOTS
    evaluation_repetitions: int = EVALUATION_REPETITIONS

    def __post_init__(self) -> None:
        if self.subject_slots != SUBJECT_SLOTS:
            raise PilotStudyError("P2.3 requires exactly subject slots 0 and 1")
        if len(self.episodes) != EPISODES_PER_SUBJECT:
            raise PilotStudyError("P2.3 requires exactly 24 developmental episodes")
        if len(self.probes) != EVALUATION_PROBES:
            raise PilotStudyError("P2.3 requires exactly 12 evaluation probes")
        if self.evaluation_repetitions != EVALUATION_REPETITIONS:
            raise PilotStudyError("P2.3 requires exactly six repetitions per probe")
        if tuple(item.ordinal for item in self.episodes) != tuple(range(EPISODES_PER_SUBJECT)):
            raise PilotStudyError("development episode ordinals must be 0 through 23")
        if tuple(item.ordinal for item in self.probes) != tuple(range(EVALUATION_PROBES)):
            raise PilotStudyError("evaluation probe ordinals must be 0 through 11")
        roots = {item.ordinal for item in self.episodes if item.event_root != "recurrence"}
        if not {6, 12, 16, 17} <= roots:
            raise PilotStudyError("declared independent event roots are missing")
        if {item.ordinal for item in self.episodes if item.dependent_recurrence} != {4, 7, 10}:
            raise PilotStudyError("dependent recurrence coordinates are not frozen")

    @property
    def development_count(self) -> int:
        return len(self.subject_slots) * len(self.episodes)

    @property
    def extraction_count(self) -> int:
        return self.development_count

    @property
    def assessment_count(self) -> int:
        return self.development_count

    @property
    def evaluation_count(self) -> int:
        return len(self.subject_slots) * len(self.probes) * self.evaluation_repetitions

    @classmethod
    def fixed(cls) -> PilotSchedule:
        """Return the approved natural-language developmental fixture."""

        texts = (
            (
                "parts",
                "I sorted socket wrenches into labeled bins, so finding a repair size "
                "takes less time.",
            ),
            ("garden", "Mulch around the tomatoes helps the soil stay damp on hot afternoons."),
            ("practice", "Playing the slow passage with a metronome made the notes more accurate."),
            (
                "parts",
                "I put spare screws in labeled drawers, which makes small repairs easier to start.",
            ),
            (
                "garden",
                "The mulch kept the garden bed moist overnight, even though the day was dry.",
            ),
            ("practice", "Repeating the difficult measure slowly helped me hit the right notes."),
            (
                "parts",
                "Labeled bins made it quicker to find a socket when a cabinet handle "
                "needed fixing.",
            ),
            (
                "garden",
                "After another hot day, the mulched bed still held moisture for the seedlings.",
            ),
            ("practice", "Daily slow practice improved my accuracy in the final phrase."),
            (
                "parts",
                "Marked workshop trays prevented a search through the whole toolbox for fasteners.",
            ),
            (
                "garden",
                "Mulch reduced evaporation and left the soil below the peppers pleasantly damp.",
            ),
            ("practice", "For this answer I chose not to use the usual practice reminder."),
            (
                "parts",
                "A labeled bin let me grab the correct wrench before the repair had to pause.",
            ),
            (
                "garden",
                "The vegetable patch needed less watering when mulch covered the bare soil.",
            ),
            (
                "practice",
                "The slow scale exercise made the next run through the tune more precise.",
            ),
            ("parts", "Sorting washers by size kept the repair bench orderly and saved time."),
            (
                "garden",
                "A thick mulch layer protected the soil from drying out during the warm week.",
            ),
            ("practice", "A separate careful rehearsal improved my accuracy on the tricky notes."),
            (
                "parts",
                "I located the right bit immediately because every workshop tray had a label.",
            ),
            ("garden", "The mulched bed stayed moist longer than the uncovered bed beside it."),
            ("practice", "Slow repetitions helped the melody settle into more accurate fingering."),
            (
                "parts",
                "Putting matching bolts together in marked bins made the next repair quicker.",
            ),
            ("garden", "The soil under the mulch remained damp after several sunny days."),
            ("practice", "Patient work with a metronome made the difficult passage more accurate."),
        )
        independent = {6, 12, 16, 17}
        dependent = {4, 7, 10}
        episodes = tuple(
            DevelopmentFixture(
                ordinal=index,
                family=family,
                text=text,
                event_root=f"episode-{index}" if index in independent else "recurrence",
                dependent_recurrence=index in dependent,
                suppress_practice_reminder=index == 11,
            )
            for index, (family, text) in enumerate(texts)
        )
        probe_texts = (
            ("chart", "The bar chart shows the second team completed more repairs than the first."),
            ("paper", "Folding the paper along the crease made the sheet easier to carry."),
            ("measurement", "The ruler reading is precise enough to distinguish the two pieces."),
            ("map", "A larger map scale shows a smaller region in greater detail."),
            ("sound", "The sound reflected from the wall and reached the listener again."),
            ("baking", "Yeast produced gas that made the dough rise during baking."),
            ("translation", "The ambiguous phrase can have two different translations."),
            ("shadow", "The afternoon shadow stretched farther as the sun moved lower."),
            ("game", "Coordinating the two moves let the players complete the board-game task."),
            ("meeting", "The group recorded its decision before ending the meeting."),
            ("tide", "The tide arrived later than the travel schedule predicted."),
            ("library", "The librarian sorted the books into their assigned subject sections."),
        )
        probes = tuple(
            EvaluationProbe(index, family, text) for index, (family, text) in enumerate(probe_texts)
        )
        return cls(episodes, probes)

    def development_request(self, episode: DevelopmentFixture) -> GenerationRequest:
        """Build the fresh prompt-local request for one fixture input."""

        return GenerationRequest(({"role": "user", "content": episode.text},))

    def development_coordinate(self, slot: int, episode: DevelopmentFixture) -> dict[str, Any]:
        return {"subject": slot, "episode": episode.ordinal, "family": episode.family}

    def extraction_coordinate(
        self, slot: int, episode: DevelopmentFixture, *, attempt: int
    ) -> dict[str, Any]:
        return {
            "subject": slot,
            "episode": episode.ordinal,
            "family": episode.family,
            "attempt": attempt,
        }

    def assessment_coordinate(self, slot: int, episode: DevelopmentFixture) -> dict[str, Any]:
        return {"subject": slot, "episode": episode.ordinal, "family": episode.family}

    def evaluation_coordinate(
        self, slot: int, probe: EvaluationProbe, repetition: int
    ) -> dict[str, Any]:
        return {
            "subject": slot,
            "probe": probe.ordinal,
            "probe_family": probe.family,
            "repetition": repetition,
        }


@dataclass(frozen=True)
class AssessmentPlan:
    """Provider request plus strict validator and publication adapter."""

    host: Host
    request: GenerationRequest | None
    validator: Callable[[str], Any] | None
    publish: Callable[[Any], int]
    role: str = "assessor"
    semantic_request: AssessorRequest | None = None
    excluded_reason: str | None = None


class ProductionAssessmentAdapter:
    """Build the production assessor request and atomic learner publication.

    This adapter is intentionally narrow: accepted source rows and the
    validated residue determine the candidate; the assessor only supplies
    semantic rows, while ``validate_and_resolve_assessor_result`` derives
    provenance from those immutable source records.
    """

    def __init__(
        self,
        runtime: PilotRuntime,
        assessor_host: Host,
        *,
        memory_exposure: Mapping[int, tuple[Mapping[str, Any], ...]] | None = None,
        replay_ancestry: Mapping[int, tuple[Mapping[str, Any], ...]] | None = None,
    ) -> None:
        self.runtime = runtime
        self.assessor_host = assessor_host
        self.memory_exposure = dict(memory_exposure or {})
        self.replay_ancestry = dict(replay_ancestry or {})

    @staticmethod
    def _sources(
        runtime: PilotRuntime, slot: int, episode_id: str
    ) -> tuple[tuple[AssessorSource, ...], tuple[str, ...], tuple[Mapping[str, Any], ...]]:
        subject = runtime.subjects.get(slot)
        if subject is None:
            raise PilotStudyError(f"no subject for assessment slot {slot}")
        rows = subject.store.connection.execute(
            "SELECT s.source_id,s.ordinal,s.content,s.role,b.purpose,b.origin_source_id "
            "FROM sources s JOIN source_bindings b ON b.source_id=s.source_id "
            "WHERE s.operation_id=(SELECT operation_id FROM episodes WHERE episode_id=?) "
            "ORDER BY s.ordinal,s.source_id",
            (episode_id,),
        ).fetchall()
        if not rows:
            raise PilotStudyError(f"episode has no bound source rows: {episode_id}")
        sources: list[AssessorSource] = []
        current_input: list[str] = []
        replay: list[Mapping[str, Any]] = []
        for index, row in enumerate(rows):
            slot_name = f"s{index}"
            purpose = str(row[4])
            role = "external" if purpose == "external_evidence" else "model_output"
            sources.append(
                AssessorSource(
                    slot_name,
                    role,
                    True,
                    str(row[2]),
                    str(row[0]),
                )
            )
            if role == "external":
                current_input.append(slot_name)
            if purpose == "replayed_context":
                replay.append(
                    {
                        "source_slot": slot_name,
                        "root": str(row[5] or row[0]),
                    }
                )
        return tuple(sources), tuple(current_input), tuple(replay)

    def __call__(
        self,
        slot: int,
        episode: DevelopmentFixture,
        development: DevelopmentOutcome,
        extraction: ExtractionOutcome,
    ) -> AssessmentPlan:
        residue = extraction.residue
        if residue is None:
            raise PilotStudyError("cannot assess an invalid extraction")
        edges = sorted(residue.edge_candidates, key=lambda value: str(value.get("key", "")))
        if not edges:
            reason = "extraction contained no relationship edge"

            def publish_excluded(_value: Any) -> int:
                receipt = self.runtime.publish_interpretation(
                    slot=slot,
                    operation_id=extraction.operation_id,
                    residue=residue,
                    observations=(),
                    learner=DevelopmentalLearner(),
                    development_operation_id=development.operation.operation_id,
                    assessor_version=ASSESSOR_SCHEMA_VERSION,
                )
                self.runtime.pilot.publish_artifact(
                    "assessment",
                    f"assessment-s{slot}-e{episode.ordinal}-excluded.json",
                    {
                        "status": "EXCLUDED",
                        "reason": reason,
                        "operation_id": extraction.operation_id,
                        "publication": receipt.to_dict(),
                    },
                )
                return 0

            return AssessmentPlan(
                self.assessor_host,
                None,
                None,
                publish_excluded,
                excluded_reason=reason,
            )
        edge = edges[0]
        relation = {
            "from": str(edge["from"]),
            "to": str(edge["to"]),
            "relation": str(edge["relationship"]),
        }
        sources, current_input, replay = self._sources(self.runtime, slot, extraction.episode_id)
        required = tuple(source.slot for source in sources)
        request = AssessorRequest(
            candidate=relation,
            sources=sources,
            monitors=(
                AssessorMonitor(
                    "candidate",
                    relation,
                    required,
                    required,
                    tuple(source.slot for source in sources if source.role == "model_output"),
                ),
            ),
            memory_exposure=self.memory_exposure.get(slot, ()),
            replay_ancestry=tuple((*replay, *self.replay_ancestry.get(slot, ()))),
            context={"current_input_source_slots": list(current_input)},
            source_purpose_mask=("external_evidence", "model_output"),
        )
        call_id = f"assessment-s{slot}-e{episode.ordinal}"

        def validate(content: str) -> tuple[ResolvedAssessment, ...]:
            decoded = json.loads(content)
            if not isinstance(decoded, Mapping):
                raise PilotStudyError("assessor result must be a JSON object")
            return validate_and_resolve_assessor_result(request, decoded)

        def publish(value: Any) -> int:
            if not isinstance(value, tuple) or not all(
                isinstance(item, ResolvedAssessment) for item in value
            ):
                raise PilotStudyError("assessor adapter received an invalid resolved result")
            resolved = tuple(value)
            source_by_slot = {source.slot: source for source in request.sources}
            observations: list[Observation] = []
            for item in resolved:
                evidence_slot = item.evidence.source_slot if item.evidence else None
                evidence_source = source_by_slot.get(evidence_slot) if evidence_slot else None
                source_role = (
                    "model_output"
                    if evidence_source and evidence_source.role == "model_output"
                    else "external"
                )
                groups = item.provenance.provenance_group_keys
                observations.append(
                    Observation(
                        target_key=str(edge["key"]),
                        context=request.monitors[0].context,
                        source_role=source_role,
                        dependence=item.provenance.dependence,
                        status=item.status,
                        relation_support=item.relation_support,
                        expression_status=item.expression_status,
                        semantic_schema_version=ASSESSOR_SCHEMA_VERSION,
                        group_key=groups[0] if groups else None,
                        provenance_group_keys=groups,
                        occurrence_key=f"{call_id}:{item.monitor_id}",
                        covered=bool(item.coverage.get("complete")),
                        relevant=True,
                        actual_exposure=False,
                        eligible=item.provenance.credit_eligible,
                        observation_id=f"{call_id}:{item.monitor_id}",
                    )
                )
            receipt = self.runtime.publish_interpretation(
                slot=slot,
                operation_id=extraction.operation_id,
                residue=residue,
                observations=tuple(observations),
                learner=DevelopmentalLearner(),
                development_operation_id=development.operation.operation_id,
                assessor_version=request.assessor_version,
            )
            self.runtime.pilot.publish_artifact(
                "assessment",
                f"{call_id}-resolution.json",
                {
                    "request": request.to_dict(),
                    "resolved": [item.to_dict() for item in resolved],
                    "publication": {
                        "operation_id": receipt.operation_id,
                        "lineage_revision": receipt.lineage_revision,
                        "graph_revision": receipt.graph_revision,
                    },
                },
            )
            return sum(
                item.status == "present" and item.relation_support == "supported"
                for item in resolved
            )

        return AssessmentPlan(
            self.assessor_host,
            assessor_generation_request(request),
            validate,
            publish,
            semantic_request=request,
        )


@dataclass(frozen=True)
class EvaluationPlan:
    """Inputs needed by :meth:`PilotRuntime.evaluate` for one readout."""

    checkpoint: str | Path
    private_snapshot: str | Path
    host: Host
    messages: tuple[Mapping[str, str], ...]
    seed: int | None = None
    parameters: Mapping[str, Any] | None = None
    system: str | None = None


@dataclass(frozen=True)
class PilotStudyReport:
    status: str
    development_completed: int
    extractions_valid: int
    extraction_repairs: int
    assessments_completed: int
    evaluations_completed: int
    admitted_relationships: int
    failure: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "development_completed": self.development_completed,
            "extractions_valid": self.extractions_valid,
            "extraction_repairs": self.extraction_repairs,
            "assessments_completed": self.assessments_completed,
            "evaluations_completed": self.evaluations_completed,
            "admitted_relationships": self.admitted_relationships,
            "engineering_adequate": self.engineering_adequate,
            "failure": self.failure,
        }

    @property
    def engineering_adequate(self) -> bool:
        return (
            self.extractions_valid >= MIN_VALID_EXTRACTIONS
            and self.admitted_relationships >= MIN_ADMITTED_RELATIONSHIPS
            and self.development_completed == EXPECTED_DEVELOPMENT_CALLS
            and self.assessments_completed == EXPECTED_ASSESSMENT_CALLS
            and self.evaluations_completed == EXPECTED_EVALUATION_CALLS
        )


DevelopmentRequestFactory = Callable[[int, DevelopmentFixture], GenerationRequest]
AssessmentFactory = Callable[
    [int, DevelopmentFixture, DevelopmentOutcome, ExtractionOutcome], AssessmentPlan
]
EvaluationFactory = Callable[[int, EvaluationProbe, int], EvaluationPlan]


class PilotStudy:
    """Run the fixed two-sibling P2.3 schedule with durable coordinates."""

    def __init__(
        self,
        pilot: PilotRun,
        runtime: PilotRuntime,
        schedule: PilotSchedule | None = None,
    ):
        self.pilot = pilot
        self.runtime = runtime
        self.schedule = schedule or PilotSchedule.fixed()
        if set(runtime.subjects) != set(self.schedule.subject_slots):
            raise PilotStudyError("runtime subjects do not match the fixed schedule")

    def _existing_repairs(self) -> int:
        report = self.pilot.reservations_report()
        return sum(
            item.get("role") == "development-extraction"
            and isinstance(item.get("coordinate"), Mapping)
            and item["coordinate"].get("attempt") == 1
            for item in report["calls"]
        )

    def _study_progress(self) -> dict[str, Any]:
        reader = getattr(self.pilot, "study_progress", None)
        if not callable(reader):
            return {}
        value = reader()
        return dict(value) if isinstance(value, Mapping) else {}

    def _record_progress(self, **fields: Any) -> None:
        writer = getattr(self.pilot, "record_study_progress", None)
        if callable(writer):
            writer(**fields)

    def _report(
        self,
        *,
        status: str,
        development: int,
        extractions: int,
        repairs: int,
        assessments: int,
        evaluations: int,
        relationships: int,
        failure: str | None = None,
    ) -> PilotStudyReport:
        report = PilotStudyReport(
            status,
            development,
            extractions,
            repairs,
            assessments,
            evaluations,
            relationships,
            failure,
        )
        self.pilot.publish_artifact("receipts", "pilot-study-report.json", report.to_dict())
        return report

    def run(
        self,
        *,
        development_request: DevelopmentRequestFactory | None = None,
        assessment: AssessmentFactory,
        evaluation: EvaluationFactory | None = None,
        stop_after_episodes: int | None = None,
        max_output_tokens: Mapping[str, int] | None = None,
    ) -> PilotStudyReport:
        """Execute or resume the schedule, stopping at the first terminal defect.

        ``assessment`` must construct the production semantic request and a
        publication adapter.  The adapter is invoked only after the returned
        result passes its validator.  A single invalid extraction consumes the
        next fixed repair coordinate; a second invalid result stops the pilot.
        """

        state = self.pilot.status()
        if state["status"] == PilotStatus.QUALIFIED.value:
            self.pilot.begin_pilot()
        elif state["status"] == PilotStatus.PAUSED.value:
            self.pilot.resume()
        elif state["status"] != PilotStatus.RUNNING.value:
            raise PilotStudyError(
                f"pilot must be QUALIFIED, PAUSED, or RUNNING; got {state['status']}"
            )
        request_factory = development_request or (
            lambda _slot, item: self.schedule.development_request(item)
        )
        limits = {
            "development-response": 256,
            "development-extraction": 1_536,
            "development-assessment": 1_536,
            "evaluation": 192,
        }
        if max_output_tokens is not None:
            limits.update({str(key): int(value) for key, value in max_output_tokens.items()})
        progress = self._study_progress()
        completed_development_ids = {
            str(value) for value in progress.get("completed_development_ids", [])
        }
        completed_evaluation_ids = {
            str(value) for value in progress.get("completed_evaluations", [])
        }
        completed_development = int(progress.get("development_completed", 0))
        valid_extractions = int(progress.get("extractions_valid", 0))
        repair_count = max(self._existing_repairs(), int(progress.get("extraction_repairs", 0)))
        assessments = int(progress.get("assessments_completed", 0))
        relationships = int(progress.get("admitted_relationships", 0))
        evaluations = int(progress.get("evaluations_completed", 0))
        processed = 0
        try:
            for slot in self.schedule.subject_slots:
                subject = self.runtime.subjects[slot]
                for episode in self.schedule.episodes:
                    development_id = f"development-s{slot}-e{episode.ordinal}"
                    if development_id in completed_development_ids:
                        continue
                    request = request_factory(slot, episode)
                    development = self.runtime.execute_development(
                        slot=slot,
                        call_id=development_id,
                        coordinate=self.schedule.development_coordinate(slot, episode),
                        request=request,
                        max_output_tokens=limits["development-response"],
                    )
                    completed_development += 1
                    extract_call = f"extraction-s{slot}-e{episode.ordinal}"
                    extraction = self.runtime.extract(
                        slot=slot,
                        call_id=extract_call,
                        coordinate=self.schedule.extraction_coordinate(slot, episode, attempt=0),
                        episode_id=development.operation.episode_id,
                        extractor_host=subject.host,
                        max_output_tokens=limits["development-extraction"],
                    )
                    if extraction.residue is None:
                        if repair_count >= MAX_EXTRACTION_REPAIRS:
                            raise PilotStudyError("finite extraction repair pool is exhausted")
                        repair_count += 1
                        extraction = self.runtime.extract(
                            slot=slot,
                            call_id=f"{extract_call}-repair",
                            coordinate=self.schedule.extraction_coordinate(
                                slot, episode, attempt=1
                            ),
                            episode_id=development.operation.episode_id,
                            extractor_host=subject.host,
                            max_output_tokens=limits["development-extraction"],
                            repair=True,
                        )
                    if extraction.residue is None:
                        raise PilotStudyError(
                            f"extraction failed after one permitted repair: {extract_call}"
                        )
                    valid_extractions += 1
                    plan = assessment(slot, episode, development, extraction)
                    if plan.excluded_reason is not None:
                        relationships += int(plan.publish(None))
                    else:
                        if plan.request is None or plan.validator is None:
                            raise PilotStudyError(
                                "non-excluded assessment plan is missing request or validator"
                            )
                        provider = self.runtime.provider_call(
                            call_id=f"assessment-s{slot}-e{episode.ordinal}",
                            role=plan.role,
                            coordinate=self.schedule.assessment_coordinate(slot, episode),
                            host=plan.host,
                            request=plan.request,
                            max_output_tokens=limits["development-assessment"],
                            validator=plan.validator,
                            artifact_category="assessment",
                        )
                        if provider.validation_error is not None:
                            raise PilotStudyError(
                                "assessment validation failed: "
                                f"assessment-s{slot}-e{episode.ordinal}: "
                                f"{provider.validation_error}"
                            )
                        relationships += int(plan.publish(provider.validated))
                    assessments += 1
                    completed_development_ids.add(development_id)
                    self._record_progress(
                        development_completed=completed_development,
                        extractions_valid=valid_extractions,
                        extraction_repairs=repair_count,
                        assessments_completed=assessments,
                        admitted_relationships=relationships,
                        evaluations_completed=evaluations,
                        completed_development_ids=sorted(completed_development_ids),
                    )
                    processed += 1
                    if stop_after_episodes is not None and processed >= stop_after_episodes:
                        self.pilot.pause("operator pause at accepted developmental boundary")
                        return self._report(
                            status=PilotStatus.PAUSED.value,
                            development=completed_development,
                            extractions=valid_extractions,
                            repairs=repair_count,
                            assessments=assessments,
                            evaluations=evaluations,
                            relationships=relationships,
                        )
            if evaluation is None:
                raise PilotStudyError("evaluation factory is required for the complete pilot")
            for slot in self.schedule.subject_slots:
                for probe in self.schedule.probes:
                    for repetition in range(self.schedule.evaluation_repetitions):
                        evaluation_id = f"evaluation-s{slot}-p{probe.ordinal}-r{repetition}"
                        if evaluation_id in completed_evaluation_ids:
                            continue
                        evaluation_plan = evaluation(slot, probe, repetition)
                        self.runtime.evaluate(
                            slot=slot,
                            call_id=evaluation_id,
                            coordinate=self.schedule.evaluation_coordinate(slot, probe, repetition),
                            checkpoint=evaluation_plan.checkpoint,
                            private_snapshot=evaluation_plan.private_snapshot,
                            host=evaluation_plan.host,
                            messages=evaluation_plan.messages,
                            max_output_tokens=limits["evaluation"],
                            seed=evaluation_plan.seed,
                            parameters=evaluation_plan.parameters,
                            system=evaluation_plan.system,
                        )
                        evaluations += 1
                        completed_evaluation_ids.add(evaluation_id)
                        self._record_progress(
                            development_completed=completed_development,
                            extractions_valid=valid_extractions,
                            extraction_repairs=repair_count,
                            assessments_completed=assessments,
                            admitted_relationships=relationships,
                            evaluations_completed=evaluations,
                            completed_development_ids=sorted(completed_development_ids),
                            completed_evaluations=sorted(completed_evaluation_ids),
                        )
            final = self.pilot.finish(
                summary={
                    "development_completed": completed_development,
                    "valid_extractions": valid_extractions,
                    "extraction_repairs": repair_count,
                    "assessments_completed": assessments,
                    "evaluations_completed": evaluations,
                    "admitted_relationships": relationships,
                }
            )
            return self._report(
                status=final["status"],
                development=completed_development,
                extractions=valid_extractions,
                repairs=repair_count,
                assessments=assessments,
                evaluations=evaluations,
                relationships=relationships,
            )
        except (
            PilotError,
            PilotStudyError,
            PilotRuntimeError,
            PublicationError,
            EvaluationError,
            OSError,
            ValueError,
        ) as exc:
            reason = f"{type(exc).__name__}: {exc}"
            try:
                self.pilot.fail("pilot execution stopped", details={"error": reason})
            except PilotError:
                pass
            return self._report(
                status=PilotStatus.FAILED.value,
                development=completed_development,
                extractions=valid_extractions,
                repairs=repair_count,
                assessments=assessments,
                evaluations=evaluations,
                relationships=relationships,
                failure=reason,
            )


__all__ = [
    "AssessmentPlan",
    "DevelopmentFixture",
    "EvaluationPlan",
    "EvaluationProbe",
    "PilotSchedule",
    "PilotStudy",
    "PilotStudyError",
    "PilotStudyReport",
    "ProductionAssessmentAdapter",
    "EXPECTED_ASSESSMENT_CALLS",
    "EXPECTED_DEVELOPMENT_CALLS",
    "EXPECTED_EVALUATION_CALLS",
    "EXPECTED_EXTRACTION_CALLS",
    "MAX_EXTRACTION_REPAIRS",
    "MIN_ADMITTED_RELATIONSHIPS",
    "MIN_VALID_EXTRACTIONS",
]
