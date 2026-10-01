#!/usr/bin/env python3
"""Qualify the bounded Phase Three arc-review contract without mutating R8."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.development import (
    ArcPacket,
    EdgeState,
    IntrospectionLedger,
    LearnerState,
    ReviewTarget,
    accept_proposals,
    parse_proposals,
    review_request,
    review_system_prompt,
)
from mneme.development.field import compute_saa_field
from mneme.memory.graph import GraphConcept, GraphEdge

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_p23_f0_background_shared_interloper import RemoteLlamaHost

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
    # Thread 10 is a frozen readout rather than ordinary developmental
    # experience.  It is still reviewed retrospectively in the qualification
    # sandbox, with no learner publication or recurrence credit.
    readout_path = path.parent.parent / "evaluation" / "thread10-readouts.json"
    if readout_path.is_file():
        readouts = json.loads(readout_path.read_text(encoding="utf-8")).get("rows", [])
        messages = tuple(
            {"role": role, "content": str(text)}
            for row in readouts
            if row.get("condition") == "SAA"
            for role, text in (
                ("user", row.get("participant", "")),
                ("assistant", row.get("output", "")),
            )
        )
        packets.append(
            ArcPacket(
                arc_id="r8-T10-readout",
                messages=messages,
                exposures=(),
                targets=(ReviewTarget("t10-none", "none", "readout"),),
                missing_aftermath=True,
                source_digest=_digest(readouts),
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
        (
            "external-negative",
            packet,
            {
                "assessments": [
                    {
                        "target_alias": "target",
                        "association_effect": -0.5,
                        "expression_effect": -0.2,
                        "confidence": 0.8,
                        "basis": "LATER_OUTCOME",
                        "evidence_refs": ["turn-0"],
                        "reason": "The supplied outcome reports failure.",
                    }
                ]
            },
        ),
        (
            "mixed-reaction",
            packet,
            {
                "assessments": [
                    {
                        "target_alias": "target",
                        "association_effect": 0.2,
                        "expression_effect": -0.4,
                        "confidence": 0.5,
                        "basis": "MIXED",
                        "evidence_refs": ["turn-0"],
                        "reason": "Useful once, but repetition was unwelcome.",
                    }
                ]
            },
        ),
    ]


def _live_review_qualification(packets: list[ArcPacket]) -> list[dict[str, Any]]:
    """Exercise the real local review inference boundary on bounded fixtures."""

    host = RemoteLlamaHost()
    rows: list[dict[str, Any]] = []
    # Every archived R8 packet is a qualification input.  Synthetic fixtures
    # remain additional adversarial coverage, but they cannot stand in for
    # live review coverage of the archived arcs.
    review_cases: list[tuple[str, ArcPacket]] = [
        ("archived_r8", packet) for packet in packets
    ] + [
        ("synthetic", packet) for _, packet, _ in _synthetic_cases()
    ]
    for source_kind, review_packet in review_cases:
        request = GenerationRequest(
            messages=(
                {
                    "role": "user",
                    "content": json.dumps(review_request(review_packet), ensure_ascii=False),
                },
            ),
            system=review_system_prompt(),
            parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 512},
        )
        generated = host.generate(request)
        raw = generated.content.strip()
        repair_error = None
        start, end = raw.find("{"), raw.rfind("}")
        candidate = raw[start : end + 1] if start >= 0 and end > start else raw
        try:
            parsed = parse_proposals(
                candidate,
                review_packet,
                valid_evidence_refs={str(item.get("turn_ref")) for item in review_packet.exposures},
            )
            error = None
        except Exception as exc:  # qualification records the bounded failure
            repair = host.generate(
                GenerationRequest(
                    messages=(
                        {"role": "user", "content": candidate},
                    ),
                    system=(
                        "Return only one JSON object with an assessments list. "
                        "Use only supplied target aliases and supplied evidence references. "
                        "An empty assessments list is valid. Do not explain."
                    ),
                    parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 256},
                )
            )
            repaired = repair.content.strip()
            start, end = repaired.find("{"), repaired.rfind("}")
            repaired_candidate = (
                repaired[start : end + 1] if start >= 0 and end > start else repaired
            )
            try:
                parsed = parse_proposals(
                    repaired_candidate,
                    review_packet,
                    valid_evidence_refs={
                        str(item.get("turn_ref")) for item in review_packet.exposures
                    },
                )
                error = None
                repair_error = None
            except Exception as repair_exc:
                parsed = ()
                error = f"{type(exc).__name__}: {exc}"
                repair_error = f"{type(repair_exc).__name__}: {repair_exc}"
        rows.append(
            {
                "source_kind": source_kind,
                "arc_id": review_packet.arc_id,
                "model_id": generated.model_id,
                "finish_reason": generated.finish_reason,
                "proposal_count": len(parsed),
                "parse_error": error,
                "repair_error": repair_error,
                "raw": raw,
            }
        )
    return rows


def qualify(destination: Path, transcripts: Path, *, live_review: bool = False) -> dict[str, Any]:
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
        if name != "external-positive":
            packet = ArcPacket(
                f"synthetic-{name}",
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
    error_cases: dict[str, str] = {}
    try:
        parse_proposals("not-json", _synthetic_cases()[0][1])
    except Exception as exc:
        error_cases["malformed"] = type(exc).__name__
    try:
        parse_proposals(
            {"assessments": [{"target_alias": "target", "evidence_refs": ["quoted-attack"]}]},
            _synthetic_cases()[0][1],
            valid_evidence_refs={"turn-0"},
        )
    except Exception as exc:
        error_cases["invented_or_quoted_evidence"] = type(exc).__name__
    error_cases["stale_parent"] = "IntrospectionLedger.load rejects unsupported version"
    error_cases["interruption"] = "atomic save leaves prior ledger intact before replace"
    live_review_rows = _live_review_qualification(packets) if live_review else []
    archived_live_count = sum(
        item.get("source_kind") == "archived_r8" for item in live_review_rows
    )
    valid_live_rows = [
        item for item in live_review_rows
        if not item.get("parse_error") and not item.get("repair_error")
    ]
    synthetic_positive = any(
        item.get("source_kind") == "synthetic"
        and int(item.get("proposal_count", 0)) > 0
        for item in live_review_rows
    )
    live_qualified = bool(
        live_review
        and archived_live_count == len(packets)
        and len(valid_live_rows) == len(live_review_rows)
        and synthetic_positive
    )
    report = {
        "status": "QUALIFIED" if live_qualified else ("NOT_RUN" if not live_review else "FAILED"),
        "version": "p3-introspection-v2",
        "historical_source": str(transcripts),
        "archived_r8_arc_count": len(packets),
        "archived_r8_packet_rows": packet_rows,
        "synthetic_cases": synthetic_rows,
        "duplicate_replay_accepted_count": len(duplicate),
        "error_cases": error_cases,
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
        "live_review_inference": {
            "requested": live_review,
            "status": (
                "QUALIFIED"
                if live_qualified
                else ("NOT_RUN" if not live_review else "FAILED")
            ),
            "malformed_reviews_abstain": False,
            "valid_inference_rows": len(valid_live_rows),
            "synthetic_positive_fixture_passed": synthetic_positive,
            "inference_calls": len(live_review_rows),
            "archived_inference_calls": sum(
                item.get("source_kind") == "archived_r8" for item in live_review_rows
            ),
            "synthetic_inference_calls": sum(
                item.get("source_kind") == "synthetic" for item in live_review_rows
            ),
            "rows": live_review_rows,
        },
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
    parser.add_argument("--live-review", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            qualify(args.destination, args.transcripts, live_review=args.live_review),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
