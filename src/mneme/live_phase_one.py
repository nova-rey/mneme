"""Bounded live Phase One acceptance driver.

The live driver is intentionally a thin orchestration layer around the
existing P0.2/P0.3/P1 services.  It owns call coordinates, hard budgeting,
private receipts, and stop-on-failure behavior; developmental state remains
owned by the continuity, interpretation, identity, and frozen-evaluation
services.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .contracts import (
    GenerationRequest,
    GenerationResult,
    HostCapabilities,
    HostFingerprint,
    TokenUsage,
)
from .controller import ResponseController, TurnIntent
from .corrections import CorrectionService
from .experiments.artifacts import file_digest
from .experiments.comparison import (
    ComparisonProbe,
    FrozenComparator,
    run_matched_comparison,
    summarize_comparison,
    write_comparison_artifacts,
)
from .experiments.evaluation import FrozenEvaluationView
from .experiments.inspection import inspect_checkpoint, inspect_store
from .experiments.live_accounting import summarize_lineage_usage
from .host import Host
from .hosts import DeepInfraGemmaHost
from .identity import IdentityService
from .memory.interpretation import (
    InterpretationService,
    InterpretationValidationError,
)
from .state.contracts import StoragePermissions
from .state.service import ContinuityService
from .state.snapshots import create_checkpoint
from .state.storage import SQLiteStore


class LivePhaseOneError(RuntimeError):
    """A required live acceptance action failed or was unsafe to continue."""


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _usage(value: TokenUsage | None) -> dict[str, int | None] | None:
    return None if value is None else {
        "input_tokens": value.input_tokens,
        "output_tokens": value.output_tokens,
        "total_tokens": value.total_tokens,
    }


def _json_file(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")


def _software_revision() -> str:
    repository = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    revision = result.stdout.strip()
    return revision if revision else "unknown"


class BudgetHost:
    """Record and reserve every provider call before dispatch."""

    def __init__(
        self,
        delegate: Host,
        report: dict[str, Any],
        maximum_calls: int = 27,
        report_path: Path | None = None,
    ):
        self.delegate = delegate
        self.report = report
        self.maximum_calls = maximum_calls
        self.report_path = report_path
        self.call_count = 0
        self.gate = "unknown"
        self.role = "unknown"

    def capabilities(self) -> HostCapabilities:
        return self.delegate.capabilities()

    def fingerprint(self) -> HostFingerprint:
        return self.delegate.fingerprint()

    def set_coordinate(self, gate: str, role: str) -> None:
        self.gate = gate
        self.role = role

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.call_count >= self.maximum_calls:
            raise LivePhaseOneError("live call budget exhausted before dispatch")
        self.call_count += 1
        ordinal = self.call_count
        record: dict[str, Any] = {
            "ordinal": ordinal,
            "gate": self.gate,
            "role": self.role,
            "request_sha256": _digest(request.generation_material()),
            "requested_output_tokens": request.parameters.get("max_new_tokens"),
            "status": "RESERVED",
        }
        self.report.setdefault("calls", []).append(record)
        if self.report_path is not None:
            _json_file(self.report_path, self.report)
        record["status"] = "DISPATCHED"
        if self.report_path is not None:
            _json_file(self.report_path, self.report)
        try:
            result = self.delegate.generate(request)
        except Exception as exc:
            record.update({"status": "UNCERTAIN", "error_type": type(exc).__name__})
            if self.report_path is not None:
                _json_file(self.report_path, self.report)
            raise
        record.update(
            {
                "status": "RETURNED",
                "provider": result.provider,
                "model_id": result.model_id,
                "finish_reason": result.finish_reason,
                "usage": _usage(result.token_usage),
                "output_sha256": hashlib.sha256(result.content.encode()).hexdigest(),
                "output_chars": len(result.content),
            }
        )
        if self.report_path is not None:
            _json_file(self.report_path, self.report)
        return result


class _NoCallHost(BudgetHost):
    """Host used to prove completed evaluation re-entry performs no call."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise LivePhaseOneError("completed evaluation re-entry attempted a host call")


def _route_rows(store: SQLiteStore) -> list[dict[str, Any]]:
    current = store.current()
    row = store.connection.execute(
        "SELECT graph_snapshot_id FROM manifests WHERE manifest_id=?",
        (current["current_manifest_id"],),
    ).fetchone()
    if row is None or row[0] is None:
        return []
    rows: list[dict[str, Any]] = []
    for route_key, edge_keys, source in store.connection.execute(
        "SELECT route_key,edge_keys_json,source_json FROM graph_routes "
        "WHERE snapshot_id=? ORDER BY route_key",
        (str(row[0]),),
    ):
        rows.append(
            {
                "route_key": str(route_key),
                "edge_keys": json.loads(str(edge_keys)),
                "evidence": json.loads(str(source)),
            }
        )
    return rows


def _accept_episode(
    store: SQLiteStore,
    instance_id: str,
    host: BudgetHost,
    gate: str,
    operation_id: str,
    text: str,
) -> dict[str, str]:
    host.set_coordinate(gate, "response")
    operation = ContinuityService(store, instance_id, host).prepare_episode(
        GenerationRequest(
            ({"role": "user", "content": text},),
            parameters={"temperature": 0.0, "max_new_tokens": 192},
        ),
        operation_id=operation_id,
    )
    generated = ContinuityService(store, instance_id, host).generate_operation(
        operation.operation_id
    )
    accepted = ContinuityService(store, instance_id, host).accept_episode(
        operation.operation_id
    )
    if generated.status not in {"RESULT_READY", "ACCEPTED"} or accepted.status != "ACCEPTED":
        raise LivePhaseOneError(f"developmental acceptance failed for {operation_id}")
    return {"episode_id": operation.episode_id, "operation_id": operation.operation_id}


def _interpret(
    store: SQLiteStore,
    instance_id: str,
    host: BudgetHost,
    episode_id: str,
    operation_id: str,
    gate: str,
    source_purposes: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    service = InterpretationService(
        store,
        instance_id,
        host,
        source_purposes=source_purposes,
    )
    prepared = service.prepare(episode_id, operation_id=operation_id)
    host.set_coordinate(gate, "extraction_initial")
    service.execute(prepared)
    repairs = 0
    try:
        residue = service.validate(prepared)
    except InterpretationValidationError:
        repairs = 1
        host.set_coordinate(gate, "extraction_repair")
        service.execute(prepared, repair=True)
        residue = service.validate(prepared)
    publication = service.publish(prepared, residue)
    return {
        "episode_id": episode_id,
        "operation_id": operation_id,
        "repairs": repairs,
        "lineage_revision": publication.lineage_revision,
        "graph_revision": publication.graph_revision,
        "edge_count": len(residue.edge_candidates),
        "route_candidate_count": len(residue.route_candidates),
        "residue_sha256": residue.content_digest,
    }


def _frozen_probe(
    checkpoint: Path,
    host: BudgetHost,
    instance_id: str,
    label: str,
    intent: TurnIntent,
) -> dict[str, Any]:
    with SQLiteStore(checkpoint, read_only=True) as frozen_store:
        prepared = ResponseController(frozen_store, instance_id, host).prepare(intent)
        before_file = file_digest(checkpoint)
        with FrozenEvaluationView(checkpoint) as view:
            before_state = view.state_digest
            host.set_coordinate("p1.2", "frozen_probe")
            result = view.generate(
                host,
                prepared.request.messages,
                seed=None,
                parameters=prepared.request.parameters,
                system=prepared.request.system,
            )
            view.assert_unchanged()
            after_state = view.state_digest
    after_file = file_digest(checkpoint)
    return {
        "label": label,
        "selected_routes": [route.route_key for route in prepared.selected],
        "suppressed_routes": [route.route_key for route in prepared.suppressed],
        "routes_payload_empty": '"routes":[]' in (prepared.request.system or "").replace(
            " ", ""
        ),
        "output_sha256": hashlib.sha256(result.content.encode()).hexdigest(),
        "output_chars": len(result.content),
        "usage": _usage(result.token_usage),
        "checkpoint_unchanged": before_file == after_file and before_state == after_state,
        "output": result.content if label == "cold_start_name" else None,
    }


def run_live_phase_one(
    workspace: str | Path,
    *,
    live_budget: str,
    host: Host | None = None,
    maximum_calls: int = 27,
) -> dict[str, Any]:
    """Execute the approved bounded live P1.1→P1.2→P1.3 schedule.

    A failed required result is persisted in ``live_summary.json`` and raises
    without dispatching a replacement study.  Existing complete artifacts are
    reused only after integrity verification by the underlying comparison and
    checkpoint readers.
    """

    if live_budget != "phase-one-v1":
        raise LivePhaseOneError("live Phase One execution requires phase-one-v1")
    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    report_path = root / "live_summary.json"
    if report_path.exists():
        raise LivePhaseOneError("live workspace already contains a report; use a new run")
    delegate = host or DeepInfraGemmaHost()
    report: dict[str, Any] = {
        "status": "RUNNING",
        "experiment_identity": "phase-one-graph-wrapper-preview",
        "contract_revision": 1,
        "software_revision": _software_revision(),
        "provider": delegate.fingerprint().to_dict().get("provider"),
        "model": delegate.fingerprint().to_dict().get("model_id"),
        "budget": {
            "maximum_calls": maximum_calls,
            "automatic_retries": False,
            "output_caps": {
                "response": 192,
                "extraction": 1536,
                "naming": 64,
            },
        },
        "fixture": {
            "id": "p1.1-natural-bridge-v1",
            "inputs": [
                "Checking the weather before our hike reminded us to pack a rain jacket.",
                "A rain jacket keeps a sudden shower from ending the hike early.",
            ],
        },
        "calls": [],
        "gates": {},
    }
    _json_file(report_path, report)
    host_wrapper = BudgetHost(delegate, report, maximum_calls, report_path)
    store: SQLiteStore | None = None
    checkpoint = root / "p1.2.checkpoint.sqlite3"
    comparison_dir = root / "p1.3-comparison"
    try:
        store_path = root / "lineage.sqlite3"
        store = SQLiteStore(store_path)
        instance_id = store.create_root(
            permissions=StoragePermissions(True, True, True, True, True),
            host_binding=host_wrapper.fingerprint().to_dict(),
            controller_version="mneme-p1-live",
        )
        report["lineage_id"] = instance_id

        episodes: list[dict[str, str]] = []
        for ordinal, text in enumerate(report["fixture"]["inputs"]):
            episodes.append(
                _accept_episode(
                    store,
                    instance_id,
                    host_wrapper,
                    "p1.1",
                    f"phase-one-live-p11-episode-{ordinal}",
                    text,
                )
            )
        interpretations = [
            _interpret(
                store,
                instance_id,
                host_wrapper,
                episode["episode_id"],
                f"phase-one-live-p11-interpretation-{ordinal}",
                "p1.1",
                source_purposes=("external_evidence",),
            )
            for ordinal, episode in enumerate(episodes)
        ]
        routes = _route_rows(store)
        multi_hop = [route for route in routes if len(route["edge_keys"]) >= 2]
        if not multi_hop:
            raise LivePhaseOneError("P1.1 required bridged route was not formed")
        report["gates"]["p1.1"] = {
            "status": "PASS",
            "episodes": episodes,
            "interpretations": interpretations,
            "routes": routes,
            "multi_hop_routes": multi_hop,
            "counters": inspect_store(store_path)["counters"],
        }

        store.close()
        store = SQLiteStore(store_path)
        before_generations = int(
            store.connection.execute("SELECT COUNT(*) FROM generation_records").fetchone()[0]
        )
        for episode in episodes:
            ContinuityService(store, instance_id, host_wrapper).generate_operation(
                episode["operation_id"]
            )
        after_generations = int(
            store.connection.execute("SELECT COUNT(*) FROM generation_records").fetchone()[0]
        )
        if before_generations != after_generations:
            raise LivePhaseOneError("accepted retry changed generation count")
        report["restart_resume"] = {
            "reopened": True,
            "accepted_retry_generation_count_unchanged": True,
        }

        host_wrapper.set_coordinate("p1.2", "naming")
        identity = IdentityService(store, instance_id).adopt_from_host(host_wrapper)
        controller = ResponseController(store, instance_id, host_wrapper)
        relevant_intent = TurnIntent(
            "Explain why the rain jacket matters on a hike.",
            memory="graph",
            parameters={"temperature": 0.0, "max_new_tokens": 192},
            operation_id="phase-one-live-p12-turn-0",
        )
        prepared = controller.prepare(relevant_intent)
        if not prepared.selected:
            raise LivePhaseOneError("P1.2 relevant turn selected no route")
        host_wrapper.set_coordinate("p1.2", "response")
        first_turn = controller.execute(prepared)
        trace = store.connection.execute(
            "SELECT selected_json,applied_json FROM turn_traces WHERE operation_id=?",
            (first_turn.operation.operation_id,),
        ).fetchone()
        if trace is None or trace[0] != trace[1] or trace[0] == "[]":
            raise LivePhaseOneError("P1.2 relevant route was not observably applied")
        first_interpretation = _interpret(
            store,
            instance_id,
            host_wrapper,
            first_turn.operation.episode_id,
            "phase-one-live-p12-interpretation-0",
            "p1.2",
        )
        route_key = prepared.selected[0].route_key
        correction_id = CorrectionService(store, instance_id).suppress(
            route_id=route_key, context_tag="explanation"
        )
        corrected = controller.prepare(
            TurnIntent(
                "Explain why the rain jacket matters on a hike.",
                memory="graph",
                context_tags=("explanation",),
                parameters={"temperature": 0.0, "max_new_tokens": 192},
                operation_id="phase-one-live-p12-turn-1",
            )
        )
        if route_key in {route.route_key for route in corrected.selected} or route_key not in {
            route.route_key for route in corrected.suppressed
        }:
            raise LivePhaseOneError("P1.2 correction did not suppress the targeted route")
        host_wrapper.set_coordinate("p1.2", "response")
        second_turn = controller.execute(corrected)
        second_interpretation = _interpret(
            store,
            instance_id,
            host_wrapper,
            second_turn.operation.episode_id,
            "phase-one-live-p12-interpretation-1",
            "p1.2",
        )
        create_checkpoint(store, checkpoint, checkpoint_id="phase-one-live-p12-checkpoint")
        checkpoint_before = file_digest(checkpoint)
        checkpoint_state_before = inspect_checkpoint(checkpoint)
        with SQLiteStore(checkpoint, read_only=True) as frozen_store:
            frozen_instance = str(frozen_store.current()["active_instance_id"])
        name_probe = _frozen_probe(
            checkpoint,
            host_wrapper,
            frozen_instance,
            "cold_start_name",
            TurnIntent(
                "What is your name? Answer with only the adopted name.",
                mode="observe",
                memory="graph",
                parameters={"temperature": 0.0, "max_new_tokens": 192},
            ),
        )
        if (identity.name or "").casefold() not in str(name_probe["output"]).casefold():
            raise LivePhaseOneError("P1.2 cold-start probe did not recover adopted name")
        unrelated_probe = _frozen_probe(
            checkpoint,
            host_wrapper,
            frozen_instance,
            "unrelated_abstention",
            TurnIntent(
                "What is a garden?",
                mode="observe",
                memory="graph",
                parameters={"temperature": 0.0, "max_new_tokens": 192},
            ),
        )
        if not unrelated_probe["routes_payload_empty"]:
            raise LivePhaseOneError("P1.2 unrelated probe carried route payload")
        if (
            file_digest(checkpoint) != checkpoint_before
            or inspect_checkpoint(checkpoint) != checkpoint_state_before
        ):
            raise LivePhaseOneError("P1.2 frozen probes changed checkpoint state")
        report["identity"] = identity.to_dict()
        report["gates"]["p1.2"] = {
            "status": "PASS",
            "relevant_route": route_key,
            "relevant_trace": {"selected_json": trace[0], "applied_json": trace[1]},
            "correction_directive_id": correction_id,
            "correction_suppressed": True,
            "interpretations": [first_interpretation, second_interpretation],
            "frozen_probes": [name_probe, unrelated_probe],
            "checkpoint_unchanged": True,
        }

        probes = [
            ComparisonProbe(
                ordinal,
                ({"role": "user", "content": text},),
            )
            for ordinal, text in enumerate(
                (
                    "Explain why the rain jacket matters on a hike.",
                    "How does the weather affect preparing for a hike?",
                    "What is an unrelated garden question?",
                    "Return JSON with one answer about hiking preparation.",
                )
            )
        ]
        provenance = {
            "experiment_name": report["experiment_identity"],
            "contract_revision": report["contract_revision"],
            "software_revision": report["software_revision"],
            "gate": "p1.3",
            "host": host_wrapper.fingerprint().to_dict(),
        }
        host_wrapper.set_coordinate("p1.3", "evaluation")
        comparator = FrozenComparator(checkpoint, host_wrapper)
        results = [
            comparator.generate(
                subject_slot="phase-one-live",
                probe=probe,
                repetition=0,
                treatment=treatment,
                seed=None,
                parameters={"temperature": 0.0, "max_new_tokens": 192},
            )
            for probe in probes
            for treatment in FrozenComparator.treatments
        ]
        write_comparison_artifacts(
            comparison_dir,
            results,
            checkpoint=checkpoint,
            host=host_wrapper,
            provenance=provenance,
        )
        before_reentry_calls = host_wrapper.call_count
        reentry = run_matched_comparison(
            checkpoint,
            _NoCallHost(delegate, report, maximum_calls),
            probes,
            subject_slot="phase-one-live",
            repetitions=1,
            artifact_dir=comparison_dir,
            provenance=provenance,
        )
        if len(reentry) != 12 or host_wrapper.call_count != before_reentry_calls:
            raise LivePhaseOneError("P1.3 completed re-entry was not exact-once")
        if (
            file_digest(checkpoint) != checkpoint_before
            or inspect_checkpoint(checkpoint) != checkpoint_state_before
        ):
            raise LivePhaseOneError("P1.3 evaluation changed developmental checkpoint")
        report["gates"]["p1.3"] = {
            "status": "PASS",
            "probe_count": len(probes),
            "treatment_count": len(FrozenComparator.treatments),
            "matched_readouts": len(results),
            "measurements": summarize_comparison(results),
            "checkpoint_unchanged": True,
            "completed_reentry_host_free": True,
            "comparison_artifact": str((comparison_dir / "comparison.json").relative_to(root)),
        }

        store.close()
        store = SQLiteStore(store_path)
        report["restart_resume"].update(
            {
                "final_reopen": True,
                "accepted_episodes": int(
                    store.connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
                ),
                "interpretations": int(
                    store.connection.execute("SELECT COUNT(*) FROM interpretations").fetchone()[0]
                ),
                "lineage_revision": int(store.current()["current_revision"]),
            }
        )
        report["usage"] = summarize_lineage_usage(store)
        report["checkpoint"] = {
            "path": checkpoint.name,
            "sha256": file_digest(checkpoint),
            "state_digest": inspect_checkpoint(checkpoint)["state_digest"],
        }
        report["provider_calls"] = host_wrapper.call_count
        report["status"] = "PASS"
        report["phase_one_live_acceptance"] = True
        _json_file(report_path, report)
        return report
    except Exception as exc:
        report["provider_calls"] = host_wrapper.call_count
        report["status"] = "FAILED"
        report["failure_type"] = type(exc).__name__
        report["failure"] = str(exc)
        report["phase_one_live_acceptance"] = False
        _json_file(report_path, report)
        raise LivePhaseOneError(str(exc)) from exc
    finally:
        if store is not None:
            try:
                store.close()
            except Exception:
                pass


__all__ = ["LivePhaseOneError", "BudgetHost", "run_live_phase_one"]
