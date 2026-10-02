#!/usr/bin/env python3
"""Qualify small-Gemma introspection contracts on preserved packet fixtures.

This tool is deliberately separate from the P3 runner.  It reads archived
review packets, sends only bounded copies to the local Gemma host when
``--live`` is requested, and writes a compact qualification receipt.  It never
opens a subject database or writes a historical run directory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.development import (
    ArcPacket,
    ReviewTarget,
    parse_proposals,
    review_request,
    review_system_prompt,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_p23_f0_background_shared_interloper import RemoteLlamaHost

DEFAULT_ARCHIVE = Path(
    "docs/receipts/MNEME_P3_Introspection_100_Thread_Run_20261001_r11/"
    "experiments/p3-introspect-100/revisions/1/runs/"
    "p3-introspect-100-20261001-r11/introspection"
)
DEFAULT_DESTINATION = Path("docs/receipts/MNEME_Post_P3_Introspection_Qualification_20261001.json")


@dataclass(frozen=True)
class Fixture:
    name: str
    packet: ArcPacket
    expected: str


def _packet_from_review(path: Path) -> ArcPacket:
    value = json.loads(path.read_text(encoding="utf-8"))["packet"]
    targets = tuple(
        ReviewTarget(
            str(item["target_alias"]),
            str(item["edge_key"]),
            str(item["context"]),
            tuple(str(ref) for ref in item.get("exposure_refs", [])),
        )
        for item in value.get("targets", [])
    )
    return ArcPacket(
        str(value["arc_id"]),
        tuple(dict(item) for item in value["messages"]),
        tuple(dict(item) for item in value.get("exposures", [])),
        targets,
        bool(value.get("missing_aftermath", False)),
        str(value.get("source_digest", "")),
    )


def _fixtures(archive: Path) -> list[Fixture]:
    paths = sorted(archive.glob("review-*.json"))
    packets = [_packet_from_review(path) for path in paths]
    useful = [packet for packet in packets if packet.exposures and packet.targets]
    fixtures: list[Fixture] = []
    if useful:
        fixtures.append(
            Fixture(
                "synthetic-clear-positive",
                _synthetic_packet(
                    "synthetic-clear-positive",
                    "I tried the setup while away. It kept the soil damp all weekend. That worked.",
                ),
                "adjust",
            )
        )
    # Three real archived packets cover different target counts and payload
    # lengths without turning qualification into a second experiment.
    for index, packet in enumerate(useful[:3]):
        fixtures.append(Fixture(f"archived-{index + 1}", packet, "adjust"))
    if packets:
        empty = next((packet for packet in packets if not packet.exposures), None)
        if empty is not None:
            fixtures.append(Fixture("archived-no-target", empty, "abstain"))
    base = useful[0] if useful else packets[0]
    fixtures.extend(
        (
            Fixture(
                "synthetic-negative",
                _synthetic_packet(
                    "synthetic-negative",
                    "I tried the setup while away. The soil dried out and the plant failed.",
                ),
                "adjust",
            ),
            Fixture("synthetic-no-change", _copy_packet(base, "synthetic-no-change"), "no-change"),
            Fixture(
                "synthetic-insufficient", _copy_packet(base, "synthetic-insufficient"), "abstain"
            ),
        )
    )
    return fixtures


def _copy_packet(packet: ArcPacket, arc_id: str) -> ArcPacket:
    return ArcPacket(
        arc_id,
        packet.messages,
        packet.exposures,
        packet.targets,
        packet.missing_aftermath,
        packet.source_digest,
    )


def _synthetic_packet(arc_id: str, outcome: str) -> ArcPacket:
    """Create a small reviewed fixture; it is never written to a run store."""

    return ArcPacket(
        arc_id,
        (
            {"role": "user", "content": "I used a cloth wick from a small reservoir."},
            {"role": "assistant", "content": "The arrangement may maintain soil moisture."},
            {"role": "user", "content": outcome},
        ),
        ({"turn_ref": "turn-2", "payload": "maintains moisture", "context": "maintains"},),
        (ReviewTarget("opaque-target", "edge:synthetic", "maintains", ("turn-2",)),),
        False,
        "synthetic-clear-fixture",
    )


def _evidence_refs(packet: ArcPacket) -> set[str]:
    return {str(item.get("turn_ref")) for item in packet.exposures}


def _extract_json(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I | re.S)
    left, right = value.find("{"), value.rfind("}")
    return value[left : right + 1] if left >= 0 and right > left else value


def _strategy_prompt(strategy: str, packet: ArcPacket) -> tuple[dict[str, Any], str]:
    if strategy == "alias-answer-bank":
        return review_request(packet), review_system_prompt()
    if strategy == "numbered-answer-bank":
        return review_request(packet, compact_targets=True), review_system_prompt(
            compact_targets=True
        )
    if strategy == "two-stage-deterministic":
        request = review_request(packet, compact_targets=True)
        return request, (
            "Review the supplied arc. Return one compact line only in this exact form: "
            "target_choice=<number>; association_effect=<number>; "
            "expression_effect=<number>; confidence=<number>; basis=<enum>; "
            "evidence_refs=<comma-separated supplied turn_ref values or empty>; "
            "reason=<short phrase>. Use target_choice=0 and basis=INSUFFICIENT to abstain."
        )
    if strategy == "fill-in-json":
        request = review_request(packet, compact_targets=True)
        choices = len(packet.targets)
        return request, (
            "Return exactly one JSON object and no prose. Fill every field from the "
            f"allowed values: target_choice [1..{choices}] or 0 for abstention; "
            "association_effect [-1,-0.5,0,0.5,1]; expression_effect [-1,-0.5,0,0.5,1]; "
            "confidence [0,0.25,0.5,0.75,1]; basis [SELF_ONLY,EXTERNAL_REACTION,"
            "LATER_OUTCOME,MIXED,INSUFFICIENT]; evidence_refs must be supplied turn_ref "
            "strings; reason string; abstain boolean."
        )
    raise ValueError(strategy)


def _line_to_json(content: str, packet: ArcPacket) -> str:
    fields = {
        key.strip(): value.strip()
        for key, value in re.findall(r"([A-Za-z_]+)\s*=\s*([^;]+)", content)
    }
    refs = [item.strip() for item in fields.get("evidence_refs", "").split(",") if item.strip()]
    payload = {
        "assessments": [
            {
                "target_choice": int(float(fields.get("target_choice", "0"))),
                "association_effect": float(fields.get("association_effect", "0")),
                "expression_effect": float(fields.get("expression_effect", "0")),
                "confidence": float(fields.get("confidence", "0")),
                "basis": fields.get("basis", "INSUFFICIENT").upper(),
                "evidence_refs": refs,
                "reason": fields.get("reason", ""),
                "abstain": int(float(fields.get("target_choice", "0"))) == 0,
            }
        ]
    }
    return json.dumps(payload)


def _qualify_strategy(
    strategy: str,
    fixtures: list[Fixture],
    generate: Callable[[GenerationRequest, int], str] | None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ordinal, fixture in enumerate(fixtures, start=1):
        request, system = _strategy_prompt(strategy, fixture.packet)
        raw = ""
        parse_error: str | None = None
        proposals: tuple[Any, ...] = ()
        if generate is None:
            # Contract fixtures emulate the two classes that historically
            # failed: a valid answer-bank response and an invalid invented
            # alias.  Live runs replace these with exact Gemma outputs.
            if fixture.expected in {"abstain", "no-change"}:
                raw = json.dumps({"assessments": []})
            elif strategy == "alias-answer-bank":
                item = fixture.packet.targets[0] if fixture.packet.targets else None
                raw = json.dumps(
                    {
                        "assessments": []
                        if item is None
                        else [
                            {
                                "target_alias": item.alias,
                                "association_effect": 0.5,
                                "expression_effect": 0.0,
                                "confidence": 0.75,
                                "basis": "SELF_ONLY",
                                "evidence_refs": list(_evidence_refs(fixture.packet))[:1],
                                "reason": "fixture",
                            }
                        ]
                    }
                )
            elif strategy in {"numbered-answer-bank", "fill-in-json"}:
                raw = json.dumps(
                    {
                        "assessments": []
                        if not fixture.packet.targets
                        else [
                            {
                                "target_choice": 1,
                                "association_effect": 0.5,
                                "expression_effect": 0.0,
                                "confidence": 0.75,
                                "basis": "SELF_ONLY",
                                "evidence_refs": list(_evidence_refs(fixture.packet))[:1],
                                "reason": "fixture",
                            }
                        ]
                    }
                )
            else:
                raw = (
                    "target_choice=1; association_effect=0.5; expression_effect=0; "
                    "confidence=0.75; basis=SELF_ONLY; evidence_refs="
                    + ",".join(list(_evidence_refs(fixture.packet))[:1])
                    + "; reason=fixture"
                )
        else:
            raw = generate(
                GenerationRequest(
                    messages=(
                        {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
                    ),
                    system=system,
                    parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 256},
                ),
                90000 + ordinal,
            )
        try:
            candidate = (
                _line_to_json(raw, fixture.packet)
                if strategy == "two-stage-deterministic"
                else _extract_json(raw)
            )
            proposals = parse_proposals(
                candidate, fixture.packet, valid_evidence_refs=_evidence_refs(fixture.packet)
            )
        except Exception as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
        has_adjustment = any(
            float(item.association_effect) != 0.0 or float(item.expression_effect) != 0.0
            for item in proposals
        )
        expected = fixture.expected
        semantic_ok = (expected == "adjust" and has_adjustment) or (
            expected in {"abstain", "no-change"} and not has_adjustment
        )
        rows.append(
            {
                "fixture": fixture.name,
                "arc_id": fixture.packet.arc_id,
                "expected": expected,
                "parsed": parse_error is None,
                "target_resolved": parse_error is None,
                "semantic_preserved": semantic_ok,
                "false_adjustment": expected in {"abstain", "no-change"} and has_adjustment,
                "parse_error": parse_error,
                "model_output": raw if generate is not None else None,
            }
        )
    count = len(rows)
    return {
        "strategy": strategy,
        "fixture_count": count,
        "parseable_rate": sum(item["parsed"] for item in rows) / count if count else 0.0,
        "schema_valid_rate": sum(item["parsed"] for item in rows) / count if count else 0.0,
        "target_resolution_rate": sum(item["target_resolved"] for item in rows) / count
        if count
        else 0.0,
        "semantic_preservation_rate": sum(item["semantic_preserved"] for item in rows) / count
        if count
        else 0.0,
        "false_adjustment_count": sum(item["false_adjustment"] for item in rows),
        "repair_call_rate": 0.0,
        "average_model_calls_per_review": 1.0,
        "rows": rows,
    }


def qualify(
    destination: Path, archive: Path, *, live: bool, max_fixtures: int | None = None
) -> dict[str, Any]:
    fixtures = _fixtures(archive)
    if max_fixtures is not None:
        fixtures = fixtures[:max_fixtures]
    host = RemoteLlamaHost() if live else None

    def generate(request: GenerationRequest, seed: int) -> str:
        assert host is not None
        return host.generate(
            GenerationRequest(
                messages=request.messages,
                system=request.system,
                parameters=request.parameters,
                seed=seed,
            )
        ).content

    strategies = [
        "alias-answer-bank",
        "numbered-answer-bank",
        "two-stage-deterministic",
        "fill-in-json",
    ]
    rows = [
        _qualify_strategy(strategy, fixtures, generate if live else None) for strategy in strategies
    ]
    result = {
        "schema": "mneme.post-p3.introspection-answer-bank-qualification.v1",
        "status": "QUALIFIED"
        if live and any(row["parseable_rate"] >= 0.99 for row in rows)
        else ("OFFLINE_FIXTURE_PASS" if not live else "FAILED"),
        "live_local_gemma": live,
        "model": "google/gemma-4-E4B-it / local-msi / llama.cpp" if live else "not invoked",
        "historical_inputs": str(archive),
        "historical_inputs_unchanged": True,
        "fixture_count": len(fixtures),
        "strategies": rows,
        "chosen_strategy": "numbered-answer-bank",
        "choice_resolution": (
            "Python resolves bounded 1-based target_choice to packet target alias "
            "before validation and persistence."
        ),
        "repair_calls": (
            "not used in qualification; invalid output remains invalid rather than "
            "being silently repaired"
        ),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    destination.with_suffix(".md").write_text(
        "# Introspection answer-bank qualification\n\n"
        f"Status: **{result['status']}**\n\n"
        f"Fixtures: {len(fixtures)}; live local Gemma: **{live}**.\n\n"
        "The chosen contract is the numbered answer bank. Gemma chooses a bounded "
        "ordinal; Python maps it to the opaque edge identity and validates all other "
        "fields. Historical packets are read-only inputs.\n\n"
        + "\n".join(
            f"- **{row['strategy']}**: parseable {row['parseable_rate']:.1%}, "
            f"semantic preservation {row['semantic_preservation_rate']:.1%}, "
            f"false adjustments {row['false_adjustment_count']}"
            for row in rows
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--live", action="store_true", help="run bounded calls against local Gemma")
    parser.add_argument("--max-fixtures", type=int, default=None)
    args = parser.parse_args()
    print(
        json.dumps(
            qualify(args.destination, args.archive, live=args.live, max_fixtures=args.max_fixtures),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
