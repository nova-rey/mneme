from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from mneme.controller import ResponseController, TurnIntent
from mneme.development import (
    ArcPacket,
    EvidenceBasis,
    FilingLevel,
    IntrospectionError,
    IntrospectionLedger,
    ReflectionProposal,
    ReviewTarget,
    accept_proposals,
    filing_request,
    filing_system_prompt,
    parse_filing,
    parse_proposals,
    reflection_request,
    reflection_system_prompt,
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


def test_compact_review_request_uses_bounded_numbered_answer_bank() -> None:
    packet = ArcPacket(
        "arc-choices",
        _packet().messages,
        _packet().exposures,
        (
            ReviewTarget("opaque-1", "e1", "maintenance", ("turn-1",)),
            ReviewTarget("opaque-2", "e2", "recovery", ("turn-1",)),
        ),
    )
    request = review_request(packet, compact_targets=True)
    assert request["targets"] == [
        {"choice": 1, "context": "maintenance"},
        {"choice": 2, "context": "recovery"},
    ]
    assert "opaque-1" not in json.dumps(request)
    assert "edge_key" not in json.dumps(request)


def test_round_one_is_prose_reflection_and_round_two_is_clerical() -> None:
    packet = _packet()
    first = reflection_request(packet)
    assert first["messages"] == [dict(item) for item in packet.messages]
    assert "edge_key" not in json.dumps(first)
    assert "JSON" in reflection_system_prompt()
    second = filing_request(packet, "The passive supply was useful but its expression was neutral.")
    assert second["reflection"].startswith("The passive supply")
    assert second["target_answer_bank"] == [{"number": 1, "context": "maintenance"}]
    assert "clerical" in filing_system_prompt()


def test_compact_filing_resolves_target_and_maps_bounded_ordinals() -> None:
    proposal = parse_filing(
        '{"target":1,"association":2,"expression":-1,"confidence":4}',
        _packet(),
        level=FilingLevel.COMPACT_JSON,
        valid_evidence_refs={"turn-1"},
    )[0]
    assert proposal.target_alias == "t1"
    assert proposal.association_effect == 1.0
    assert proposal.expression_effect == -0.5
    assert proposal.confidence == 1.0


@pytest.mark.parametrize(
    ("level", "value"),
    [
        (
            FilingLevel.MULTIPLE_CHOICE_JSON,
            '{"target":1,"effect":"B","expression":"D","confidence":3}',
        ),
        (FilingLevel.KEY_VALUE, "TARGET: 1\nASSOCIATION: B\nEXPRESSION: D\nCONFIDENCE: 3"),
        (FilingLevel.MINIMAL, "1 B D 3"),
    ],
)
def test_round_two_small_forms_have_one_deterministic_parser(
    level: FilingLevel, value: str
) -> None:
    proposals = parse_filing(value, _packet(), level=level, valid_evidence_refs={"turn-1"})
    assert len(proposals) == 1
    assert proposals[0].target_alias == "t1"
    assert proposals[0].association_effect == -0.5
    assert proposals[0].expression_effect == 0.5


def test_round_two_abstention_is_safe_and_does_not_require_target_ids() -> None:
    assert (
        parse_filing(
            '{"target":0,"association":0,"expression":0,"confidence":0}',
            _packet(),
            level=FilingLevel.COMPACT_JSON,
        )
        == ()
    )


def test_round_two_rejects_invented_target_and_illegal_values() -> None:
    with pytest.raises(IntrospectionError):
        parse_filing(
            '{"target":2,"association":0,"expression":0,"confidence":0}',
            _packet(),
            level=FilingLevel.COMPACT_JSON,
        )
    with pytest.raises(IntrospectionError):
        parse_filing(
            '{"target":1,"association":9,"expression":0,"confidence":0}',
            _packet(),
            level=FilingLevel.COMPACT_JSON,
        )


@pytest.mark.parametrize(
    ("name", "filing", "expects_adjustment"),
    [
        ("positive", '{"target":1,"association":2,"expression":1,"confidence":4}', True),
        ("negative", '{"target":1,"association":-2,"expression":-1,"confidence":4}', True),
        ("expression-only", '{"target":1,"association":0,"expression":-2,"confidence":4}', True),
        ("neutral", '{"target":1,"association":0,"expression":0,"confidence":0}', False),
        ("insufficient", '{"target":0,"association":0,"expression":0,"confidence":0}', False),
    ],
)
def test_round_two_filing_reaches_bounded_state_mutation_cases(
    name: str, filing: str, expects_adjustment: bool
) -> None:
    packet = _packet()
    proposals = parse_filing(filing, packet, level=FilingLevel.COMPACT_JSON)
    accepted = accept_proposals(packet, proposals)
    assert bool(accepted) is expects_adjustment, name
    if name == "expression-only":
        assert accepted[0].association_delta == 0
        assert accepted[0].expression_delta < 0


def test_round_two_malformed_filing_abstains_safely_at_boundary() -> None:
    with pytest.raises(IntrospectionError):
        parse_filing("not a filing", _packet(), level=FilingLevel.COMPACT_JSON)


def test_parser_resolves_numbered_target_without_exposing_opaque_alias() -> None:
    packet = ArcPacket(
        "arc-choices",
        _packet().messages,
        _packet().exposures,
        (
            ReviewTarget("opaque-1", "e1", "maintenance", ("turn-1",)),
            ReviewTarget("opaque-2", "e2", "recovery", ("turn-1",)),
        ),
    )
    proposals = parse_proposals(
        {
            "assessments": [
                {
                    "target_choice": 2,
                    "association_effect": -0.4,
                    "expression_effect": 0.2,
                    "confidence": 0.8,
                    "basis": "EXTERNAL_REACTION",
                    "evidence_refs": ["turn-1"],
                    "reason": "The second exposed association was unwelcome.",
                }
            ]
        },
        packet,
        valid_evidence_refs={"turn-1"},
    )
    assert proposals[0].target_alias == "opaque-2"
    assert (
        parse_proposals(
            {"assessments": [{"target_alias": "T1", "basis": "INSUFFICIENT"}]},
            packet,
        )[0].target_alias
        == "opaque-1"
    )


def test_parser_rejects_out_of_range_numbered_target() -> None:
    with pytest.raises(IntrospectionError):
        parse_proposals(
            {"assessments": [{"target_choice": 3}]},
            ArcPacket(
                "arc-choice",
                _packet().messages,
                _packet().exposures,
                (ReviewTarget("opaque-1", "e1", "maintenance", ("turn-1",)),),
            ),
        )


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
    with pytest.raises(IntrospectionError, match="no assessments list"):
        parse_proposals({"target_choice": 1}, packet)


def test_self_only_is_bounded_and_external_can_be_stronger() -> None:
    packet = _packet()
    self_only = ReflectionProposal("t1", 1.0, 1.0, 1.0, EvidenceBasis.SELF_ONLY, ("turn-1",))
    external = ReflectionProposal("t1", 1.0, 1.0, 1.0, EvidenceBasis.EXTERNAL_REACTION, ("turn-1",))
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


def test_ledger_preserves_two_round_review_without_enabling_ordinary_learning(tmp_path) -> None:
    packet = _packet()
    proposal = ReflectionProposal("t1", 0.5, 0.0, 0.8, EvidenceBasis.SELF_ONLY, ("turn-1",))
    accepted = accept_proposals(packet, (proposal,))
    ledger = IntrospectionLedger(tmp_path / "ledger.json")
    ledger.record_review(
        packet,
        (proposal,),
        accepted=accepted,
        review_metadata={
            "reflection": "The association was useful.",
            "filing": '{"target":1,"association":1}',
            "ordinary_learning": True,
        },
    )
    ledger.save()
    row = json.loads((tmp_path / "ledger.json").read_text())["reviews"][0]
    assert row["reflection"] == "The association was useful."
    assert row["filing"].startswith("{")
    assert row["ordinary_learning"] is False


def test_invalid_role_and_abstention_contract() -> None:
    with pytest.raises(IntrospectionError):
        ArcPacket("arc", ({"role": "system", "content": "x"},), (), ())
    packet = _packet()
    with pytest.raises(IntrospectionError):
        ReflectionProposal("t1", 0.1, 0, 0.5, EvidenceBasis.SELF_ONLY, abstain=True)
    assert (
        accept_proposals(
            packet,
            (ReflectionProposal("t1", 0, 0, 0.0, EvidenceBasis.INSUFFICIENT, abstain=True),),
        )
        == ()
    )


def test_controller_loads_persisted_ledger_at_saa_boundary(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "subject.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(True, True, True, True, True, True),
        host_binding=FakeHost().fingerprint().to_dict(),
    )
    ledger = IntrospectionLedger(tmp_path / "ledger.json")
    packet = _packet()
    proposal = ReflectionProposal("t1", 0.5, 0, 0.8, EvidenceBasis.EXTERNAL_REACTION, ("turn-1",))
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
    state = LearnerState(edge_states=(EdgeState("e1", accessibility=700_000, support=700_000),))
    baseline = compute_saa_field("passive supply", concepts, edges, state, field_seed=17)
    reduced = compute_saa_field(
        "passive supply",
        concepts,
        edges,
        state,
        field_seed=17,
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
