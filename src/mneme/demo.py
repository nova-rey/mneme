"""Bounded, offline Phase One gate demonstrations.

The approved Phase One plan names one gate driver for the three stop gates.
This module is intentionally a thin fixture orchestrator: persistence remains
owned by P0.2, interpretation/publication by P1.1, response/identity by P1.2,
and frozen comparison by P1.3.  Gate manifests are private workspace
receipts; they contain digests and coordinates rather than a second state
system or model-facing context.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import GenerationRequest, GenerationResult, TokenUsage
from .controller import ResponseController, TurnIntent
from .corrections import CorrectionService
from .experiments.comparison import ComparisonProbe, run_matched_comparison, summarize_comparison
from .experiments.inspection import inspect_checkpoint, inspect_store
from .hosts import FakeHost
from .identity import IdentityService
from .memory import InterpretationPublisher, InterpretationService, validate_residue
from .state.contracts import StoragePermissions
from .state.service import ContinuityService
from .state.snapshots import create_checkpoint, fork_from_checkpoint
from .state.storage import SQLiteStore


class DemoError(RuntimeError):
    """The requested offline gate cannot be demonstrated safely."""


_GATES = ("p1.1", "p1.2", "p1.3")
_RECEIPT_NAME = "gate.json"


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _payload_without_digest(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    payload.pop("manifest_sha256", None)
    return payload


def _manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DemoError(f"gate evidence is unreadable: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("manifest_sha256"), str):
        raise DemoError(f"gate evidence has no integrity digest: {path}")
    digest = str(value["manifest_sha256"])
    if _digest(_payload_without_digest(value)) != digest:
        raise DemoError(f"gate evidence failed integrity validation: {path}")
    return value


def _inventory(root: Path, report: Mapping[str, Any]) -> dict[str, str]:
    files: dict[str, str] = {}
    for relative in report.get("artifact_paths", []):
        if not isinstance(relative, str):
            raise DemoError("gate report contains an invalid artifact path")
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise DemoError(f"gate artifact is missing: {relative}")
        files[relative] = _file_digest(path)
    return files


def _load_prior(workspace: Path, gate: str) -> dict[str, Any]:
    previous = _GATES[_GATES.index(gate) - 1]
    path = workspace / previous / _RECEIPT_NAME
    if not path.is_file() or path.is_symlink():
        raise DemoError(f"required preceding gate evidence is missing: {previous}")
    report = _manifest(path)
    if report.get("gate") != previous or report.get("status") != "PASS":
        raise DemoError(f"required preceding gate evidence is not accepted: {previous}")
    expected = report.get("artifact_inventory")
    if not isinstance(expected, dict):
        raise DemoError(f"preceding gate has no artifact inventory: {previous}")
    actual = _inventory(workspace, report)
    if actual != {str(key): str(value) for key, value in expected.items()}:
        raise DemoError(f"preceding gate artifact inventory changed: {previous}")
    return report


def _write_gate(workspace: Path, gate: str, artifacts: list[Path], **fields: Any) -> dict[str, Any]:
    relative = [str(path.relative_to(workspace)) for path in artifacts]
    report: dict[str, Any] = {
        "artifact_kind": "mneme-phase-one-offline-gate",
        "schema_version": 1,
        "gate": gate,
        "status": "PASS",
        "host": "fake",
        "created_at": _utc(),
        "artifact_paths": relative,
        **fields,
    }
    # A timestamp is useful for private inspection but is deliberately absent
    # from the content digest used by gate identity and idempotency.
    digest_payload = dict(report)
    digest_payload.pop("created_at", None)
    report["content_sha256"] = _digest(digest_payload)
    report["artifact_inventory"] = {
        str(path): _file_digest(workspace / path) for path in relative
    }
    report["manifest_sha256"] = _digest(_payload_without_digest(report))
    path = workspace / gate / _RECEIPT_NAME
    _atomic_json(path, report)
    return report


def _existing_gate(workspace: Path, gate: str) -> dict[str, Any] | None:
    path = workspace / gate / _RECEIPT_NAME
    if not path.exists():
        return None
    report = _manifest(path)
    if report.get("gate") != gate or report.get("status") != "PASS":
        raise DemoError(f"existing gate evidence is not accepted: {gate}")
    expected = report.get("artifact_inventory")
    if not isinstance(expected, dict):
        raise DemoError(f"existing gate has no artifact inventory: {gate}")
    actual = _inventory(workspace, report)
    if actual != {str(key): str(value) for key, value in expected.items()}:
        raise DemoError(f"existing gate artifact inventory changed: {gate}")
    return report


def _residue_payload(text: str) -> dict[str, Any]:
    """Return a small source-supported residue for the fixture extractor."""

    if "weather before our hike" in text:
        first = {
            "key": "weather-check",
            "label": "Weather Check",
            "kind": "topic",
            "evidence": "weather",
        }
        second = {
            "key": "rain-jacket",
            "label": "Rain Jacket",
            "kind": "object",
            "evidence": "rain jacket",
        }
        relationship = "enables"
        edge_key = "weather-enables-rain-jacket"
    elif "rain jacket keeps" in text:
        first = {
            "key": "rain-jacket",
            "label": "Rain Jacket",
            "kind": "object",
            "evidence": "rain jacket",
        }
        second = {
            "key": "hike-continuation",
            "label": "Hike Continuation",
            "kind": "event",
            "evidence": "ending the hike early",
        }
        relationship = "enables"
        edge_key = "rain-jacket-enables-hike"
    else:
        raise DemoError(f"unknown Phase One fixture input: {text!r}")
    return {
        "core_concepts": [
            {
                "key": first["key"],
                "label": first["label"],
                "kind": first["kind"],
                "evidence": [{"source": "s0", "evidence": first["evidence"]}],
                "confidence": 0.9,
                "salience": 0.5,
                "origin": "model_output",
            },
            {
                "key": second["key"],
                "label": second["label"],
                "kind": second["kind"],
                "evidence": [{"source": "s0", "evidence": second["evidence"]}],
                "confidence": 0.8,
                "salience": 0.5,
                "origin": "model_output",
            },
        ],
        "edge_candidates": [
            {
                "key": edge_key,
                "from": first["key"],
                "to": second["key"],
                "relationship": relationship,
                "evidence": [{"source": "s0", "evidence": text}],
                "confidence": 0.8,
                "origin": "model_output",
            }
        ],
    }


class _ResidueFixtureHost(FakeHost):
    """FakeHost that supplies only deterministic, source-bound fixture residues."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.messages and "Choose one concise name" in request.messages[0].get(
            "content", ""
        ):
            return GenerationResult(
                '{"name":"Phase One Fixture"}',
                self.model_id,
                "builtin",
                dict(request.parameters),
                request.seed,
                TokenUsage(18, 5, 23),
                0.0,
                "stop",
                {"fixture": True},
                {"fixture": "deterministic_naming"},
            )
        if request.messages and request.messages[0].get("content", "").startswith(
            '{"source_slots":'
        ):
            source_payload = json.loads(request.messages[0]["content"])
            source_slots = source_payload.get("source_slots", {})
            text = source_slots.get("s0") if isinstance(source_slots, dict) else None
            if not isinstance(text, str):
                raise DemoError("fixture extractor received no source slot")
            content = json.dumps(_residue_payload(text), sort_keys=True)
            return GenerationResult(
                content,
                self.model_id,
                "builtin",
                dict(request.parameters),
                request.seed,
                TokenUsage(12, len(content.split()), 12 + len(content.split())),
                0.0,
                "stop",
                {"fixture": True},
                {"fixture": "source_bound_residue"},
            )
        return super().generate(request)


def _p11(workspace: Path) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    store_path = workspace / "lineage.sqlite3"
    if store_path.exists():
        raise DemoError("P1.1 workspace contains an unexpected existing lineage store")
    host = _ResidueFixtureHost()
    texts = (
        "Checking the weather before our hike reminded us to pack a rain jacket.",
        "A rain jacket keeps a sudden shower from ending the hike early.",
    )
    with SQLiteStore(store_path) as store:
        instance = store.create_root(
            permissions=StoragePermissions(
                store=True, export=True, interpret=True, recall=True, provider_reuse=True
            )
        )
        continuity = ContinuityService(store, instance, host)
        publications: list[dict[str, Any]] = []
        for ordinal, text in enumerate(texts):
            operation = continuity.prepare_episode(
                GenerationRequest(
                    ({"role": "user", "content": text},),
                    seed=ordinal,
                ),
                operation_id=f"phase-one-p11-episode-{ordinal}",
            )
            continuity.generate_operation(operation.operation_id)
            accepted = continuity.accept_episode(operation.operation_id)
            interpretation = InterpretationService(store, instance, host).prepare(
                operation.episode_id,
                operation_id=f"phase-one-p11-interpretation-{ordinal}",
            )
            interpretation_service = InterpretationService(store, instance, host)
            interpretation_service.execute(interpretation)
            residue = interpretation_service.validate(interpretation)
            publication = interpretation_service.publish(interpretation, residue)
            publications.append(
                {
                    "episode_id": accepted.episode_id,
                    "episode_revision": accepted.revision,
                    "interpretation_revision": publication.lineage_revision,
                    "graph_revision": publication.graph_revision,
                    "residue_sha256": residue.content_digest,
                }
            )
        checkpoint = workspace / "p1.1" / "lineage.checkpoint.sqlite3"
        create_checkpoint(store, checkpoint, checkpoint_id="phase-one-p11-checkpoint")
        counters = inspect_store(store_path)["counters"]
        report = _write_gate(
            workspace,
            "p1.1",
            [checkpoint],
            lineage_id=instance,
            checkpoint=str(checkpoint.relative_to(workspace)),
            publications=publications,
            counters=counters,
            evidence={
                "accepted_episodes": len(publications),
                "fixture_inputs": list(texts),
                "graph_routes": int(
                    store.connection.execute("SELECT COUNT(*) FROM graph_routes").fetchone()[0]
                ),
                "interpretation_calls": len(publications),
            },
            working_store=str(store_path.relative_to(workspace)),
            working_store_sha256=_file_digest(store_path),
        )
    return report


def _p12(workspace: Path) -> dict[str, Any]:
    prior = _load_prior(workspace, "p1.2")
    store_path = workspace / "lineage.sqlite3"
    if not store_path.is_file():
        raise DemoError("P1.1 lineage store is missing")
    host = _ResidueFixtureHost()
    with SQLiteStore(store_path) as store:
        current = store.current()
        instance = str(current["active_instance_id"])
        identity = IdentityService(store, instance).adopt_from_host(host)
        controller = ResponseController(store, instance, host)
        prepared = controller.prepare(
            TurnIntent(
                "Explain why the rain jacket matters on a hike",
                memory="graph",
                operation_id="phase-one-p12-response",
            )
        )
        result = controller.execute(prepared)
        correction = CorrectionService(store, instance).suppress(
            route_id=prepared.selected[0].route_key
            if prepared.selected
            else "derived:missing-fixture-route",
            context_tag="explanation",
        )
        post_correction = controller.prepare(
            TurnIntent(
                "Explain why the rain jacket matters on a hike",
                memory="graph",
                context_tags=("explanation",),
                operation_id="phase-one-p12-correction-check",
            )
        )
        checkpoint = workspace / "p1.2" / "lineage.checkpoint.sqlite3"
        create_checkpoint(store, checkpoint, checkpoint_id="phase-one-p12-checkpoint")
        child = workspace / "p1.2" / "fork.sqlite3"
        child_id = fork_from_checkpoint(
            checkpoint,
            child,
            child_id="11111111-1111-4111-8111-111111111111",
        )
        with SQLiteStore(child, read_only=True) as child_store:
            child_lineage = child_store.connection.execute(
                "SELECT parent_instance_id,fork_checkpoint_id FROM lineages WHERE instance_id=?",
                (child_id,),
            ).fetchone()
            if child_lineage is None or child_lineage[0] != instance:
                raise DemoError("P1.2 fork does not preserve parent lineage")
            child_identity = IdentityService(child_store, child_id).current()
            if child_identity is None or child_identity.name != identity.name:
                raise DemoError("P1.2 fork did not inherit self-view content")
        counters = inspect_store(store_path)["counters"]
        report = _write_gate(
            workspace,
            "p1.2",
            [checkpoint, child],
            prior_gate_sha256=prior["manifest_sha256"],
            lineage_id=instance,
            checkpoint=str(checkpoint.relative_to(workspace)),
            counters=counters,
            evidence={
                "identity_name": identity.name,
                "identity_adopted_from_host": True,
                "selected_routes": [route.route_key for route in prepared.selected],
                "post_correction_selected_routes": [
                    route.route_key for route in post_correction.selected
                ],
                "response_status": result.operation.status,
                "response_revision": result.operation.revision,
                "correction_directive_id": correction,
                "memory_payload_used": bool(prepared.selected),
                "fork_parent_instance_id": instance,
                "fork_child_instance_id": child_id,
                "fork_inherited_identity": True,
            },
            working_store=str(store_path.relative_to(workspace)),
            working_store_sha256=_file_digest(store_path),
        )
    return report


def _p13(workspace: Path) -> dict[str, Any]:
    prior = _load_prior(workspace, "p1.3")
    source_checkpoint = workspace / "p1.2" / "lineage.checkpoint.sqlite3"
    if not source_checkpoint.is_file():
        raise DemoError("P1.2 checkpoint is missing")
    authored_child = workspace / "p1.3" / "authored-control.sqlite3"
    authored_checkpoint = workspace / "p1.3" / "authored-control.checkpoint.sqlite3"
    fork_from_checkpoint(
        source_checkpoint,
        authored_child,
        child_id="22222222-2222-4222-8222-222222222222",
    )
    authored_text = "Authored control route: VRAM constrains model capacity"
    with SQLiteStore(authored_child) as authored_store:
        authored_instance = str(authored_store.current()["active_instance_id"])
        operation = ContinuityService(
            authored_store, authored_instance, FakeHost()
        ).prepare_episode(
            GenerationRequest(({"role": "user", "content": authored_text},)),
            operation_id="phase-one-p13-authored-control-episode",
        )
        continuity = ContinuityService(authored_store, authored_instance, FakeHost())
        continuity.generate_operation(operation.operation_id)
        continuity.accept_episode(operation.operation_id)
        residue = validate_residue(
            {
                "core_concepts": [
                    {
                        "key": "authored-vram",
                        "label": "VRAM",
                        "kind": "resource",
                        "source_spans": [{"source_slot": "s0", "start": 24, "end": 28}],
                        "confidence": 0.9,
                        "origin": "authored_control",
                    },
                    {
                        "key": "authored-capacity",
                        "label": "model capacity",
                        "kind": "concept",
                        "source_spans": [{"source_slot": "s0", "start": 40, "end": 54}],
                        "confidence": 0.9,
                        "origin": "authored_control",
                    },
                ],
                "edge_candidates": [
                    {
                        "key": "authored-control-edge",
                        "from": "authored-vram",
                        "to": "authored-capacity",
                        "relationship": "constrains",
                        "source_spans": [{"source_slot": "s0", "start": 24, "end": 54}],
                        "confidence": 0.9,
                        "origin": "authored_control",
                    }
                ],
                "route_candidates": [
                    {
                        "key": "authored-control-route",
                        "edge_keys": ["authored-control-edge"],
                        "source_spans": [{"source_slot": "s0", "start": 24, "end": 54}],
                        "confidence": 0.9,
                        "origin": "authored_control",
                    }
                ],
            },
            {"s0": authored_text},
        )
        publication = InterpretationPublisher(authored_store, authored_instance).publish(
            InterpretationPublisher(authored_store, authored_instance).prepare(
                operation.episode_id,
                operation_id="phase-one-p13-authored-control-interpretation",
            ),
            residue,
        )
        create_checkpoint(
            authored_store,
            authored_checkpoint,
            checkpoint_id="phase-one-p13-authored-control-checkpoint",
        )
        authored_revision = publication.lineage_revision
    checkpoint = authored_checkpoint
    before_file = _file_digest(checkpoint)
    before_state = inspect_checkpoint(checkpoint)
    artifact_dir = workspace / "p1.3" / "comparison"
    probes = [
        ComparisonProbe(0, ({"role": "user", "content": "Explain VRAM capacity"},)),
        ComparisonProbe(1, ({"role": "user", "content": "What is a garden?"},)),
        ComparisonProbe(
            2,
            (
                {
                    "role": "user",
                    "content": "Return JSON with one key named answer about VRAM capacity.",
                },
            ),
        ),
        ComparisonProbe(
            3,
            (
                {
                    "role": "user",
                    "content": "Use the authored control route to explain VRAM capacity.",
                },
            ),
        ),
    ]
    results = run_matched_comparison(
        checkpoint,
        FakeHost(),
        probes,
        subject_slot="phase-one-fixture",
        repetitions=1,
        seeds={(0, 0, "no_memory"): 7},
        artifact_dir=artifact_dir,
        provenance={"gate": "p1.3", "prior_gate_sha256": prior["manifest_sha256"]},
    )
    class _FailingHost(FakeHost):
        def generate(self, request: GenerationRequest) -> GenerationResult:
            raise DemoError("completed comparison unexpectedly called the host")

    rerun = run_matched_comparison(
        checkpoint,
        _FailingHost(),
        probes,
        subject_slot="phase-one-fixture",
        repetitions=1,
        seeds={(0, 0, "no_memory"): 7},
        artifact_dir=artifact_dir,
        provenance={"gate": "p1.3", "prior_gate_sha256": prior["manifest_sha256"]},
    )
    if len(rerun) != len(results):
        raise DemoError("completed comparison re-entry returned incomplete results")
    after_file = _file_digest(checkpoint)
    after_state = inspect_checkpoint(checkpoint)
    if before_file != after_file or before_state != after_state:
        raise DemoError("frozen comparison changed checkpoint state")
    artifacts = [
        source_checkpoint,
        authored_child,
        authored_checkpoint,
        artifact_dir / "comparison.json",
        artifact_dir / "comparison.md",
    ]
    return _write_gate(
        workspace,
        "p1.3",
        artifacts,
        prior_gate_sha256=prior["manifest_sha256"],
        checkpoint=str(checkpoint.relative_to(workspace)),
        source_checkpoint=str(source_checkpoint.relative_to(workspace)),
        counters=after_state["counters"],
        evidence={
            "matched_readouts": len(results),
            "probe_count": len(probes),
            "identity_enabled": False,
            "treatments": [result.treatment for result in results],
            "measurements": summarize_comparison(results),
            "checkpoint_file_unchanged": True,
            "checkpoint_state_unchanged": True,
            "idempotent_reentry_without_host_call": True,
            "authored_control_child": str(authored_child.relative_to(workspace)),
            "authored_control_route": "authored-control-route",
            "authored_control_revision": authored_revision,
            "comparison_artifact": str((artifact_dir / "comparison.json").relative_to(workspace)),
        },
    )


def run_phase_one_gate(
    *, gate: str, host: str, workspace: str | Path, live_budget: str | None = None
) -> dict[str, Any]:
    """Run one bounded FakeHost gate and return its private manifest."""

    if gate not in _GATES:
        raise DemoError(f"unknown Phase One gate: {gate}")
    if host != "fake":
        if live_budget != "phase-one-v1":
            raise DemoError(
                "live Phase One gates require the approved --live-budget phase-one-v1"
            )
        raise DemoError(
            "live Phase One execution is not provided by the offline gate driver; "
            "no host call was made"
        )
    if live_budget is not None:
        raise DemoError("--live-budget is only valid with a live host")
    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    existing = _existing_gate(root, gate)
    if existing is not None:
        return existing
    if gate == "p1.1":
        return _p11(root)
    if gate == "p1.2":
        return _p12(root)
    return _p13(root)


__all__ = ["DemoError", "run_phase_one_gate"]
