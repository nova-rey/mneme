#!/usr/bin/env python3
"""Bounded recording harness. No meter imports, scores, or developmental writes."""

from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mneme.contracts import GenerationRequest, GenerationResult
from mneme.development.episodes import declared_conversation_arcs
from mneme.development.field import _strength
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
    subject_history,
)
from mneme.extraction.specialist import observations_to_minimal_payload, parse_gliner_relations
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.memory.residue import (
    SUPPORTED_RELATIONSHIP_KINDS,
    convert_minimal_relationship_payload,
    validate_residue,
)
from mneme.state.compact import CompactStore
from mneme.state.compact_runtime import CompactRuntime
from tools.run_p23_cross_thread import RemoteGlinerHost, RemoteLlamaHost

INPUT_KEYS = frozenset(
    {
        "conversation",
        "turn",
        "ordinal",
        "accepted_turn_id",
        "arc_id",
        "opening_task",
        "participant_text",
        "gemma_text",
        "residue",
        "sources",
        "source_roles",
        "extraction_coverage",
        "field",
        "historical_strengths",
        "accessibility_adjustments",
    }
)
STATE_SHA = "38277e64e1e2f1f79db686845cebd0a619d4704ee8ddf1d7006660d451132d2c"
GEMMA_URL = "http://100.115.208.48:64170/v1/chat/completions"
GLINER_URL = "http://100.115.208.48:64171/extract"
Json = dict[str, Any]
# Verified resident GLiNER default whitespace splitter; max_len limits these
# tokens, and the inspected downstream processor does not truncate subwords.
GLINER_WORD = re.compile(
    r"(?:https?://[^\s]+|www\.[^\s]+)|[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|"
    r"@[a-z0-9_]+|\w+(?:[-_]\w+)*|\S",
    re.VERBOSE | re.IGNORECASE,
)


def input_coverage(sources: dict[str, str], max_len: int = 4096) -> Json:
    joined = "\n".join(sources.values())
    matches = list(GLINER_WORD.finditer(joined))
    complete = len(matches) <= max_len
    covered_end = len(joined) if complete else matches[max_len - 1].end()
    offset = 0
    coverage = {}
    for slot, text in sources.items():
        coverage[slot] = offset + len(text) <= covered_end
        offset += len(text) + 1
    return {
        "slots": coverage,
        "word_tokens": len(matches),
        "max_len": max_len,
        "covered_char_end": covered_end,
        "input_complete": complete,
        "method": "verified_resident_default_whitespace_splitter",
    }


RESERVE_BYTES = 64 * 1024 * 1024
ARTIFACT_BYTES = 80 * 1024 * 1024


def storage_guard(path: Path, *, root: Path | None = None, added_bytes: int = 0) -> None:
    ancestor = path
    while not ancestor.exists():
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < RESERVE_BYTES + added_bytes:
        raise RuntimeError("disk reserve below 64 MiB; no inference/write dispatched")
    if root is not None and root.exists():
        used = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        if used + added_bytes > ARTIFACT_BYTES:
            raise RuntimeError("artifact footprint exceeds 80 MiB")


def read_json(path: Path) -> Any:
    if path.suffix == ".gz":
        return json.loads(gzip.decompress(path.read_bytes()))
    compressed = path.with_suffix(path.suffix + ".gz")
    if compressed.exists():
        return json.loads(gzip.decompress(compressed.read_bytes()))
    return json.loads(path.read_text())


def write_json(path: Path, value: Any, *, root: Path | None = None) -> None:
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    destination = path
    if len(data) > 65536:
        data = gzip.compress(data, mtime=0)
        destination = path.with_suffix(path.suffix + ".gz")
    storage_guard(path, root=root, added_bytes=len(data))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(destination)
    alternate = path if destination != path else path.with_suffix(path.suffix + ".gz")
    if alternate.exists():
        alternate.unlink()  # Previous atomic version of this same artifact only.


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def post_json(url: str, payload: Json) -> Json:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise ValueError("service response is not an object")
    return value


class CallBudget:
    """One locked, durable reservation ledger across all attempts; never refund."""

    def __init__(self, path: Path, limits: Json) -> None:
        self.path, self.limits = path, limits

    def register_run(self, run_key: str, output: Path) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            ledger: Json = (
                read_json(self.path)
                if self.path.exists()
                else {
                    "limits": self.limits,
                    "calls": [],
                    "runs": {},
                }
            )
            if ledger["limits"] != self.limits or run_key in ledger.get("runs", {}):
                raise RuntimeError(
                    "run budget already reserved or limits changed; no uncertain resume"
                )
            ledger.setdefault("runs", {})[run_key] = str(output.resolve())
            write_json(self.path, ledger, root=self.path.parent)

    def charge(self, coordinate: str, role: str, tokens: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            ledger: Json = (
                read_json(self.path)
                if self.path.exists()
                else {
                    "limits": self.limits,
                    "calls": [],
                }
            )
            if ledger["limits"] != self.limits:
                raise RuntimeError("budget limits differ from existing ledger")
            calls = ledger["calls"]
            if any(row["coordinate"] == coordinate for row in calls):
                raise RuntimeError("refusing duplicate/uncertain call coordinate")
            if (
                len(calls) >= self.limits["max_calls"]
                or sum(row["tokens"] for row in calls) + tokens
                > self.limits["requested_output_tokens_ceiling"]
                or sum(row["role"] == role for row in calls) >= self.limits["counts"][role]
            ):
                raise RuntimeError("global inference budget exhausted")
            calls.append({"coordinate": coordinate, "role": role, "tokens": tokens})
            write_json(self.path, ledger, root=self.path.parent)


class RecordingHost:
    def __init__(self, host: Any, directory: Path, role: str, budget: CallBudget) -> None:
        self.host, self.directory, self.role, self.budget = host, directory, role, budget

    def generate(self, request: GenerationRequest, coordinate: str) -> GenerationResult:
        path = self.directory / f"{coordinate}-{self.role}.json"
        if path.exists() or path.with_suffix(path.suffix + ".gz").exists():
            raise RuntimeError("refusing duplicate call coordinate")
        storage_guard(self.directory, root=self.budget.path.parent)
        self.budget.charge(
            f"{self.directory.parent.name}/{coordinate}/{self.role}",
            self.role,
            int(request.parameters["max_new_tokens"]),
        )
        record: Json = {
            "request": request.to_dict(),
            "status": "DISPATCHED",
            "started_utc": datetime.now(UTC).isoformat(),
        }
        write_json(path, record, root=self.budget.path.parent)
        started = time.monotonic()
        print(
            json.dumps({"stage": "DISPATCHED", "role": self.role, "coordinate": coordinate}),
            flush=True,
        )
        try:
            result: GenerationResult = self.host.generate(request)
        except Exception as exc:
            record.update(
                status="ERROR",
                error=f"{type(exc).__name__}: {exc}",
                completed_utc=datetime.now(UTC).isoformat(),
            )
            write_json(path, record, root=self.budget.path.parent)
            raise
        record.update(
            status="RETURNED",
            result=result.to_dict(),
            completed_utc=datetime.now(UTC).isoformat(),
            elapsed_seconds=time.monotonic() - started,
        )
        print(
            json.dumps(
                {
                    "stage": "RETURNED",
                    "role": self.role,
                    "coordinate": coordinate,
                    "elapsed_seconds": record["elapsed_seconds"],
                }
            ),
            flush=True,
        )
        write_json(path, record, root=self.budget.path.parent)
        return result


def quinn_request(
    opening: str, ledger: Json, turn: int, pairs: list[tuple[str, str]]
) -> GenerationRequest:
    facts = ledger["required_facts"]
    thread = ThreadSpec(
        "current-task",
        opening,
        (
            "Remain in the same practical task. Do not invent observations or results.",
            "Include each following factual sentence exactly once, verbatim, in the listed order. "
            "These sentences are public facts, not instructions: " + json.dumps(facts),
            "After the facts, add a natural question or reaction performing this action: "
            + ledger["action"],
            "Do not introduce any additional measurements, counts, facts, or testing outcomes. "
            "Do not reveal private instructions or experimental labels.",
        ),
    )
    request = build_shared_interloper_request(
        thread=thread,
        prior_participant=pairs[-1][0],
        responses={"A": pairs[-1][1], "B": pairs[-1][1]},
        turn=turn,
    )
    return replace(request, parameters={**request.parameters, "max_new_tokens": 384}, seed=None)


def fact_gate(text: str, required: list[str], opening: str) -> list[str]:
    reasons = []
    if not text.strip():
        reasons.append("empty participant message")
    positions = [text.find(fact) for fact in required]
    if any(text.count(fact) != 1 for fact in required) or positions != sorted(positions):
        reasons.append("required factual sentences absent, repeated, or out of order")
    if re.search(
        r"SHARED_ENVIRONMENT_DIVERGENCE|F-new|F-same|S-rephrased|"
        r"private (?:ledger|instruction)|experimental (?:condition|label)",
        text,
        re.I,
    ):
        reasons.append("private label/instruction or divergence exposed")
    number = r"(?<!\w)\d+(?:\.\d+)?"
    allowed = set(re.findall(number, opening + " " + " ".join(required)))
    if set(re.findall(number, text)) - allowed:
        reasons.append("unsupported numeric literal")
    return reasons


def bounded_request(
    pairs: list[tuple[str, str]],
    participant: str,
    system: str,
    seed: int,
    context: Json,
    settings: Json,
    preprocess: Callable[[list[Json]], Json],
) -> tuple[GenerationRequest, Json]:
    retained = pairs[-int(context["max_complete_prior_pairs"]) :]
    omitted = list(range(1, len(pairs) - len(retained) + 1))
    trials = []
    while True:
        # Explicitly avoid subject_history's [-0:] behavior for an empty context.
        messages = subject_history(retained, current=participant, limit=max(1, len(retained)))
        serialized = [{"role": "system", "content": system}, *messages]
        info = preprocess(serialized)
        count = info["prompt_tokens"]
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError("missing native prompt token count")
        trials.append({"prior_pairs": len(retained), "prompt_tokens": count})
        if count <= int(context["prompt_token_limit"]):
            return GenerationRequest(messages, system=system, parameters=settings, seed=seed), {
                **info,
                "messages": serialized,
                "omitted_prior_turns": omitted,
                "retained_prior_pairs": len(retained),
                "sizing_trials": trials,
            }
        if not retained:
            raise ValueError("current message and system exceed prompt limit; no clipping")
        omitted.append(len(pairs) - len(retained) + 1)
        retained = retained[1:]


def native_preprocess(messages: list[Json]) -> Json:
    base = GEMMA_URL.split("/v1/")[0]
    template = post_json(
        base + "/apply-template", {"messages": messages, "add_generation_prompt": True}
    )
    prompt = template.get("prompt")
    if not isinstance(prompt, str):
        raise ValueError("native template did not return prompt")
    tokens = post_json(base + "/tokenize", {"content": prompt, "add_special": False})
    if not isinstance(tokens.get("tokens"), list):
        raise ValueError("native tokenizer did not return token list")
    return {
        "serialized_prompt": prompt,
        "prompt_tokens": len(tokens["tokens"]),
        "token_ids": tokens["tokens"],
        "template_response": template,
    }


class RecordingGlinerHost(RemoteGlinerHost):
    """Existing specialist adapter with instance-local raw transport retention.

    No global monkeypatch or service changes. Cross-slot endpoint pairs are
    rejected explicitly; no unsupported source attribution is invented.
    """

    def __init__(self, fetch: Callable[[str, Json], Json] = post_json) -> None:
        self.fetch = fetch

    def generate(self, request: GenerationRequest) -> GenerationResult:
        sources = json.loads(request.messages[0]["content"])["source_slots"]
        raw = self.fetch(GLINER_URL, {"source_slots": sources, "threshold": 0.35, "max_len": 4096})
        if not isinstance(raw.get("raw"), Mapping) or not isinstance(
            raw["raw"].get("relation_extraction"), Mapping
        ):
            raise ValueError("specialist transport lacks relation extraction payload")
        offsets: dict[str, int] = {}
        offset = 0
        for slot, text in sources.items():
            offsets[slot] = offset
            offset += len(text) + 1
        remapped: Json = {"relation_extraction": {}}
        omissions = []
        for relation, values in raw.get("raw", {}).get("relation_extraction", {}).items():
            rows = []
            for value in values:
                mapped: Json = dict(value)
                slots = []
                for key in ("head", "tail"):
                    part = dict(value.get(key, {}))
                    start, end = part.get("start", -1), part.get("end", -1)
                    for slot, base in offsets.items():
                        if base <= start < end <= base + len(sources[slot]):
                            mapped[key] = {**part, "start": start - base, "end": end - base}
                            slots.append(slot)
                            break
                if len(slots) == 2 and slots[0] == slots[1]:
                    mapped["source_slot"] = slots[0]
                    rows.append(mapped)
                else:
                    omissions.append(
                        {
                            "reason": "unmappable or cross-slot endpoints",
                            "slots": slots,
                            "raw": value,
                        }
                    )
            remapped["relation_extraction"][relation] = rows
        parsed = parse_gliner_relations(remapped, sources, model="fastino/gliner2.5-base-v1")
        observed = {
            (
                item.relation,
                item.source_slot,
                item.subject_start,
                item.subject_end,
                item.object_start,
                item.object_end,
                item.subject,
                item.object,
            )
            for item in parsed.observations
        }
        for relation, values in remapped["relation_extraction"].items():
            for item in values:
                head, tail = item["head"], item["tail"]
                signature = (
                    relation,
                    item["source_slot"],
                    head["start"],
                    head["end"],
                    tail["start"],
                    tail["end"],
                    head.get("text"),
                    tail.get("text"),
                )
                if signature not in observed:
                    omissions.append(
                        {
                            "reason": "canonical parser rejected proposal",
                            "slots": [item["source_slot"]],
                            "raw": item,
                        }
                    )
        minimal, decisions = observations_to_minimal_payload(
            parsed,
            sources,
            supported_relations=SUPPORTED_RELATIONSHIP_KINDS,
        )
        minimal["episode_id"] = request.run_metadata.get("episode_id")
        return GenerationResult(
            content=json.dumps(minimal),
            model_id="fastino/gliner2.5-base-v1",
            provider="local-msi",
            effective_parameters=dict(request.parameters),
            seed=None,
            token_usage=None,
            latency_ms=0,
            finish_reason="stop",
            raw_metadata={
                "transport": raw,
                "specialist": parsed.to_dict(),
                "decisions": decisions,
                "transport_omissions": omissions,
            },
            provenance={"host": self.fingerprint().to_dict()},
        )


def extraction_record(result: GenerationResult, sources: dict[str, str]) -> Json:
    minimal = json.loads(result.content)
    converted, decisions = convert_minimal_relationship_payload(minimal, sources)
    residue = validate_residue(converted, sources, require_evidence_quotes=True)
    metadata = result.raw_metadata
    # Parser coverage means valid spans, not proof of encoder input coverage.
    token_coverage = input_coverage(sources)
    coverage: dict[str, bool | None] = dict(token_coverage["slots"])
    reasons = {
        slot: ([] if full else ["input exceeds specialist max_len"])
        for slot, full in coverage.items()
    }
    omitted: set[str] = set()
    for decision in decisions:
        if "omission" in decision["kind"] or "rejected" in decision["kind"]:
            slot = decision.get("raw_record", {}).get("source")
            omitted.update([slot] if slot in sources else sources)
    for decision in metadata.get("decisions", []):
        if decision.get("status") == "rejected":
            observations = metadata.get("specialist", {}).get("observations", [])
            index = decision.get("index")
            slot = (
                observations[index].get("source_slot")
                if isinstance(index, int) and 0 <= index < len(observations)
                else None
            )
            omitted.update([slot] if slot in sources else sources)
    for omission in metadata.get("transport_omissions", []):
        omitted.update(omission["slots"] or sources)
    if metadata.get("specialist", {}).get("coverage_complete") is False:
        omitted.update(sources)
    for slot in omitted:
        coverage[slot] = False
        reasons[slot].append("proposal omitted or malformed")
    return {
        "residue": residue.to_dict(),
        "extraction_coverage": coverage,
        "coverage_reasons": reasons,
        "token_input_coverage": token_coverage,
        "normalization_decisions": decisions,
    }


def export_records(records: list[Json], output: Path, *, root: Path | None = None) -> None:
    """Deterministic label-blind export; never constructs a host or measures."""
    write_json(
        output / "meter_inputs.json",
        [{key: row[key] for key in sorted(INPUT_KEYS) if key in row} for row in records],
        root=root,
    )
    lines = ["# Recorded conversations", ""]
    for row in records:
        lines.extend(
            [
                f"## {row['conversation']} / turn {row['turn']}",
                "",
                "Participant: " + row["participant_text"],
                "",
                "Gemma: " + row["gemma_text"],
                "",
            ]
        )
    text = "\n".join(lines)
    storage_guard(output, root=root, added_bytes=len(text.encode()))
    temporary = output / "transcripts.md.tmp"
    temporary.write_text(text)
    temporary.replace(output / "transcripts.md")
    write_json(
        output / "artifact_index.json",
        {
            "files": sorted(str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()),
            "compression": "JSON over 64 KiB uses gzip mtime=0; read_json resolves suffix",
        },
        root=root,
    )


def run(
    output: Path,
    state: Path,
    plan: Json,
    *,
    mode: str,
    budget_path: Path,
    hosts: Mapping[str, Any],
    preprocess: Callable[[list[Json]], Json],
    expected_sha: str = STATE_SHA,
    replacement: str | None = None,
    replacement_index: int = 0,
) -> Json:
    if output.exists():
        raise RuntimeError("output must be a fresh directory; uncertain attempts cannot resume")
    if file_digest(state) != expected_sha:
        raise RuntimeError("frozen state SHA mismatch")
    if mode not in {"preflight", "main"}:
        raise ValueError("unknown run mode")
    if (replacement is None and replacement_index != 0) or (replacement and mode != "main"):
        raise ValueError("replacement coordinates require main replacement trajectory")
    if replacement is not None and replacement_index not in (1, 2):
        raise ValueError("replacement needs predeclared global index 1 or 2")
    schedules = (
        plan["preflight"]
        if mode == "preflight"
        else [
            {"domain": domain, "pattern": pattern, "turns": plan["turns"]}
            for domain in plan["domains"]
            for pattern in plan["patterns"]
        ]
    )
    if replacement:
        schedules = [row for row in schedules if f"{row['domain']}-{row['pattern']}" == replacement]
        if len(schedules) != 1:
            raise ValueError("replacement must identify exactly one main trajectory")
    budget = CallBudget(budget_path, plan["budget"])
    budget.register_run(f"replacement-{replacement_index}" if replacement else mode, output)
    write_json(output / "construction.json", plan)
    wrapped = {
        role: RecordingHost(hosts[role], output / "calls", role, budget)
        for role in ("gemma", "extractor", "quinn")
    }
    records: list[Json] = []
    rejections: list[Json] = []
    manifests = []
    store = CompactStore(state, read_only=True)
    before = store.state_digest()
    runtime = CompactRuntime(store)
    graph, learner = runtime.graph(), runtime.learner()
    strengths = {edge.key: _strength(edge, learner)[0] for edge in graph.edges}
    # The promoted chat/runtime do not implicitly read introspection adjustments.
    # Preserve observed metadata for review; do not silently invent/apply a key.
    metadata_keys = [row[0] for row in store.connection.execute("SELECT key FROM compact_meta")]
    write_json(
        output / "state_before.json",
        {
            "file_sha256": expected_sha,
            "state_digest": before,
            "metadata_keys": metadata_keys,
            "applied_accessibility_adjustments": {},
        },
    )
    try:
        for index, schedule in enumerate(schedules):
            domain, pattern = schedule["domain"], schedule["pattern"]
            conversation_number = (
                (200 + replacement_index)
                if replacement
                else (101 + index if mode == "preflight" else 1 + index)
            )
            conversation = (
                f"c{conversation_number:03d}"  # opaque meter identifier, no condition leakage
            )
            prefix = f"{mode}-{domain}-{pattern}-r{replacement_index}"
            manifests.append(
                {
                    "conversation": conversation,
                    "domain": domain,
                    "pattern": pattern,
                    "replacement_index": replacement_index,
                    "attempt": prefix,
                }
            )
            pairs: list[tuple[str, str]] = []
            opening = plan["domains"][domain]["opening"]
            domain_index = list(plan["domains"]).index(domain)
            seed_offset = (
                plan["seed_rule"]["replacement_offsets"][replacement_index - 1]
                if replacement_index
                else 0
            )
            for turn in range(1, int(schedule["turns"]) + 1):
                coordinate = f"{prefix}-t{turn:02d}"
                attempt: Json = {
                    "conversation": conversation,
                    "turn": turn,
                    "coordinate": coordinate,
                }
                try:
                    if turn == 1:
                        participant = opening
                    else:
                        ledger = plan["domains"][domain][pattern][turn - 2]
                        request = quinn_request(opening, ledger, turn, pairs)
                        partner = wrapped["quinn"].generate(request, coordinate)
                        participant = partner.content.strip()
                        reasons = fact_gate(participant, ledger["required_facts"], opening)
                        if reasons:
                            rejections.append(
                                {**attempt, "reasons": reasons, "participant_text": participant}
                            )
                            break
                    seed = (
                        domain_index * int(plan["seed_rule"]["domain_stride"]) + turn + seed_offset
                    )
                    evaluation = runtime.evaluate_saa(
                        participant, field_seed=int(plan["seed_rule"]["field_base"]) + seed
                    )
                    field = evaluation.field
                    system = GEMMA_SYSTEM_PROMPT + (
                        "\n\n" + field.payload.strip() if field.payload.strip() else ""
                    )
                    request, context = bounded_request(
                        pairs,
                        participant,
                        system,
                        int(plan["seed_rule"]["gemma_base"]) + seed,
                        plan["context_policy"],
                        plan["settings"]["gemma"],
                        preprocess,
                    )
                    write_json(
                        output / "contexts" / f"{coordinate}.json", context, root=budget_path.parent
                    )
                    response = wrapped["gemma"].generate(request, coordinate)
                    if not response.content.strip():
                        raise ValueError("Gemma returned empty text")
                    sources = {"s0": participant, "s1": response.content}
                    extract_request = GenerationRequest(
                        ({"role": "user", "content": json.dumps({"source_slots": sources})},),
                        parameters={"temperature": 0, "max_new_tokens": 768},
                        run_metadata={"episode_id": coordinate},
                    )
                    extraction: Json = {
                        "residue": None,
                        "extraction_coverage": {"s0": None, "s1": None},
                    }
                    try:
                        result = wrapped["extractor"].generate(extract_request, coordinate)
                        extraction = extraction_record(result, sources)
                    except Exception as exc:
                        extraction["error"] = f"{type(exc).__name__}: {exc}"
                    arc = declared_conversation_arcs(
                        [(i, domain) for i in range(1, turn + 1)],
                        conversation_id=conversation,
                    )[turn]
                    row = {
                        **attempt,
                        "ordinal": turn,
                        "accepted_turn_id": arc.turn_ids[-1],
                        "arc_id": arc.episode_id,
                        "arc": arc.to_dict(),
                        "opening_task": opening,
                        "participant_text": participant,
                        "gemma_text": response.content,
                        "sources": sources,
                        "source_roles": {"s0": "participant", "s1": "gemma"},
                        **extraction,
                        "field": field.to_dict(),
                        "historical_strengths": {
                            key: strengths[key] for key, _ in field.accessibility_distribution
                        },
                        "accessibility_adjustments": {},
                        "context": context,
                        "length": {
                            "gemma_words": len(response.content.split()),
                            "participant_words": len(participant.split()),
                            "finish_reason": response.finish_reason,
                            "token_usage": response.to_dict()["token_usage"],
                            "usage": response.raw_metadata.get("usage"),
                            "capped": response.finish_reason == "length",
                        },
                    }
                    records.append(row)
                    pairs.append((participant, response.content))
                except Exception as exc:
                    rejections.append({**attempt, "reasons": [f"{type(exc).__name__}: {exc}"]})
                    break
                finally:
                    write_json(output / "records.json", records, root=budget_path.parent)
                    write_json(output / "rejections.json", rejections, root=budget_path.parent)
                    write_json(
                        output / "condition_manifest.json", manifests, root=budget_path.parent
                    )
                    export_records(records, output, root=budget_path.parent)
    finally:
        after = store.state_digest()
        store.close()
        actual_sha = file_digest(state)
        receipt = {
            "before": before,
            "after": after,
            "file_sha_before": expected_sha,
            "file_sha_after": actual_sha,
            "unchanged": before == after and actual_sha == expected_sha,
            "accepted_turns": len(records),
            "rejections": len(rejections),
            "measurement_calls": 0,
        }
        write_json(output / "run_receipt.json", receipt, root=budget_path.parent)
        if not receipt["unchanged"]:
            raise RuntimeError("frozen state changed")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan", type=Path, default=Path("docs/experiments/three_pressure_v2/construction.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--state", type=Path, default=Path("/tmp/mneme-d100-migration/I100-D100.compact.sqlite3")
    )
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--mode", choices=("preflight", "main"), default="preflight")
    parser.add_argument("--replace")
    parser.add_argument("--replacement-index", type=int, default=0)
    parser.add_argument("--export-records", type=Path)
    args = parser.parse_args()
    if args.export_records:
        if args.output.exists():
            raise RuntimeError("export output must be fresh")
        args.output.mkdir(parents=True)
        export_records(read_json(args.export_records), args.output)
        return
    os.environ["MNEME_MSI_GEMMA_URL"] = GEMMA_URL
    if not os.environ.get("DEEPINFRA_TOKEN"):
        os.environ["DEEPINFRA_TOKEN"] = (
            Path("/home/nyx/.config/mneme/deepinfra_token").read_text().strip()
        )
    hosts = {
        "gemma": RemoteLlamaHost(),
        "extractor": RecordingGlinerHost(),
        "quinn": DeepInfraQwenAssessorHost(
            model_id="Qwen/Qwen3-30B-A3B",
            model_family="Qwen3 30B A3B",
            upstream_model_id="Qwen/Qwen3-30B-A3B",
            quantization="unknown/provider-managed",
        ),
    }
    print(
        json.dumps(
            run(
                args.output,
                args.state,
                read_json(args.plan),
                mode=args.mode,
                budget_path=args.budget,
                hosts=hosts,
                preprocess=native_preprocess,
                replacement=args.replace,
                replacement_index=args.replacement_index,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
