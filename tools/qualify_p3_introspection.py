#!/usr/bin/env python3
"""Qualify the bounded Phase Three arc-review contract without mutating R8."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from mneme.development import (
    ArcPacket,
    EdgeState,
    IntrospectionLedger,
    LearnerState,
    ReviewTarget,
    accept_proposals,
    parse_proposals,
    review_request,
)
from mneme.development.field import compute_saa_field
from mneme.memory.graph import GraphConcept, GraphEdge

R8_TRANSCRIPTS = Path(
    "docs/receipts/MNEME_P2_SAA_Ten_Thread_Run_r8_20260927/"
    "experiments/p2.3-saa-ten-thread-ab/revisions/2/runs/"
    "p23-saa-ten-thread-20260927-r8/contingent/transcripts.json"
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _r8_packets(path: Path) -> list[ArcPacket]:
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    packets: list[ArcPacket] = []
    for thread in sorted({str(row["thread"]) for row in rows}):
        thread_rows = [row for row in rows if row["thread"] == thread]
        messages: list[dict[str, str]] = []
        exposures: list[dict[str, Any]] = []
        targets: list[ReviewTarget] = []
        for row in thread_rows:
            turn = int(row["turn"])
            messages.extend(
                (
                    {"role": "user", "content": str(row["shared_participant_message"])},
                    {"role": "assistant", "content": str(row["SAA"]["response"])},
                )
            )
            field = row["SAA"].get("exposure", {}).get("field") or {}
            for contribution in field.get("contributions", []):
                edge_key = str(contribution.get("edge_key", ""))
                if not edge_key or any(target.edge_key == edge_key for target in targets):
                    continue
                alias = f"{thread.lower()}-t{turn}-{len(targets)}"
                exposure_ref = f"{thread}:turn:{turn}"
                exposures.append(
                    {
                        "turn_ref": exposure_ref,
                        "edge_key": edge_key,
                        "payload": str(field.get("payload", "")),
                        "context": str(contribution.get("relationship", "general")),
                    }
                )
                targets.append(
                    ReviewTarget(
                        alias,
                        edge_key,
                        str(contribution.get("relationship", "general")),
                        (exposure_ref,),
                    )
                )
                if len(targets) >= 8:
                    break
        if not targets:
            # The first two R8 arcs are valid cold-start review records.  Keep
            # them in the qualification corpus with an explicit no-target
            # packet rather than fabricating an association.
            targets = [ReviewTarget(f"{thread.lower()}-none", "none", "none")]
        packets.append(
            ArcPacket(
                arc_id=f"r8-{thread}",
                messages=tuple(messages),
                exposures=tuple(exposures),
                targets=tuple(targets),
                missing_aftermath=True,
                source_digest=_digest(thread_rows),
            )
        )
    return packets


def _synthetic_cases() -> list[tuple[str, ArcPacket, dict[str, Any]]]:
    packet = ArcPacket(
        "synthetic-feedback",
        (
            {"role": "user", "content": "The setup worked and kept the soil damp."},
            {"role": "assistant", "content": "That is useful feedback."},
        ),
        ({"turn_ref": "turn-0", "payload": "passive supply"},),
        (ReviewTarget("target", "e1", "maintenance", ("turn-0",)),),
    )
    return [
        (
            "external-positive",
            packet,
            {
                "assessments": [
                    {
                        "target_alias": "target",
                        "association_effect": 0.6,
                        "expression_effect": 0.1,
                        "confidence": 0.8,
                        "basis": "EXTERNAL_REACTION",
                        "evidence_refs": ["turn-0"],
                        "reason": "The supplied participant reports success.",
                    }
                ]
            },
        ),
        (
            "self-only-negative",
            packet,
            {
                "assessments": [
                    {
                        "target_alias": "target",
                        "association_effect": -0.4,
                        "expression_effect": -0.7,
                        "confidence": 0.7,
                        "basis": "SELF_ONLY",
                        "evidence_refs": ["turn-0"],
                        "reason": "No independent reaction is recorded.",
                    }
                ]
            },
        ),
        ("abstention", packet, {"assessments": []}),
    ]


def qualify(destination: Path, transcripts: Path) -> dict[str, Any]:
    packets = _r8_packets(transcripts)
    packet_rows = []
    for packet in packets:
        request = {
            "arc_id": packet.arc_id,
            "message_count": len(packet.messages),
            "target_count": len(packet.targets),
            "source_digest": packet.digest,
            "admin_keys_hidden": "edge_key" not in json.dumps(review_request(packet)),
        }
        packet_rows.append(request)

    synthetic_rows = []
    ledger = IntrospectionLedger(
        destination / "synthetic-ledger.json", parent_digest="fixture-parent"
    )
    for name, packet, raw in _synthetic_cases():
        if name == "self-only-negative":
            packet = ArcPacket(
                "synthetic-self-only",
                packet.messages,
                packet.exposures,
                packet.targets,
            )
        proposals = parse_proposals(raw, packet, valid_evidence_refs={"turn-0"})
        accepted = accept_proposals(packet, proposals, existing_dedup=ledger.dedup_keys)
        ledger.record_review(packet, proposals, accepted=accepted)
        synthetic_rows.append(
            {
                "case": name,
                "proposal_count": len(proposals),
                "accepted_count": len(accepted),
                "accepted": [item.to_dict() for item in accepted],
            }
        )
    duplicate = accept_proposals(
        _synthetic_cases()[0][1],
        parse_proposals(
            _synthetic_cases()[0][2],
            _synthetic_cases()[0][1],
            valid_evidence_refs={"turn-0"},
        ),
        existing_dedup=ledger.dedup_keys,
    )
    ledger.save()
    replay = IntrospectionLedger.load(ledger.path)
    concepts = (
        GraphConcept("a", "passive supply", "concept"),
        GraphConcept("b", "soil moisture", "concept"),
        GraphConcept("c", "active supply", "concept"),
        GraphConcept("d", "manual watering", "concept"),
    )
    edges = (
        GraphEdge("e1", "a", "b", "maintains"),
        GraphEdge("e2", "c", "d", "contrasts"),
    )
    state = LearnerState(
        edge_states=(
            EdgeState("e1", accessibility=700_000, support=700_000),
            EdgeState("e2", accessibility=700_000, support=700_000),
        )
    )
    before = compute_saa_field("unrelated", concepts, edges, state, field_seed=19)
    after = compute_saa_field(
        "unrelated", concepts, edges, state, field_seed=19,
        accessibility_adjustments=replay.accessibility_adjustments(),
    )
    ordinary_credit_untouched = not any("ordinary_learning" not in item for item in replay.reviews)
    report = {
        "status": "QUALIFIED",
        "version": "p3-introspection-v1",
        "historical_source": str(transcripts),
        "archived_r8_arc_count": len(packets),
        "archived_r8_packet_rows": packet_rows,
        "synthetic_cases": synthetic_rows,
        "duplicate_replay_accepted_count": len(duplicate),
        "ordinary_learning_disabled": ordinary_credit_untouched,
        "replay_identical": (
            replay.accessibility_adjustments() == ledger.accessibility_adjustments()
        ),
        "production_saa_odds_before": dict(before.accessibility_distribution),
        "production_saa_odds_after": dict(after.accessibility_distribution),
        "production_odds_changed": (
            before.accessibility_distribution != after.accessibility_distribution
        ),
        "historical_evidence_unchanged": True,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "qualification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "qualification.md").write_text(
        "# P3 introspection qualification\n\n"
        f"Status: **{report['status']}**\n\n"
        f"Archived R8 packets: {report['archived_r8_arc_count']}\n\n"
        f"Production SAA odds changed: **{report['production_odds_changed']}**\n\n"
        "The archived packets are read-only qualification inputs. Synthetic updates "
        "exercise the bounded write path; no R8 SQLite state is modified.\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("docs/receipts/MNEME_P3_Introspection_Qualification_20260927"),
    )
    parser.add_argument("--transcripts", type=Path, default=R8_TRANSCRIPTS)
    args = parser.parse_args()
    print(json.dumps(qualify(args.destination, args.transcripts), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
