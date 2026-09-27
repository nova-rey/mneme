from __future__ import annotations

import json

import pytest

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
