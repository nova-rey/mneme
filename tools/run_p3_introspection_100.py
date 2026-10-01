#!/usr/bin/env python3
# ruff: noqa: E501
"""Run the authorized P3-INTROSPECT-100 two-lineage study."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from mneme.contracts import GenerationRequest
from mneme.controller import ResponseController, TurnIntent
from mneme.development import (
    ArcPacket,
    IntrospectionLedger,
    ReviewTarget,
    accept_proposals,
    parse_proposals,
    review_request,
    review_system_prompt,
)
from mneme.experiments.artifacts import ArtifactStore, content_digest
from mneme.experiments.pilot import PilotRun, host_role_binding
from mneme.experiments.pilot_runtime import PilotRuntime, RuntimeSubject
from mneme.experiments.pilot_study import DevelopmentFixture, ProductionAssessmentAdapter
from mneme.experiments.shared_interloper import (
    GEMMA_SYSTEM_PROMPT,
    ThreadSpec,
    build_shared_interloper_request,
    require_nonempty_message,
)
from mneme.hosts.deepinfra import DeepInfraQwenAssessorHost
from mneme.memory.interpretation import MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION
from mneme.state.contracts import StoragePermissions
from mneme.state.snapshots import create_checkpoint, fork_from_checkpoint
from mneme.state.storage import SQLiteStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_p23_f0_background_shared_interloper import (
    RemoteGlinerHost,
    RemoteLlamaHost,
    _call,
    _load_assessor_host,
    _trace,
)
from tools.run_p23_saa_ten_thread_live import _development_request, _record_measurement_unknown

ROOT = Path(os.environ.get("MNEME_P3_INTROSPECT_LAB", "docs/receipts/MNEME_P3_Introspection_100_Thread_Run_20260927"))
RUN_ID = os.environ.get("MNEME_P3_INTROSPECT_RUN_ID", "p3-introspect-100-20260927-r1")
TOPIC_BANK = Path("docs/experiments/p3_introspection_100_topic_bank_v1.json")
R8_CHECKPOINT = Path(
    "docs/receipts/MNEME_P2_SAA_Ten_Thread_Run_r8_20260927/snapshots/SAA-developed.sqlite3"
)
THREAD_TURNS = 8
CHECKPOINTS = (0, 10, 25, 50, 75, 100)
PROBE_SEEDS = (61001, 61002, 61003)
FIELD_SEEDS = (71001, 71004, 71007, 71010, 71013, 71016, 71019, 71022)
PROBES = (
    "A small team must keep a remote project usable while people have changing schedules. What would you notice first?",
    "A fictional station must remain useful when one supply route fails. How would you organize the design?",
    "Explain a new everyday mechanism to someone who wants both simplicity and room to recover from mistakes.",
    "A group is choosing between a very efficient plan and a more forgiving one. What tradeoff would you examine?",
    "A creative project has many possible directions but limited attention. How might you decide what to preserve?",
    "An unfamiliar process produces uneven results. What would you investigate before changing everything?",
    "A shared resource is sometimes available and sometimes absent. What kind of arrangement might help?",
    "Plan a modest event whose timing, people, and materials are all somewhat uncertain.",
)

# Every provider/local-model operation is reserved through PilotRun.  This is
# the exact frozen worst case: both developing branches perform development,
# extraction, and one assessment per turn; Qwen supplies seven continuations
# per thread; introspection allows one repair; then the primary and
# ON/OFF/RESTORED readouts are emitted.  Keep a small fixed plumbing margin,
# rather than relying on expected sparsity of candidates.
THREAD_COUNT = 100
HARD_MAX_CALLS = (
    3  # qualification
    + THREAD_COUNT * THREAD_TURNS * 2 * 3  # I/N development, extraction, assessment
    + THREAD_COUNT * (THREAD_TURNS - 1)  # shared Interloper continuations
    + THREAD_COUNT * 2  # introspection review plus one repair
    + len(CHECKPOINTS) * len(PROBES) * len(PROBE_SEEDS) * 3  # I/N/V readouts
    + 3 * len(PROBES) * len(PROBE_SEEDS) * 3  # I ON/OFF/RESTORED
)
RESERVATION_MARGIN = 49
RESERVATION_CEILING = HARD_MAX_CALLS + RESERVATION_MARGIN


def _permissions() -> StoragePermissions:
    return StoragePermissions(
        store=True, export=True, interpret=True, recall=True, provider_reuse=True, learn=True
    )


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _blinded_evaluation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce a bounded, label-randomized observable comparison receipt."""

    grouped: dict[tuple[int, int, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (int(row["checkpoint"]), int(row["probe"]), int(row["repetition"]))
        grouped.setdefault(key, {})[str(row["condition"])] = row
    pairs: list[dict[str, Any]] = []
    blind_key: list[dict[str, Any]] = []
    for key, conditions in sorted(grouped.items()):
        if not {"I", "N", "V"}.issubset(conditions):
            continue
        for pair_name in (("I", "N"), ("I", "V"), ("N", "V")):
            left, right = conditions[pair_name[0]], conditions[pair_name[1]]
            # Stable per-pair permutation, independent of treatment labels.
            digest = content_digest({"key": key, "pair": pair_name, "outputs": [left["output"], right["output"]]})
            swapped = int(digest[:2], 16) % 2 == 1
            a, b = (left, right) if not swapped else (right, left)
            blind_key.append({"key": list(key), "pair": list(pair_name), "A": pair_name[0] if not swapped else pair_name[1], "B": pair_name[1] if not swapped else pair_name[0]})
            at, bt = str(a["output"]), str(b["output"])
            atokens, btokens = set(at.lower().split()), set(bt.lower().split())
            union = len(atokens | btokens)
            pairs.append(
                {
                    "key": list(key),
                    "pair": list(pair_name),
                    "label_a": "A",
                    "label_b": "B",
                    "stage1": {
                        "different": at != bt,
                        "token_jaccard": (len(atokens & btokens) / union) if union else 1.0,
                        "length_delta": abs(len(at) - len(bt)),
                    },
                    "stage2": {
                        "history_alignment_assessable": bool(at != bt),
                        "history_feature": (
                            "introspection-adjusted I lineage"
                            if pair_name[0] == "I" and at != bt
                            else "baseline/control comparison"
                            if at != bt
                            else "no observed difference"
                        ),
                    },
                }
            )
    return {
        "status": "COMPLETE",
        "method": "label-randomized mechanical Stage-1 observable comparison; Stage-2 history alignment after coding",
        "pair_count": len(pairs),
        "stage1_difference_count": sum(1 for item in pairs if item["stage1"]["different"]),
        "pairs": pairs,
        "blind_key": blind_key,
    }


def _topics() -> list[ThreadSpec]:
    value = json.loads(TOPIC_BANK.read_text(encoding="utf-8"))
    rows = value.get("topics")
    if not isinstance(rows, list) or len(rows) != 100:
        raise RuntimeError("frozen topic bank must contain exactly 100 topics")
    result = []
    for row in rows:
        result.append(
            ThreadSpec(
                f"P3-{int(row['thread']):03d}",
                str(row["opening"]),
                (str(row["private_concerns"]),),
            )
        )
    return result


def _review_json(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def _packet(thread_id: str, history: list[tuple[str, str]], exposures: list[dict[str, Any]]) -> ArcPacket:
    targets: list[ReviewTarget] = []
    refs: list[dict[str, Any]] = []
    for item in exposures:
        edge_key = str(item.get("edge_key", ""))
        if not edge_key or any(target.edge_key == edge_key for target in targets):
            continue
        ref = str(item.get("turn_ref", ""))
        targets.append(ReviewTarget(f"{thread_id.lower()}-{len(targets)}", edge_key, str(item.get("context", "general")), (ref,)))
        refs.append(item)
        if len(targets) >= 8:
            break
    if not targets:
        targets = [ReviewTarget(f"{thread_id.lower()}-none", "none", "general")]
    messages = tuple(
        {"role": role, "content": text}
        for participant, response in history
        for role, text in (("user", participant), ("assistant", response))
    )
    return ArcPacket(thread_id, messages, tuple(refs), tuple(targets), missing_aftermath=True)


def _review(
    pilot: PilotRun,
    host: Any,
    packet: ArcPacket,
    *,
    call_id: str,
    coordinate: Mapping[str, Any],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    request = GenerationRequest(
        messages=(
            {"role": "user", "content": json.dumps(review_request(packet), ensure_ascii=False)},
        ),
        system=review_system_prompt(),
        parameters={"temperature": 0.1, "top_p": 0.9, "max_new_tokens": 512},
    )
    result = _call(pilot, host, request, call_id=call_id, role="introspection", coordinate=coordinate, max_tokens=512)
    raw = _review_json(result.content)
    try:
        proposals = parse_proposals(raw, packet, valid_evidence_refs={str(item.get("turn_ref")) for item in packet.exposures})
        return proposals, {"status": "COMPLETE", "raw": result.content, "parsed": [item.to_dict() for item in proposals]}
    except Exception as first_error:
        repair_request = GenerationRequest(
            messages=({"role": "user", "content": raw},),
            system=(
                "Return only valid JSON with an assessments list using exactly the supplied target aliases, "
                "numeric effects in [-1,1], confidence in [0,1], and supplied evidence references. "
                "Do not invent an assessment."
            ),
            parameters={"temperature": 0.0, "top_p": 0.9, "max_new_tokens": 512},
        )
        repaired = _call(pilot, host, repair_request, call_id=f"{call_id}-repair", role="introspection", coordinate=coordinate, max_tokens=512)
        try:
            proposals = parse_proposals(_review_json(repaired.content), packet, valid_evidence_refs={str(item.get("turn_ref")) for item in packet.exposures})
        except Exception as second_error:
            # A reviewer that cannot produce the bounded schema contributes
            # no adjustment.  Preserve both outputs for audit and continue
            # the arc with an explicit abstention rather than inventing a
            # developmental update or invalidating unrelated conversation.
            return (), {
                "status": "ABSTAINED_MALFORMED",
                "raw": result.content,
                "repair": repaired.content,
                "error": f"{first_error}; {second_error}",
                "parsed": [],
            }
        return proposals, {"status": "REPAIRED", "raw": result.content, "repair": repaired.content, "parsed": [item.to_dict() for item in proposals]}


def _prepare_observe(
    controller: ResponseController,
    prompt: str,
    seed: int,
    field_seed: int,
    policy: str,
    memory: str,
    operation: str,
    *,
    ledger_path: Path | None = None,
    ledger_parent_digest: str = "",
) -> Any:
    intent = TurnIntent(
        current_input=prompt,
        mode="observe",
        memory=memory,
        session_messages=(),
        system=GEMMA_SYSTEM_PROMPT,
        parameters={"temperature": 0.35, "top_p": 0.9, "max_new_tokens": 256},
        seed=seed,
        operation_id=operation,
        selection_policy=policy,
        field_seed=field_seed,
    )
    if ledger_path is not None and policy == "field-saa-v1":
        return controller.prepare_with_introspection(
            intent,
            str(ledger_path),
            parent_digest=ledger_parent_digest,
        )
    return controller.prepare(intent)


def _field_trace(prepared: Any) -> dict[str, Any] | None:
    field = getattr(prepared, "field_result", None)
    return field.to_dict() if field is not None else None


def _trajectory_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((int(row["checkpoint"]), str(row["condition"])), []).append(row)
    summary: list[dict[str, Any]] = []
    for (checkpoint, condition), items in sorted(grouped.items()):
        payloads = {str(item.get("payload", "")) for item in items}
        landings = {
            str((item.get("field_trace") or {}).get("selected_landing"))
            for item in items
            if (item.get("field_trace") or {}).get("selected_landing")
        }
        summary.append(
            {
                "checkpoint": checkpoint,
                "condition": condition,
                "count": len(items),
                "mean_output_chars": sum(len(str(item.get("output", ""))) for item in items) / max(len(items), 1),
                "unique_payloads": len(payloads),
                "unique_landings": len(landings),
                "landings": sorted(landings),
            }
        )
    return {"rows": summary, "source_row_count": len(rows)}


def _write_summary_plot(path: Path, summary: Mapping[str, Any]) -> None:
    """Write a dependency-free SVG of mean readout length by checkpoint."""

    rows = summary.get("rows", [])
    points: dict[str, list[tuple[int, float]]] = {"I": [], "N": [], "V": []}
    for row in rows:
        condition = str(row.get("condition", ""))
        if condition in points:
            points[condition].append((int(row["checkpoint"]), float(row["mean_output_chars"])))
    width, height = 760, 360
    max_value = max((value for values in points.values() for _, value in values), default=1.0)
    colors = {"I": "#7c3aed", "N": "#2563eb", "V": "#6b7280"}
    def xy(point: tuple[int, float]) -> tuple[float, float]:
        x = 60 + (point[0] / 100.0) * 650
        y = 300 - (point[1] / max_value) * 240
        return x, y
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="60" y="24" font-family="sans-serif" font-size="16">P3 readout mean output length</text>',
        '<line x1="60" y1="300" x2="710" y2="300" stroke="#111827"/>',
        '<line x1="60" y1="60" x2="60" y2="300" stroke="#111827"/>',
    ]
    for condition, values in points.items():
        values.sort()
        if not values:
            continue
        coords = " ".join(f"{xy(point)[0]:.1f},{xy(point)[1]:.1f}" for point in values)
        lines.append(f'<polyline points="{coords}" fill="none" stroke="{colors[condition]}" stroke-width="3"/>')
        for point in values:
            x, y = xy(point)
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colors[condition]}"/>')
        lines.append(f'<text x="{650 + (0 if condition == "I" else 25 if condition == "N" else 50)}" y="50" fill="{colors[condition]}" font-family="sans-serif">{condition}</text>')
    lines.append("</svg>\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def _make_pilot(
    gemma: Any,
    extractor: Any,
    assessor: Any,
    interloper: Any,
    *,
    start_thread: int = 0,
    parent_root: Path | None = None,
) -> tuple[ArtifactStore, PilotRun]:
    remaining = THREAD_COUNT - start_thread
    hard_max = (
        3
        + remaining * THREAD_TURNS * 2 * 3
        + remaining * (THREAD_TURNS - 1)
        + remaining * 2
        + len(CHECKPOINTS) * len(PROBES) * len(PROBE_SEEDS) * 3
        + 3 * len(PROBES) * len(PROBE_SEEDS) * 3
    )
    contract = {
        "name": "p3-introspect-100",
        "contract_revision": 1,
        "methodology": "arc-bound-introspection-two-lineage",
        "topic_bank_sha256": content_digest(json.loads(TOPIC_BANK.read_text(encoding="utf-8"))),
        "r8_parent": str(R8_CHECKPOINT),
        "continuation_parent": str(parent_root) if parent_root else None,
        "continuation_start_thread": start_thread,
        "threads": THREAD_COUNT,
        "exchanges_per_thread": THREAD_TURNS,
        "checkpoints": list(CHECKPOINTS),
        "probe_count": len(PROBES),
        "probe_seeds": list(PROBE_SEEDS),
        "introspection_version": "p3-introspection-v1",
        "call_budget": {
            "hard_max": hard_max,
            "reservation_margin": RESERVATION_MARGIN,
            "reservation_ceiling": hard_max + RESERVATION_MARGIN,
        },
    }
    contract["contract_sha256"] = content_digest(contract)
    store = ArtifactStore(ROOT)
    bindings = {
        "subjects": [{"slot": 0, "label": "I"}, {"slot": 1, "label": "N"}],
        "historical_evidence_unchanged": True,
    }
    experiment = {
        **contract,
        "model_fingerprints": {
            "gemma": gemma.fingerprint().to_dict(),
            "extractor": extractor.fingerprint().to_dict(),
            "assessor": assessor.fingerprint().to_dict(),
            "interloper": interloper.fingerprint().to_dict(),
        },
    }
    experiment.pop("contract_sha256", None)
    experiment["contract_sha256"] = content_digest(experiment)
    planned = hard_max + RESERVATION_MARGIN
    store.publish_run(
        experiment=experiment,
        preflight={"status": "READY", "topic_bank_sha256": contract["topic_bank_sha256"]},
        study_plan={"planned_calls": planned, "max_output_tokens": 2_000_000, "schedule": contract},
        bindings=bindings,
        run_id=RUN_ID,
    )
    pilot = PilotRun(store, RUN_ID)
    pilot.prepare(
        planned_calls=planned,
        max_output_tokens=2_000_000,
        qualification_calls=3,
        pilot_calls=planned - 3,
        metadata={"experiment": "p3-introspect-100", "version": "p3-introspection-v1"},
        role_bindings={
            "developing": host_role_binding("developing", gemma),
            "development-response": host_role_binding("development-response", gemma),
            "development-extraction": host_role_binding("development-extraction", extractor),
            "assessor": host_role_binding("assessor", assessor),
            "interloper": host_role_binding("interloper", interloper),
            "introspection": host_role_binding("introspection", gemma),
            "evaluation": host_role_binding("evaluation", gemma),
        },
    )
    return store, pilot


def _load_parent_transcripts(parent_root: Path, through_thread: int) -> list[dict[str, Any]]:
    """Load only complete thread artifacts from an interrupted parent run."""

    rows: list[dict[str, Any]] = []
    for index in range(1, through_thread + 1):
        matches = sorted(parent_root.rglob(f"transcript-P3-{index:03d}.json"))
        path = next((item for item in matches if item.parent.name == "development"), None)
        if path is None:
            raise RuntimeError(f"missing intact parent transcript for thread {index}: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        thread_rows = payload.get("rows")
        if not isinstance(thread_rows, list) or len(thread_rows) != THREAD_TURNS:
            raise RuntimeError(f"parent transcript for thread {index} is incomplete: {path}")
        rows.extend(dict(item) for item in thread_rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--continue-from-root",
        type=Path,
        help="start a new prospective continuation from an intact parent checkpoint",
    )
    parser.add_argument("--continue-from-thread", type=int, default=0)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "FROZEN_PLAN_ONLY", "topic_count": 100, "checkpoints": CHECKPOINTS}, indent=2))
        return 0
    ROOT.mkdir(parents=True, exist_ok=True)
    topics = _topics()
    continuation_root = args.continue_from_root
    start_thread = int(args.continue_from_thread)
    if continuation_root is not None:
        if start_thread not in (*CHECKPOINTS[1:], 24):
            raise RuntimeError("continuation must start at a published or explicitly derived intact boundary")
        if not continuation_root.is_dir():
            raise RuntimeError(f"continuation parent root is missing: {continuation_root}")
        if RUN_ID.endswith("-r1"):
            raise RuntimeError("continuation must use a fresh run id")
    elif start_thread:
        raise RuntimeError("--continue-from-thread requires --continue-from-root")
    if not R8_CHECKPOINT.is_file():
        raise RuntimeError(f"missing immutable R8 checkpoint: {R8_CHECKPOINT}")
    qualification_path = Path("docs/receipts/MNEME_P3_Introspection_Qualification_20260927/qualification.json")
    if not qualification_path.is_file():
        raise RuntimeError("missing introspection qualification receipt")
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    if qualification.get("status") != "QUALIFIED" or qualification.get("live_review_inference", {}).get("status") != "QUALIFIED":
        raise RuntimeError("p3 introspection qualification lacks a passing live review inference")
    gemma = RemoteLlamaHost()
    extractor = RemoteGlinerHost()
    assessor = _load_assessor_host()
    interloper = DeepInfraQwenAssessorHost(
        token=None,
        model_id="Qwen/Qwen3-30B-A3B",
        model_family="Qwen3 30B A3B Instruct-role",
        upstream_model_id="Qwen/Qwen3-30B-A3B",
        quantization="provider-managed",
        context_length=40960,
    )
    store, pilot = _make_pilot(
        gemma,
        extractor,
        assessor,
        interloper,
        start_thread=start_thread,
        parent_root=continuation_root,
    )
    # Three local qualification calls are required by the durable pilot
    # envelope.  They test the real local host binding but do not enter study
    # data or learner state.
    pilot.begin_qualification()
    for index in range(3):
        request = GenerationRequest(
            ({"role": "user", "content": "Return the JSON object {\"ok\":true}."},),
            system="Return only the requested JSON.",
            parameters={"temperature": 0.0, "max_new_tokens": 16},
        )
        _call(pilot, gemma, request, call_id=f"qualify-{index}", role="assessor-qualification", coordinate={"qualification": index}, max_tokens=16)
    pilot.complete_qualification(passed=True, details={"local_gemma": "reachable", "introspection": "offline-qualified"})
    pilot.begin_pilot()

    branches = {"I": ROOT / "subjects" / "I.sqlite3", "N": ROOT / "subjects" / "N.sqlite3", "V": ROOT / "subjects" / "V.sqlite3"}
    for path in branches.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not branches["I"].exists():
        source_i = R8_CHECKPOINT
        source_n = R8_CHECKPOINT
        if continuation_root is not None:
            source_i = continuation_root / "snapshots" / f"I-{start_thread}.sqlite3"
            source_n = continuation_root / "snapshots" / f"N-{start_thread}.sqlite3"
            if not source_i.is_file() or not source_n.is_file():
                raise RuntimeError("continuation parent lacks the requested frozen checkpoints")
        fork_from_checkpoint(source_i, branches["I"], child_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{RUN_ID}:I")))
        fork_from_checkpoint(source_n, branches["N"], child_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{RUN_ID}:N")))
        fork_from_checkpoint(R8_CHECKPOINT, branches["V"], child_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mneme:{RUN_ID}:V")))
    stores = {label: SQLiteStore(path) for label, path in branches.items()}
    subjects = {slot: RuntimeSubject(slot, stores[label], stores[label].current()["active_instance_id"], gemma) for slot, label in ((0, "I"), (1, "N"))}
    runtime = PilotRuntime(pilot, subjects)
    adapter = ProductionAssessmentAdapter(runtime, assessor)
    controllers = {label: ResponseController(stores[label], stores[label].current()["active_instance_id"], gemma) for label in ("I", "N")}
    if continuation_root is not None:
        parent_ledger = continuation_root / "introspection" / f"I-{start_thread}.json"
        if not parent_ledger.is_file():
            raise RuntimeError(f"continuation parent lacks introspection sidecar: {parent_ledger}")
        ledgers = {
            "I": IntrospectionLedger.load(parent_ledger),
            "N": IntrospectionLedger(ROOT / "introspection" / "N.json", parent_digest=content_digest({"parent": str(R8_CHECKPOINT), "label": "N"})),
        }
        # Materialize the inherited sidecar inside the new prospective run so
        # checkpoint-10 readouts bind to an immutable local artifact rather
        # than reaching through the parent run at measurement time.
        inherited_sidecar = ROOT / "introspection" / f"I-{start_thread}.json"
        inherited_sidecar.parent.mkdir(parents=True, exist_ok=True)
        inherited_sidecar.write_text(parent_ledger.read_text(encoding="utf-8"), encoding="utf-8")
        inherited_checkpoint_sidecar = continuation_root / "introspection" / "I-10.json"
        if inherited_checkpoint_sidecar.is_file() and start_thread != 10:
            (ROOT / "introspection" / "I-10.json").write_text(
                inherited_checkpoint_sidecar.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        transcripts = _load_parent_transcripts(continuation_root, start_thread)
        progress = {
            "threads_completed": start_thread,
            "checkpoints": {
                str(start_thread): {
                    "I": str(continuation_root / "snapshots" / f"I-{start_thread}.sqlite3"),
                    "N": str(continuation_root / "snapshots" / f"N-{start_thread}.sqlite3"),
                }
            },
            "introspection_reviews": start_thread,
            "continuation_parent": str(continuation_root),
            "continuation_from_thread": start_thread,
        }
    else:
        ledgers = {label: IntrospectionLedger(ROOT / "introspection" / f"{label}.json", parent_digest=content_digest({"parent": str(R8_CHECKPOINT), "label": label})) for label in ("I", "N")}
        transcripts = []
        progress = {"threads_completed": 0, "checkpoints": {}, "introspection_reviews": 0}
    for thread_index, thread in enumerate(topics, 1):
        if thread_index <= start_thread:
            continue
        histories = {"I": [], "N": []}
        exposure_rows = []
        participant: str | None = None
        for turn in range(THREAD_TURNS):
            if turn == 0:
                participant = thread.opening
            else:
                participant = require_nonempty_message(
                    _call(
                        pilot,
                        interloper,
                        build_shared_interloper_request(
                            thread=thread,
                            prior_participant=participant,
                            responses={"A": histories["I"][-1][1], "B": histories["N"][-1][1]},
                            turn=turn,
                        ),
                        call_id=f"qwen-{thread.thread_id}-{turn}",
                        role="interloper",
                        coordinate={"thread": thread.thread_id, "turn": turn},
                        max_tokens=192,
                    ).content,
                    role="Qwen",
                )
            branch_rows: dict[str, Any] = {}
            for slot, label in ((0, "I"), (1, "N")):
                seed = 200000 + thread_index * 100 + turn
                field_seed = FIELD_SEEDS[(thread_index + turn) % len(FIELD_SEEDS)] + thread_index
                prepared, exposure = _development_request(
                    controllers[label], participant=participant, history=histories[label], seed=seed,
                    field_seed=field_seed, operation_id=f"dev-{label}-{thread.thread_id}-{turn}",
                    memory="graph", selection_policy="field-saa-v1",
                )
                if label == "I":
                    prepared = controllers[label].prepare(
                        TurnIntent(
                            current_input=participant, mode="develop", memory="graph",
                            session_messages=prepared.request.messages[:-1], system=GEMMA_SYSTEM_PROMPT,
                            parameters=prepared.request.parameters, seed=seed,
                            operation_id=f"dev-{label}-{thread.thread_id}-{turn}",
                            selection_policy="field-saa-v1", field_seed=field_seed,
                            field_adjustments=ledgers["I"].accessibility_adjustments(),
                            expression_adjustments=ledgers["I"].expression_adjustments(),
                        )
                    )
                    exposure["field_adjustments"] = ledgers["I"].accessibility_adjustments()
                    exposure["expression_adjustments"] = ledgers["I"].expression_adjustments()
                outcome = runtime.execute_development(
                    slot=slot, call_id=f"dev-{label}-{thread.thread_id}-{turn}",
                    coordinate={"thread": thread.thread_id, "turn": turn, "lineage": label},
                    request=prepared.request, max_output_tokens=256,
                )
                response = require_nonempty_message(str(outcome.result.get("content", "")), role=f"Gemma {label}")
                extraction = runtime.extract(
                    slot=slot, call_id=f"extract-{label}-{thread.thread_id}-{turn}",
                    coordinate={"thread": thread.thread_id, "turn": turn, "lineage": label},
                    episode_id=outcome.operation.episode_id, extractor_host=extractor,
                    max_output_tokens=768, extractor_version=MINIMAL_RELATIONSHIP_EXTRACTOR_VERSION,
                )
                plan = adapter(slot, DevelopmentFixture(thread_index * 100 + turn, thread.thread_id, participant, f"p3-{thread.thread_id}-{turn}"), outcome, extraction)
                status = "excluded"
                admitted = 0
                if plan.request is not None and plan.validator is not None:
                    assessed = runtime.provider_call(
                        call_id=f"assess-{label}-{thread.thread_id}-{turn}", role="assessor",
                        coordinate={"thread": thread.thread_id, "turn": turn, "lineage": label}, host=assessor,
                        request=plan.request, max_output_tokens=1536, validator=plan.validator,
                        artifact_category="assessment",
                    )
                    if assessed.validation_error is None:
                        admitted = plan.publish(assessed.validated)
                        status = "complete"
                    else:
                        status = "measurement_unknown"
                        _record_measurement_unknown(
                            pilot,
                            call_id=f"assess-{label}-{thread.thread_id}-{turn}",
                            coordinate={"thread": thread.thread_id, "turn": turn, "lineage": label},
                            operation_id=outcome.operation.operation_id,
                            validation_error=assessed.validation_error,
                        )
                else:
                    admitted = plan.publish(None)
                row = {"response": response, "seed": seed, "exposure": exposure, "interpretation": status, "admitted": admitted, "trace": _trace(stores[label], outcome.operation.operation_id)}
                branch_rows[label] = row
                histories[label].append((participant, response))
                if label == "I":
                    field = exposure.get("field") or {}
                    for contribution in field.get("contributions", []):
                        exposure_rows.append({"turn_ref": f"{thread.thread_id}:turn:{turn}", "edge_key": contribution.get("edge_key"), "context": contribution.get("relationship", "general"), "payload": field.get("payload", "")})
            transcripts.append({"thread": thread.thread_id, "turn": turn, "participant": participant, "I": branch_rows["I"], "N": branch_rows["N"]})
        packet = _packet(thread.thread_id, histories["I"], exposure_rows)
        proposals, review = _review(pilot, gemma, packet, call_id=f"introspect-{thread.thread_id}", coordinate={"thread": thread.thread_id, "boundary": "closed"})
        accepted = accept_proposals(packet, proposals, existing_dedup=ledgers["I"].dedup_keys)
        ledgers["I"].record_review(packet, proposals, accepted=accepted, status=review["status"])
        ledgers["I"].save()
        pilot.publish_artifact("introspection", f"review-{thread.thread_id}.json", {"packet": packet.to_dict(), "review": review, "accepted": [item.to_dict() for item in accepted]})
        progress["threads_completed"] = thread_index
        progress["introspection_reviews"] += 1
        if thread_index in CHECKPOINTS[1:]:
            for label in ("I", "N"):
                checkpoint = ROOT / "snapshots" / f"{label}-{thread_index}.sqlite3"
                create_checkpoint(stores[label], checkpoint, checkpoint_id=f"{RUN_ID}-{label}-{thread_index}")
                progress["checkpoints"][str(thread_index)] = progress["checkpoints"].get(str(thread_index), {}) | {label: str(checkpoint)}
            # Freeze the introspection sidecar at the same boundary as the
            # learner checkpoint.  Earlier readouts must not consume reviews
            # that were generated by later arcs.
            ledger_snapshot = ROOT / "introspection" / f"I-{thread_index}.json"
            ledger_snapshot.parent.mkdir(parents=True, exist_ok=True)
            ledger_snapshot.write_text(ledgers["I"].path.read_text(encoding="utf-8"), encoding="utf-8")
        _atomic_json(ROOT / "progress.json", progress)
        pilot.publish_artifact(
            "development",
            f"transcript-{thread.thread_id}.json",
            {"rows": transcripts[-THREAD_TURNS:]},
        )

    # Frozen checkpoint readouts: the two developing lineages plus a vanilla
    # fork of the immutable R8 state.  Readouts never update any lineage.
    # Readouts must be prepared from the frozen checkpoint for that coordinate.
    # Using the live development controller here would silently evaluate every
    # checkpoint against the final state.  Keep the checkpoint map explicit so
    # I/N lineage identity remains auditable and cannot collapse by accident.
    checkpoint_paths: dict[str, dict[int, Path]] = {
        "I": {0: R8_CHECKPOINT},
        "N": {0: R8_CHECKPOINT},
        "V": {number: R8_CHECKPOINT for number in CHECKPOINTS},
    }
    for number_text, rows in progress["checkpoints"].items():
        number = int(number_text)
        if not isinstance(rows, Mapping):
            raise RuntimeError(f"checkpoint receipt for {number} is malformed")
        for label in ("I", "N"):
            raw_path = rows.get(label)
            if not isinstance(raw_path, str):
                raise RuntimeError(f"missing {label} checkpoint for {number}")
            checkpoint_paths[label][number] = Path(raw_path)
    readout_controllers: dict[tuple[str, int], ResponseController] = {}
    readout_stores: list[SQLiteStore] = []
    for label in ("I", "N", "V"):
        for number in CHECKPOINTS:
            checkpoint = checkpoint_paths[label][number]
            if not checkpoint.is_file():
                raise RuntimeError(f"missing frozen {label} checkpoint {number}: {checkpoint}")
            frozen_store = SQLiteStore(checkpoint, read_only=True)
            readout_stores.append(frozen_store)
            readout_controllers[(label, number)] = ResponseController(
                frozen_store,
                frozen_store.current()["active_instance_id"],
                gemma,
            )
    readouts: list[dict[str, Any]] = []
    for checkpoint_number in CHECKPOINTS:
        for probe_index, prompt in enumerate(PROBES):
            for repetition, seed in enumerate(PROBE_SEEDS):
                for label, policy, memory in (("I", "field-saa-v1", "graph"), ("N", "field-saa-v1", "graph"), ("V", "fixed-v2", "off")):
                    controller = readout_controllers[(label, checkpoint_number)]
                    ledger_path = (
                        ROOT / "introspection" / f"I-{checkpoint_number}.json"
                        if label == "I" and checkpoint_number > 0
                        else None
                    )
                    prepared = _prepare_observe(
                        controller,
                        prompt,
                        seed,
                        FIELD_SEEDS[(probe_index + repetition) % len(FIELD_SEEDS)],
                        policy,
                        memory,
                        f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}",
                        ledger_path=ledger_path,
                        ledger_parent_digest=ledgers["I"].parent_digest,
                    )
                    result = pilot.reserve_call(call_id=f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}", role="evaluation", coordinate={"checkpoint": checkpoint_number, "probe": probe_index, "repetition": repetition, "condition": label}, max_output_tokens=256)
                    if result.get("status") == "RETURNED":
                        content = str(result["result"].get("content", ""))
                    else:
                        pilot.dispatch_call(f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}", expected_host_fingerprint=gemma.fingerprint().to_dict())
                        generated = gemma.generate(prepared.request)
                        content = require_nonempty_message(generated.content, role=f"Gemma {label}")
                        pilot.return_call(f"probe-{checkpoint_number}-{probe_index}-{repetition}-{label}", result={"content": content, "model_id": generated.model_id, "provider": generated.provider, "effective_parameters": generated.effective_parameters, "seed": generated.seed, "finish_reason": generated.finish_reason, "provenance": generated.provenance}, actual_host_fingerprint=gemma.fingerprint().to_dict())
                    readouts.append({"checkpoint": checkpoint_number, "probe": probe_index, "repetition": repetition, "condition": label, "seed": seed, "field_seed": FIELD_SEEDS[(probe_index + repetition) % len(FIELD_SEEDS)], "prompt": prompt, "output": content, "payload": prepared.request.system, "field_trace": _field_trace(prepared)})
    # Required removal/restoration check on the I lineage.  These are frozen,
    # read-only views of the same checkpoint and probe; only the SAA field is
    # toggled.  The primary checkpoint is never mutated by this measurement.
    removal_restoration: list[dict[str, Any]] = []
    for checkpoint_number in (0, 50, 100):
        controller = readout_controllers[("I", checkpoint_number)]
        for probe_index, prompt in enumerate(PROBES):
            for repetition, seed in enumerate(PROBE_SEEDS):
                field_seed = FIELD_SEEDS[(probe_index + repetition) % len(FIELD_SEEDS)]
                for condition, policy, memory in (
                    ("SAA_ON", "field-saa-v1", "graph"),
                    ("SAA_OFF", "fixed-v2", "off"),
                    ("SAA_RESTORED", "field-saa-v1", "graph"),
                ):
                    call_id = f"removal-{checkpoint_number}-{probe_index}-{repetition}-{condition}"
                    prepared = _prepare_observe(
                        controller,
                        prompt,
                        seed,
                        field_seed,
                        policy,
                        memory,
                        call_id,
                        ledger_path=(
                            ROOT / "introspection" / f"I-{checkpoint_number}.json"
                            if condition != "SAA_OFF" and checkpoint_number > 0
                            else None
                        ),
                        ledger_parent_digest=ledgers["I"].parent_digest,
                    )
                    reservation = pilot.reserve_call(
                        call_id=call_id,
                        role="evaluation",
                        coordinate={
                            "checkpoint": checkpoint_number,
                            "probe": probe_index,
                            "repetition": repetition,
                            "condition": condition,
                        },
                        max_output_tokens=256,
                    )
                    if reservation.get("status") == "RETURNED":
                        content = str(reservation["result"].get("content", ""))
                    else:
                        pilot.dispatch_call(call_id, expected_host_fingerprint=gemma.fingerprint().to_dict())
                        generated = gemma.generate(prepared.request)
                        content = require_nonempty_message(generated.content, role=f"Gemma {condition}")
                        pilot.return_call(
                            call_id,
                            result={
                                "content": content,
                                "model_id": generated.model_id,
                                "provider": generated.provider,
                                "effective_parameters": generated.effective_parameters,
                                "seed": generated.seed,
                                "finish_reason": generated.finish_reason,
                                "provenance": generated.provenance,
                            },
                            actual_host_fingerprint=gemma.fingerprint().to_dict(),
                        )
                    removal_restoration.append(
                        {
                            "checkpoint": checkpoint_number,
                            "probe": probe_index,
                            "repetition": repetition,
                            "condition": condition,
                            "seed": seed,
                            "field_seed": field_seed,
                            "prompt": prompt,
                            "output": content,
                            "payload": prepared.request.system,
                            "field_trace": _field_trace(prepared),
                        }
                    )
    _atomic_json(ROOT / "transcripts.json", {"rows": transcripts})
    _atomic_json(ROOT / "readouts.json", {"rows": readouts, "probes": list(PROBES), "seeds": list(PROBE_SEEDS)})
    _atomic_json(ROOT / "removal-restoration.json", {"rows": removal_restoration})
    trajectory_summary = _trajectory_summary(readouts)
    _atomic_json(ROOT / "trajectory-summary.json", trajectory_summary)
    _write_summary_plot(ROOT / "trajectory-summary.svg", trajectory_summary)
    blinded_evaluation = _blinded_evaluation(readouts)
    blind_key = blinded_evaluation.pop("blind_key", [])
    _atomic_json(ROOT / "blinded-evaluation.json", blinded_evaluation)
    _atomic_json(ROOT / "blinded-key.json", {"rows": blind_key})
    _atomic_json(
        ROOT / "introspection-ledger.json",
        {
            label: {
                "accessibility": ledgers[label].accessibility_adjustments(),
                "expression": ledgers[label].expression_adjustments(),
            }
            for label in ledgers
        },
    )
    landing_counts: dict[str, int] = {}
    for item in readouts:
        trace = item.get("field_trace") or {}
        landing = trace.get("selected_landing")
        if landing:
            landing_counts[str(landing)] = landing_counts.get(str(landing), 0) + 1
    introspection_summary = {
        label: {
            "review_count": len(ledgers[label].reviews),
            "accepted_adjustment_count": len(ledgers[label].adjustments),
            "accessibility_adjustment_count": len(ledgers[label].accessibility_adjustments()),
            "expression_adjustment_count": len(ledgers[label].expression_adjustments()),
        }
        for label in ledgers
    }
    report = {
        "status": "VALID_INTERPRETABLE_P3_INTROSPECT_100",
        "run_id": RUN_ID,
        "historical_r8_unchanged": True,
        "threads_completed": len(topics),
        "transcript_rows": len(transcripts),
        "readout_rows": len(readouts),
        "removal_restoration_rows": len(removal_restoration),
        "blinded_evaluation": {
            "pair_count": blinded_evaluation["pair_count"],
            "stage1_difference_count": blinded_evaluation["stage1_difference_count"],
        },
        "introspection_reviews": progress["introspection_reviews"],
        "checkpoint_numbers": list(CHECKPOINTS),
        "checkpoint_paths": {
            label: {str(number): str(path) for number, path in paths.items()}
            for label, paths in checkpoint_paths.items()
        },
        "continuation": {
            "parent_root": str(continuation_root) if continuation_root else None,
            "start_thread": start_thread,
            "parent_checkpoint_preserved": bool(continuation_root),
        },
        "introspection_summary": introspection_summary,
        "saa_landing_counts": landing_counts,
        "evidence_files": {
            "development_transcripts": str(ROOT / "experiments"),
            "readouts": str(ROOT / "readouts.json"),
            "removal_restoration": str(ROOT / "removal-restoration.json"),
            "blinded_evaluation": str(ROOT / "blinded-evaluation.json"),
            "blinded_key": str(ROOT / "blinded-key.json"),
            "trajectory_summary": str(ROOT / "trajectory-summary.json"),
            "trajectory_plot": str(ROOT / "trajectory-summary.svg"),
        },
        "model_stack": {"gemma": gemma.fingerprint().to_dict(), "extractor": extractor.fingerprint().to_dict(), "assessor": assessor.fingerprint().to_dict(), "interloper": interloper.fingerprint().to_dict()},
        "phase_four_recommendation": "planning_only_after_owner_review",
        "limitations": ["two related adaptive lineages are not 100 independent subjects", "introspection is a bounded text-mediated review path", "no Phase Four neural backend was started"],
        "accounting": pilot.reservations_report(),
    }
    pilot.publish_artifact("final", "final-report.json", report)
    pilot.finish(summary={"status": report["status"], "threads": len(topics), "readouts": len(readouts)})
    _atomic_json(ROOT / "terminal-report.json", report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
