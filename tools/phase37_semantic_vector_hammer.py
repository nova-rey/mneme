#!/usr/bin/env python3
"""Isolated, resumable Phase 3.7 semantic control-vector qualification.

This utility uses a disposable llama.cpp server and external artifact directory.
It never imports MNEME code or loads developmental state.
"""
# ruff: noqa: E501, E701, E702
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ModuleNotFoundError:  # corpus-only tests do not require research dependencies
    np = None  # type: ignore[assignment]

MODEL = "/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf"
MODEL_SHA256 = "79dde517866cfbb5c00230b530de17910fc7fc78f8827554d0e14281ce5faf03"
GENERATOR = "/tmp/mneme-phase36-llama-build/bin/llama-cvector-generator"
SERVER = "/home/rey/src/llama.cpp/build-cuda/bin/llama-server"
GGUF_PY = "/tmp/mneme-phase36-llama/gguf-py"
N_LAYERS, HIDDEN = 41, 2560
SEEDS = (937100, 937101)
SCREEN_GAIN = 0.60
GAINS = (0.20, 0.60, 1.00, 1.50)
RANGES = {"early_middle": (9, 18), "middle": (17, 29), "late_middle": (28, 38), "broad": (1, 41)}
SAMPLER = {"temperature": 0.35, "top_k": 40, "top_p": 0.90, "min_p": 0.05}


@dataclass(frozen=True)
class Target:
    identifier: str
    title: str
    description: str
    evaluation_prompts: tuple[str, str]
    contrasts: tuple[tuple[str, str], ...]


def pairs(*items: tuple[str, str]) -> tuple[tuple[str, str], ...]:
    assert len(items) == 16
    return items


TARGETS: tuple[Target, ...] = (
    Target(
        "ecological_succession",
        "Ecological succession",
        "Disturbed systems often develop through enabling stages: early pioneer measures alter conditions for later structure; stabilization and mature organization emerge over time; immediate total replacement is not always best.",
        (
            "A community radio station has lost listeners after a long period of irregular programming. It has a small budget, several aging shows, and volunteers with different interests. What should its programming committee do next?",
            "A city has acquired a narrow, noisy strip of land beside a busy road. Residents want it to become more useful, but the city cannot afford a major redevelopment. What should it do?",
        ),
        pairs(
            ("After a fire, hardy ground cover is established first; it holds soil and creates shade that later shrubs can use.", "After a fire, planners install the final mature landscape immediately and treat early temporary growth as wasted effort."),
            ("A damaged hillside is stabilized with small roots and ground cover before deeper-rooted plants are introduced.", "A damaged hillside is replanted in one final step without first stabilizing the exposed soil."),
            ("A neglected site begins with modest repairs that make later, more durable organization possible.", "A neglected site waits for a single complete rebuild before any useful improvement can begin."),
            ("A recovery team establishes simple reliable routines first, then adds more demanding capabilities after those routines hold.", "A recovery team installs every advanced capability at once, assuming the final arrangement can be imposed immediately."),
            ("Temporary supports improve the environment enough that later structures can take root and persist.", "Temporary supports are rejected because only the finished structure is considered worthwhile."),
            ("A bare area develops through successive occupants, each changing conditions for what can persist next.", "A bare area is treated as though the final occupants can succeed without any earlier changes to conditions."),
            ("A community restores a damaged place in stages, using early successes to reduce uncertainty before later commitments.", "A community restores a damaged place by committing to the entire final design before learning from any early work."),
            ("Early interventions are chosen for their ability to make a later arrangement viable, not for looking complete on day one.", "Interventions are chosen only for looking complete on day one, regardless of whether they support later stability."),
            ("A restoration plan lets preliminary work alter constraints before deciding the mature arrangement.", "A restoration plan fixes the mature arrangement first and treats later constraints as irrelevant."),
            ("Small durable footholds are created first, then linked into a more stable larger system.", "The plan attempts to create the whole large system immediately, with no smaller footholds."),
            ("Conditions are improved progressively so that more demanding forms of organization become feasible later.", "Conditions are ignored while demanding forms of organization are installed immediately."),
            ("A damaged system is allowed to recover through a sequence in which each phase prepares the next.", "A damaged system is expected to jump directly from disruption to its desired final state."),
            ("Early work is evaluated by whether it changes the environment in ways that support later work.", "Early work is dismissed unless it already looks like the final desired result."),
            ("A plan protects early fragile gains while they create conditions for longer-term stabilization.", "A plan repeatedly replaces early fragile gains instead of letting them stabilize into a foundation."),
            ("Recovery proceeds through path-dependent stages rather than treating all actions as interchangeable.", "Recovery treats every action as interchangeable and independent of what happened before."),
            ("A staged approach begins with pioneers that can handle harsh conditions and leaves later roles for when conditions improve.", "A staged approach is rejected in favor of installing later roles before conditions can support them."),
        ),
    ),
    Target(
        "musical_counterpoint",
        "Musical counterpoint",
        "Several independent lines can remain locally coherent while interacting to form a coordinated whole; coordination need not collapse work into one line; complementary roles and planned interactions can create tension and resolution.",
        (
            "A district library wants one large reading room to feel welcoming to quiet researchers, families with children, and people dropping in for short visits. How should it plan the room and its programming?",
            "A civic information hotline receives questions from residents, local businesses, and nonprofit groups. People say the service is confusing even when staff know the answers. How should the hotline be redesigned?",
        ),
        pairs(
            ("Several teams keep clear independent responsibilities and meet at defined handoff points where their work affects one another.", "Several teams surrender their independent responsibilities and route all work through one central sequence."),
            ("Each contributor maintains a coherent local task while responding to the changing work of the others.", "Contributors abandon local coherence and wait for one master task to dictate every next move."),
            ("Complementary roles interact without duplicating one another, creating a coordinated whole from distinct parts.", "All roles are made identical so coordination comes only from everyone doing the same thing."),
            ("Parallel work streams retain autonomy but use deliberate points of alignment and adjustment.", "Parallel work streams are prohibited; every task must wait for the previous one to finish."),
            ("Independent plans are designed to remain understandable alone and useful when combined.", "Plans are designed only as fragments of one opaque centralized plan."),
            ("Different lines carry different responsibilities and periodically resolve tensions where they intersect.", "Different responsibilities are collapsed into one role so intersections cannot occur."),
            ("Coordination comes from listening and responding at interaction points, not from forcing uniform movement.", "Coordination comes only from forcing every participant into uniform movement at all times."),
            ("A larger pattern emerges when several self-contained efforts are arranged to complement one another.", "A larger pattern is pursued by erasing differences among all efforts."),
            ("Local initiative is preserved while shared rules prevent incompatible choices at key moments.", "Local initiative is eliminated so shared rules control every choice at every moment."),
            ("Distinct contributors develop their own material and exchange cues that shape the common result.", "Distinct contributors are forbidden from developing their own material and only repeat the same central instruction."),
            ("Good coordination allows temporary tension between independent aims, followed by explicit resolution.", "Good coordination eliminates independent aims so no tension or resolution can ever occur."),
            ("Several activities proceed simultaneously, each legible in itself and responsive to the others.", "Only one activity may proceed, because simultaneous activity is treated as necessarily incoherent."),
            ("The system values complementarity: one role can leave room for another rather than competing for identical scope.", "The system values identical scope: every role competes to cover the same work."),
            ("Interfaces let separate work streams influence one another without merging their identities.", "Interfaces are removed so separate work streams must merge into one identity."),
            ("Coordination uses recurring exchanges among distinct roles, producing structure without a single controlling line.", "Coordination uses a single controlling line and denies distinct roles any meaningful exchange."),
            ("A group combines independent, responsive contributions into a coherent arrangement.", "A group accepts coherence only by making all contributions subordinate copies of one contribution."),
        ),
    ),
    Target(
        "defense_in_depth",
        "Defense in depth",
        "Resilient defense uses multiple partially independent layers with distinct detection and response roles; local containment and evidence-based escalation mean one bypassed barrier does not imply total failure.",
        (
            "A university club keeps losing shared equipment from its storage room. Keys are copied informally, inventory records are inconsistent, and nobody is sure who should fix small problems. What should the club change?",
            "A small nonprofit plans public events with volunteers who vary in experience. Tasks occasionally fall through, but the group wants to become more reliable without treating volunteers as suspects. What operating changes would help?",
        ),
        pairs(
            ("A problem is met by several distinct checks: early detection, local containment, and escalation when evidence warrants it.", "A problem is met by one central check; if it misses the problem, no other response exists."),
            ("Different safeguards watch for different failure signals and can act independently when one signal is missed.", "All safeguards watch for the same signal and fail together when that single signal is missed."),
            ("A small issue is contained locally while larger or repeated evidence triggers a broader response.", "Every issue either receives no response or immediately triggers the broadest possible response."),
            ("Several non-identical barriers reduce the chance that one overlooked problem becomes a total failure.", "One identical barrier is treated as sufficient, even though its failure leaves no remaining protection."),
            ("Detection, containment, recovery, and escalation have separate roles that reinforce one another.", "Detection, containment, recovery, and escalation are all assigned to one overloaded role."),
            ("A missed check does not end protection because another layer can notice a different trace later.", "A missed check ends protection because no later layer is allowed to notice a different trace."),
            ("Local responders can limit harm quickly while preserving a path to evidence-based escalation.", "Local responders must wait for a central authority, even when a small harm could be limited immediately."),
            ("Safeguards are diverse so common mistakes do not defeat every protection at once.", "Safeguards are uniform so the same mistake defeats every protection at once."),
            ("The design anticipates partial failures and uses fallback roles rather than assuming perfect compliance.", "The design assumes perfect compliance and provides no fallback roles for partial failures."),
            ("Several modest protections combine so that bypassing one does not grant unrestricted access.", "One strong protection is relied on exclusively, so bypassing it grants unrestricted access."),
            ("Evidence accumulates across layers before high-cost intervention, while lower-cost containment can happen early.", "High-cost intervention is triggered without evidence accumulation, while low-cost containment is unavailable."),
            ("A disturbance can be isolated near its source before it spreads to unrelated parts of the system.", "A disturbance is allowed to spread until a single central response can address everything at once."),
            ("Different people and tools contribute distinct checks rather than repeating the same fragile procedure.", "Different people and tools repeat the same fragile procedure rather than contributing distinct checks."),
            ("The system remains useful when one layer is absent because remaining layers have non-overlapping functions.", "The system becomes useless when one layer is absent because all layers have the same function."),
            ("Responses scale with severity and confidence, preserving ordinary activity while addressing real risk.", "Responses ignore severity and confidence, treating all situations as either unrestricted or shut down."),
            ("A resilient plan makes it difficult for a single overlooked problem to become a system-wide collapse.", "A fragile plan permits a single overlooked problem to become a system-wide collapse."),
        ),
    ),
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical(value) + b"\n")
    with tmp.open("rb") as f:
        os.fsync(f.fileno())
    tmp.replace(path)


def text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    with tmp.open("rb") as f:
        os.fsync(f.fileno())
    tmp.replace(path)


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n")


def prompt(statement: str) -> str:
    return "<|start_header_id|>system<|end_header_id|>\n\nUse the following concrete situation as an organizing lens for a short response.\n" + statement + "<|eot_id|><|start_header_id|>user<|end_header_id|>\n\nHow should a local group plan a difficult project?\n<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"


def manifest(root: Path) -> dict[str, Any]:
    value = {"experiment": "mneme-phase-3-7-semantic-vector-hammer", "model": MODEL, "model_sha256": MODEL_SHA256, "layer_mapping": {"ignored_capture": "l_out layer zero", "directions": list(range(1, 42))}, "targets": [asdict(t) for t in TARGETS], "ranges": RANGES, "gains": GAINS, "screen_gain": SCREEN_GAIN, "seeds": SEEDS, "sampler": SAMPLER}
    value["sha256"] = sha(value)
    # Normalize tuples to the UTF-8 JSON form persisted by atomic().
    return json.loads(canonical(value).decode("utf-8"))


def ensure_manifest(root: Path) -> dict[str, Any]:
    expected = manifest(root)
    path = root / "manifest.json"
    if path.exists():
        got = json.loads(path.read_text())
        if got != expected:
            raise RuntimeError("immutable manifest differs")
    else:
        atomic(path, expected)
    return expected


def post(base: str, endpoint: str, payload: dict[str, Any], timeout: int = 1800) -> dict[str, Any]:
    req = urllib.request.Request(base + endpoint, data=canonical(payload), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def server(root: Path, *, vector: Path | None, layer_range: tuple[int, int], gain: float, fn: Any) -> Any:
    # Bind a disposable port before each isolated server. A fixed research port can
    # accidentally route a coordinate to a stale prior server after interruption.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = int(reservation.getsockname()[1])
    tag = f"{vector.stem if vector else 'none'}-{layer_range[0]}-{layer_range[1]}-{gain}-{port}-{time.time_ns()}"
    log = root / "server" / f"{tag}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [SERVER, "-m", MODEL, "-ngl", "99", "-c", "8192", "--host", "127.0.0.1", "--port", str(port), "--reasoning-format", "deepseek", "--no-warmup"]
    if vector:
        cmd += ["--control-vector-scaled", f"{vector}:{gain}", "--control-vector-layer-range", str(layer_range[0]), str(layer_range[1])]
    out = log.open("w")
    process = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, text=True)
    try:
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("server died: " + log.read_text(errors="replace")[-1000:])
            try:
                post(base, "/tokenize", {"content": "ready", "add_special": False}, 10)
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("server did not become ready")
        return fn(base, cmd, log)
    finally:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(30)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(30)
        out.close()


def generate(base: str, user_prompt: str, seed: int) -> dict[str, Any]:
    messages = [{"role": "user", "content": user_prompt}]
    request = {"model": Path(MODEL).name, "messages": messages, "stream": False, "cache_prompt": False, "seed": seed, "max_tokens": 4096, "chat_template_kwargs": {"enable_thinking": True}, **SAMPLER}
    template = post(base, "/apply-template", {"messages": messages, "add_generation_prompt": True, "chat_template_kwargs": {"enable_thinking": True}}, 30)
    started = time.monotonic(); response = post(base, "/v1/chat/completions", request); elapsed = time.monotonic() - started
    choice = response.get("choices", [{}])[0]; message = choice.get("message", {})
    return {"request": request, "request_sha256": sha(request), "model_visible_prompt": template.get("prompt"), "prompt_sha256": hashlib.sha256(str(template.get("prompt", "")).encode()).hexdigest(), "response": response, "reasoning": message.get("reasoning_content", ""), "final": message.get("content", ""), "finish_reason": choice.get("finish_reason"), "usage": response.get("usage"), "elapsed_s": elapsed}


def baseline(root: Path) -> None:
    ensure_manifest(root); path = root / "baseline.json"; rows = json.loads(path.read_text()).get("rows", []) if path.exists() else []
    done = {(x["target"], x["context"], x["seed"]) for x in rows}
    def run(base: str, cmd: list[str], log: Path) -> None:
        nonlocal rows
        for target in TARGETS:
            for index, user_prompt in enumerate(target.evaluation_prompts):
                for seed in SEEDS:
                    key = (target.identifier, index, seed)
                    if key in done: continue
                    row = {"target": target.identifier, "context": index, "seed": seed, "server_command": cmd, "server_log": str(log), "generation": generate(base, user_prompt, seed)}
                    rows.append(row); atomic(path, {"rows": rows, "complete": False})
        atomic(path, {"rows": rows, "complete": True})
    server(root, vector=None, layer_range=RANGES["broad"], gain=0, fn=run)


def pairs_files(root: Path, target: Target, index: int | None) -> tuple[Path, Path]:
    directory = root / "contrasts" / target.identifier / ("all" if index is None else f"pair-{index:02d}")
    items = target.contrasts if index is None else (target.contrasts[index],)
    pos, neg = directory / "positive.txt", directory / "negative.txt"
    text_atomic(pos, "\n".join(escape(prompt(x[0])) for x in items) + "\n")
    text_atomic(neg, "\n".join(escape(prompt(x[1])) for x in items) + "\n")
    atomic(directory / "pairs.json", {"target": target.identifier, "items": list(items), "sha256": sha(items)})
    return pos, neg


def read_vector(path: Path) -> dict[int, np.ndarray]:
    sys.path.insert(0, GGUF_PY)
    from gguf import GGUFReader  # type: ignore
    reader = GGUFReader(str(path)); rows: dict[int, np.ndarray] = {}
    for tensor in reader.tensors:
        if tensor.name.startswith("direction."):
            rows[int(tensor.name.split(".", 1)[1])] = np.asarray(tensor.data, dtype=np.float32).reshape(-1).copy()
    if sorted(rows) != list(range(1, 42)) or any(v.shape != (HIDDEN,) for v in rows.values()):
        raise RuntimeError(f"bad layer identity {path}")
    return rows


def write_vector(path: Path, values: dict[int, np.ndarray], description: str) -> None:
    sys.path.insert(0, GGUF_PY)
    from gguf import GGUFWriter  # type: ignore
    path.parent.mkdir(parents=True, exist_ok=True); staged = path.with_suffix(".tmp")
    writer = GGUFWriter(staged, "controlvector"); writer.add_string("controlvector.model_hint", "gemma4"); writer.add_uint32("controlvector.layer_count", 41); writer.add_string("general.description", description)
    for layer in range(1, 42): writer.add_tensor(f"direction.{layer}", np.asarray(values[layer], dtype=np.float32))
    writer.write_header_to_file(); writer.write_kv_data_to_file(); writer.write_tensors_to_file(); writer.close(); staged.replace(path)


def make_one(root: Path, target: Target, method: str, index: int | None = None) -> Path:
    label = "all" if index is None else f"pair-{index:02d}"; output = root / "work-vectors" / target.identifier / method / f"{label}.gguf"
    if output.exists(): return output
    pos, neg = pairs_files(root, target, index); log = output.with_suffix(".log"); output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [GENERATOR, "-m", MODEL, "-ngl", "99", "--method", "mean", "--positive-file", str(pos), "--negative-file", str(neg), "-o", str(output), "--log-file", str(log)]
    started = time.monotonic(); cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True); elapsed = time.monotonic()-started; text_atomic(log, cp.stdout)
    if cp.returncode or not output.exists(): raise RuntimeError(f"vector generation failed {target.identifier} {label}: {log}")
    read_vector(output); atomic(output.with_suffix(".json"), {"target": target.identifier, "method": method, "pair_index": index, "elapsed_s": elapsed, "command": cmd, "sha256": hash_file(output), "bytes": output.stat().st_size})
    return output


def construct(root: Path, selected_target: str | None = None) -> None:
    if np is None:
        raise RuntimeError("construct requires numpy in the isolated research environment")
    ensure_manifest(root)
    active = [target for target in TARGETS if selected_target in (None, target.identifier)]
    if not active:
        raise ValueError(f"unknown target {selected_target}")
    for target in active:
        mean_path = root / "vectors" / f"{target.identifier}-mean.gguf"
        if not mean_path.exists():
            source = make_one(root, target, "mean", None); mean_path.parent.mkdir(parents=True, exist_ok=True); subprocess.run(["cp", "--reflink=auto", str(source), str(mean_path)], check=True)
        robust_path = root / "vectors" / f"{target.identifier}-median.gguf"
        if not robust_path.exists():
            members = [read_vector(make_one(root, target, "median-member", i)) for i in range(len(target.contrasts))]
            robust = {layer: np.median(np.stack([member[layer] for member in members]), axis=0) for layer in range(1, 42)}
            write_vector(robust_path, robust, f"Phase 3.7 coordinate-wise median of 16 exact-Q2 pair vectors: {target.identifier}")
        atomic(root / "vectors" / f"{target.identifier}.json", {"target": asdict(target), "mean": {"path": str(mean_path), "sha256": hash_file(mean_path)}, "median": {"path": str(robust_path), "sha256": hash_file(robust_path)}, "contrast_hash": sha(target.contrasts), "pair_count": 16, "directions": list(range(1,42))})


def random_like(root: Path, vector: Path, target: str) -> Path:
    if np is None:
        raise RuntimeError("random control construction requires numpy")
    path = root / "vectors" / f"{target}-random.gguf"
    if path.exists(): return path
    rng = np.random.default_rng(int(hashlib.sha256(("phase37"+target).encode()).hexdigest()[:16],16)); original = read_vector(vector)
    values = {}
    for layer, value in original.items():
        row = rng.normal(size=HIDDEN).astype(np.float32); values[layer] = row / np.linalg.norm(row) * np.linalg.norm(value)
    write_vector(path, values, f"Phase 3.7 matched random control {target}"); return path


def screen(root: Path, selected_target: str | None = None) -> None:
    """Screen one target at a time; each vector/range gets one reusable server."""
    ensure_manifest(root)
    path = root / "screen.json"
    rows = json.loads(path.read_text()).get("rows", []) if path.exists() else []
    done = {(x["target"], x["method"], x["range"]) for x in rows}
    active = [target for target in TARGETS if selected_target in (None, target.identifier)]
    if not active:
        raise ValueError(f"unknown target {selected_target}")
    for target in active:
        for method in ("mean", "median"):
            vector = root / "vectors" / f"{target.identifier}-{method}.gguf"
            for name, layer_range in RANGES.items():
                if (target.identifier, method, name) in done:
                    continue
                def run(base: str, cmd: list[str], log: Path) -> dict[str, Any]:
                    return {
                        "target": target.identifier, "method": method, "range": name,
                        "layer_range": layer_range, "gain": SCREEN_GAIN,
                        "vector_sha256": hash_file(vector), "server_command": cmd,
                        "server_log": str(log),
                        "generation": generate(base, target.evaluation_prompts[0], SEEDS[0]),
                    }
                rows.append(server(root, vector=vector, layer_range=layer_range, gain=SCREEN_GAIN, fn=run))
                atomic(path, {"rows": rows, "complete": False})
    atomic(path, {"rows": rows, "complete": True})

def eval_candidate(root: Path, target_id: str, method: str, range_name: str) -> None:
    """Full validation groups four context/seed calls under each loaded vector."""
    target = next(x for x in TARGETS if x.identifier == target_id)
    vector = root / "vectors" / f"{target_id}-{method}.gguf"
    random = random_like(root, vector, target_id)
    path = root / "validation" / f"{target_id}-{method}-{range_name}.json"
    rows = json.loads(path.read_text()).get("rows", []) if path.exists() else []
    done = {(r["variant"], float(r["gain"])) for r in rows}
    layer_range = RANGES[range_name]
    variants: list[tuple[str, Path | None, tuple[float, ...]]] = [
        ("none", None, (0.0,)),
        ("candidate", vector, GAINS),
        ("random", random, GAINS),
        ("sign_reversal", vector, tuple(-value for value in GAINS)),
    ]
    for variant, vec, gains in variants:
        for gain in gains:
            if (variant, float(gain)) in done:
                continue
            progress = root / "validation-progress" / f"{target_id}-{method}-{range_name}-{variant}-{gain:+.2f}.json"
            prior = json.loads(progress.read_text()).get("calls", []) if progress.exists() else []
            seen = {(call["context"], call["seed"]) for call in prior}
            def run(base: str, cmd: list[str], log: Path) -> dict[str, Any]:
                calls = list(prior)
                for context, prompt_text in enumerate(target.evaluation_prompts):
                    for seed in SEEDS:
                        if (context, seed) in seen:
                            continue
                        calls.append({"context": context, "seed": seed, "generation": generate(base, prompt_text, seed)})
                        atomic(progress, {"target": target_id, "variant": variant, "gain": gain, "calls": calls, "complete": False})
                atomic(progress, {"target": target_id, "variant": variant, "gain": gain, "calls": calls, "complete": True})
                return {
                    "target": target_id, "method": method, "range": range_name,
                    "layer_range": layer_range, "variant": variant, "gain": gain,
                    "vector_sha256": None if vec is None else hash_file(vec),
                    "server_command": cmd, "server_log": str(log), "calls": calls,
                    "progress_path": str(progress), "progress_sha256": hash_file(progress),
                }
            rows.append(server(root, vector=vec, layer_range=layer_range, gain=gain, fn=run))
            atomic(path, {"rows": rows, "complete": False})
    atomic(path, {"rows": rows, "complete": True})

def status(root: Path) -> None:
    result={"root":str(root),"manifest":(root/"manifest.json").exists(),"baseline":(root/"baseline.json").exists(),"vectors":sorted(str(x) for x in (root/"vectors").glob("*.gguf")) if (root/"vectors").exists() else [],"screen_rows":len(json.loads((root/"screen.json").read_text()).get("rows",[])) if (root/"screen.json").exists() else 0,"validations":sorted(str(x) for x in (root/"validation").glob("*.json")) if (root/"validation").exists() else []}; print(json.dumps(result,indent=2))


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("stage",choices=("baseline","construct","screen","validate","status")); parser.add_argument("--root",type=Path,required=True); parser.add_argument("--target"); parser.add_argument("--method",choices=("mean","median")); parser.add_argument("--range",dest="range_name",choices=tuple(RANGES)); args=parser.parse_args(); root=args.root.resolve(); root.mkdir(parents=True,exist_ok=True)
    if hash_file(Path(MODEL)) != MODEL_SHA256: raise RuntimeError("GGUF SHA mismatch")
    if args.stage=="baseline": baseline(root)
    elif args.stage=="construct": construct(root, args.target)
    elif args.stage=="screen": screen(root, args.target)
    elif args.stage=="validate":
        if not (args.target and args.method and args.range_name): parser.error("validate needs --target --method --range")
        eval_candidate(root,args.target,args.method,args.range_name)
    else: status(root)
if __name__=="__main__": main()
