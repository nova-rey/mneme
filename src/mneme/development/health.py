"""Fail-fast diagnostics for the SAA host-treatment boundary.

The health classifier is deliberately separate from the field algorithm.  It
does not change candidate eligibility or repair a bad state; it classifies
the first observable point where an enabled field failed to reach the host.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .field import FieldResult
from .learner import LearnerState


def assess_saa_treatment_health(
    result: FieldResult,
    learner: LearnerState,
    edges: Iterable[Any],
    *,
    blocked_edges: Iterable[str] = (),
) -> dict[str, Any]:
    """Classify whether one SAA field coordinate actually delivered treatment.

    ``cold_start``, ``disabled``, and ``blocked`` are explicit non-error
    outcomes.  Once an earned learner value should be reachable, missing
    graph bindings, distributions, landings, pressure, or payloads are
    distinct failures rather than an indistinguishable empty field.
    """

    edge_rows = tuple(edges)
    blocked = set(blocked_edges)
    positive_state: set[str] = set()
    for state in learner.edge_states:
        strength = max(state.accessibility, state.support)
        if state.consequence < 0:
            strength = max(0, strength + state.consequence)
        if strength > 0:
            positive_state.add(state.target_key)
    graph_keys = {str(edge.key) for edge in edge_rows}
    positive_graph = graph_keys & positive_state
    unblocked_graph = positive_graph - blocked
    base: dict[str, Any] = {
        "field_enabled": bool(result.field_enabled),
        "positive_state_count": len(positive_state),
        "graph_edge_count": len(graph_keys),
        "positive_graph_count": len(positive_graph),
        "blocked_positive_count": len(positive_graph & blocked),
        "distribution_count": len(result.accessibility_distribution),
        "selected_landing": result.selected_landing,
        "total_pressure": result.total_pressure,
        "payload_nonempty": bool(result.payload.strip()),
    }
    if not result.field_enabled:
        return {**base, "status": "disabled", "reason": "field_disabled_by_policy_or_intent"}
    if not positive_state:
        return {**base, "status": "cold_start", "reason": "no_eligible_earned_state"}
    if not positive_graph:
        return {
            **base,
            "status": "binding_mismatch",
            "reason": "earned_learner_keys_do_not_resolve_to_current_graph_edges",
        }
    if not unblocked_graph:
        return {**base, "status": "blocked", "reason": "all_earned_graph_edges_are_blocked"}
    if not result.accessibility_distribution:
        return {
            **base,
            "status": "empty_distribution",
            "reason": "eligible_state_lost_before_sampling",
        }
    if result.selected_landing is None:
        return {
            **base,
            "status": "missing_landing",
            "reason": "distribution_did_not_select_a_landing",
        }
    if result.total_pressure <= 0:
        return {**base, "status": "zero_pressure", "reason": "landing_produced_no_pressure"}
    if not result.payload.strip():
        return {
            **base,
            "status": "empty_payload",
            "reason": "renderer_suppressed_nonzero_field",
        }
    return {**base, "status": "healthy", "reason": "field_treatment_delivered"}


__all__ = ["assess_saa_treatment_health"]
