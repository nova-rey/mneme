"""Offline contract and evidence tests for the D100 descendant trial."""

import json

from mneme.development.learner import (
    Dependence,
    ExpressionStatus,
    Observation,
    ObservationStatus,
    RelationSupport,
    SourceRole,
    TransitionInput,
)
from mneme.experiments.d100_trial import (
    FROZEN_PROBES,
    THREAD_SCHEDULE,
    CompactTrialBranch,
    TrialConfig,
    ancestor_equivalence,
    copy_ancestor,
    render_report,
    validate_schedule,
    validate_trial_evidence,
)
from mneme.state.compact import CompactStore


def _ancestor(path):
    with CompactStore.create(path) as store:
        store.put_graph(
            nodes={"n1": {"label": "A", "kind": "concept"}},
            edges={"e1": {"source": "n1", "target": "n1", "relationship": "supports"}},
            routes={"r1": {"edge_keys": ["e1"]}},
        )
        store.put_learner(
            "e1",
            "general",
            {"accessibility": 100_000, "support": 50_000},
            operation_id="fixture",
        )


def test_schedule_is_frozen_and_heterogeneous():
    validate_schedule()
    assert [item.number for item in THREAD_SCHEDULE] == list(range(1, 11))
    assert len({item.domain for item in THREAD_SCHEDULE}) == 10
    assert THREAD_SCHEDULE[-1].number == 10
    assert "community" in THREAD_SCHEDULE[-1].opening


def test_trial_config_rejects_missing_ancestor(tmp_path):
    config = TrialConfig(tmp_path / "missing.sqlite3", tmp_path / "out")
    try:
        config.validate()
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing ancestor must fail before live dispatch")


def test_copy_and_equivalence_are_read_only_and_digest_stable(tmp_path):
    source = tmp_path / "source.sqlite3"
    destination = tmp_path / "ancestor.sqlite3"
    _ancestor(source)
    receipt = copy_ancestor(source, destination)
    assert receipt["verification"] == "PASS"
    assert receipt["normative_status"] == "convenience_developed_ancestor"
    equivalence = ancestor_equivalence(source, destination)
    assert equivalence["pass"] is True
    assert equivalence["graph_equal"] is True
    assert equivalence["learner_equal"] is True


def test_report_validator_requires_full_terminal_evidence():
    payload = {
        "trial_version": "d100-compact-introspection-10-v1",
        "d100_normative_status": "convenience_developed_ancestor",
        "ancestor_equivalence": {"pass": True},
        "threads": [{"thread": number} for number in range(1, 11)],
        "I2": {},
        "N2": {},
        "pre_probes": [],
        "post_probes": [],
        "removal_restoration": {},
        "introspection_summary": {},
        "persistence": {},
    }
    assert validate_trial_evidence(payload) == []
    payload.pop("post_probes")
    assert "post_probes" in validate_trial_evidence(payload)


def test_report_is_human_readable_and_does_not_worship_ancestor():
    payload = {
        "run_id": "fixture",
        "disposition": "VALID_INTERPRETABLE_OR_BORING",
        "ancestor_equivalence": {"pass": True, "source_state_digest": "abc"},
        "compact_schema_version": 1,
        "threads": [{"thread": i} for i in range(1, 11)],
        "introspection_summary": {"I2": {}, "N2": {}},
        "removal_restoration": {"status": "PASS"},
    }
    report = render_report(payload)
    assert "not a normative model" in report
    assert "D100" in report


def test_frozen_probe_bank_has_modest_fixed_size_and_is_serializable():
    assert 2 <= len(FROZEN_PROBES) <= 8
    assert json.loads(json.dumps(list(FROZEN_PROBES))) == list(FROZEN_PROBES)


def test_compact_branch_uses_persisted_graph_and_saa_field(tmp_path):
    source = tmp_path / "source.sqlite3"
    _ancestor(source)
    with CompactStore(source) as store:
        branch = CompactTrialBranch(store)
        before = branch.field("unfamiliar process", field_seed=7)
        assert before.field_enabled is True
        assert before.selected_landing == "e1"
        result = branch.apply(
            TransitionInput(
                operation_id="development-1",
                observations=(
                    Observation(
                        target_key="e1",
                        context="general",
                        source_role=SourceRole.EXTERNAL,
                        dependence=Dependence.EXTERNAL_SUPPORTED,
                        status=ObservationStatus.PRESENT,
                        relation_support=RelationSupport.SUPPORTED,
                        expression_status=ExpressionStatus.AFFIRMED,
                        actual_exposure=True,
                        conversation_arc_id="arc-1",
                        occurrence_key="obs-1",
                    ),
                ),
            )
        )
        assert result.state.edge("e1", "general").accessibility > 100_000
        assert store.learner_state()[("e1", "general")]["accessibility"] == result.state.edge(
            "e1", "general"
        ).accessibility
        assert store.verify() == []
