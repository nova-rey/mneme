# ruff: noqa: E402

from __future__ import annotations

import importlib.util
from pathlib import Path

from mneme.development.learner import (
    LearnerState,
    Observation,
    TransitionInput,
    apply_transition,
)

_SPEC = importlib.util.spec_from_file_location(
    "mneme_final_episodic_harness",
    Path(__file__).parents[1] / "tools" / "run_p23_final_episodic.py",
)
assert _SPEC is not None and _SPEC.loader is not None
_HARNESS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_HARNESS)
TARGET_TURNS = _HARNESS.TARGET_TURNS
_arc_map = _HARNESS._arc_map
_turns = _HARNESS._turns


def test_final_schedule_has_five_spaced_target_opportunities() -> None:
    assert TARGET_TURNS == (0, 2, 11, 20, 29)
    assert len(_turns("external")) == 30
    assert len(_turns("model")) == 30
    for branch in ("external", "model"):
        arcs = _arc_map(branch, _turns(branch))
        assert len({item.episode_id for item in arcs.values()}) == 30
        assert arcs[2].refractory_active is (branch == "model")
        assert arcs[11].rounds_since_prior == 8


def test_external_schedule_reaches_fixed_consolidation_gap_without_cap_hack() -> None:
    state = LearnerState()
    target_operations = {1, 3, 12, 21, 30}
    for operation in range(1, 31):
        observations = ()
        if operation in target_operations:
            index = sorted(target_operations).index(operation)
            observations = (
                Observation(
                    target_key="c-target",
                    context="general",
                    source_role="external",
                    status="present",
                    dependence="external_supported",
                    covered=True,
                    actual_exposure=True,
                    conversation_arc_id=f"arc-{index}",
                    group_key=f"group-{index}",
                    provenance_group_keys=(f"group-{index}",),
                    occurrence_key=f"occurrence-{index}",
                    eligible=True,
                ),
            )
        result = apply_transition(
            state,
            TransitionInput(operation_id=f"offline-{operation}", observations=observations),
        )
        state = result.state
    update = result.updates[0]
    assert update.credited == 80_000
    assert update.after.relevant_opportunities == 5
    assert update.after.last_consolidation_opportunity == 5
