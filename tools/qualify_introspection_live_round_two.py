#!/usr/bin/env python3
"""Live Gemma qualification for introspection Round Two filing contracts.

This is a read-only qualification harness. It reads archived packet copies, runs
an unconstrained reflection followed by one of six bounded filing interfaces,
and writes compact JSON with every live model output and timing record. It never
opens a subject database, mutates a ledger, or changes historical P3 artifacts.

The local MSI Gemma host is reached through the existing RemoteLlamaHost adapter.
Use --live only after the host health probe succeeds.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.development import ArcPacket, ReviewTarget

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_p23_cross_thread import RemoteLlamaHost

DEFAULT_ARCHIVE = Path(
    "docs/receipts/MNEME_P3_Introspection_100_Thread_Run_20261001_r11/"
    "experiments/p3-introspect-100/revisions/1/runs/"
    "p3-introspect-100-20261001-r11/introspection"
)
DEFAULT_DESTINATION = Path(
    "docs/receipts/MNEME_Introspection_Round_Two_Live_Gemma_Qualification_20261002.json"
)

LEVELS = ("full_json", "compact_json", "multiple_choice_json", "key_value", "minimal", "microcall")

REFLECTION_SYSTEM = (
    "This is private internal reflection about a completed conversational arc. "
    "Review your own immediately preceding interaction and the supplied associative "
    "framings. Ordinary developmental learning is paused during this review. Think "
    "naturally in concise prose about which associations were useful, harmful, "
    "distracting, neutral, uncertain, worth expressing, or better left latent. "
    "Ground the reflection in the supplied interaction. Do not invent targets, "
    "feedback, outcomes, or hidden reasoning. This is not a database form: do not "
    "output JSON, aliases, edge IDs, evidence-reference syntax, or database vocabulary."
)


@dataclass(frozen=True)
class Fixture:
    name: str
    packet: ArcPacket
    expected_class: str | None = None


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


def _synthetic(
    name: str, arc: str, outcome: str, *, expected: str | None, targets: int = 1
) -> Fixture:
    messages = (
        {"role": "user", "content": "I tried the arrangement while away."},
        {"role": "assistant", "content": "A passive arrangement may maintain the resource."},
        {"role": "user", "content": outcome},
    )
    exposures = tuple(
        {"turn_ref": f"turn-{i}", "payload": p, "context": c}
        for i, (p, c) in enumerate(
            (("passive maintenance", "maintains"), ("fallback option", "supports"))[:targets]
        )
    )
    packet_targets = tuple(
        ReviewTarget(f"opaque-{i}", f"edge:{i}", c, (f"turn-{i}",))
        for i, c in enumerate(("maintains", "supports")[:targets])
    )
    return Fixture(
        name,
        ArcPacket(arc, messages, exposures, packet_targets, False, f"fixture-{name}"),
        expected,
    )


def load_fixtures(archive: Path, count: int = 8) -> list[Fixture]:
    paths = sorted(archive.glob("review-*.json"))
    packets = [_packet_from_review(p) for p in paths]
    useful = [p for p in packets if p.targets and p.exposures]
    fixtures: list[Fixture] = [
        _synthetic(
            "useful-positive",
            "synthetic-positive",
            "It worked well and kept the resource available.",
            expected="positive",
        ),
        _synthetic(
            "harmful-distracting",
            "synthetic-negative",
            "It failed badly and distracted me from the real issue.",
            expected="negative",
        ),
        _synthetic(
            "neutral",
            "synthetic-neutral",
            "I noticed it but have no clear outcome yet.",
            expected="neutral",
        ),
        _synthetic(
            "insufficient",
            "synthetic-insufficient",
            "I have not tried it, so I cannot tell.",
            expected="insufficient",
        ),
        _synthetic(
            "competing-targets",
            "synthetic-competing",
            "One part helped, but the other was distracting.",
            expected=None,
            targets=2,
        ),
        _synthetic(
            "expression-only",
            "synthetic-expression",
            "The idea was useful internally, but saying it aloud confused the plan.",
            expected=None,
        ),
    ]
    fixtures.extend(
        Fixture(f"archived-{i + 1}", p, None)
        for i, p in enumerate(useful[: max(0, count - len(fixtures))])
    )
    if not any(not p.exposures for p in packets):
        fixtures.append(
            _synthetic(
                "no-target",
                "synthetic-no-target",
                "There is no association to review.",
                expected="no_target",
            )
        )
    else:
        empty = next(p for p in packets if not p.exposures)
        fixtures.append(Fixture("archived-no-target", empty, "no_target"))
    return fixtures[:count]


def reflection_request(packet: ArcPacket) -> dict[str, Any]:
    return {
        "arc_id": packet.arc_id,
        "messages": [dict(item) for item in packet.messages],
        "recorded_associations": [
            {
                "target_number": i,
                "association_context": target.context,
                "exposure_refs": list(target.exposure_refs),
                "exposures": [
                    {k: v for k, v in exposure.items() if k in {"turn_ref", "payload", "context"}}
                    for exposure in packet.exposures
                    if not target.exposure_refs
                    or str(exposure.get("turn_ref")) in target.exposure_refs
                ],
            }
            for i, target in enumerate(packet.targets, 1)
        ],
        "missing_aftermath": packet.missing_aftermath,
    }


def _answer_bank(packet: ArcPacket) -> str:
    targets = "\n".join(f"{i}. {target.context}" for i, target in enumerate(packet.targets, 1))
    refs = sorted({str(x.get("turn_ref")) for x in packet.exposures if x.get("turn_ref")})
    return (
        "TARGETS (choose a number; 0=abstain):\n"
        f"{targets or '0. None'}\nEVIDENCE LABELS: {refs or ['none']}"
    )


def filing_prompt(level: str, packet: ArcPacket, reflection: str) -> tuple[str, str]:
    bank = _answer_bank(packet)
    context = f"{bank}\n\nROUND-ONE REFLECTION:\n{reflection[:12000]}"
    common = (
        "Translate the opinion you just expressed into the requested filing only. "
        "This is clerical transcription, not a new reflection. Never invent a target, "
        "identifier, evidence reference, or vocabulary. Target 0 means abstain. "
        "Association and expression choices are A=-2, B=-1, C=0, D=+1, E=+2. "
        "Confidence is 0 none, 1 low, 2 medium, 3 high, 4 very high.\n\n"
    )
    if level == "full_json":
        form = (
            '{"target_choice":1,"association_effect":0,"expression_effect":0,'
            '"confidence":0,"basis":"INSUFFICIENT","evidence_refs":[],'
            '"abstain":false}'
        )
    elif level == "compact_json":
        form = '{"target":1,"association":"C","expression":"C","confidence":2}'
    elif level == "multiple_choice_json":
        form = '{"target":1,"effect":"C","expression":"C","confidence":2}'
    elif level == "key_value":
        form = "TARGET: 1\nASSOCIATION: C\nEXPRESSION: C\nCONFIDENCE: 2"
    elif level == "minimal":
        form = "1 C C 2"
    else:
        form = "One integer only for each question, in order."
    return context, common + f"Return only this form, with no prose:\n{form}"


def _clean_json(raw: str) -> Any:
    text = raw.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    left, right = text.find("{"), text.rfind("}")
    if left >= 0 and right > left:
        text = text[left : right + 1]
    return json.loads(text)


def _choice(v: Any, *, upper: bool = True) -> str:
    if isinstance(v, bool):
        raise ValueError("boolean is not a choice")
    if isinstance(v, (int, float)) and float(v).is_integer():
        n = int(v)
        if 0 <= n <= 4:
            return str(n)
    s = str(v).strip()
    return s.upper() if upper else s


def parse_filing(level: str, raw: str, packet: ArcPacket) -> dict[str, Any]:
    if level in {"full_json", "compact_json", "multiple_choice_json"}:
        data = _clean_json(raw)
        if not isinstance(data, dict):
            raise ValueError("filing is not object")
        target = data.get("target_choice", data.get("target", 0))
        assoc = data.get("association_effect", data.get("association", data.get("effect", "C")))
        expr = data.get("expression_effect", data.get("expression", "C"))
        confidence = data.get("confidence", 0)
        target_num = int(str(target))
        if target_num < 0 or target_num > len(packet.targets):
            raise ValueError("target out of answer-bank range")
        if isinstance(assoc, (int, float)):
            assoc_code = {-2: "A", -1: "B", 0: "C", 1: "D", 2: "E"}.get(int(assoc))
            if assoc_code is None:
                raise ValueError("association out of range")
        else:
            assoc_code = str(assoc).strip().upper()
        if isinstance(expr, (int, float)):
            expr_code = {-2: "A", -1: "B", 0: "C", 1: "D", 2: "E"}.get(int(expr))
            if expr_code is None:
                raise ValueError("expression out of range")
        else:
            expr_code = str(expr).strip().upper()
        if assoc_code not in "ABCDE" or expr_code not in "ABCDE":
            raise ValueError("illegal effect choice")
        conf = int(confidence)
        if not 0 <= conf <= 4:
            raise ValueError("confidence out of range")
        basis = str(data.get("basis", "INSUFFICIENT")).upper()
        refs = data.get("evidence_refs", [])
        if not isinstance(refs, list):
            raise ValueError("evidence refs not list")
        legal_refs = {str(x.get("turn_ref")) for x in packet.exposures if x.get("turn_ref")}
        if any(str(ref) not in legal_refs for ref in refs):
            raise ValueError("invented evidence reference")
        return {
            "target": target_num,
            "association": assoc_code,
            "expression": expr_code,
            "confidence": conf,
            "basis": basis,
            "evidence_refs": refs,
        }
    if level == "key_value":
        fields = {}
        for line in raw.strip().splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip().upper()] = value.strip()
        if set(fields) < {"TARGET", "ASSOCIATION", "EXPRESSION", "CONFIDENCE"}:
            raise ValueError("missing key/value field")
        return parse_filing(
            "multiple_choice_json",
            json.dumps(
                {
                    "target": fields["TARGET"],
                    "effect": fields["ASSOCIATION"],
                    "expression": fields["EXPRESSION"],
                    "confidence": fields["CONFIDENCE"],
                }
            ),
            packet,
        )
    if level == "minimal":
        parts = raw.strip().split()
        if len(parts) != 4:
            raise ValueError("minimal answer must have four fields")
        return parse_filing(
            "key_value",
            (
                f"TARGET: {parts[0]}\nASSOCIATION: {parts[1]}\n"
                f"EXPRESSION: {parts[2]}\nCONFIDENCE: {parts[3]}"
            ),
            packet,
        )
    raise ValueError("microcall requires per-question parser")


def parse_micro(raws: list[str], packet: ArcPacket) -> dict[str, Any]:
    vals = []
    for raw in raws:
        text = raw.strip()
        m = re.search(r"(?<!\d)([0-9])(?!(?:\d))", text)
        if not m:
            raise ValueError("microcall did not return one integer")
        vals.append(int(m.group(1)))
    if len(vals) != 4:
        raise ValueError("microcall field count")
    if vals[0] < 0 or vals[0] > len(packet.targets) or vals[1] > 4 or vals[2] > 4 or vals[3] > 4:
        raise ValueError("microcall value out of range")
    return {
        "target": vals[0],
        "association": "ABCDE"[vals[1]],
        "expression": "ABCDE"[vals[2]],
        "confidence": vals[3],
        "basis": "UNSPECIFIED",
        "evidence_refs": [],
    }


def _semantic_consistency(reflection: str, filing: dict[str, Any]) -> str:
    text = reflection.lower()
    assoc = filing.get("association")
    if assoc not in {"A", "B", "C", "D", "E"}:
        return "unknown"
    positive = any(
        x in text for x in ("useful", "helpful", "worked", "worth expressing", "beneficial")
    )
    negative = any(
        x in text for x in ("harmful", "distracting", "confusing", "avoid expressing", "unhelpful")
    )
    if positive and negative:
        return "mixed_or_review"
    if positive and assoc in {"A", "B"}:
        return "obvious_contradiction"
    if negative and assoc in {"D", "E"}:
        return "obvious_contradiction"
    return "not_obviously_contradictory"


def _reflection_quality(reflection: str, fixture: Fixture) -> dict[str, Any]:
    """Conservative mechanical reflection checks; not a semantic judge."""

    text = reflection.strip().lower()
    contexts = {target.context.lower() for target in fixture.packet.targets}
    mentions_context = bool(text and any(context in text for context in contexts))
    discusses_review = any(
        token in text
        for token in (
            "useful",
            "harmful",
            "distract",
            "neutral",
            "association",
            "framing",
            "express",
        )
    )
    return {
        "nonempty": bool(text),
        "mentions_supplied_context": mentions_context,
        "discusses_review_dimensions": discusses_review,
        "mechanical_specificity": bool(text) and (mentions_context or discusses_review),
    }


def _call(host: Any, request: GenerationRequest) -> dict[str, Any]:
    started = time.perf_counter()
    result = host.generate(request)
    latency = (time.perf_counter() - started) * 1000
    return {
        "content": result.content,
        "model_id": result.model_id,
        "provider": result.provider,
        "seed": result.seed,
        "latency_ms": result.latency_ms if result.latency_ms is not None else latency,
        "wall_latency_ms": latency,
        "finish_reason": result.finish_reason,
        "token_usage": result.token_usage,
        "raw_metadata": result.raw_metadata,
        "provenance": result.provenance,
    }


def evaluate_cell(
    host: Any, fixture: Fixture, level: str, seed: int, fallback: bool
) -> dict[str, Any]:
    reflection_call = _call(
        host,
        GenerationRequest(
            messages=(
                {
                    "role": "user",
                    "content": json.dumps(reflection_request(fixture.packet), ensure_ascii=False),
                },
            ),
            system=REFLECTION_SYSTEM,
            parameters={"temperature": 0.2, "top_p": 0.9, "max_new_tokens": 384},
            seed=seed,
        ),
    )
    reflection = str(reflection_call["content"])
    filing_prompt_body, filing_system = filing_prompt(level, fixture.packet, reflection)
    filing_calls = []
    parsed = None
    error = None
    if level == "microcall":
        questions = [
            "Which target number should be filed? Reply with one integer only (0=abstain).",
            "Association effect? Reply 0= -2, 1= -1, 2=0, 3=+1, 4=+2.",
            "Expression effect? Reply 0= -2, 1= -1, 2=0, 3=+1, 4=+2.",
            "Confidence? Reply 0=none, 1=low, 2=medium, 3=high, 4=very high.",
        ]
        for i, question in enumerate(questions):
            filing_calls.append(
                _call(
                    host,
                    GenerationRequest(
                        messages=(
                            {
                                "role": "user",
                                "content": (
                                    f"{_answer_bank(fixture.packet)}\n\n"
                                    f"ROUND-ONE REFLECTION:\n{reflection[:12000]}\n\n"
                                    f"{question}"
                                ),
                            },
                        ),
                        system="Answer only the requested single integer. No prose.",
                        parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 8},
                        seed=seed + 100 + i,
                    ),
                )
            )
        try:
            parsed = parse_micro([str(c["content"]) for c in filing_calls], fixture.packet)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    else:
        filing_calls.append(
            _call(
                host,
                GenerationRequest(
                    messages=({"role": "user", "content": filing_prompt_body},),
                    system=filing_system,
                    parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 192},
                    seed=seed + 1,
                ),
            )
        )
        try:
            parsed = parse_filing(level, str(filing_calls[0]["content"]), fixture.packet)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    fallback_call = None
    fallback_parsed = None
    fallback_error = None
    if error and fallback and level != "minimal":
        body, system = filing_prompt("minimal", fixture.packet, reflection)
        fallback_call = _call(
            host,
            GenerationRequest(
                messages=({"role": "user", "content": body},),
                system=system,
                parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 32},
                seed=seed + 2,
            ),
        )
        try:
            fallback_parsed = parse_filing("minimal", str(fallback_call["content"]), fixture.packet)
        except Exception as exc:
            fallback_error = f"{type(exc).__name__}: {exc}"
    return {
        "fixture": fixture.name,
        "arc_id": fixture.packet.arc_id,
        "level": level,
        "seed": seed,
        "expected_class": fixture.expected_class,
        "reflection": reflection_call,
        "filing": filing_calls,
        "first_attempt": {"valid": parsed is not None, "parsed": parsed, "error": error},
        "fallback": None
        if fallback_call is None
        else {
            "valid": fallback_parsed is not None,
            "parsed": fallback_parsed,
            "error": fallback_error,
            "call": fallback_call,
        },
        "eventual_valid": parsed is not None or fallback_parsed is not None,
        "semantic_consistency": _semantic_consistency(reflection, parsed or fallback_parsed or {}),
        "reflection_quality": _reflection_quality(reflection, fixture),
        "call_count": 1 + len(filing_calls) + (1 if fallback_call is not None else 0),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(pred: Callable[[dict[str, Any]], bool]) -> float:
        return sum(pred(r) for r in rows) / len(rows) if rows else 0.0

    latencies = [
        float(r["reflection"]["wall_latency_ms"])
        + sum(float(c["wall_latency_ms"]) for c in r["filing"])
        for r in rows
    ]
    return {
        "reviews": len(rows),
        "first_attempt_parse_rate": rate(lambda r: bool(r["first_attempt"]["valid"])),
        "target_valid_rate": rate(
            lambda r: bool(
                r["first_attempt"]["parsed"] and r["first_attempt"]["parsed"].get("target", 0) <= 8
            )
        ),
        "legal_value_rate": rate(lambda r: bool(r["first_attempt"]["valid"])),
        "eventual_valid_rate": rate(lambda r: bool(r["eventual_valid"])),
        "reflection_nonempty_rate": rate(lambda r: bool(str(r["reflection"]["content"]).strip())),
        "reflection_specificity_rate": rate(
            lambda r: bool(r["reflection_quality"]["mechanical_specificity"])
        ),
        "obvious_contradiction_count": sum(
            r["semantic_consistency"] == "obvious_contradiction" for r in rows
        ),
        "fallback_rate": rate(lambda r: r["fallback"] is not None),
        "average_calls_per_review": statistics.mean([r["call_count"] for r in rows]) if rows else 0,
        "median_wall_latency_ms": statistics.median(latencies) if latencies else 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    fixtures = load_fixtures(args.archive, args.fixtures)
    host = RemoteLlamaHost()
    result: dict[str, Any] = {
        "schema": "mneme.introspection.round-two.live-gemma-qualification.v1",
        "status": "RUNNING",
        "model": host.fingerprint().to_dict(),
        "historical_archive": str(args.archive),
        "historical_inputs_unchanged": True,
        "levels": list(LEVELS),
        "screening": {},
        "torture": {},
    }
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    # Screening: every level uses real reflection + real filing on the same
    # diverse bounded fixture set. Outputs are persisted after each level.
    for level in LEVELS:
        rows = [
            evaluate_cell(host, fixture, level, args.seed + i, fallback=False)
            for i, fixture in enumerate(fixtures)
        ]
        result["screening"][level] = {"summary": summarize(rows), "rows": rows}
        args.destination.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    # Pick by expressive frontier, then torture the selected level. Selection
    # is frozen from screening metrics and never tuned from torture outputs.
    chosen = max(
        LEVELS,
        key=lambda level: (
            result["screening"][level]["summary"]["first_attempt_parse_rate"],
            -LEVELS.index(level),
        ),
    )
    result["chosen_level"] = chosen
    torture_rows = []
    for i in range(args.torture_reviews):
        fixture = fixtures[i % len(fixtures)]
        torture_rows.append(
            evaluate_cell(host, fixture, chosen, args.seed + 10_000 + i, fallback=True)
        )
        if (i + 1) % 5 == 0:
            result["torture"] = {
                "level": chosen,
                "summary": summarize(torture_rows),
                "rows": torture_rows,
            }
            args.destination.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
    result["torture"] = {"level": chosen, "summary": summarize(torture_rows), "rows": torture_rows}
    result["status"] = "COMPLETE"
    args.destination.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--fixtures", type=int, default=8)
    parser.add_argument("--torture-reviews", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20_026_100)
    parser.add_argument(
        "--dry-run", action="store_true", help="validate packet loading without model calls"
    )
    args = parser.parse_args()
    if args.dry_run:
        fixtures = load_fixtures(args.archive, args.fixtures)
        print(json.dumps({"fixtures": [f.name for f in fixtures], "levels": LEVELS}, indent=2))
        return 0
    result = run(args)
    print(
        json.dumps(
            {
                "status": result["status"],
                "chosen_level": result.get("chosen_level"),
                "torture": result.get("torture", {}).get("summary"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
