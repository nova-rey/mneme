#!/usr/bin/env python3
# ruff: noqa: E501, E402, I001
"""Continue the preserved reasoning-ON specimen through frozen T26--T30.

This runner is deliberately separate from the historical 25-thread runner.
It writes the complete host request/reasoning signal and candidate-level NLI
evidence to an append-only coordinate journal before the next coordinate is
started.  The ON-25 source store is copied and never opened writable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from mneme.contracts import GenerationRequest
from mneme.development.introspection import (
    ArcPacket,
    FilingLevel,
    ReviewTarget,
    accept_proposals,
    filing_system_prompt,
    parse_microcall_explicit,
    reflection_request,
    reflection_system_prompt,
)
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
    build_subject_request,
    require_nonempty_message,
)
from mneme.state.compact import CompactStore
from mneme.state.compact_runtime import CompactRuntime

from tools.run_p23_cross_thread import RemoteGlinerHost
from tools.run_p23_f0_background_shared_interloper import RemoteNliBackend
from tools.run_reasoning_25_thread import (
    CandidateObservation,
    DeterministicRemoteGemma,
    call,
    checkpoint,
    digest_bytes,
    graph_with_observations,
    histories_to_messages,
    result_record,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost

SCHEDULE_PATH = ROOT / "docs/receipts/MNEME_ON25_ON30_Continuation_Schedule_20261003.json"
PARENT_RUN = "mneme-reasoning-25-fresh-20261003-r1"
PARENT_LIVE = Path("/home/nyx/mneme_artifacts/mneme-reasoning-25-fresh-20261003-r1/ON-live.compact.sqlite3")
EXPECTED_PARENT_SHA = "46fe26a72d3dfdefca3e8973c1ce1c5a7a75ec6995dd089926b681c35fe15b0c"
EXPECTED_PARENT_DIGEST = "74cad10e4883a3d8bb7e73223b5151f37a0728d78ef246ffd905beeaa650e151"
EXPECTED_PARENT_CHECKPOINT_SHA = "0c774ded58f39451d261297282aa4293b41247ecd1c79b1bec1dd6fa95b3697e"
GEMMA_BASE = 810100
FIELD_BASE = 820100
REFLECTION_BASE = 830100
FILING_BASE = 840100


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_schedule() -> tuple[dict[str, Any], str]:
    raw = SCHEDULE_PATH.read_bytes()
    schedule = json.loads(raw.decode("utf-8"))
    if schedule.get("parent_run_id") != PARENT_RUN or len(schedule.get("threads", [])) != 5:
        raise RuntimeError("continuation schedule is not the authorized five-thread ON-25 schedule")
    return schedule, hashlib.sha256(raw).hexdigest()


def parent_check() -> dict[str, Any]:
    if not PARENT_LIVE.exists() or sha256(PARENT_LIVE) != EXPECTED_PARENT_SHA:
        raise RuntimeError("ON-25 live specimen hash does not match authorized parent")
    with CompactStore(PARENT_LIVE, read_only=True) as store:
        digest = store.state_digest()
        verify = store.verify()
    if digest != EXPECTED_PARENT_DIGEST or verify:
        raise RuntimeError(f"ON-25 integrity mismatch: digest={digest} verify={verify}")
    return {"path": str(PARENT_LIVE), "sha256": EXPECTED_PARENT_SHA, "state_digest": digest, "verify": verify, "checkpoint_sha256": EXPECTED_PARENT_CHECKPOINT_SHA}


def introspect_on(
    host: DeterministicRemoteGemma,
    history: list[tuple[str, str]],
    exposures: list[dict[str, Any]],
    thread: int,
    calls: list[dict[str, Any]],
    adjustments: dict[str, int],
    expression_adjustments: dict[str, int],
) -> dict[str, Any]:
    by_landing: dict[str, list[str]] = {}
    for exposure in exposures:
        if exposure.get("selected_landing"):
            by_landing.setdefault(str(exposure["selected_landing"]), []).append(str(exposure["turn_ref"]))
    if not by_landing:
        return {"thread": thread, "status": "ABSTAINED_NO_TARGETS", "targets": [], "accepted": [], "filing": []}
    targets = tuple(ReviewTarget(str(i), edge, "selected associative framing", tuple(refs)) for i, (edge, refs) in enumerate(sorted(by_landing.items()), 1))
    packet = ArcPacket(f"thread-{thread}-ON-arc", tuple(histories_to_messages(history)), tuple(exposures), targets)
    reflection_seed = REFLECTION_BASE + thread * 10
    reflection_result = call(host, GenerationRequest(({"role": "user", "content": json.dumps(reflection_request(packet), ensure_ascii=False)},), system=reflection_system_prompt(), parameters={"temperature": 0.35, "top_p": 0.9, "top_k": 40, "min_p": 0.05, "max_new_tokens": 8192}, seed=reflection_seed), label=f"ON:thread-{thread}:reflection", calls=calls)
    reflection = reflection_result.content
    target_lines = "\n".join(f"{target.alias}. {target.context}" for target in targets)
    questions = (
        f"Which single target are you evaluating? Reply 0 for none, or one of {', '.join(target.alias for target in targets)} only.",
        "Is there enough evidence for a substantive judgment? Reply 0 or 1 only.",
        "Was the selected association useful or interesting? Reply 0 or 1 only.",
        "Was it harmful or distracting? Reply 0 or 1 only.",
        "Was expressing it helpful? Reply 0 or 1 only.",
        "Should it be expressed less or left latent? Reply 0 or 1 only.",
        "Confidence: reply 1 none, 2 low, 3 medium, 4 high, or 5 very high.",
    )
    answers: list[str] = []
    filing: list[dict[str, Any]] = []
    for index, question in enumerate(questions):
        prompt = f"TARGET OPTIONS:\n{target_lines}\n\nROUND-ONE REFLECTION:\n{reflection[:12000]}\n\n{question}"
        result = call(host, GenerationRequest(({"role": "user", "content": prompt},), system=filing_system_prompt(FilingLevel.MICROCALL_EXPLICIT), parameters={"temperature": 0.0, "top_p": 0.9, "top_k": 40, "min_p": 0.05, "max_new_tokens": 512, "chat_template_kwargs": {"enable_thinking": False}}, seed=FILING_BASE + thread * 100 + index), label=f"ON:thread-{thread}:filing-{index}", calls=calls)
        answers.append(result.content.strip())
        filing.append({"question": question, "answer": result.content.strip(), "result": result_record(result, output=True)})
    try:
        proposals = parse_microcall_explicit(answers, packet)
        accepted = accept_proposals(packet, proposals)
    except Exception as exc:
        return {"thread": thread, "status": "ABSTAINED_MALFORMED", "targets": [target.to_dict() for target in targets], "reflection": reflection, "filing": filing, "answers": answers, "accepted": [], "error": f"{type(exc).__name__}: {exc}"}
    for item in accepted:
        adjustments[item.edge_key] = adjustments.get(item.edge_key, 0) + item.association_delta
        expression_adjustments[item.edge_key] = expression_adjustments.get(item.edge_key, 0) + item.expression_delta
    return {"thread": thread, "status": "ACCEPTED" if accepted else "NO_CHANGE", "targets": [target.to_dict() for target in targets], "reflection": reflection, "filing": filing, "answers": answers, "proposals": [item.to_dict() for item in proposals], "accepted": [item.to_dict() for item in accepted], "adjustments_after": dict(adjustments), "expression_adjustments_after": dict(expression_adjustments)}


def run(output_root: Path) -> dict[str, Any]:
    schedule, schedule_sha = load_schedule()
    parent = parent_check()
    output_root.mkdir(parents=True, exist_ok=True)
    live = output_root / "ON-30-live.compact.sqlite3"
    if live.exists():
        raise RuntimeError(f"refusing to overwrite existing continuation: {live}")
    shutil.copyfile(PARENT_LIVE, live)
    with CompactStore(live, telemetry=True, telemetry_retention=128, journal_retention=256) as store:
        store.set_metadata("continuation", {"parent_run": PARENT_RUN, "parent_state_digest": EXPECTED_PARENT_DIGEST, "schedule_sha256": schedule_sha})
        store.set_metadata("run_id", "mneme-reasoning-on-25-to-30-20261003")
    host = DeterministicRemoteGemma("Gemma-ON", 64173, "on", 8192)
    gliner = RemoteGlinerHost()
    nli = RemoteNliBackend()
    qwen = DeepInfraQwenAssessorHost(model_id="Qwen/Qwen3-30B-A3B", model_family="Qwen3 30B A3B Instruct-role", upstream_model_id="Qwen/Qwen3-30B-A3B", quantization="provider-managed", context_length=40960, token=None)
    calls: list[dict[str, Any]] = []
    coordinate_path = output_root / "coordinate-evidence.jsonl"
    evidence_path = output_root / "development-evidence.json"
    rows: list[dict[str, Any]] = []
    all_extractions: list[dict[str, Any]] = []
    all_reviews: list[dict[str, Any]] = []
    storage: list[dict[str, Any]] = []
    adjustments: dict[str, int] = {}
    expressions: dict[str, int] = {}
    with CompactStore(live, telemetry=True, telemetry_retention=128, journal_retention=256) as store:
        runtime = CompactRuntime(store)
        for item in schedule["threads"]:
            thread = int(item["thread"])
            histories: list[tuple[str, str]] = []
            exposures: list[dict[str, Any]] = []
            participant = str(item["opening"])
            thread_rows: list[dict[str, Any]] = []
            for turn in range(4):
                if turn > 0:
                    time.sleep(4.0)
                    shared_request = build_shared_interloper_request(thread=ThreadSpec(item["id"], item["opening"], tuple(item["concerns"])), prior_participant=participant, responses={"A": histories[-1][1], "B": histories[-1][1]}, turn=turn)
                    shared = call(qwen, shared_request, label=f"Qwen:thread-{thread}:turn-{turn}", calls=calls)
                    participant = require_nonempty_message(shared.content, role="shared Qwen")
                state_before = store.state_digest()
                field_seed = FIELD_BASE + thread * 100 + turn
                field = runtime.evaluate_saa(participant, field_seed=field_seed, field_adjustments=adjustments, expression_adjustments=expressions, fail_on_unhealthy=True)
                system = GEMMA_SYSTEM_PROMPT + (("\n\n" + field.field.payload) if field.field.payload else "")
                gemma_seed = GEMMA_BASE + thread * 100 + turn
                req = build_subject_request(pairs=histories, participant_message=participant, seed=gemma_seed, memory_system=system, turn=turn)
                req = GenerationRequest(req.messages, system=req.system, parameters={**req.parameters, "top_k": 40, "min_p": 0.05, "max_new_tokens": host.max_tokens}, seed=req.seed, run_metadata=req.run_metadata)
                result = call(host, req, label=f"Gemma-ON:thread-{thread}:turn-{turn}", calls=calls)
                response = require_nonempty_message(result.content, role="Gemma ON")
                histories.append((participant, response))
                exposure = {"turn_ref": f"thread-{thread}-turn-{turn}", "payload": field.field.payload, "selected_landing": field.field.selected_landing, "field_seed": field_seed, "health": dict(field.health)}
                exposures.append(exposure)
                source = participant + "\n" + response
                extraction = call(gliner, GenerationRequest(({"role": "user", "content": json.dumps({"source_slots": {"s0": source}})},), parameters={"max_new_tokens": 768}), label=f"GLiNER:ON:thread-{thread}:turn-{turn}", calls=calls, include_output=True)
                parsed = json.loads(extraction.content)
                relationships = parsed.get("relationships", [])
                observations: list[CandidateObservation] = []
                for rel in relationships if isinstance(relationships, list) else []:
                    if not isinstance(rel, dict):
                        continue
                    evidence = str(rel.get("evidence", ""))
                    start = max(0, source.find(evidence)) if evidence else 0
                    observations.append(CandidateObservation(str(rel.get("from", "")), str(rel.get("relation", "")), str(rel.get("to", "")), str(rel.get("source", "s0")), start, start + len(evidence)))
                graph, learner, admitted, assessment = graph_with_observations(runtime, tuple(observations), source, nli, f"thread-{thread}-turn-{turn}-ON")
                publication = runtime.publish_state(graph, learner, operation_id=f"thread-{thread}-turn-{turn}-ON", metadata={"field_adjustments": adjustments, "expression_adjustments": expressions})
                state_after = store.state_digest()
                coord = {"lineage": "ON", "thread": thread, "turn": turn, "participant_input": participant, "conversation_context": [{"role": "user", "content": p} for p, _ in histories[:-1]] + ([{"role": "user", "content": participant}, {"role": "assistant", "content": response}] if histories else []), "saa": field.field.to_dict(), "saa_health": dict(field.health), "gemma": result_record(result, output=True), "model_visible_request": result.raw_metadata.get("request_payload"), "model_visible_request_utf8": result.raw_metadata.get("request_body_utf8"), "extraction_raw": parsed, "assessment": assessment, "admitted": admitted, "publication": publication, "state_digest_before": state_before, "state_digest_after": state_after}
                append_jsonl(coordinate_path, coord)
                thread_rows.append(coord)
                all_extractions.append(coord)
            review = introspect_on(host, histories, exposures, thread, calls, adjustments, expressions)
            all_reviews.append(review)
            store.set_metadata("field_adjustments", adjustments)
            store.set_metadata("expression_adjustments", expressions)
            metrics = runtime.record_thread_metrics(thread)
            storage.append({"thread": thread, "metrics": metrics, "state_digest": store.state_digest(), "coordinate_count": len(thread_rows)})
            rows.extend(thread_rows)
            atomic_json(evidence_path, {"run_id": "mneme-reasoning-on-25-to-30-20261003", "parent": parent, "schedule_sha256": schedule_sha, "completed_thread": thread, "coordinates": rows, "introspection": all_reviews, "storage": storage, "calls": calls})
            atomic_json(output_root / "progress.json", {"run_id": "mneme-reasoning-on-25-to-30-20261003", "completed_thread": thread, "schedule_sha256": schedule_sha, "state_digest": store.state_digest(), "coordinate_count": len(rows)})
    final = {"path": str(live), "sha256": sha256(live), "bytes": live.stat().st_size}
    checkpoint_path = output_root / "checkpoints" / "thread-030-ON.compact.sqlite3"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with CompactStore(live, telemetry=True, telemetry_retention=128, journal_retention=256) as store:
        checkpoint_info = checkpoint(store, checkpoint_path, "mneme-reasoning-on-25-to-30-thread-30")
        final["state_digest"] = store.state_digest()
        final["verify"] = store.verify()
    payload = {"run_id": "mneme-reasoning-on-25-to-30-20261003", "parent": parent, "schedule": schedule, "schedule_sha256": schedule_sha, "live": final, "checkpoint": checkpoint_info, "coordinates": rows, "introspection": all_reviews, "storage": storage, "calls": {"total": len(calls), "records": calls}, "limitations": ["Prospective ON-only observation; no matched OFF continuation.", "Threads 1-25 reasoning text remains unavailable in the historical parent evidence."]}
    atomic_json(output_root / "final-evidence.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.output_root)
    print(json.dumps({"run_id": payload["run_id"], "thread": 30, "live": payload["live"], "checkpoint": payload["checkpoint"], "coordinates": len(payload["coordinates"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
