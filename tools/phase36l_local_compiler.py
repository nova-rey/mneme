#!/usr/bin/env python3
"""Bounded, local-only Phase 3.6L neural-compiler screen.

This research utility never imports MNEME runtime state.  It constructs
research-only exact-Q2 control vectors in a disposable llama.cpp worktree,
fits a small semantic-description-to-vector mapper, and records every
artifact outside Git.  Stages are deliberately restartable: every immutable
artifact is atomically written before the next target is attempted.
"""
# ruff: noqa: E501, I001
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ModuleNotFoundError:  # local unit tests exercise the frozen corpus only
    np = None  # type: ignore[assignment]


MODEL = "/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf"
MODEL_SHA256 = "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"
GENERATOR = "/tmp/mneme-phase36-llama-build/bin/llama-cvector-generator"
LLAMA_SERVER = "/home/rey/src/llama.cpp/build-cuda/bin/llama-server"
GGUF_PY = "/tmp/mneme-phase36-llama/gguf-py"
N_LAYERS = 41
HIDDEN = 2560
CORPUS_VERSION = "phase36l-exact-q2-v2-balanced-target-presence"
EMBEDDER = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDER_REVISION = "main"
SAMPLER = {"temperature": 0.35, "top_k": 40, "top_p": 0.90, "min_p": 0.05}
EVALUATION_SEEDS = (936100, 936101)
GAINS = (0.35, 0.70)
REGIONS = {
    "early": (1, 12),
    "middle": (13, 28),
    "late_middle": (29, 41),
    "broad": (1, 41),
}


@dataclass(frozen=True)
class Target:
    identifier: str
    category: str
    description: str
    role: str


# The corpus is declared in source rather than adapted to any observed vector
# or completion.  The held-out descriptions are visible in the frozen corpus,
# but their vectors and embeddings are not used until the mapper is frozen.
TRAINING: tuple[Target, ...] = (
    Target("calm_deescalation", "affective_disposition", "Stay calm and de-escalate tension before acting.", "training"),
    Target("constructive_curiosity", "affective_disposition", "Treat uncertainty as an invitation to ask useful questions.", "training"),
    Target("patient_listening", "interpersonal_stance", "Listen carefully before proposing a solution.", "training"),
    Target("measured_optimism", "affective_disposition", "Keep a hopeful outlook while naming real constraints.", "training"),
    Target("respect_autonomy", "interpersonal_stance", "Preserve people’s ability to choose among meaningful options.", "training"),
    Target("clear_boundaries", "interpersonal_stance", "Make responsibilities and limits explicit without hostility.", "training"),
    Target("reciprocal_trust", "interpersonal_stance", "Build trust through reciprocal, observable commitments.", "training"),
    Target("cooperative_problem_solving", "cooperation", "Frame problems as opportunities for cooperative problem solving.", "training"),
    Target("transparent_coordination", "cooperation", "Coordinate shared work through visible information and clear handoffs.", "training"),
    Target("fair_contribution", "cooperation", "Distribute contributions fairly while recognizing different capacities.", "training"),
    Target("negotiated_tradeoffs", "cooperation", "Make tradeoffs explicit and negotiate them rather than hiding them.", "training"),
    Target("precaution_uncertainty", "risk_uncertainty", "Take sensible precautions when outcomes are uncertain.", "training"),
    Target("reversible_decisions", "risk_uncertainty", "Prefer reversible decisions while uncertainty is high.", "training"),
    Target("quantified_uncertainty", "risk_uncertainty", "Separate what is known, estimated, and unknown.", "training"),
    Target("adversarial_assumptions", "risk_uncertainty", "Test plans against plausible failure and adversarial assumptions.", "training"),
    Target("resource_conservation", "scarcity_resource", "Conserve scarce resources for uses with the highest durable value.", "training"),
    Target("prioritize_scarcity", "scarcity_resource", "Prioritize scarce capacity using explicit, reviewable criteria.", "training"),
    Target("maintenance_stewardship", "scarcity_resource", "Treat maintenance as stewardship that preserves future options.", "training"),
    Target("long_horizon_planning", "temporal_orientation", "Account for consequences that unfold over a long horizon.", "training"),
    Target("staged_sequencing", "temporal_orientation", "Sequence work in stages so later choices retain useful flexibility.", "training"),
    Target("timely_feedback", "temporal_orientation", "Create timely feedback before small errors become expensive.", "training"),
    Target("cyclical_maintenance", "temporal_orientation", "Use recurring maintenance rhythms instead of emergency-only repair.", "training"),
    Target("distributed_authority", "hierarchy_equality", "Distribute authority to people closest to the relevant information.", "training"),
    Target("accountable_leadership", "hierarchy_equality", "Pair leadership authority with visible accountability.", "training"),
    Target("equitable_access", "hierarchy_equality", "Design access so benefits are not captured by a narrow group.", "training"),
    Target("source_skepticism", "evidence_skepticism", "Check sources and incentives before trusting a claim.", "training"),
    Target("triangulate_evidence", "evidence_skepticism", "Triangulate important claims with independent evidence.", "training"),
    Target("falsifiable_tests", "evidence_skepticism", "Use tests that could genuinely disconfirm a proposal.", "training"),
    Target("modular_simplicity", "simplicity_complexity", "Prefer modular simplicity that keeps parts understandable.", "training"),
    Target("interface_complexity", "simplicity_complexity", "Manage complexity by giving parts clear, stable interfaces.", "training"),
    Target("systems_perspective", "local_global", "Consider system-wide interactions instead of isolated local effects.", "training"),
    Target("local_tailoring", "local_global", "Adapt a general approach to local conditions and knowledge.", "training"),
    Target("redundant_fallback", "resilience", "Use redundancy and graceful fallback to keep a system functioning.", "training"),
    Target("failure_isolation", "resilience", "Isolate failures so one broken part does not disable everything.", "training"),
    Target("disciplined_exploration", "exploration_exploitation", "Explore promising alternatives while keeping the learning bounded.", "training"),
    Target("reliable_exploitation", "exploration_exploitation", "Use proven approaches when reliability matters more than novelty.", "training"),
    Target("adaptive_rules", "structure_flexibility", "Use rules that can adapt when the situation changes materially.", "training"),
    Target("procedural_consistency", "structure_flexibility", "Apply a consistent process so decisions are predictable and reviewable.", "training"),
    Target("abstract_pattern", "abstraction_concreteness", "Look for an abstract pattern that connects superficially different cases.", "training"),
    Target("operational_detail", "abstraction_concreteness", "Translate plans into concrete operational details and responsibilities.", "training"),
    Target("proportional_response", "judgment", "Match the scale of a response to the scale of the actual problem.", "training"),
    Target("diagnostic_clarity", "judgment", "Clarify what failed and why before prescribing a remedy.", "training"),
    Target("legible_process", "judgment", "Make a process legible so participants can understand and correct it.", "training"),
    Target("incremental_commitment", "judgment", "Make commitments incrementally when learning can improve later choices.", "training"),
    Target("shared_observation", "coordination", "Create shared observation so people can coordinate from the same facts.", "training"),
    Target("role_complementarity", "coordination", "Use complementary roles so different strengths support one shared aim.", "training"),
    Target("constraint_creativity", "creative_judgment", "Use constraints to focus creative choices instead of treating them only as obstacles.", "training"),
    Target("audience_legibility", "creative_judgment", "Make a design legible to the people who will use or encounter it.", "training"),
)

HELD_OUT: tuple[Target, ...] = (
    Target("harbor_capacity_windows", "relational_structural", "A harbor coordinates access to limited shared space through timing and docking windows.", "held_out"),
    Target("watershed_layer_retention", "relational_structural", "A watershed slows water through layered retention so heavy rain does not become immediate flooding.", "held_out"),
    Target("rhythm_variation", "relational_structural", "A musical arrangement uses recurring rhythm with measured variation to sustain attention.", "held_out"),
    Target("wayfinding_reorientation", "relational_structural", "Wayfinding uses landmarks and periodic reorientation to prevent small errors from becoming disorientation.", "held_out"),
    Target("negative_space_composition", "relational_structural", "Visual composition uses negative space to make important elements easier to perceive.", "held_out"),
    Target("queue_bottleneck_flow", "relational_structural", "A queue improves flow by identifying and relieving its changing bottleneck.", "held_out"),
    Target("ecosystem_feedback", "relational_structural", "An ecosystem stays viable through feedback loops that reveal stress before collapse.", "held_out"),
    Target("repairable_access", "relational_structural", "Repairable systems expose access points and diagnostics so small faults can be corrected early.", "held_out"),
)

CONTRAST_CONTEXTS = (
    "a neighborhood committee deciding how to run a shared project",
    "a small hospital team responding to an operational problem",
    "a school planning an unfamiliar community program",
    "a volunteer group maintaining equipment with limited time",
    "a public service redesigning a confusing process",
    "a local organization choosing among several imperfect plans",
)

LAYER_TARGETS = ("precaution_uncertainty", "cooperative_problem_solving", "redundant_fallback")
LAYER_PROMPTS = {
    "precaution_uncertainty": "A town may open a trail after unusually heavy rain. Give practical advice for deciding safely.",
    "cooperative_problem_solving": "Two volunteer groups both need the same community room. Suggest a constructive way to proceed.",
    "redundant_fallback": "A neighborhood’s only water pump has begun to fail intermittently. What should they do next?",
}
EVAL_PROMPTS: dict[str, tuple[str, str]] = {
    "harbor_capacity_windows": (
        "A neighborhood tool library has six popular tools. People keep them longer than expected and others cannot tell when they will be free. Propose a lightweight arrangement that stays fair without becoming bureaucratic.",
        "A shared pottery studio has one kiln and several members with overlapping projects. Firings conflict, finished work sits too long, and people are frustrated. How should the studio coordinate use?",
    ),
    "watershed_layer_retention": (
        "An apartment building’s courtyard floods after short heavy rains, then dries out quickly. The residents want a practical improvement plan. What would you consider?",
        "A city park’s paths wash out after storms even though the surrounding ground is often dry. Give a staged plan for reducing damage.",
    ),
    "rhythm_variation": (
        "A museum is redesigning a one-hour tour. Visitors say it feels monotonous even though the exhibits are good. How might the staff improve the experience?",
        "A team’s weekly updates are either repetitive or chaotic. Suggest a format that keeps attention without making everyone relearn the process each week.",
    ),
    "wayfinding_reorientation": (
        "A large hospital gets frequent complaints that visitors become lost after one wrong turn. What changes would make navigation more forgiving?",
        "A civic website has grown over years and people cannot find forms once they leave the home page. How would you improve navigation?",
    ),
    "negative_space_composition": (
        "A local health clinic needs a poster explaining three urgent steps, but early drafts feel cluttered. What design guidance would you give?",
        "A dashboard for a volunteer program shows too much at once and people miss its most important alert. How should it be redesigned?",
    ),
    "queue_bottleneck_flow": (
        "A community clinic has long waits even after adding more reception volunteers. How would you diagnose and improve the process?",
        "A neighborhood meal service has enough cooks but meals still leave late. Suggest a way to find and relieve the real constraint.",
    ),
    "ecosystem_feedback": (
        "A community garden looks healthy until a few weeks each summer, when several problems appear at once. How could the group notice trouble earlier and respond?",
        "A town’s recycling program loses participants gradually, but organizers only notice when monthly totals collapse. What operating changes would help?",
    ),
    "repairable_access": (
        "A volunteer bicycle fleet often sits unused because small problems take too long to diagnose. What should the group change?",
        "A shared workshop has equipment that fails in minor ways, but only one person knows how to inspect it. How could the workshop become easier to maintain?",
    ),
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(path.suffix + ".tmp")
    staged.write_bytes(canonical(value) + b"\n")
    with staged.open("rb") as stream:
        os.fsync(stream.fileno())
    staged.replace(path)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(path.suffix + ".tmp")
    staged.write_text(value, encoding="utf-8")
    with staged.open("rb") as stream:
        os.fsync(stream.fileno())
    staged.replace(path)


def targets() -> dict[str, Target]:
    rows = TRAINING + HELD_OUT
    assert len(TRAINING) == 48 and len(HELD_OUT) == 8
    assert len({row.identifier for row in rows}) == len(rows)
    return {row.identifier: row for row in rows}


def escape_line(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def contrast_pair(target: Target, index: int) -> tuple[str, str]:
    context = CONTRAST_CONTEXTS[index]
    positive = (
        "<|start_header_id|>system<|end_header_id|>\\n\\n"
        f"Treat this consideration as a useful organizing lens: {target.description}"
        "<|eot_id|><|start_header_id|>user<|end_header_id|>\\n\\n"
        f"Briefly explain how you would approach {context}."
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\\n\\n"
    )
    negative = (
        "<|start_header_id|>system<|end_header_id|>\\n\\n"
        f"Treat this consideration as unavailable for organizing your response: {target.description}"
        "<|eot_id|><|start_header_id|>user<|end_header_id|>\\n\\n"
        f"Briefly explain how you would approach {context}."
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\\n\\n"
    )
    return positive, negative


def write_pairs(root: Path, target: Target) -> tuple[Path, Path, list[dict[str, str]]]:
    directory = root / "contrasts" / target.identifier
    positive_path, negative_path = directory / "positive.txt", directory / "negative.txt"
    pairs = []
    for index in range(6):
        positive, negative = contrast_pair(target, index)
        pairs.append({"positive": positive, "negative": negative, "context": CONTRAST_CONTEXTS[index]})
    atomic_text(positive_path, "\n".join(escape_line(pair["positive"]) for pair in pairs) + "\n")
    atomic_text(negative_path, "\n".join(escape_line(pair["negative"]) for pair in pairs) + "\n")
    atomic_json(directory / "pairs.json", {"target": asdict(target), "pairs": pairs, "sha256": digest(pairs)})
    return positive_path, negative_path, pairs


class GpuSampler:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        samples: list[dict[str, Any]] = []
        while not self.stop.is_set():
            try:
                row = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used,memory.free,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
                    text=True,
                ).strip().split(",")
                samples.append({"at": time.time(), "memory_used_mib": float(row[0]), "memory_free_mib": float(row[1]), "temperature_c": float(row[2]), "power_w": float(row[3])})
            except Exception as exc:  # keep benchmark evidence even if one probe fails
                samples.append({"at": time.time(), "error": str(exc)})
            self.stop.wait(0.5)
        atomic_json(self.path, samples)

    def __enter__(self) -> GpuSampler:
        self.thread.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop.set()
        self.thread.join(timeout=5)


def construct_vector(root: Path, target: Target, *, force: bool = False) -> dict[str, Any]:
    output = root / "vectors" / f"{target.identifier}.gguf"
    receipt_path = root / "vectors" / f"{target.identifier}.json"
    if receipt_path.exists() and output.exists() and not force:
        return json.loads(receipt_path.read_text(encoding="utf-8"))
    positive, negative, pairs = write_pairs(root, target)
    log = root / "logs" / f"construct-{target.identifier}.log"
    gpu = root / "metrics" / f"gpu-{target.identifier}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    command = [GENERATOR, "-m", MODEL, "-ngl", "99", "--method", "mean", "--positive-file", str(positive), "--negative-file", str(negative), "-o", str(output), "--log-file", str(log)]
    with GpuSampler(gpu):
        completed = subprocess.run(command, cwd="/tmp/mneme-phase36-llama", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    elapsed = time.monotonic() - started
    atomic_text(log, completed.stdout)
    if completed.returncode != 0 or not output.exists():
        raise RuntimeError(f"vector construction failed for {target.identifier}; inspect {log}")
    layers = read_vector(output)
    if sorted(layers) != list(range(1, N_LAYERS + 1)) or any(values.shape != (HIDDEN,) for values in layers.values()):
        raise RuntimeError(f"invalid layer identity in {output}")
    samples = json.loads(gpu.read_text(encoding="utf-8"))
    used = [row["memory_used_mib"] for row in samples if "memory_used_mib" in row]
    record = {
        "target": asdict(target), "model": MODEL, "model_sha256": MODEL_SHA256,
        "generator": GENERATOR, "generator_command": command, "pair_count": len(pairs),
        "pair_sha256": digest(pairs), "elapsed_s": elapsed, "returncode": completed.returncode,
        "vector_path": str(output), "vector_sha256": file_hash(output), "vector_bytes": output.stat().st_size,
        "layer_ids": list(range(1, N_LAYERS + 1)), "layer_norms": {str(layer): float(np.linalg.norm(value)) for layer, value in layers.items()},
        "peak_gpu_memory_mib": max(used) if used else None,
        "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "log_path": str(log), "log_sha256": file_hash(log), "gpu_metrics_path": str(gpu),
    }
    atomic_json(receipt_path, record)
    return record


def read_vector(path: Path) -> dict[int, np.ndarray]:
    sys.path.insert(0, GGUF_PY)
    from gguf import GGUFReader  # type: ignore[import-not-found]
    reader = GGUFReader(str(path))
    values: dict[int, np.ndarray] = {}
    for tensor in reader.tensors:
        if tensor.name.startswith("direction."):
            layer = int(tensor.name.split(".", 1)[1])
            values[layer] = np.asarray(tensor.data, dtype=np.float32).reshape(-1).copy()
    return values


def write_vector(path: Path, values: dict[int, np.ndarray], *, note: str) -> None:
    sys.path.insert(0, GGUF_PY)
    from gguf import GGUFWriter  # type: ignore[import-not-found]
    if sorted(values) != list(range(1, N_LAYERS + 1)):
        raise ValueError("must write explicit direction.1 through direction.41")
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(path.suffix + ".tmp")
    writer = GGUFWriter(staged, "controlvector")
    writer.add_string("controlvector.model_hint", "gemma4")
    writer.add_uint32("controlvector.layer_count", N_LAYERS)
    writer.add_string("general.description", note)
    for layer in range(1, N_LAYERS + 1):
        row = np.asarray(values[layer], dtype=np.float32)
        if row.shape != (HIDDEN,) or not np.isfinite(row).all():
            raise ValueError(f"invalid direction.{layer}")
        writer.add_tensor(f"direction.{layer}", row)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    staged.replace(path)


def corpus(root: Path) -> dict[str, Any]:
    payload = {
        "version": CORPUS_VERSION, "model": MODEL, "model_sha256": MODEL_SHA256,
        "control_vector_layer_identity": {"capture": "ignore l_out layer zero", "directions": list(range(1, N_LAYERS + 1)), "hidden_size": HIDDEN},
        "contrast_pair_count": 6, "training": [asdict(row) for row in TRAINING], "held_out": [asdict(row) for row in HELD_OUT],
    }
    payload["sha256"] = digest(payload)
    return payload


def ensure_corpus(root: Path) -> dict[str, Any]:
    path = root / "corpus.json"
    expected = corpus(root)
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if loaded != expected:
            raise RuntimeError("existing corpus differs from frozen Phase 3.6L corpus")
        return loaded
    atomic_json(path, expected)
    return expected


def stage_pilot(root: Path) -> None:
    manifest = ensure_corpus(root)
    pilot = Target("pilot_redundant_fallback", "stage1_measurement", "Use redundancy and graceful fallback to keep a system functioning.", "pilot")
    prep_started = time.monotonic()
    write_pairs(root, pilot)
    prep_s = time.monotonic() - prep_started
    receipt = construct_vector(root, pilot)
    estimates = {}
    for training_count, heldout_count in ((24, 6), (32, 8), (48, 8)):
        estimates[f"{training_count}_training_{heldout_count}_heldout"] = {
            "vectors": training_count + heldout_count,
            "projected_vector_construction_s": receipt["elapsed_s"] * (training_count + heldout_count),
            "projected_vector_disk_bytes": receipt["vector_bytes"] * (training_count + heldout_count),
        }
    atomic_json(root / "stage1_cost.json", {"corpus_sha256": manifest["sha256"], "contrast_preparation_s": prep_s, "pilot": receipt, "estimates": estimates, "decision_rule": "Choose 48+8 when the measured vector-only projection fits an unattended overnight-to-one-day run; otherwise choose 24+6 minimum."})


def stage_training_vectors(root: Path) -> None:
    ensure_corpus(root)
    selection = root / "corpus_selection.json"
    if not selection.exists():
        raise RuntimeError("select the frozen corpus from measured Stage-1 cost before construction")
    if json.loads(selection.read_text(encoding="utf-8")).get("no_target_vectors_existed_at_selection") is not True:
        raise RuntimeError("invalid corpus selection boundary")
    for index, target in enumerate(TRAINING, 1):
        receipt = construct_vector(root, target)
        atomic_json(root / "progress" / "training_vectors.json", {"completed": index, "total": len(TRAINING), "last": receipt})


def stage_select_corpus(root: Path) -> None:
    """Freeze the Stage-1 cost decision before any corpus vector is built."""
    cost = json.loads((root / "stage1_cost.json").read_text(encoding="utf-8"))
    estimate = cost["estimates"]["48_training_8_heldout"]
    if estimate["projected_vector_construction_s"] > 24 * 60 * 60:
        raise RuntimeError("48+8 exceeded the predeclared one-day vector construction limit")
    frozen = ensure_corpus(root)
    atomic_json(root / "corpus_selection.json", {
        "selected_training_targets": 48,
        "selected_held_out_targets": 8,
        "reason": "The observed six-pair exact-Q2 target cost projects to under one day and well below available disk capacity; choose the largest predeclared corpus.",
        "stage1_projection": estimate,
        "corpus_sha256": frozen["sha256"],
        "no_target_vectors_existed_at_selection": not any((root / "vectors" / f"{target.identifier}.gguf").exists() for target in TRAINING + HELD_OUT),
    })


def _post(url: str, payload: dict[str, Any], timeout: float = 900) -> dict[str, Any]:
    data = canonical(payload)
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_http(base: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("llama-server exited before becoming ready")
        try:
            _post(base + "/tokenize", {"content": "ready", "add_special": False}, timeout=10)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("llama-server did not become ready")


def with_server(root: Path, vector: Path | None, layer_range: tuple[int, int], body: Any) -> Any:
    port = 64260
    log = root / "server-logs" / f"{vector.stem if vector else 'none'}-{layer_range[0]}-{layer_range[1]}-{int(time.time() * 1000)}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    command = [LLAMA_SERVER, "-m", MODEL, "-ngl", "99", "-c", "8192", "--host", "127.0.0.1", "--port", str(port), "--reasoning-format", "deepseek", "--no-warmup"]
    if vector is not None:
        command += ["--control-vector", str(vector), "--control-vector-layer-range", str(layer_range[0]), str(layer_range[1])]
    stream = log.open("w", encoding="utf-8")
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, text=True)
    try:
        base = f"http://127.0.0.1:{port}"
        _wait_http(base, process)
        return body(base, command, log)
    finally:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=30)
        stream.close()


def generation(base: str, prompt: str, seed: int) -> dict[str, Any]:
    messages = [{"role": "user", "content": prompt}]
    request = {"model": Path(MODEL).name, "messages": messages, "stream": False, "cache_prompt": False, "seed": seed, "max_tokens": 4096, "chat_template_kwargs": {"enable_thinking": True}, **SAMPLER}
    template = _post(base + "/apply-template", {"messages": messages, "add_generation_prompt": True, "chat_template_kwargs": {"enable_thinking": True}})
    started = time.monotonic()
    response = _post(base + "/v1/chat/completions", request, timeout=1800)
    elapsed = time.monotonic() - started
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    return {"request": request, "request_sha256": digest(request), "model_visible_prompt": template.get("prompt"), "model_visible_prompt_sha256": hashlib.sha256(str(template.get("prompt", "")).encode()).hexdigest(), "response": response, "reasoning": message.get("reasoning_content", ""), "final": message.get("content", ""), "finish_reason": choice.get("finish_reason"), "usage": response.get("usage"), "elapsed_s": elapsed}


def stage_layer(root: Path) -> None:
    ensure_corpus(root)
    output: list[dict[str, Any]] = []
    for target_id in LAYER_TARGETS:
        vector = root / "vectors" / f"{target_id}.gguf"
        if not vector.exists():
            raise RuntimeError("construct all training vectors before layer qualification")
        for region, layer_range in REGIONS.items():
            def run(base: str, command: list[str], log: Path) -> dict[str, Any]:
                row = generation(base, LAYER_PROMPTS[target_id], 936000 + len(output))
                return {"target": target_id, "region": region, "layer_range": layer_range, "command": command, "server_log": str(log), "server_log_sha256": file_hash(log), "generation": row}
            output.append(with_server(root, vector, layer_range, run))
            atomic_json(root / "layer_qualification.json", {"regions": REGIONS, "rows": output, "selection_rule": "Choose one predeclared global region that changes target-aligned reasoning or final framing in more than one of the three distinct targets without obvious competence damage. If none does, use broad 1-41 as the mechanically qualified baseline."})


def stage_layer_baseline(root: Path) -> None:
    """Record no-vector anchors without changing the already-persisted range rows."""
    path = root / "layer_baselines.json"
    if path.exists():
        return
    rows: list[dict[str, Any]] = []
    for index, target_id in enumerate(LAYER_TARGETS):
        def run(base: str, command: list[str], log: Path) -> dict[str, Any]:
            return {"target": target_id, "seed": 936000 + 4 * index, "command": command, "server_log": str(log), "generation": generation(base, LAYER_PROMPTS[target_id], 936000 + 4 * index)}
        rows.append(with_server(root, None, REGIONS["broad"], run))
        atomic_json(path, {"rows": rows, "complete": False})
    atomic_json(path, {"rows": rows, "complete": True})


def stage_select_layer(root: Path) -> None:
    """Freeze the one global application range before mapper fitting."""
    qualification = json.loads((root / "layer_qualification.json").read_text(encoding="utf-8"))
    baselines = json.loads((root / "layer_baselines.json").read_text(encoding="utf-8"))
    if len(qualification.get("rows", [])) != len(LAYER_TARGETS) * len(REGIONS):
        raise RuntimeError("incomplete layer qualification")
    if len(baselines.get("rows", [])) != len(LAYER_TARGETS):
        raise RuntimeError("incomplete no-vector anchors")
    atomic_json(root / "layer_selection.json", {
        "selected_region": "broad",
        "layer_range": list(REGIONS["broad"]),
        "reason": "All four predeclared ranges produced usable completions, but target-aligned content was largely invited by the qualification prompts and no narrower region showed a defensible global advantage. Broad 1-41 is the predeclared mechanically qualified baseline, frozen before mapper fit and held-out construction.",
        "qualification_sha256": file_hash(root / "layer_qualification.json"),
        "baseline_sha256": file_hash(root / "layer_baselines.json"),
    })


def embedder(root: Path):
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("install sentence-transformers in the local Phase 3.6L environment before fitting") from exc
    cache = root / "embedder-cache"
    model = SentenceTransformer(EMBEDDER, cache_folder=str(cache), revision=EMBEDDER_REVISION, device="cpu")
    return model


def matrix_for(root: Path, target_rows: tuple[Target, ...]) -> tuple[np.ndarray, list[dict[str, Any]]]:
    vectors: list[np.ndarray] = []
    metadata: list[dict[str, Any]] = []
    for target in target_rows:
        path = root / "vectors" / f"{target.identifier}.gguf"
        if not path.exists():
            raise RuntimeError(f"missing vector for {target.identifier}")
        layers = read_vector(path)
        vectors.append(np.concatenate([layers[layer] for layer in range(1, N_LAYERS + 1)]))
        metadata.append({"id": target.identifier, "vector_sha256": file_hash(path), "layer_norms": {str(layer): float(np.linalg.norm(layers[layer])) for layer in layers}})
    return np.vstack(vectors), metadata


def stage_fit(root: Path, rank: int = 12) -> None:
    ensure_corpus(root)
    if not (root / "layer_selection.json").exists():
        raise RuntimeError("freeze a global layer range before mapper fitting")
    if any((root / "vectors" / f"{target.identifier}.gguf").exists() for target in HELD_OUT):
        raise RuntimeError("held-out vectors exist before mapper fitting; preserve held-out isolation")
    model = embedder(root)
    descriptions = [target.description for target in TRAINING]
    embeddings = np.asarray(model.encode(descriptions, normalize_embeddings=True, show_progress_bar=True), dtype=np.float32)
    vector_matrix, vector_meta = matrix_for(root, TRAINING)
    mean = vector_matrix.mean(axis=0)
    centered = vector_matrix - mean
    _u, _s, basis = np.linalg.svd(centered, full_matrices=False)
    rank = min(rank, len(TRAINING) - 1, basis.shape[0])
    basis = basis[:rank]
    coefficients = centered @ basis.T
    embedding_mean = embeddings.mean(axis=0)
    x = embeddings - embedding_mean
    choices = (0.01, 0.1, 1.0, 10.0)
    loo: dict[str, float] = {}
    for alpha in choices:
        errors = []
        for omit in range(len(TRAINING)):
            keep = np.arange(len(TRAINING)) != omit
            weights = np.linalg.solve(x[keep].T @ x[keep] + alpha * np.eye(x.shape[1]), x[keep].T @ coefficients[keep])
            predicted = x[omit] @ weights
            errors.append(float(np.mean((predicted - coefficients[omit]) ** 2)))
        loo[str(alpha)] = float(np.mean(errors))
    alpha = min(choices, key=lambda value: loo[str(value)])
    weights = np.linalg.solve(x.T @ x + alpha * np.eye(x.shape[1]), x.T @ coefficients)
    np.savez_compressed(root / "mapper.npz", mean=mean, basis=basis, embedding_mean=embedding_mean, weights=weights, embeddings=embeddings, ids=np.array([target.identifier for target in TRAINING]))
    receipt = {"embedder": {"id": EMBEDDER, "revision": EMBEDDER_REVISION, "dimension": int(embeddings.shape[1]), "normalization": "L2", "device": "cpu"}, "training_target_count": len(TRAINING), "held_out_vector_visibility": False, "vector_shape": list(vector_matrix.shape), "rank": rank, "ridge_candidates": list(choices), "leave_one_out_coefficient_mse": loo, "selected_ridge_alpha": alpha, "training_vectors": vector_meta, "mapper_path": str(root / "mapper.npz"), "mapper_sha256": file_hash(root / "mapper.npz")}
    atomic_json(root / "mapper.json", receipt)


def stage_heldout_vectors(root: Path) -> None:
    if not (root / "mapper.npz").exists():
        raise RuntimeError("freeze mapper before constructing held-out vectors")
    for index, target in enumerate(HELD_OUT, 1):
        receipt = construct_vector(root, target)
        atomic_json(root / "progress" / "heldout_vectors.json", {"completed": index, "total": len(HELD_OUT), "last": receipt})


def stage_make_controls(root: Path) -> None:
    model = embedder(root)
    saved = np.load(root / "mapper.npz", allow_pickle=False)
    mean, basis, embedding_mean, weights = (saved[key] for key in ("mean", "basis", "embedding_mean", "weights"))
    train_embeddings = saved["embeddings"]
    ids = [str(value) for value in saved["ids"]]
    held_embeddings = np.asarray(model.encode([target.description for target in HELD_OUT], normalize_embeddings=True, show_progress_bar=True), dtype=np.float32)
    controls: list[dict[str, Any]] = []
    for target, embedding in zip(HELD_OUT, held_embeddings, strict=True):
        flat = mean + ((embedding - embedding_mean) @ weights) @ basis
        compiler_layers = {layer: flat[(layer - 1) * HIDDEN:layer * HIDDEN].astype(np.float32) for layer in range(1, N_LAYERS + 1)}
        compiler_path = root / "generated-vectors" / f"{target.identifier}-compiler.gguf"
        write_vector(compiler_path, compiler_layers, note=f"Phase 3.6L compiler vector for held-out {target.identifier}")
        similarities = train_embeddings @ embedding
        nearest_index = int(np.argmax(similarities))
        nearest_id = ids[nearest_index]
        nearest_source = root / "vectors" / f"{nearest_id}.gguf"
        nearest_path = root / "generated-vectors" / f"{target.identifier}-nearest-{nearest_id}.gguf"
        shutil.copy2(nearest_source, nearest_path)
        rng = np.random.default_rng(int(hashlib.sha256(target.identifier.encode()).hexdigest()[:16], 16))
        random_layers: dict[int, np.ndarray] = {}
        for layer, value in compiler_layers.items():
            norm = float(np.linalg.norm(value))
            row = rng.normal(size=HIDDEN).astype(np.float32)
            random_layers[layer] = row / np.linalg.norm(row) * norm if norm else row * 0.0
        random_path = root / "generated-vectors" / f"{target.identifier}-random.gguf"
        write_vector(random_path, random_layers, note=f"Phase 3.6L norm-matched random vector for held-out {target.identifier}")
        reference_path = root / "vectors" / f"{target.identifier}.gguf"
        controls.append({"target": target.identifier, "compiler": {"path": str(compiler_path), "sha256": file_hash(compiler_path)}, "nearest": {"training_target": nearest_id, "semantic_cosine": float(similarities[nearest_index]), "path": str(nearest_path), "sha256": file_hash(nearest_path)}, "random": {"path": str(random_path), "sha256": file_hash(random_path)}, "bespoke_reference": {"path": str(reference_path), "sha256": file_hash(reference_path)}})
    atomic_json(root / "controls.json", {"controls": controls, "gain_set": list(GAINS), "layer_regions_predeclared": REGIONS, "evaluation_seeds": list(EVALUATION_SEEDS)})


def stage_eval(root: Path, layer_range: tuple[int, int]) -> None:
    controls = json.loads((root / "controls.json").read_text(encoding="utf-8"))["controls"]
    receipt_path = root / "evaluation.json"
    previous = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    if previous and previous.get("layer_range") != list(layer_range):
        raise RuntimeError("evaluation receipt belongs to a different frozen layer range")
    rows: list[dict[str, Any]] = list(previous.get("rows", []))
    completed = {(row["target"], row["variant"], float(row["gain"])) for row in rows}
    preflight_done = any(
        any(call.get("determinism_preflight") for call in row.get("calls", []))
        for row in rows
    )
    for control in controls:
        target = control["target"]
        variants: list[tuple[str, Path | None]] = [("none", None)]
        variants += [("compiler", Path(control["compiler"]["path"])), ("nearest", Path(control["nearest"]["path"])), ("random", Path(control["random"]["path"])), ("bespoke_reference", Path(control["bespoke_reference"]["path"]))]
        for variant, vector in variants:
            for gain in (GAINS if variant != "none" else (0.0,)):
                identity = (target, variant, float(gain))
                if identity in completed:
                    continue
                def run(base: str, command: list[str], log: Path) -> dict[str, Any]:
                    nonlocal preflight_done
                    progress = root / "evaluation-progress" / f"{target}-{variant}-{gain:.2f}.json"
                    partial = json.loads(progress.read_text(encoding="utf-8")) if progress.exists() else {}
                    calls = list(partial.get("calls", []))
                    seen = {(call.get("context_index"), call.get("seed")) for call in calls if not call.get("determinism_preflight")}
                    row_base = {"target": target, "variant": variant, "gain": gain, "layer_range": layer_range, "vector": None if vector is None else {"path": str(vector), "sha256": file_hash(vector)}, "server_command": command, "server_log": str(log)}
                    if not preflight_done:
                        first = generation(base, EVAL_PROMPTS[target][0], EVALUATION_SEEDS[0])
                        duplicate = generation(base, EVAL_PROMPTS[target][0], EVALUATION_SEEDS[0])
                        stable = (first["reasoning"] == duplicate["reasoning"] and first["final"] == duplicate["final"] and first["finish_reason"] == duplicate["finish_reason"])
                        calls.append({"determinism_preflight": True, "first": first, "duplicate": duplicate, "byte_identical": stable})
                        atomic_json(progress, {**row_base, "calls": calls, "complete": False})
                        if not stable:
                            raise RuntimeError("cache_prompt=false duplicate diverged; stop sensitive evaluation")
                        preflight_done = True
                    for context_index, prompt in enumerate(EVAL_PROMPTS[target]):
                        for seed in EVALUATION_SEEDS:
                            if (context_index, seed) in seen:
                                continue
                            calls.append({"determinism_preflight": False, "context_index": context_index, "seed": seed, "generation": generation(base, prompt, seed)})
                            atomic_json(progress, {**row_base, "calls": calls, "complete": False})
                    atomic_json(progress, {**row_base, "calls": calls, "complete": True})
                    return {**row_base, "calls": calls, "progress_path": str(progress), "progress_sha256": file_hash(progress)}
                # The fixed gains are applied by a per-run vector scaled at startup through llama's native flag.
                if vector is None:
                    row = with_server(root, None, layer_range, run)
                else:
                    # with_server deliberately has a small interface.  Create a scaled copy with exact values so the
                    # evidence remains explicit and independent of server argument parsing.
                    layers = read_vector(vector)
                    scaled_path = root / "scaled-vectors" / f"{target}-{variant}-{gain:.2f}.gguf"
                    write_vector(scaled_path, {layer: values * gain for layer, values in layers.items()}, note=f"Phase 3.6L scaled {variant} gain={gain}")
                    row = with_server(root, scaled_path, layer_range, run)
                    row["applied_scaled_vector"] = {"path": str(scaled_path), "sha256": file_hash(scaled_path)}
                rows.append(row)
                completed.add(identity)
                atomic_json(receipt_path, {"layer_range": layer_range, "rows": rows, "complete": False})
    atomic_json(receipt_path, {"layer_range": layer_range, "rows": rows, "complete": True})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("pilot", "select-corpus", "training-vectors", "layer", "layer-baseline", "select-layer", "fit", "heldout-vectors", "controls", "eval"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--layer-range", default="1:41")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if file_hash(Path(MODEL)) != MODEL_SHA256:
        raise RuntimeError("frozen Gemma GGUF hash mismatch")
    if args.stage == "pilot":
        stage_pilot(root)
    elif args.stage == "select-corpus":
        stage_select_corpus(root)
    elif args.stage == "training-vectors":
        stage_training_vectors(root)
    elif args.stage == "layer":
        stage_layer(root)
    elif args.stage == "layer-baseline":
        stage_layer_baseline(root)
    elif args.stage == "select-layer":
        stage_select_layer(root)
    elif args.stage == "fit":
        stage_fit(root)
    elif args.stage == "heldout-vectors":
        stage_heldout_vectors(root)
    elif args.stage == "controls":
        stage_make_controls(root)
    elif args.stage == "eval":
        low, high = (int(value) for value in args.layer_range.split(":"))
        if not (1 <= low <= high <= N_LAYERS):
            raise ValueError("layer range must be within directions 1..41")
        stage_eval(root, (low, high))


if __name__ == "__main__":
    main()
