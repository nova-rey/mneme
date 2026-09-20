"""Pure, replayable Phase Two learner transitions.

The learner in this module is deliberately independent of SQLite, hosts,
wall-clock time, and controller code.  A caller supplies an immutable state
and one fully described terminal operation; the returned state is a new value.
This keeps arithmetic and attribution auditable before it is connected to the
durable publication boundary.

All numerical values are fixed-point integers at :data:`FIXED_SCALE`.  The
public dataclasses are intentionally small and JSON-serialisable so a caller
can persist the input, output, and exact before/after state around this pure
transition.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Literal

FIXED_SCALE = 1_000_000
FIXED_ONE = FIXED_SCALE
POOL = 80_000
LIFETIME_CAP = 120_000
INDUCED_CAP = 10_000
ROLLING_CAP = 200_000
OPPORTUNITY_CAP = 160_000
CONSEQUENCE_STEP = 50_000
CONSEQUENCE_EXPOSURE_CAP = 100_000
CONSEQUENCE_ROLLING_CAP = 100_000


class LearnerError(ValueError):
    """The pure learner input is malformed or outside its contract."""


class SourceRole(StrEnum):
    EXTERNAL = "external"
    MODEL_OUTPUT = "model_output"


class ObservationStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class Dependence(StrEnum):
    EXTERNAL_SUPPORTED = "external_supported"
    CURRENT_INPUT_ECHO = "current_input_echo"
    REPLAY_LINKED = "replay_linked"
    EXPOSURE_LINKED = "exposure_linked"
    NO_IDENTIFIED_LINK = "no_identified_link"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    DUPLICATE = "duplicate"


class TerminalDisposition(StrEnum):
    ACCEPTED = "accepted"
    EXCLUDED = "excluded"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    PENDING = "pending"


def to_fixed(value: int | float | str | Decimal) -> int:
    """Convert a decimal value to fixed point by truncating toward zero."""

    if isinstance(value, bool):
        raise LearnerError("boolean is not a fixed-point value")
    try:
        decimal = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise LearnerError(f"invalid fixed-point value: {value!r}") from exc
    if not decimal.is_finite():
        raise LearnerError("fixed-point values must be finite")
    return int(decimal * FIXED_SCALE)


def from_fixed(value: int) -> Decimal:
    """Return a fixed-point integer as an exact :class:`Decimal`."""

    _validate_fixed(value, field="value")
    return Decimal(value) / Decimal(FIXED_SCALE)


def _validate_fixed(value: int, *, field: str, minimum: int = 0, maximum: int = FIXED_ONE) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LearnerError(f"{field} must be an integer fixed-point value")
    if not minimum <= value <= maximum:
        raise LearnerError(f"{field} is outside [{minimum}, {maximum}]")


def _mul_div(value: int, numerator: int, denominator: int) -> int:
    """Multiply and divide, truncating toward zero for either sign."""

    if denominator <= 0:
        raise LearnerError("denominator must be positive")
    product = value * numerator
    return product // denominator if product >= 0 else -((-product) // denominator)


def _clip(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _as_role(value: SourceRole | str) -> SourceRole:
    try:
        if value == "model":
            value = SourceRole.MODEL_OUTPUT
        return value if isinstance(value, SourceRole) else SourceRole(value)
    except ValueError as exc:
        raise LearnerError(f"unsupported source role: {value!r}") from exc


def _as_status(value: ObservationStatus | str) -> ObservationStatus:
    try:
        return value if isinstance(value, ObservationStatus) else ObservationStatus(value)
    except ValueError as exc:
        raise LearnerError(f"unsupported observation status: {value!r}") from exc


def _as_dependence(value: Dependence | str) -> Dependence:
    try:
        return value if isinstance(value, Dependence) else Dependence(value)
    except ValueError as exc:
        raise LearnerError(f"unsupported dependence category: {value!r}") from exc


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Observation:
    """One source-bound monitored occurrence supplied to the pure transition."""

    target_key: str = ""
    context: str = "general"
    source_role: SourceRole | str = SourceRole.EXTERNAL
    dependence: Dependence | str = Dependence.EXTERNAL_SUPPORTED
    status: ObservationStatus | str = ObservationStatus.PRESENT
    group_key: str | None = None
    occurrence_key: str | None = None
    covered: bool = True
    relevant: bool = True
    actual_exposure: bool = False
    eligible: bool = True
    edge_key: str | None = None
    observation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.target_key and self.edge_key:
            object.__setattr__(self, "target_key", self.edge_key)
        if not self.target_key or not isinstance(self.target_key, str):
            raise LearnerError("observation target_key must be non-empty")
        if not self.context or not isinstance(self.context, str):
            raise LearnerError("observation context must be non-empty")
        if self.source_role == "model":
            object.__setattr__(self, "source_role", SourceRole.MODEL_OUTPUT)
        _as_role(self.source_role)
        _as_dependence(self.dependence)
        _as_status(self.status)
        if self.group_key is not None and not self.group_key:
            raise LearnerError("group_key must be non-empty when supplied")
        if self.occurrence_key is not None and not self.occurrence_key:
            raise LearnerError("occurrence_key must be non-empty when supplied")
        if self.occurrence_key is None and self.observation_id is not None:
            object.__setattr__(self, "occurrence_key", self.observation_id)

    @property
    def key(self) -> tuple[str, str]:
        return (self.target_key, self.context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_key": self.target_key,
            "edge_key": self.target_key,
            "context": self.context,
            "source_role": _as_role(self.source_role).value,
            "dependence": _as_dependence(self.dependence).value,
            "status": _as_status(self.status).value,
            "group_key": self.group_key,
            "occurrence_key": self.occurrence_key,
            "covered": self.covered,
            "relevant": self.relevant,
            "actual_exposure": self.actual_exposure,
            "eligible": self.eligible,
        }


@dataclass(frozen=True)
class ConsequenceAssessment:
    """One explicit, attributable contextual consequence assessment."""

    operation_id: str
    route_key: str
    context: str = "general"
    direction: Literal[-1, 1] = 1
    exposure_id: str | None = None
    outcome: Literal["known", "unknown"] = "known"
    relevant: bool = True
    opportunity: int | None = None

    def __post_init__(self) -> None:
        if not self.operation_id or not self.route_key or not self.context:
            raise LearnerError("consequence identity fields must be non-empty")
        if self.direction not in (-1, 1):
            raise LearnerError("consequence direction must be -1 or 1")
        if self.outcome not in ("known", "unknown"):
            raise LearnerError("consequence outcome must be known or unknown")
        if self.exposure_id is not None and not self.exposure_id:
            raise LearnerError("exposure_id must be non-empty when supplied")
        if self.opportunity is not None and self.opportunity < 0:
            raise LearnerError("consequence opportunity cannot be negative")

    @property
    def key(self) -> tuple[str, str]:
        return (self.route_key, self.context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "route_key": self.route_key,
            "context": self.context,
            "direction": self.direction,
            "exposure_id": self.exposure_id,
            "outcome": self.outcome,
            "relevant": self.relevant,
            "opportunity": self.opportunity,
        }


@dataclass(frozen=True)
class TransitionInput:
    """A terminal operation consumed by :func:`apply_transition`."""

    operation_id: str
    observations: tuple[Observation, ...] = ()
    terminal_disposition: TerminalDisposition | str = TerminalDisposition.ACCEPTED
    terminal: bool = True
    modeled_advance_ticks: int = 0
    advance_targets: tuple[tuple[str, str], ...] = ()
    consequences: tuple[ConsequenceAssessment, ...] = ()

    def __post_init__(self) -> None:
        if not self.operation_id:
            raise LearnerError("operation_id must be non-empty")
        disposition = (
            self.terminal_disposition
            if isinstance(self.terminal_disposition, TerminalDisposition)
            else TerminalDisposition(self.terminal_disposition)
        )
        if disposition is TerminalDisposition.PENDING and self.terminal:
            raise LearnerError("pending operation cannot be terminal")
        if self.modeled_advance_ticks < 0:
            raise LearnerError("modeled_advance_ticks cannot be negative")
        if self.modeled_advance_ticks and disposition is not TerminalDisposition.ACCEPTED:
            raise LearnerError("modeled advance must use an accepted terminal operation")
        for target, context in self.advance_targets:
            if not target or not context:
                raise LearnerError("advance target and context must be non-empty")

    @property
    def disposition(self) -> TerminalDisposition:
        return (
            self.terminal_disposition
            if isinstance(self.terminal_disposition, TerminalDisposition)
            else TerminalDisposition(self.terminal_disposition)
        )


@dataclass(frozen=True)
class CreditWindow:
    opportunity: int
    amount: int


@dataclass(frozen=True)
class EdgeState:
    """Materialized learner state for one canonical edge/context."""

    target_key: str = "legacy"
    context: str = "general"
    accessibility: int = 0
    support: int = 0
    consequence: int = 0
    relevant_opportunities: int = 0
    inactivity_ticks: int = 0
    lifetime_by_group: tuple[tuple[str, int], ...] = ()
    induced_by_group: tuple[tuple[str, int], ...] = ()
    rolling_credits: tuple[CreditWindow, ...] = ()
    last_consolidation_opportunity: int | None = None
    raw_occurrence_count: int = 0

    def __post_init__(self) -> None:
        if not self.target_key or not self.context:
            raise LearnerError("edge state identity must be non-empty")
        _validate_fixed(self.accessibility, field="accessibility")
        _validate_fixed(self.support, field="support")
        if not -250_000 <= self.consequence <= 250_000:
            raise LearnerError("edge consequence is outside [-.25, .25]")
        if min(
            self.relevant_opportunities,
            self.inactivity_ticks,
            self.raw_occurrence_count,
        ) < 0:
            raise LearnerError("edge counters cannot be negative")
        for name, values in (
            ("lifetime_by_group", self.lifetime_by_group),
            ("induced_by_group", self.induced_by_group),
        ):
            previous: str | None = None
            for key, amount in values:
                if not key or (previous is not None and key <= previous):
                    raise LearnerError(f"{name} must be sorted and unique")
                _validate_fixed(amount, field=f"{name}[{key}]")
                previous = key
        previous_opportunity = -1
        for item in self.rolling_credits:
            if item.opportunity <= previous_opportunity or item.amount < 0:
                raise LearnerError("rolling credits must be ordered and non-negative")
            _validate_fixed(item.amount, field="rolling credit")
            previous_opportunity = item.opportunity
        if (
            self.last_consolidation_opportunity is not None
            and self.last_consolidation_opportunity < 0
        ):
            raise LearnerError("last consolidation opportunity cannot be negative")

    @property
    def key(self) -> tuple[str, str]:
        return (self.target_key, self.context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_key": self.target_key,
            "context": self.context,
            "accessibility": self.accessibility,
            "support": self.support,
            "consequence": self.consequence,
            "relevant_opportunities": self.relevant_opportunities,
            "inactivity_ticks": self.inactivity_ticks,
            "lifetime_by_group": {key: amount for key, amount in self.lifetime_by_group},
            "induced_by_group": {key: amount for key, amount in self.induced_by_group},
            "rolling_credits": [
                {"opportunity": item.opportunity, "amount": item.amount}
                for item in self.rolling_credits
            ],
            "last_consolidation_opportunity": self.last_consolidation_opportunity,
            "raw_occurrence_count": self.raw_occurrence_count,
        }


@dataclass(frozen=True)
class RouteState:
    """Contextual consequence state for one canonical route/context."""

    route_key: str
    context: str = "general"
    consequence: int = 0
    by_exposure: tuple[tuple[str, int], ...] = ()
    rolling_consequences: tuple[CreditWindow, ...] = ()
    applied_assessments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.route_key or not self.context:
            raise LearnerError("route state identity must be non-empty")
        if not -250_000 <= self.consequence <= 250_000:
            raise LearnerError("consequence is outside [-.25, .25]")
        previous: str | None = None
        for key, amount in self.by_exposure:
            if not key or (previous is not None and key <= previous):
                raise LearnerError("by_exposure must be sorted and unique")
            _validate_fixed(amount, field=f"by_exposure[{key}]")
            previous = key
        previous_opportunity = -1
        for item in self.rolling_consequences:
            if item.opportunity <= previous_opportunity or item.amount < 0:
                raise LearnerError("rolling consequences must be ordered")
            _validate_fixed(item.amount, field="rolling consequence")
            previous_opportunity = item.opportunity
        if tuple(sorted(set(self.applied_assessments))) != self.applied_assessments:
            raise LearnerError("applied assessments must be sorted and unique")

    @property
    def key(self) -> tuple[str, str]:
        return (self.route_key, self.context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_key": self.route_key,
            "context": self.context,
            "consequence": self.consequence,
            "by_exposure": {key: amount for key, amount in self.by_exposure},
            "rolling_consequences": [
                {"opportunity": item.opportunity, "amount": item.amount}
                for item in self.rolling_consequences
            ],
            "applied_assessments": list(self.applied_assessments),
        }


@dataclass(frozen=True)
class LearnerState:
    """Immutable state accepted by and returned from pure transitions."""

    edge_states: tuple[EdgeState, ...] = ()
    route_states: tuple[RouteState, ...] = ()
    global_opportunity: int = 0
    applied_operations: tuple[str, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        edge_keys = [item.key for item in self.edge_states]
        route_keys = [item.key for item in self.route_states]
        if edge_keys != sorted(set(edge_keys)):
            raise LearnerError("edge states must be sorted and unique")
        if route_keys != sorted(set(route_keys)):
            raise LearnerError("route states must be sorted and unique")
        if self.global_opportunity < 0:
            raise LearnerError("global opportunity cannot be negative")
        if tuple(sorted(set(self.applied_operations))) != self.applied_operations:
            raise LearnerError("applied operations must be sorted and unique")

    @classmethod
    def empty(cls) -> LearnerState:
        return cls()

    def edge(self, target_key: str, context: str = "general") -> EdgeState:
        key = (target_key, context)
        for item in self.edge_states:
            if item.key == key:
                return item
        return EdgeState(target_key, context)

    def route(self, route_key: str, context: str = "general") -> RouteState:
        key = (route_key, context)
        for item in self.route_states:
            if item.key == key:
                return item
        return RouteState(route_key, context)

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "global_opportunity": self.global_opportunity,
            "edge_states": [item.to_dict() for item in self.edge_states],
            "route_states": [item.to_dict() for item in self.route_states],
            "applied_operations": list(self.applied_operations),
        }


@dataclass(frozen=True)
class Contribution:
    target_key: str
    context: str
    source_role: str
    group_key: str
    dependence: str
    proposed: int
    awarded: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_key": self.target_key,
            "context": self.context,
            "source_role": self.source_role,
            "group_key": self.group_key,
            "dependence": self.dependence,
            "proposed": self.proposed,
            "awarded": self.awarded,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EdgeUpdate:
    target_key: str
    context: str
    before: EdgeState
    after: EdgeState
    credited: int
    retention: str | None
    observed_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_key": self.target_key,
            "context": self.context,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "credited": self.credited,
            "retention": self.retention,
            "observed_status": self.observed_status,
        }


@dataclass(frozen=True)
class TransitionResult:
    state: LearnerState
    operation_id: str
    duplicate: bool
    pending: bool
    global_opportunity_delta: int
    contributions: tuple[Contribution, ...] = ()
    updates: tuple[EdgeUpdate, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "duplicate": self.duplicate,
            "pending": self.pending,
            "global_opportunity_delta": self.global_opportunity_delta,
            "contributions": [item.to_dict() for item in self.contributions],
            "updates": [item.to_dict() for item in self.updates],
            "reasons": list(self.reasons),
            "state": self.state.to_dict(),
        }


@dataclass(frozen=True)
class ConsequenceResult:
    state: LearnerState
    assessment_id: str
    duplicate: bool
    awarded: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "duplicate": self.duplicate,
            "awarded": self.awarded,
            "reason": self.reason,
            "state": self.state.to_dict(),
        }


def _tuple_map(values: Iterable[tuple[str, int]]) -> tuple[tuple[str, int], ...]:
    result: dict[str, int] = {}
    for key, amount in values:
        result[key] = amount
    return tuple(sorted(result.items()))


def _window(
    values: Iterable[CreditWindow], opportunity: int, amount: int
) -> tuple[CreditWindow, ...]:
    merged = [item for item in values if item.opportunity != opportunity]
    merged.append(CreditWindow(opportunity, amount))
    return tuple(sorted(merged, key=lambda item: item.opportunity)[-8:])


def _window_total(values: Iterable[CreditWindow]) -> int:
    return sum(item.amount for item in values)


def _dependence_factor(dependence: Dependence) -> tuple[int, int]:
    if dependence in {Dependence.EXTERNAL_SUPPORTED}:
        return (1, 1)
    if dependence in {Dependence.REPLAY_LINKED, Dependence.EXPOSURE_LINKED}:
        return (1, 10)
    if dependence is Dependence.NO_IDENTIFIED_LINK:
        return (1, 4)
    return (0, 1)


def _is_induced(dependence: Dependence) -> bool:
    return dependence in {Dependence.REPLAY_LINKED, Dependence.EXPOSURE_LINKED}


def _is_consolidatable(dependence: Dependence) -> bool:
    return not _is_induced(dependence) and dependence not in {
        Dependence.CURRENT_INPUT_ECHO,
        Dependence.UNKNOWN,
        Dependence.CONFLICT,
        Dependence.DUPLICATE,
    }


def _dedupe_observations(observations: Sequence[Observation]) -> tuple[Observation, ...]:
    result: dict[tuple[str, str, str, str], Observation] = {}
    for item in observations:
        occurrence = item.occurrence_key or (
            f"{item.target_key}:{item.context}:{item.group_key or ''}"
        )
        key = (item.target_key, item.context, _as_role(item.source_role).value, occurrence)
        # Repeated identical occurrence records are one observation.  Conflicting
        # duplicate rows become unknown rather than silently selecting one.
        existing = result.get(key)
        if existing is None:
            result[key] = item
        elif existing.status != item.status:
            result[key] = Observation(
                target_key=item.target_key,
                context=item.context,
                source_role=item.source_role,
                dependence=Dependence.CONFLICT,
                status=ObservationStatus.UNKNOWN,
                group_key=item.group_key,
                occurrence_key=occurrence,
                covered=False,
                relevant=False,
            )
    return tuple(result[key] for key in sorted(result))


def _replace_edge(edges: dict[tuple[str, str], EdgeState], state: EdgeState) -> None:
    edges[state.key] = state


def _replace_route(routes: dict[tuple[str, str], RouteState], state: RouteState) -> None:
    routes[state.key] = state


def _decay(edge: EdgeState, *, opportunity: int, ticks: int) -> EdgeState:
    current = edge
    for _ in range(ticks):
        inactivity = current.inactivity_ticks + 1
        support = current.support
        if inactivity >= 8:
            support = _mul_div(support, 255, 256)
        current = EdgeState(
            target_key=current.target_key,
            context=current.context,
            accessibility=_mul_div(current.accessibility, 7, 8),
            support=support,
            consequence=current.consequence,
            relevant_opportunities=current.relevant_opportunities + 1,
            inactivity_ticks=inactivity,
            lifetime_by_group=current.lifetime_by_group,
            induced_by_group=current.induced_by_group,
            rolling_credits=_window(current.rolling_credits, opportunity, 0),
            last_consolidation_opportunity=current.last_consolidation_opportunity,
            raw_occurrence_count=current.raw_occurrence_count,
        )
        opportunity += 1
    return current


def _apply_consequence_mutable(
    routes: dict[tuple[str, str], RouteState],
    assessment: ConsequenceAssessment,
    current_opportunity: int,
) -> tuple[int, str, bool]:
    route = routes.get(assessment.key, RouteState(assessment.route_key, assessment.context))
    if assessment.operation_id in route.applied_assessments:
        return 0, "duplicate", True
    applied = tuple(sorted((*route.applied_assessments, assessment.operation_id)))
    if assessment.outcome == "unknown" or not assessment.relevant:
        _replace_route(routes, RouteState(**{**route.__dict__, "applied_assessments": applied}))
        return 0, "unknown_or_irrelevant", False
    exposure_key = assessment.exposure_id or assessment.operation_id
    by_exposure = dict(route.by_exposure)
    exposure_used = by_exposure.get(exposure_key, 0)
    opportunity = (
        assessment.opportunity
        if assessment.opportunity is not None
        else current_opportunity
    )
    rolling_used = _window_total(route.rolling_consequences)
    remaining = min(
        CONSEQUENCE_STEP,
        CONSEQUENCE_EXPOSURE_CAP - exposure_used,
        CONSEQUENCE_ROLLING_CAP - rolling_used,
    )
    if remaining <= 0:
        _replace_route(
            routes,
            RouteState(
                **{
                    **route.__dict__,
                    "applied_assessments": applied,
                    "rolling_consequences": _window(route.rolling_consequences, opportunity, 0),
                }
            ),
        )
        return 0, "consequence_cap_exhausted", False
    awarded = remaining * assessment.direction
    by_exposure[exposure_key] = exposure_used + remaining
    rolling = _window(route.rolling_consequences, opportunity, rolling_used + remaining)
    # ``rolling`` stores absolute awarded amounts for the current eight-window
    # accounting.  Keep the route value itself signed.
    _replace_route(
        routes,
        RouteState(
            route_key=route.route_key,
            context=route.context,
            consequence=_clip(route.consequence + awarded, -250_000, 250_000),
            by_exposure=_tuple_map(by_exposure.items()),
            rolling_consequences=rolling,
            applied_assessments=applied,
        ),
    )
    return awarded, "awarded", False


def apply_consequence(
    state: LearnerState | EdgeState,
    assessment: ConsequenceAssessment | int,
) -> ConsequenceResult | EdgeState:
    """Apply one explicit consequence without mutating ``state``.

    The ``EdgeState, +/-50000`` form remains as a compatibility shim for the
    first P2.1 focused fixtures; production code uses the attributed
    ``LearnerState, ConsequenceAssessment`` form.
    """

    if isinstance(state, EdgeState) and isinstance(assessment, int):
        if assessment not in {-50_000, 50_000}:
            raise LearnerError("consequence delta must be +/-0.05")
        return replace(state, consequence=_clip(state.consequence + assessment, -250_000, 250_000))
    if not isinstance(state, LearnerState) or not isinstance(assessment, ConsequenceAssessment):
        raise LearnerError("invalid consequence arguments")

    routes = {item.key: item for item in state.route_states}
    awarded, reason, duplicate = _apply_consequence_mutable(
        routes, assessment, state.global_opportunity
    )
    new_state = LearnerState(
        edge_states=state.edge_states,
        route_states=tuple(sorted(routes.values(), key=lambda item: item.key)),
        global_opportunity=state.global_opportunity,
        applied_operations=state.applied_operations,
        schema_version=state.schema_version,
    )
    return ConsequenceResult(new_state, assessment.operation_id, duplicate, awarded, reason)


def route_score(
    state: LearnerState,
    edge_keys: Sequence[str],
    route_key: str,
    context: str = "general",
) -> tuple[int, int, bool]:
    """Return ``(base, score, eligible_by_restraint)`` in fixed-point units."""

    if not edge_keys:
        raise LearnerError("route must contain at least one edge")
    values: list[int] = []
    for key in edge_keys:
        edge = state.edge(key, context)
        values.append(_mul_div(edge.accessibility, 6, 10) + _mul_div(edge.support, 4, 10))
    base = sum(values) // len(values)
    score = base + state.route(route_key, context).consequence
    return base, score, state.route(route_key, context).consequence > -250_000 and score > 0


@dataclass(frozen=True)
class RouteSpec:
    route_key: str
    edge_keys: tuple[str, ...]
    query_coverage: int
    directness: int = 0
    canonical_key: str | None = None
    context: str = "general"
    hard_gates_pass: bool = True
    current_relevance_passes: bool = True

    def __post_init__(self) -> None:
        if not self.route_key or not self.edge_keys:
            raise LearnerError("route identity and edge_keys must be non-empty")
        if self.query_coverage < 0 or self.directness < 0:
            raise LearnerError("route ranking values cannot be negative")


def select_routes(
    state: LearnerState | Iterable[Mapping[str, Any]],
    routes: Iterable[RouteSpec] | Mapping[str, EdgeState],
    *,
    opportunity: int | None = None,
    max_routes: int = 2,
) -> tuple[RouteSpec, ...]:
    """Select learned-v1 routes with highest-coverage-only exploration.

    This helper returns semantic candidates only.  Serialization and payload
    limits remain the caller's responsibility; a candidate omitted while
    serializing was never exposed.
    """

    if max_routes <= 0:
        return ()
    if not isinstance(state, LearnerState):
        legacy_routes = tuple(state)
        edge_map = routes
        if not isinstance(edge_map, Mapping):
            raise LearnerError("legacy route selection requires an edge mapping")
        edge_states = tuple(
            sorted(
                (
                    value
                    if value.target_key != "legacy"
                    else replace(value, target_key=str(key), context="general")
                    for key, value in edge_map.items()
                ),
                key=lambda item: item.key,
            )
        )
        legacy_state = LearnerState(edge_states=edge_states, global_opportunity=0)
        specs = tuple(
            RouteSpec(
                route_key=str(item.get("route_key", "")),
                edge_keys=tuple(str(key) for key in item.get("edge_keys", ())),
                query_coverage=int(item.get("query_coverage", 0)),
                directness=int(item.get("directness", 0)),
            )
            for item in legacy_routes
        )
        selected = select_routes(
            legacy_state,
            specs,
            opportunity=opportunity,
            max_routes=max_routes,
        )
        return tuple(
            {
                "route_key": item.route_key,
                "edge_keys": list(item.edge_keys),
                "query_coverage": item.query_coverage,
            }
            for item in selected
        )
    if not isinstance(routes, Iterable):
        raise LearnerError("routes must be iterable")
    candidates: list[tuple[RouteSpec, int, int]] = []
    for route in routes:
        base, score, restraint = route_score(state, route.edge_keys, route.route_key, route.context)
        if not route.hard_gates_pass or not route.current_relevance_passes or not restraint:
            continue
        candidates.append((route, score, base))
    ordered = sorted(
        candidates,
        key=lambda item: (
            -item[0].query_coverage,
            -item[1],
            -item[0].directness,
            item[0].canonical_key or item[0].route_key,
        ),
    )
    if opportunity is None or opportunity % 4 != 0:
        return tuple(item[0] for item in ordered[:max_routes])
    highest = max((item[0].query_coverage for item in ordered), default=None)
    tier = [item for item in ordered if item[0].query_coverage == highest]
    if len(tier) < 3:
        return tuple(item[0] for item in ordered[:max_routes])
    first = tier[0]
    remainder = sorted(
        tier[1:], key=lambda item: item[0].canonical_key or item[0].route_key
    )
    selected = [first, remainder[((opportunity // 4) - 1) % len(remainder)]]
    return tuple(item[0] for item in selected[:max_routes])


def apply_transition(state: LearnerState, transition: TransitionInput) -> TransitionResult:
    """Apply one deterministic development operation to an immutable state."""

    if transition.operation_id in state.applied_operations:
        return TransitionResult(
            state=state,
            operation_id=transition.operation_id,
            duplicate=True,
            pending=False,
            global_opportunity_delta=0,
            reasons=("duplicate_operation",),
        )
    if not transition.terminal:
        return TransitionResult(
            state=state,
            operation_id=transition.operation_id,
            duplicate=False,
            pending=True,
            global_opportunity_delta=0,
            reasons=("operation_not_terminal",),
        )

    edges = {item.key: item for item in state.edge_states}
    routes = {item.key: item for item in state.route_states}
    current_opportunity = state.global_opportunity
    global_delta = transition.modeled_advance_ticks or 1
    new_global = current_opportunity + global_delta
    contributions: list[Contribution] = []
    updates: list[EdgeUpdate] = []
    reasons: list[str] = []

    # Explicit modeled time is deliberately separate from observations and
    # never manufactures an unsupported/observed absence record.
    if transition.modeled_advance_ticks:
        targets = transition.advance_targets or tuple(
            sorted({item.key for item in transition.observations if item.relevant})
        )
        for target, context in targets:
            before = edges.get((target, context), EdgeState(target, context))
            after = _decay(
                before,
                opportunity=current_opportunity + 1,
                ticks=transition.modeled_advance_ticks,
            )
            _replace_edge(edges, after)
            updates.append(
                EdgeUpdate(target, context, before, after, 0, "modeled_advance", "modeled_advance")
            )
        reasons.append("modeled_advance")
    elif transition.disposition in {
        TerminalDisposition.FAILED,
        TerminalDisposition.EXCLUDED,
        TerminalDisposition.UNCERTAIN,
    }:
        reasons.append("measurement_unknown")
    elif transition.disposition is TerminalDisposition.ACCEPTED:
        deduped = _dedupe_observations(transition.observations)
        by_target: dict[tuple[str, str], list[Observation]] = defaultdict(list)
        for observation in deduped:
            by_target[observation.key].append(observation)

        # Determine one covered status per target. Conflicting statuses fail
        # closed into unknown rather than treating absence as missing evidence.
        target_status: dict[tuple[str, str], ObservationStatus] = {}
        for key, observations in by_target.items():
            statuses = {
                _as_status(item.status)
                for item in observations
                if item.covered and item.relevant
            }
            if len(statuses) == 1:
                target_status[key] = next(iter(statuses))
            elif len(statuses) > 1:
                target_status[key] = ObservationStatus.UNKNOWN

        candidates: list[tuple[Observation, int, int, str, int]] = []
        # Source pools are divided among distinct admitted target keys before
        # dependence discounts. Zero-credit observations retain their share.
        for role in (SourceRole.EXTERNAL, SourceRole.MODEL_OUTPUT):
            role_observations = [
                item
                for item in deduped
                if _as_role(item.source_role) is role
                and item.covered
                and item.relevant
                and _as_status(item.status) is ObservationStatus.PRESENT
                and target_status.get(item.key) is ObservationStatus.PRESENT
            ]
            target_keys = sorted({item.key for item in role_observations})
            if not target_keys:
                continue
            base_share, remainder = divmod(POOL, len(target_keys))
            shares = {
                key: base_share + (1 if index < remainder else 0)
                for index, key in enumerate(target_keys)
            }
            for item in role_observations:
                dependence = _as_dependence(item.dependence)
                numerator, denominator = _dependence_factor(dependence)
                proposed = _mul_div(shares[item.key], numerator, denominator)
                group = item.group_key or item.occurrence_key or transition.operation_id
                candidates.append((item, proposed, numerator, group, denominator))

        candidates.sort(
            key=lambda item: (
                item[0].target_key,
                item[0].context,
                _as_role(item[0].source_role).value,
                item[3],
                _as_dependence(item[0].dependence).value,
                item[0].occurrence_key or "",
            )
        )
        per_operation_remaining = OPPORTUNITY_CAP
        credited_by_target: dict[tuple[str, str], int] = defaultdict(int)
        consolidation_possible: dict[tuple[str, str], bool] = defaultdict(bool)
        for item, proposed, _numerator, group, _denominator in candidates:
            dependence = _as_dependence(item.dependence)
            edge = edges.get(item.key, EdgeState(item.target_key, item.context))
            lifetime = dict(edge.lifetime_by_group)
            induced = dict(edge.induced_by_group)
            rolling_used = _window_total(edge.rolling_credits)
            allowed = min(
                proposed,
                max(0, LIFETIME_CAP - lifetime.get(group, 0)),
                max(0, per_operation_remaining),
                max(0, ROLLING_CAP - rolling_used),
            )
            if _is_induced(dependence):
                allowed = min(allowed, max(0, INDUCED_CAP - induced.get(group, 0)))
            if allowed:
                lifetime[group] = lifetime.get(group, 0) + allowed
                if _is_induced(dependence):
                    induced[group] = induced.get(group, 0) + allowed
                per_operation_remaining -= allowed
                credited_by_target[item.key] += allowed
                if _is_consolidatable(dependence):
                    consolidation_possible[item.key] = True
                reason = "awarded"
            elif proposed:
                reason = "cap_exhausted"
            else:
                reason = "zero_credit_dependence"
            contributions.append(
                Contribution(
                    item.target_key,
                    item.context,
                    _as_role(item.source_role).value,
                    group,
                    dependence.value,
                    proposed,
                    allowed,
                    reason,
                )
            )
            _replace_edge(
                edges,
                EdgeState(
                    target_key=edge.target_key,
                    context=edge.context,
                    accessibility=edge.accessibility,
                    support=edge.support,
                    consequence=edge.consequence,
                    relevant_opportunities=edge.relevant_opportunities,
                    inactivity_ticks=edge.inactivity_ticks,
                    lifetime_by_group=_tuple_map(lifetime.items()),
                    induced_by_group=_tuple_map(induced.items()),
                    rolling_credits=edge.rolling_credits,
                    last_consolidation_opportunity=edge.last_consolidation_opportunity,
                    raw_occurrence_count=edge.raw_occurrence_count,
                ),
            )

        for key in sorted(target_status):
            status = target_status[key]
            before = edges.get(key, EdgeState(*key))
            credited = credited_by_target.get(key, 0)
            edge = before
            if status is ObservationStatus.UNKNOWN:
                after = edge
                retention: str | None = None
            elif status is ObservationStatus.ABSENT:
                if edge.relevant_opportunities == before.relevant_opportunities:
                    after = _decay(edge, opportunity=current_opportunity + 1, ticks=1)
                else:
                    after = edge
                retention = "observed_nonrecurrence"
            else:
                opportunity = current_opportunity + 1
                relevant = edge.relevant_opportunities + 1
                support = edge.support
                last_consolidation = edge.last_consolidation_opportunity
                if credited > 0 and consolidation_possible.get(key, False):
                    if last_consolidation is None or relevant - last_consolidation >= 4:
                        support = min(FIXED_ONE, support + credited // 4)
                        last_consolidation = relevant
                after = EdgeState(
                    target_key=edge.target_key,
                    context=edge.context,
                    accessibility=min(FIXED_ONE, edge.accessibility + credited),
                    support=support,
                    consequence=edge.consequence,
                    relevant_opportunities=relevant,
                    inactivity_ticks=0,
                    lifetime_by_group=edge.lifetime_by_group,
                    induced_by_group=edge.induced_by_group,
                    rolling_credits=_window(edge.rolling_credits, opportunity, credited),
                    last_consolidation_opportunity=last_consolidation,
                    raw_occurrence_count=edge.raw_occurrence_count
                    + sum(
                        1
                        for item in by_target[key]
                        if _as_status(item.status) is ObservationStatus.PRESENT
                    ),
                )
                retention = None
            _replace_edge(edges, after)
            updates.append(
                EdgeUpdate(
                    key[0],
                    key[1],
                    before,
                    after,
                    credited,
                    retention,
                    status.value,
                )
            )

    for assessment in transition.consequences:
        awarded, reason, _duplicate = _apply_consequence_mutable(
            routes, assessment, new_global
        )
        if reason != "awarded":
            reasons.append(reason)
        elif awarded:
            reasons.append("consequence_awarded")

    applied_operations = tuple(sorted((*state.applied_operations, transition.operation_id)))
    new_state = LearnerState(
        edge_states=tuple(sorted(edges.values(), key=lambda item: item.key)),
        route_states=tuple(sorted(routes.values(), key=lambda item: item.key)),
        global_opportunity=new_global,
        applied_operations=applied_operations,
        schema_version=state.schema_version,
    )
    return TransitionResult(
        state=new_state,
        operation_id=transition.operation_id,
        duplicate=False,
        pending=False,
        global_opportunity_delta=global_delta,
        contributions=tuple(contributions),
        updates=tuple(updates),
        reasons=tuple(reasons),
    )


@dataclass(frozen=True)
class LearnerResult:
    """Compatibility result for the original P2.1 pure-kernel API."""

    state: Mapping[tuple[str, str], EdgeState]
    deltas: Mapping[tuple[str, str], int]
    reasons: Mapping[tuple[str, str], str]
    opportunity: int


@dataclass(frozen=True)
class LearnerConfig:
    """Compatibility view of the fixed Phase Two coefficients."""

    version: str = "learner-v1"
    external_pool: int = POOL
    model_pool: int = POOL
    lifetime_cap: int = LIFETIME_CAP
    induced_cap: int = INDUCED_CAP
    rolling_cap: int = ROLLING_CAP
    opportunity_cap: int = OPPORTUNITY_CAP
    consolidation_gap: int = 4
    retention_enabled: bool = True


@dataclass(frozen=True)
class DevelopmentalLearner:
    """Small adapter retaining the initial mapping-based learner interface."""

    config: LearnerConfig = field(default_factory=LearnerConfig)

    def apply(
        self,
        state: Mapping[tuple[str, str], EdgeState],
        observations: Iterable[Observation],
        *,
        opportunity: int,
    ) -> LearnerResult:
        prior = LearnerState(
            edge_states=tuple(
                sorted(
                    (
                        value
                        if value.target_key != "legacy"
                        else replace(value, target_key=key[0], context=key[1])
                        for key, value in state.items()
                    ),
                    key=lambda item: item.key,
                )
            ),
            global_opportunity=max(0, opportunity - 1),
        )
        result = apply_transition(
            prior,
            TransitionInput(
                operation_id=f"compat:{opportunity}",
                observations=tuple(observations),
            ),
        )
        deltas = {(item.target_key, item.context): item.credited for item in result.updates}
        reasons = {
            (item.target_key, item.context): (
                "credited"
                if item.credited
                else "support_seen_credit_capped"
                if item.observed_status == ObservationStatus.PRESENT.value
                else "measurement_unknown"
            )
            for item in result.updates
        }
        return LearnerResult(
            {item.key: item for item in result.state.edge_states},
            deltas,
            reasons,
            opportunity,
        )


def route_exposure(
    edge_states: Mapping[str, EdgeState], edge_keys: Sequence[str]
) -> bool:
    """Compatibility route eligibility for the original edge-map API."""

    if not edge_keys or any(key not in edge_states for key in edge_keys):
        return False
    values = [edge_states[key] for key in edge_keys]
    base = sum(
        _mul_div(item.accessibility, 6, 10) + _mul_div(item.support, 4, 10)
        for item in values
    )
    score = base // len(values) + sum(item.consequence for item in values) // len(values)
    return all(item.consequence > -250_000 for item in values) and score > 0


__all__ = [
    "CONSEQUENCE_EXPOSURE_CAP",
    "CONSEQUENCE_ROLLING_CAP",
    "CONSEQUENCE_STEP",
    "Dependence",
    "ConsequenceAssessment",
    "Contribution",
    "DevelopmentalLearner",
    "EdgeState",
    "EdgeUpdate",
    "FIXED_ONE",
    "FIXED_SCALE",
    "INDUCED_CAP",
    "LearnerError",
    "LearnerConfig",
    "LearnerResult",
    "LearnerState",
    "LIFETIME_CAP",
    "Observation",
    "ObservationStatus",
    "EdgeUpdate",
    "POOL",
    "RouteSpec",
    "RouteState",
    "ROLLING_CAP",
    "SourceRole",
    "TerminalDisposition",
    "TransitionInput",
    "TransitionResult",
    "apply_consequence",
    "apply_transition",
    "from_fixed",
    "route_score",
    "select_routes",
    "to_fixed",
]
