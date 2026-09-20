"""Small fixed-point, replayable Phase Two learner.

This module has no model or database dependency.  It consumes immutable
observations and returns a new state, making arithmetic and replay suitable
for ordinary unit tests and later durable publication.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

FIXED_SCALE = 1_000_000


def _clip(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _content_key(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LearnerConfig:
    """Versioned coefficients.  Values are fixed-point integer units."""

    version: str = "learner-v1"
    external_pool: int = 80_000
    model_pool: int = 80_000
    lifetime_cap: int = 120_000
    induced_cap: int = 10_000
    rolling_cap: int = 200_000
    opportunity_cap: int = 160_000
    consolidation_factor_num: int = 1
    consolidation_factor_den: int = 4
    consolidation_gap: int = 4
    retention_enabled: bool = False

    def __post_init__(self) -> None:
        if self.external_pool < 0 or self.model_pool < 0:
            raise ValueError("source pools must be non-negative")
        if not 0 < self.consolidation_factor_num <= self.consolidation_factor_den:
            raise ValueError("invalid consolidation factor")
        if self.consolidation_gap < 1:
            raise ValueError("consolidation gap must be positive")


@dataclass(frozen=True)
class EdgeState:
    """Materialized values for one canonical edge and context."""

    accessibility: int = 0
    support: int = 0
    consequence: int = 0
    lifetime_credit: int = 0
    induced_credit: int = 0
    rolling_credit: int = 0
    last_consolidation_opportunity: int | None = None
    inactivity_ticks: int = 0

    def __post_init__(self) -> None:
        for name in (
            "accessibility",
            "support",
            "lifetime_credit",
            "induced_credit",
            "rolling_credit",
        ):
            value = getattr(self, name)
            if not 0 <= value <= FIXED_SCALE:
                raise ValueError(f"{name} outside fixed-point bounds")
        if not -250_000 <= self.consequence <= 250_000:
            raise ValueError("consequence outside fixed-point bounds")
        if self.inactivity_ticks < 0:
            raise ValueError("inactivity ticks must be non-negative")

    @property
    def score(self) -> int:
        return (self.accessibility * 6 + self.support * 4) // 10 + self.consequence

    def to_dict(self) -> dict[str, Any]:
        return {
            "accessibility": self.accessibility,
            "support": self.support,
            "consequence": self.consequence,
            "lifetime_credit": self.lifetime_credit,
            "induced_credit": self.induced_credit,
            "rolling_credit": self.rolling_credit,
            "last_consolidation_opportunity": self.last_consolidation_opportunity,
            "inactivity_ticks": self.inactivity_ticks,
        }


@dataclass(frozen=True)
class Observation:
    """One source-aware, immutable developmental observation."""

    edge_key: str
    context: str = "general"
    status: str = "present"
    source_role: str = "external"
    dependence: str = "external_supported"
    dependence_group: str = ""
    observation_id: str = ""
    eligible: bool = True
    actual_exposure: bool = False
    covered: bool = True

    def __post_init__(self) -> None:
        if not self.edge_key or not self.context:
            raise ValueError("observation requires edge and context")
        if self.status not in {"present", "absent", "unknown"}:
            raise ValueError("invalid observation status")
        if self.source_role not in {"external", "model", "none"}:
            raise ValueError("invalid source role")
        if self.dependence not in {
            "external_supported",
            "current_input_echo",
            "replay_linked",
            "exposure_linked",
            "no_identified_link",
            "unknown",
            "duplicate",
        }:
            raise ValueError("invalid dependence category")


@dataclass(frozen=True)
class LearnerResult:
    state: Mapping[tuple[str, str], EdgeState]
    deltas: Mapping[tuple[str, str], int]
    reasons: Mapping[tuple[str, str], str]
    opportunity: int


@dataclass(frozen=True)
class DevelopmentalLearner:
    config: LearnerConfig = field(default_factory=LearnerConfig)

    def apply(
        self,
        state: Mapping[tuple[str, str], EdgeState],
        observations: Iterable[Observation],
        *,
        opportunity: int,
    ) -> LearnerResult:
        """Apply one completed opportunity deterministically.

        Unknown, excluded, and duplicate observations do not advance a target.
        Capped presence is still presence and therefore cannot be interpreted as
        absence.  P2.1 leaves retention disabled; P2.2 can enable it through a
        versioned configuration without changing this transition order.
        """

        if opportunity < 1:
            raise ValueError("opportunity must be positive")
        grouped: dict[tuple[str, str], list[Observation]] = {}
        for observation in observations:
            key = (observation.edge_key, observation.context)
            grouped.setdefault(key, []).append(observation)
        next_state = dict(state)
        deltas: dict[tuple[str, str], int] = {}
        reasons: dict[tuple[str, str], str] = {}
        total = 0
        for key in sorted(grouped):
            rows = grouped[key]
            prior = state.get(key, EdgeState())
            if not any(row.eligible and row.covered for row in rows):
                continue
            if any(row.status == "unknown" for row in rows):
                reasons[key] = "measurement_unknown"
                continue
            if any(row.status == "present" for row in rows):
                contribution = self._contribution(prior, rows, opportunity)
                contribution = min(contribution, self.config.opportunity_cap - total)
                contribution = max(0, contribution)
                after = replace(
                    prior,
                    accessibility=min(FIXED_SCALE, prior.accessibility + contribution),
                    inactivity_ticks=0,
                )
                consolidation = 0
                if contribution and (
                    prior.last_consolidation_opportunity is None
                    or opportunity - prior.last_consolidation_opportunity
                    >= self.config.consolidation_gap
                ):
                    consolidation = (
                        contribution
                        * self.config.consolidation_factor_num
                        // self.config.consolidation_factor_den
                    )
                    after = replace(
                        after,
                        support=min(FIXED_SCALE, prior.support + consolidation),
                        last_consolidation_opportunity=opportunity,
                    )
                after = replace(
                    after,
                    lifetime_credit=min(FIXED_SCALE, prior.lifetime_credit + contribution),
                    induced_credit=min(
                        FIXED_SCALE, prior.induced_credit + self._induced(rows, contribution)
                    ),
                    rolling_credit=min(FIXED_SCALE, prior.rolling_credit + contribution),
                )
                next_state[key] = after
                deltas[key] = contribution
                reasons[key] = "credited" if contribution else "support_seen_credit_capped"
                total += contribution
                continue
            if any(row.status == "absent" for row in rows) and self.config.retention_enabled:
                after = replace(
                    prior,
                    accessibility=prior.accessibility * 7 // 8,
                    support=(prior.support * 255 // 256)
                    if prior.inactivity_ticks + 1 >= 8
                    else prior.support,
                    inactivity_ticks=prior.inactivity_ticks + 1,
                )
                next_state[key] = after
                deltas[key] = 0
                reasons[key] = "observed_nonrecurrence"
        return LearnerResult(next_state, deltas, reasons, opportunity)

    def _contribution(
        self, prior: EdgeState, rows: Sequence[Observation], opportunity: int
    ) -> int:
        unique = {row.observation_id or _content_key(row.__dict__) for row in rows}
        rows = tuple(
            row
            for row in rows
            if row.observation_id or row.actual_exposure or row.status == "present"
        )
        if not rows or not unique:
            return 0
        pool = (
            self.config.external_pool
            if any(row.source_role == "external" for row in rows)
            else self.config.model_pool
        )
        factors = {
            "external_supported": 1.0,
            "current_input_echo": 0.0,
            "replay_linked": 0.10,
            "exposure_linked": 0.10,
            "no_identified_link": 0.25,
            "unknown": 0.0,
            "duplicate": 0.0,
        }
        factor = max(factors[row.dependence] for row in rows)
        raw = int(pool * factor)
        remaining_lifetime = max(0, self.config.lifetime_cap - prior.lifetime_credit)
        remaining_rolling = max(0, self.config.rolling_cap - prior.rolling_credit)
        remaining_induced = max(0, self.config.induced_cap - prior.induced_credit)
        if factor <= 0:
            return 0
        if factor <= 0.10:
            raw = min(raw, remaining_induced)
        return min(raw, remaining_lifetime, remaining_rolling)

    def _induced(self, rows: Sequence[Observation], contribution: int) -> int:
        return (
            contribution
            if any(row.dependence in {"replay_linked", "exposure_linked"} for row in rows)
            else 0
        )


def apply_consequence(state: EdgeState, delta: int) -> EdgeState:
    """Apply one already-attributed contextual consequence."""

    if delta not in {-50_000, 50_000}:
        raise ValueError("consequence delta must be +/-0.05")
    return replace(state, consequence=_clip(state.consequence + delta, -250_000, 250_000))


def route_exposure(edge_states: Mapping[str, EdgeState], edge_keys: Sequence[str]) -> bool:
    """Return whether a route can be supplied under learned-v1 eligibility."""

    if not edge_keys:
        return False
    values = [edge_states[key] for key in edge_keys if key in edge_states]
    if len(values) != len(edge_keys):
        return False
    if any(value.consequence <= -250_000 for value in values):
        return False
    score = sum(value.score for value in values) // len(values)
    return score > 0


def select_routes(
    routes: Iterable[Mapping[str, Any]],
    edge_states: Mapping[str, EdgeState],
    *,
    opportunity: int,
    max_routes: int = 2,
) -> tuple[dict[str, Any], ...]:
    """Select bounded routes, with exploration restricted to top coverage."""

    if opportunity < 1 or max_routes < 1:
        raise ValueError("invalid selection bounds")
    eligible: list[dict[str, Any]] = []
    for route in routes:
        keys = tuple(str(item) for item in route.get("edge_keys", ()))
        if route_exposure(edge_states, keys):
            copy = dict(route)
            copy["learned_score"] = sum(edge_states[key].score for key in keys) // len(keys)
            eligible.append(copy)
    ranked = sorted(
        eligible,
        key=lambda item: (
            -int(item.get("query_coverage", 0)),
            -int(item["learned_score"]),
            len(item.get("edge_keys", ())),
            _canonical({key: item[key] for key in sorted(item) if key not in {"learned_score"}}),
        ),
    )
    if opportunity % 4 or len({int(item.get("query_coverage", 0)) for item in ranked[:1]}) == 0:
        return tuple(ranked[:max_routes])
    highest = max(int(item.get("query_coverage", 0)) for item in ranked)
    tier = [item for item in ranked if int(item.get("query_coverage", 0)) == highest]
    if len(tier) < 3:
        return tuple(ranked[:max_routes])
    rest = sorted(tier[1:], key=lambda item: _canonical(item))
    return tuple([tier[0], rest[((opportunity // 4) - 1) % len(rest)]][:max_routes])


__all__ = [
    "FIXED_SCALE",
    "DevelopmentalLearner",
    "EdgeState",
    "LearnerConfig",
    "LearnerResult",
    "Observation",
    "apply_consequence",
    "route_exposure",
    "select_routes",
]
