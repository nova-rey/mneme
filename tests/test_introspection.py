from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from mneme.controller import ResponseController, TurnIntent
from mneme.development import (
    ArcPacket,
    EvidenceBasis,
    IntrospectionError,
    IntrospectionLedger,
    ReflectionProposal,
    ReviewTarget,
    accept_proposals,
    parse_proposals,
    review_request,
)
from mneme.development.field import compute_saa_field
from mneme.development.learner import EdgeState, LearnerState
from mneme.hosts import FakeHost
from mneme.memory.graph import GraphConcept, GraphEdge
from mneme.state.contracts import StoragePermissions
from mneme.state.storage import SQLiteStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_p3_introspection_100 import _arc_slices


def _packet() -> ArcPacket:
    return ArcPacket(
        arc_id="arc-1",
        messages=(
            {"role": "user", "content": "The reservoir helped while I was away."},
            {"role": "assistant", "content": "A passive supply may help."},
        ),
        exposures=({"turn_ref": "turn-1", "edge_key": "e1", "payload": "passive supply"},),
        targets=(ReviewTarget("t1", "e1", "maintenance", ("turn-1",)),),
    )


def test_review_request_hides_admin_target_identity() -> None:
    request = review_request(_packet())
    assert request["targets"] == [{"target_alias": "t1", "context": "maintenance"}]
    assert "edge_key" not in json.dumps(request)


def test_parser_rejects_unknown_alias_and_evidence() -> None:
    packet = _packet()
    with pytest.raises(IntrospectionError):
        parse_proposals({"assessments": [{"target_alias": "bad"}]}, packet)
    with pytest.raises(IntrospectionError):
        parse_proposals(
            {"assessments": [{"target_alias": "t1", "evidence_refs": ["not-real"]}]},
            packet,
            valid_evidence_refs={"turn-1"},
        )


def test_self_only_is_bounded_and_external_can_be_stronger() -> None:
    packet = _packet()
    self_only = ReflectionProposal("t1", 1.0, 1.0, 1.0, EvidenceBasis.SELF_ONLY, ("turn-1",))
    external = ReflectionProposal(
        "t1", 1.0, 1.0, 1.0, EvidenceBasis.EXTERNAL_REACTION, ("turn-1",)
    )
    a = accept_proposals(packet, (self_only,))
    b = accept_proposals(packet, (external,))
    assert len(a) == len(b) == 1
    assert abs(a[0].association_delta) < abs(b[0].association_delta)
    assert a[0].basis is EvidenceBasis.SELF_ONLY


def test_dedup_and_ledger_replay_are_idempotent(tmp_path) -> None:
    packet = _packet()
    proposal = ReflectionProposal("t1", 0.5, -0.25, 0.8, EvidenceBasis.LATER_OUTCOME, ("turn-1",))
    accepted = accept_proposals(packet, (proposal,))
    ledger = IntrospectionLedger(tmp_path / "ledger.json", parent_digest="parent")
    ledger.record_review(packet, (proposal,), accepted=accepted)
    ledger.save()
    loaded = IntrospectionLedger.load(tmp_path / "ledger.json")
    assert loaded.accessibility_adjustments() == {"e1": accepted[0].association_delta}
    assert loaded.expression_adjustments() == {"e1": accepted[0].expression_delta}
    assert accept_proposals(packet, (proposal,), existing_dedup=loaded.dedup_keys) == ()
    assert loaded.parent_digest == "parent"


def test_invalid_role_and_abstention_contract() -> None:
    with pytest.raises(IntrospectionError):
        ArcPacket("arc", ({"role": "system", "content": "x"},), (), ())
    packet = _packet()
    with pytest.raises(IntrospectionError):
        ReflectionProposal("t1", 0.1, 0, 0.5, EvidenceBasis.SELF_ONLY, abstain=True)
    assert accept_proposals(
        packet,
        (ReflectionProposal("t1", 0, 0, 0.0, EvidenceBasis.INSUFFICIENT, abstain=True),),
    ) == ()


def test_controller_loads_persisted_ledger_at_saa_boundary(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "subject.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(True, True, True, True, True, True),
        host_binding=FakeHost().fingerprint().to_dict(),
    )
    ledger = IntrospectionLedger(tmp_path / "ledger.json")
    packet = _packet()
    proposal = ReflectionProposal(
        "t1", 0.5, 0, 0.8, EvidenceBasis.EXTERNAL_REACTION, ("turn-1",)
    )
    accepted = accept_proposals(packet, (proposal,))
    ledger.record_review(packet, (proposal,), accepted=accepted)
    ledger.save()
    prepared = ResponseController(store, instance, FakeHost()).prepare_with_introspection(
        TurnIntent(
            "unrelated context",
            memory="graph",
            selection_policy="field-saa-v1",
            field_seed=7,
            operation_id="ledger-boundary",
        ),
        str(ledger.path),
    )
    assert prepared.intent.field_adjustments == ledger.accessibility_adjustments()
    assert prepared.intent.expression_adjustments == ledger.expression_adjustments()


def test_expression_adjustment_is_applied_after_accessibility_selection() -> None:
    concepts = (
        GraphConcept("a", "passive supply", "concept"),
        GraphConcept("b", "soil moisture", "concept"),
    )
    edges = (GraphEdge("e1", "a", "b", "maintains"),)
    state = LearnerState(
        edge_states=(EdgeState("e1", accessibility=700_000, support=700_000),)
    )
    baseline = compute_saa_field("passive supply", concepts, edges, state, field_seed=17)
    reduced = compute_saa_field(
        "passive supply", concepts, edges, state, field_seed=17,
        expression_adjustments={"e1": -500_000},
    )
    assert reduced.selected_landing == baseline.selected_landing == "e1"
    assert reduced.accessibility_distribution == baseline.accessibility_distribution
    assert reduced.total_pressure < baseline.total_pressure
    assert dict(reduced.expression_adjustments) == {"e1": -500_000}


def test_arc_slices_keep_continuous_subject_together() -> None:
    history = [
        ("My plants are drying.", "How often do you water?"),
        ("The pots are in strong sun.", "A reservoir could help."),
        ("I can check them on Sunday.", "That gives you a maintenance window."),
        ("The soil is still warm.", "Shade may reduce stress."),
    ]
    assert [item[1:3] for item in _arc_slices("P3-001", history, [])] == [(0, 4)]


def test_arc_slices_close_on_explicit_topic_pivot() -> None:
    history = [
        ("My plants are drying.", "How often do you water?"),
        ("The pots are in strong sun.", "A reservoir could help."),
        ("Anyway, I need to pack for a road trip.", "How long is the trip?"),
        ("I have one bag.", "Choose the essentials first."),
    ]
    assert [item[1:3] for item in _arc_slices("P3-002", history, [])] == [(0, 2), (2, 4)]


def test_arc_slices_are_replay_deterministic() -> None:
    history = [("A topic continues.", "A response."), ("More detail.", "Another response.")]
    assert _arc_slices("P3-003", history, []) == _arc_slices("P3-003", history, [])
