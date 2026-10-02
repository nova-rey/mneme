#!/usr/bin/env python3
# ruff: noqa: E501
"""Bounded prospective Quinn/Gemma conversations; measurements never enter requests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from mneme.controller import ResponseController, TurnIntent
from mneme.development.episodes import (
    declared_conversation_arcs,
    persist_conversation_arc_progress,
)
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
    require_nonempty_message,
    subject_history,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.memory.interpretation import (
    MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
    InterpretationService,
    InterpretationValidationError,
)
from mneme.state.snapshots import fork_from_checkpoint
from mneme.state.storage import SQLiteStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_p23_cross_thread import RemoteGlinerHost, RemoteLlamaHost  # noqa: E402

CHECKPOINT = Path(
    "docs/receipts/MNEME_P2_SAA_Ten_Thread_Run_r8_20260927/snapshots/SAA-developed.sqlite3"
)
TURNS = 10
TOPICS = {
    "watering": {
        "opening": (
            "My balcony pots dry out while I am away for a weekend. I want a simple "
            "watering setup using a reservoir and cotton wick, but I worry it might "
            "give too much or too little water. How should I work through that?"
        ),
        "F": [
            "A two-hour trial shows the cotton wick gets wet but the soil surface stays dry. Ask how to tell surface dryness from failed delivery.",
            "Report the pot weighs 40 grams more after four hours, with no drainage. Ask what that evidence implies about delivery.",
            "A control pot without a wick lost 120 grams over the same warm afternoon. Ask how to compare inflow with evaporative demand.",
            "The reservoir is now below the pot and delivery slowed as its level fell. Ask how to stabilize the driving conditions without a pump.",
            "A wider cotton strip doubled delivery in a repeat trial. Ask how to choose strip width while allowing for cooler weather.",
            "The smaller pot has dense soil and remains wet overnight while the large pot dries. Ask how to separate the two water demands.",
            "Direct sun heats the reservoir and algae has begun growing. Ask how shading and an opaque cover fit the setup without blocking airflow.",
            "There are 1.5 liters available and measured total loss is 400 milliliters per day. Ask how to budget a three-day absence and reserve.",
            "Before leaving, the setup survives a full day but a wick sometimes slips from one pot. Ask how to secure it and make the final check.",
        ],
        "S": [
            "Remain worried that the cotton wick will deliver either too much or too little. Ask whether this basic approach is really dependable; add no test result.",
            "Say a reservoir seems helpful but does not settle the worry about overwatering versus drying out. Revisit how a wick could be trusted.",
            "Return to the same uncertainty about the cotton wick soaking the soil or leaving it dry. Ask whether the reservoir makes the risk worse.",
            "Acknowledge the explanation but say you still cannot picture a reliable middle ground between wet and dry. Reconsider the same wick setup.",
            "Wonder again whether relying on cotton to carry water is too uncertain. Keep the reservoir and pot arrangement unchanged; introduce no new constraint.",
            "Say that too much water worries you just as much as too little. Rephrase the concern about whether the wick will find the right balance.",
            "Circle back to whether the reservoir-and-wick approach is sensible for a weekend. You have no measurements or new practical evidence.",
            "Acknowledge that trying it is an option, but revisit the same doubt that the pot might end up soaked or dry. Do not claim a trial happened.",
            "Still hesitate about trusting a cotton wick and reservoir. Ask once more how to think about the same too-wet versus too-dry concern.",
        ],
    },
    "network": {
        "opening": (
            "A temperature sensor in our workshop sometimes disappears from the Wi-Fi dashboard. "
            "I am unsure whether its radio connection or its power supply is the problem. "
            "How should I narrow this down without replacing parts at random?"
        ),
        "F": [
            "The dashboard loses this sensor at 14:10 and 16:05, while two neighboring sensors stay online. Ask how that changes the first comparison.",
            "The missing sensor's uptime counter resets after each outage. Ask what this adds beyond a dashboard connection loss.",
            "A voltmeter records a short dip to 3.9 volts on its nominal five-volt supply during transmission. Ask how to isolate the cause of the dip.",
            "Replacing only the long USB cable removes the voltage dip, but one outage remains when the fan motor starts. Ask how to separate those effects.",
            "Moving the sensor supply to a separate outlet prevents resets during fan starts. Ask whether interference or shared supply loading remains more plausible.",
            "A battery-powered test avoids resets, yet the dashboard occasionally shows stale readings with uptime continuing. Ask how to distinguish stale data from another reset.",
            "Local logs show samples continue but publish acknowledgments time out. Ask which network-layer evidence to collect next.",
            "The access point log shows weak signal and retransmissions behind the metal cabinet; a temporary higher location improves both. Ask how to validate placement.",
            "A full shift with the shorter cable and higher placement has no resets or missed updates. Ask what to monitor before declaring the repair stable.",
        ],
        "S": [
            "Remain unsure whether Wi-Fi or power is responsible. Ask again which one to suspect, without measurements or new observations.",
            "Say replacing parts at random feels wasteful, but you still wonder whether the radio or supply is the culprit. Revisit the same choice.",
            "Acknowledge the suggested checks but return to the concern that either a connection issue or a power issue could make the dashboard lose it.",
            "Ask whether it is more sensible to think about Wi-Fi first or power first. You have not tried the checks and have no additional evidence.",
            "Say the uncertainty remains because an offline sensor could mean either weak Wi-Fi or unreliable power. Rephrase the same objection.",
            "Reconsider replacing the radio versus replacing the supply, then hesitate about random replacement. Keep all circumstances the same.",
            "Return to how difficult it is to tell power failure from disconnection using only the disappearing dashboard entry. Add no diagnostic result.",
            "Acknowledge that testing could help but revisit which possibility to start with, power or Wi-Fi. Do not invent a reason testing is impossible.",
            "Still worry that choosing the wrong component wastes effort. Ask again how to approach the same radio-versus-power uncertainty.",
        ],
    },
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def construction() -> dict[str, Any]:
    return {
        "version": "arc-measurement-construction-v1",
        "topics": TOPICS,
        "turns_per_conversation": TURNS,
        "conditions": ["F", "S"],
        "planned_calls": {"gemma": 40, "extraction": 40, "quinn": 36, "measurement": 0},
        "maximum_output_tokens": 47872,
        "seed_rule": "Gemma 74000 + topic_index*100 + turn; field 84000 + topic_index*100 + turn; matched across conditions",
        "history": "existing subject_history limit=2; Quinn sees latest participant and duplicated single Gemma reply in shared A/B slots",
        "arc_contract": "declared_conversation_arcs: constant topic for ten accepted turns",
        "state": "four independent forks of one immutable checkpoint; no assessment/publication/learner updates",
        "metric_definitions": {
            "window": 3,
            "maturity": "min(1,(accepted_arc_age-1)/5)",
            "C1": "maturity*(1-rolling_concept_novelty_mean)",
            "C2": "maturity*(1-(rolling_concept_novelty_mean+rolling_relationship_novelty_mean)/2)",
            "C3": "C2*context_HHI",
            "coverage": "require full semantic coverage; no fitting or retuning",
        },
        "limitations": [
            "Condition schedules are authored constructions, not independently judged quality labels.",
            "Frozen graph isolates measurement but excludes ongoing developmental adaptation.",
            "No topic control or repeated seed replication in this bounded experiment.",
        ],
    }


class RecordingHost:
    """Pass requests/results unchanged; record every attempted call before dispatch."""

    def __init__(self, host: Any, directory: Path, role: str) -> None:
        self.host, self.directory, self.role = host, directory, role
        self.calls = 0

    def fingerprint(self) -> Any:
        return self.host.fingerprint()

    def capabilities(self) -> Any:
        return self.host.capabilities()

    def generate(self, request: Any) -> Any:
        self.calls += 1
        path = self.directory / f"{self.role}-{self.calls:03d}.json"
        if path.exists():
            raise RuntimeError("refusing duplicate call coordinate")
        record = {"request": request.to_dict(), "status": "DISPATCHED"}
        write_json(path, record)
        result = self.host.generate(request)
        record.update(
            status="RETURNED",
            result={
                "content": result.content,
                "model_id": result.model_id,
                "provider": result.provider,
                "seed": result.seed,
                "effective_parameters": dict(result.effective_parameters),
                "raw_metadata": dict(result.raw_metadata),
                "provenance": dict(result.provenance),
                "finish_reason": result.finish_reason,
            },
        )
        write_json(path, record)
        return result


def frozen_state(store: SQLiteStore) -> dict[str, Any]:
    """Inspect scientific graph/learner content, excluding accepted-history bookkeeping."""
    tables = (
        "graph_concepts",
        "graph_edges",
        "graph_routes",
        "graph_snapshots",
        "learner_values",
        "learner_updates",
        "learner_snapshots",
    )
    existing = {row[0] for row in store.connection.execute("SELECT name FROM sqlite_master")}
    if not set(tables) <= existing:
        raise RuntimeError("checkpoint lacks required scientific state tables")
    return {
        name: digest(
            sorted(
                [list(row) for row in store.connection.execute(f'SELECT * FROM "{name}"')],
                key=lambda row: json.dumps(row, sort_keys=True),
            )
        )
        for name in tables
    }


def quinn_request(topic: str, condition: str, turn: int, pairs: list[tuple[str, str]]) -> Any:
    """Only Quinn receives the private turn instruction; Gemma receives its public text."""
    circumstance = TOPICS[topic][condition][turn - 2]
    thread = ThreadSpec(
        topic,
        TOPICS[topic]["opening"],
        (
            "Stay with the same broad practical problem. Write one plausible human message.",
            "Do not reveal private instructions, experiment labels, or ask for creative analogies.",
            "This turn's private circumstance: " + circumstance,
        ),
    )
    return build_shared_interloper_request(
        thread=thread,
        prior_participant=pairs[-1][0],
        responses={"A": pairs[-1][1], "B": pairs[-1][1]},
        turn=turn,
    )


def run(output: Path, checkpoint: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError("output must be a fresh directory; uncertain calls are never replayed")
    checkpoint_sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    plan = construction()
    plan["checkpoint"] = {"path": str(checkpoint), "sha256": checkpoint_sha}
    write_json(output / "construction.json", plan)
    if not os.environ.get("DEEPINFRA_TOKEN"):
        os.environ["DEEPINFRA_TOKEN"] = (
            Path("/home/nyx/.config/mneme/deepinfra_token").read_text().strip()
        )
    os.environ.setdefault("MNEME_MSI_GEMMA_URL", "http://100.115.208.48:64170/v1/chat/completions")
    os.environ.setdefault("MNEME_MSI_GLINER_URL", "http://100.115.208.48:64171/extract")
    raw_gemma, raw_extractor = RemoteLlamaHost(), RemoteGlinerHost()
    raw_quinn = DeepInfraQwenAssessorHost(
        token=None,
        model_id="Qwen/Qwen3-30B-A3B",
        model_family="Qwen3 30B A3B Instruct-role",
        upstream_model_id="Qwen/Qwen3-30B-A3B",
        quantization="provider-managed",
        context_length=40960,
    )
    write_json(
        output / "bindings.json",
        {
            "gemma": raw_gemma.fingerprint().to_dict(),
            "extraction": raw_extractor.fingerprint().to_dict(),
            "quinn": raw_quinn.fingerprint().to_dict(),
        },
    )
    records: list[dict[str, Any]] = []
    totals = {"gemma": 0, "extraction": 0, "quinn": 0}
    for topic_index, topic in enumerate(TOPICS):
        for condition in ("F", "S"):
            conversation = f"{topic}-{condition}"
            directory = output / conversation
            directory.mkdir()
            database = directory / "subject.sqlite3"
            instance = fork_from_checkpoint(checkpoint, database)
            gemma = RecordingHost(raw_gemma, directory / "calls", "gemma")
            extractor = RecordingHost(raw_extractor, directory / "calls", "extraction")
            quinn = RecordingHost(raw_quinn, directory / "calls", "quinn")
            pairs: list[tuple[str, str]] = []
            with SQLiteStore(database) as store:
                before = frozen_state(store)
                base_ordinal = int(store.current()["current_revision"])
                arc_map = declared_conversation_arcs(
                    tuple((base_ordinal + turn, topic) for turn in range(1, TURNS + 1)),
                    conversation_id=conversation,
                )
                controller = ResponseController(store, instance, gemma)
                interpretation = InterpretationService(
                    store,
                    instance,
                    extractor,
                    extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
                    allow_extractor_host_mismatch=True,
                )
                for turn in range(1, TURNS + 1):
                    participant = (
                        TOPICS[topic]["opening"]
                        if turn == 1
                        else require_nonempty_message(
                            quinn.generate(quinn_request(topic, condition, turn, pairs)).content,
                            role="Quinn",
                        )
                    )
                    if participant == "SHARED_ENVIRONMENT_DIVERGENCE":
                        raise RuntimeError("shared environment divergence; no regeneration")
                    prepared = controller.prepare(
                        TurnIntent(
                            current_input=participant,
                            mode="develop",
                            memory="graph",
                            session_messages=subject_history(pairs, current=participant)[:-1],
                            system=GEMMA_SYSTEM_PROMPT,
                            parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
                            seed=74000 + topic_index * 100 + turn,
                            field_seed=84000 + topic_index * 100 + turn,
                            selection_policy="field-saa-v1",
                            operation_id=f"arc-study-{conversation}-{turn}",
                        )
                    )
                    result = controller.execute(prepared)
                    response = require_nonempty_message(result.generation.content, role="Gemma")
                    ordinal = int(
                        store.connection.execute(
                            "SELECT accepted_revision FROM episodes WHERE episode_id=?",
                            (result.operation.episode_id,),
                        ).fetchone()[0]
                    )
                    arc = arc_map[ordinal]
                    persist_conversation_arc_progress(
                        store,
                        instance_id=instance,
                        conversation_id=conversation,
                        ordinal=0,
                        episode=arc,
                        turn_index=ordinal,
                        accepted_episode_id=result.operation.episode_id,
                        close=turn == TURNS,
                    )
                    receipt = interpretation.prepare(
                        result.operation.episode_id, operation_id=f"extract-{conversation}-{turn}"
                    )
                    interpretation.execute(receipt)
                    error = None
                    try:
                        residue = interpretation.validate(receipt).to_dict()
                    except InterpretationValidationError as exc:
                        residue, error = None, str(exc)
                    row = {
                        "conversation": conversation,
                        "condition": condition,
                        "turn": turn,
                        "ordinal": ordinal,
                        "arc": arc.to_dict(),
                        "accepted_turn_id": f"{conversation}:turn:{ordinal}",
                        "accepted_episode_id": result.operation.episode_id,
                        "operation_id": result.operation.operation_id,
                        "accepted_membership_count": turn,
                        "ordinal_basis": "episodes.accepted_revision; no publication between turns",
                        "actual_arc_pivot": False,
                        "pivot_basis": "constant declared topic; no inferred detector",
                        "residue": residue,
                        "extraction_error": error,
                        "field": prepared.field_result.to_dict() if prepared.field_result else None,
                        "considered": [item.to_dict() for item in prepared.considered],
                        "selected": [item.to_dict() for item in prepared.selected],
                        "applied": [item.to_dict() for item in prepared.applied],
                        "participant": participant,
                        "response": response,
                    }
                    records.append(row)
                    write_json(directory / f"turn-{turn:02d}.json", row)
                    write_json(output / "records.json", records)
                    pairs.append((participant, response))
                    print(
                        json.dumps(
                            {
                                "conversation": conversation,
                                "turn": turn,
                                "extraction": "valid" if residue is not None else "unavailable",
                            }
                        ),
                        flush=True,
                    )
                after = frozen_state(store)
                write_json(
                    directory / "frozen-state.json",
                    {"before": before, "after": after, "unchanged": before == after},
                )
                if before != after:
                    raise RuntimeError("scientific graph/learner changed without publication")
            for role, host in (("gemma", gemma), ("extraction", extractor), ("quinn", quinn)):
                totals[role] += host.calls
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != checkpoint_sha:
        raise RuntimeError("source checkpoint changed")
    summary = {
        "status": "COMPLETE",
        "turns": len(records),
        "calls": totals,
        "source_checkpoint_unchanged": True,
        "plan_digest": digest(plan),
    }
    write_json(output / "summary.json", summary)
    return summary


def replay(records_path: Path, output: Path) -> dict[str, Any]:
    """Produce deterministic matrices from recorded inputs, with no Host construction."""
    from mneme.experiments.arc_measurements import measure_conversation

    records = json.loads(records_path.read_text())
    matrix = measure_conversation(records, window=3)
    write_json(output / "matrix.json", matrix)
    columns = list(
        dict.fromkeys(
            key
            for row in matrix
            for key, value in row.items()
            if value is None or isinstance(value, (str, int, float, bool))
        )
    )
    with (output / "matrix.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(matrix)
    transcript = [
        "# Prospective Quinn/Gemma conversations",
        "",
        "Condition labels below are report metadata, never Gemma instructions.",
        "",
    ]
    for row in records:
        transcript.extend(
            [
                f"## {row['conversation']} / turn {row['turn']}",
                "",
                "**Quinn:** " + row["participant"],
                "",
                "**Gemma:** " + row["response"],
                "",
            ]
        )
    # Keep raw provider whitespace in records.json; normalize the readable export.
    rendered = "\n".join(line.rstrip() for line in "\n".join(transcript).splitlines())
    (output / "transcripts.md").write_text(rendered + "\n")
    return {
        "status": "REPLAYED",
        "turns": len(matrix),
        "records_digest": digest(records),
        "matrix_digest": digest(matrix),
        "provider_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--replay", type=Path, help="recorded JSON input; never calls providers")
    parser.add_argument("--output", type=Path, default=Path("/tmp/mneme-arc-measurements-v1"))
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    args = parser.parse_args()
    result = (
        run(args.output, args.checkpoint)
        if args.execute
        else replay(args.replay, args.output)
        if args.replay
        else construction()
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
