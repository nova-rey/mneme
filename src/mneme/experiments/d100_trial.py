# ruff: noqa: E501
"""Contract and evidence helpers for the D100 ten-thread trial.

This module deliberately does not own provider orchestration.  The trial uses
an already validated CompactStore runtime supplied by the caller.  It freezes
the prospective schedule, seeds, probe set, and evidence shape so a runtime
adapter cannot silently change the study while wiring model calls.

The D100 ancestor is a convenient developed parent.  It is never treated as a
normative reference and this module never mutates the source artifact.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ..development.field import FieldConfig, FieldResult
from ..development.learner import (
    EdgeState,
    LearnerState,
    TransitionInput,
    TransitionResult,
    apply_transition,
)
from ..memory.graph import GraphConcept, GraphEdge, GraphRoute
from ..state.compact import CompactStore, CompactStoreError
from ..state.compact_runtime import CompactGraphView, CompactRuntime

TRIAL_VERSION = "d100-compact-introspection-10-v1"
REPORT_NAME = "MNEME_D100_Compact_Ancestor_and_10_Thread_Introspection_Trial_20261002"


@dataclass(frozen=True)
class TrialThread:
    """One frozen prospective conversational thread."""

    number: int
    domain: str
    opening: str
    concerns: str


# These subjects are deliberately broad and heterogeneous.  They are fixed
# before a developed ancestor is inspected and contain no target association.
THREAD_SCHEDULE: tuple[TrialThread, ...] = (
    TrialThread(
        1,
        "water management",
        "I am trying to keep a shared garden useful during a dry week.",
        "limited water, unattended care, and visible signs of trouble",
    ),
    TrialThread(
        2,
        "local travel",
        "I need to plan a short trip when the weather and timing are uncertain.",
        "packing, route changes, and recovery from missed connections",
    ),
    TrialThread(
        3,
        "cooking",
        "I want to improvise dinner from ingredients that do not quite fit together.",
        "substitution, sequencing, and preserving options",
    ),
    TrialThread(
        4,
        "music",
        "Our small ensemble keeps losing its shape when the tempo changes.",
        "timing, repetition, variation, and listening",
    ),
    TrialThread(
        5,
        "repair",
        "A household tool works intermittently and I only have basic supplies.",
        "diagnosis, isolation, and reversible repair",
    ),
    TrialThread(
        6,
        "games",
        "I am designing a simple game where luck should not erase every good decision.",
        "probability, uneven outcomes, and recovery",
    ),
    TrialThread(
        7,
        "visual art",
        "I have too many visual ideas for one small poster.",
        "composition, emphasis, omission, and revision",
    ),
    TrialThread(
        8,
        "coordination",
        "Several people share equipment but their schedules rarely line up.",
        "handoffs, visibility, fairness, and unattended use",
    ),
    TrialThread(
        9,
        "observation",
        "I am trying to keep track of a changing night sky with modest equipment.",
        "calibration, uncertainty, repeated observation, and interpretation",
    ),
    TrialThread(
        10,
        "isolated seasonal community",
        "A small seasonal community must prepare for an uncertain month with limited supplies and changing volunteers.",
        "sequencing, resources, communication, adaptation, and graceful recovery",
    ),
)

FROZEN_PROBES: tuple[str, ...] = (
    "A small team must keep an unfamiliar project usable while people have changing schedules. What would you examine first?",
    "An arrangement must tolerate an interruption without making every earlier effort useless. How would you think about it?",
    "A creative plan has many possible directions but limited attention. What should guide what remains visible?",
    "An unfamiliar process produces uneven results. What would you investigate before changing the whole process?",
)

GEMMA_SEEDS: tuple[int, ...] = (91001, 91002, 91003, 91004)
FIELD_SEEDS: tuple[int, ...] = (92001, 92002, 92003, 92004)
REMOVAL_SEED = 93001
REMOVAL_FIELD_SEED = 94001


def validate_schedule(schedule: tuple[TrialThread, ...] = THREAD_SCHEDULE) -> None:
    """Reject accidental schedule drift before a provider call is possible."""

    if tuple(item.number for item in schedule) != tuple(range(1, 11)):
        raise ValueError("D100 trial requires exactly ten numbered threads")
    if len({item.domain for item in schedule}) != 10:
        raise ValueError("D100 trial domains must be distinct")
    for item in schedule:
        if not item.opening.strip() or not item.concerns.strip():
            raise ValueError(f"thread {item.number} is incomplete")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_ancestor(source: str | Path, destination: str | Path) -> dict[str, Any]:
    """Copy a CompactStore ancestor and verify it can be reopened.

    The source is opened read-only and never replaced.  The destination is
    published atomically through a temporary sibling and then reopened in
    read-only mode.  This is intentionally independent of the live trial.
    """

    source_path = Path(source)
    destination_path = Path(destination)
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("ancestor source and destination must differ")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if destination_path.exists():
        raise FileExistsError(destination_path)
    with CompactStore(source_path, read_only=True) as source_store:
        source_problems = source_store.verify()
        if source_problems:
            raise CompactStoreError(f"ancestor source failed verification: {source_problems}")
        source_digest = source_store.state_digest()
        source_graph = source_store.graph_state()
        source_learner = source_store.learner_state()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    staging = destination_path.with_name(f".{destination_path.name}.staging")
    if staging.exists():
        staging.unlink()
    try:
        shutil.copyfile(source_path, staging)
        with CompactStore(staging, read_only=True) as copied:
            copied_problems = copied.verify()
            if copied_problems:
                raise CompactStoreError(f"copied ancestor failed verification: {copied_problems}")
            if copied.state_digest() != source_digest:
                raise CompactStoreError("ancestor digest changed during copy")
            if copied.graph_state() != source_graph or copied.learner_state() != source_learner:
                raise CompactStoreError("ancestor logical state changed during copy")
        staging.replace(destination_path)
    finally:
        staging.unlink(missing_ok=True)
    return {
        "source": str(source_path),
        "destination": str(destination_path),
        "source_sha256": _sha256(source_path),
        "destination_sha256": _sha256(destination_path),
        "bytes": destination_path.stat().st_size,
        "state_digest": source_digest,
        "verification": "PASS",
        "normative_status": "convenience_developed_ancestor",
    }


def ancestor_equivalence(source: str | Path, copy: str | Path) -> dict[str, Any]:
    """Compare two compact stores without mutating either one."""

    with CompactStore(source, read_only=True) as left, CompactStore(copy, read_only=True) as right:
        left_problems = left.verify()
        right_problems = right.verify()
        graph_equal = left.graph_state() == right.graph_state()
        learner_equal = left.learner_state() == right.learner_state()
        return {
            "source": str(source),
            "copy": str(copy),
            "source_verify": left_problems,
            "copy_verify": right_problems,
            "graph_equal": graph_equal,
            "learner_equal": learner_equal,
            "state_digest_equal": left.state_digest() == right.state_digest(),
            "source_state_digest": left.state_digest(),
            "copy_state_digest": right.state_digest(),
            "pass": not left_problems
            and not right_problems
            and graph_equal
            and learner_equal
            and left.state_digest() == right.state_digest(),
        }


class TrialRuntime(Protocol):
    """Minimal runtime boundary used by the live adapter.

    Implementations own local Gemma/GLiNER/assessor calls and CompactStore
    transactions.  The harness supplies only frozen schedules, matched seeds,
    and artifact coordinates; it never falls back to the historical SQLite
    runtime.
    """

    def run_trial(self, config: TrialConfig) -> Mapping[str, Any]: ...


def _json_value(value: Any, default: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value if value is not None else default


def _graph_objects(
    store: CompactStore,
) -> tuple[tuple[GraphConcept, ...], tuple[GraphEdge, ...], tuple[GraphRoute, ...]]:
    """Decode compact rows into the existing pure graph/field objects."""

    state = store.graph_state()
    concepts = tuple(
        GraphConcept(
            str(row.get("node_key", row.get("concept_key", row.get("key")))),
            str(row.get("label", row.get("normalized_label", ""))),
            str(row.get("kind", "concept")),
            tuple(_json_value(row.get("evidence", row.get("evidence_json")), ())),
            {},
        )
        for row in state["nodes"].values()
    )
    edges = tuple(
        GraphEdge(
            str(row.get("edge_key", row.get("key"))),
            str(row.get("source_key", row.get("source"))),
            str(row.get("target_key", row.get("target"))),
            str(row.get("relationship", "association")),
            tuple(_json_value(row.get("evidence", row.get("evidence_json")), ())),
            {},
        )
        for row in state["edges"].values()
    )
    routes = tuple(
        GraphRoute(
            str(row.get("route_key", row.get("key"))),
            tuple(_json_value(row.get("edge_keys", row.get("edge_keys_json")), ())),
            tuple(_json_value(row.get("evidence", row.get("source_json")), ())),
            {},
        )
        for row in state["routes"].values()
    )
    return concepts, edges, routes


def _learner_from_store(store: CompactStore) -> LearnerState:
    rows: list[EdgeState] = []
    for (edge_key, context), value in store.learner_state().items():
        rows.append(
            EdgeState(
                target_key=edge_key,
                context=context,
                accessibility=int(value.get("accessibility", 0)),
                support=int(value.get("support", 0)),
                consequence=int(value.get("consequence", 0)),
                relevant_opportunities=int(
                    value.get("relevant_opportunities", value.get("opportunity", 0))
                ),
                inactivity_ticks=int(value.get("inactivity_ticks", 0)),
                unsupported_streak=int(value.get("unsupported_streak", 0)),
                raw_occurrence_count=int(value.get("raw_occurrence_count", 0)),
                episode_keys=tuple(sorted(str(item) for item in value.get("episode_keys", []))),
            )
        )
    return LearnerState(edge_states=tuple(sorted(rows, key=lambda item: item.key)))


@dataclass
class CompactTrialBranch:
    """CompactStore-backed graph/learner boundary for one trial branch."""

    store: CompactStore
    field_config: FieldConfig = field(default_factory=lambda: FieldConfig(version="f0-saa-v1"))
    learner: LearnerState = field(init=False)
    runtime: CompactRuntime = field(init=False)

    def __post_init__(self) -> None:
        self.runtime = CompactRuntime(self.store)
        self.learner = self.runtime.learner()

    @property
    def graph(
        self,
    ) -> tuple[tuple[GraphConcept, ...], tuple[GraphEdge, ...], tuple[GraphRoute, ...]]:
        graph = self.runtime.graph()
        return graph.concepts, graph.edges, graph.routes

    def field(
        self,
        query: str,
        *,
        field_seed: int,
        enabled: bool = True,
        adjustments: Mapping[str, int] | None = None,
        expression_adjustments: Mapping[str, int] | None = None,
    ) -> FieldResult:
        return self.runtime.evaluate_saa(
            query,
            field_seed=field_seed,
            config=self.field_config,
            field_adjustments=adjustments,
            expression_adjustments=expression_adjustments,
            enabled=enabled,
        ).field

    def publish_graph(
        self,
        concepts: tuple[GraphConcept, ...],
        edges: tuple[GraphEdge, ...],
        routes: tuple[GraphRoute, ...],
    ) -> int:
        return self.runtime.publish_state(
            CompactGraphView(concepts, edges, routes),
            self.learner,
            operation_id="graph-publication",
        )["graph_revision"]

    def apply(self, transition: TransitionInput) -> TransitionResult:
        result = apply_transition(self.learner, transition)
        self.learner = result.state
        self.runtime.publish_state(
            self.runtime.graph(), self.learner, operation_id=transition.operation_id
        )
        return result


@dataclass(frozen=True)
class TrialConfig:
    """Frozen settings passed to a validated CompactStore runtime."""

    ancestor_path: Path
    output_root: Path
    run_id: str = "d100-introspection-10-20261002"
    schedule: tuple[TrialThread, ...] = THREAD_SCHEDULE
    probes: tuple[str, ...] = FROZEN_PROBES
    gemma_seeds: tuple[int, ...] = GEMMA_SEEDS
    field_seeds: tuple[int, ...] = FIELD_SEEDS
    introspection_version: str = "p3-introspection-v3-live-round-two"
    filing_level: str = "microcall_explicit"
    compact_schema_version: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        validate_schedule(self.schedule)
        if len(self.gemma_seeds) != len(self.field_seeds):
            raise ValueError("matched Gemma and field seed schedules must have equal length")
        if not self.ancestor_path.is_file():
            raise FileNotFoundError(self.ancestor_path)


def validate_trial_evidence(payload: Mapping[str, Any]) -> list[str]:
    """Return missing/invalid terminal evidence fields for readable reports."""

    problems: list[str] = []
    if payload.get("trial_version") != TRIAL_VERSION:
        problems.append("trial_version")
    if payload.get("d100_normative_status") != "convenience_developed_ancestor":
        problems.append("d100_normative_status")
    if not isinstance(payload.get("ancestor_equivalence"), Mapping):
        problems.append("ancestor_equivalence")
    threads = payload.get("threads")
    if not isinstance(threads, list) or sorted(
        int(item.get("thread", 0)) for item in threads if isinstance(item, Mapping)
    ) != list(range(1, 11)):
        problems.append("threads")
    for key in ("I2", "N2"):
        if not isinstance(payload.get(key), Mapping):
            problems.append(key)
    for key in (
        "pre_probes",
        "post_probes",
        "removal_restoration",
        "introspection_summary",
        "persistence",
    ):
        if key not in payload:
            problems.append(key)
    return problems


def render_report(payload: Mapping[str, Any]) -> str:
    """Render a concise human-readable report from machine-readable output."""

    return "\n".join(
        [
            "# MNEME D100 Compact Ancestor and 10-Thread Introspection Trial",
            "",
            f"- Run: `{payload.get('run_id', 'unknown')}`",
            f"- Disposition: **{payload.get('disposition', 'UNSET')}**",
            "- D100 status: reusable developed ancestor for convenience; not a normative model.",
            "- Historical P3 evidence: immutable; no Thread 1–100 rerun.",
            "",
            "## Ancestor and persistence",
            "",
            f"- Ancestor equivalence: `{payload.get('ancestor_equivalence', {}).get('pass', False)}`",
            f"- CompactStore schema: `{payload.get('compact_schema_version', 'unknown')}`",
            f"- State digest: `{payload.get('ancestor_equivalence', {}).get('source_state_digest', 'unknown')}`",
            "",
            "## Trial",
            "",
            "I2 is introspection-enabled and N2 is introspection-disabled. Both are disposable descendants of the same D100 copy, use the same shared participant trajectory, and use matched Gemma/field seeds.",
            "",
            f"- Threads completed: `{len(payload.get('threads', []))}/10`",
            f"- I2 introspection summary: `{json.dumps(payload.get('introspection_summary', {}).get('I2', {}), sort_keys=True)}`",
            f"- N2 introspection summary: `{json.dumps(payload.get('introspection_summary', {}).get('N2', {}), sort_keys=True)}`",
            f"- Removal/restoration: `{payload.get('removal_restoration', {}).get('status', 'UNSET')}`",
            "",
            "## Evidence",
            "",
            "The JSON receipt contains complete coordinate-level transcripts, field traces, reflections, filings, persistence measurements, and matched probe outputs. This report does not treat D100 as a truth or quality reference.",
            "",
        ]
    )


__all__ = [
    "FIELD_SEEDS",
    "FROZEN_PROBES",
    "GEMMA_SEEDS",
    "REMOVAL_FIELD_SEED",
    "REMOVAL_SEED",
    "REPORT_NAME",
    "THREAD_SCHEDULE",
    "TRIAL_VERSION",
    "TrialConfig",
    "TrialRuntime",
    "TrialThread",
    "ancestor_equivalence",
    "copy_ancestor",
    "render_report",
    "validate_schedule",
    "validate_trial_evidence",
]
