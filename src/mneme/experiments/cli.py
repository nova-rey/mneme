"""Experiment command handlers used by :mod:`mneme.cli`.

The contract and preparation commands are the P0.3 surface.  P0.4 execution is
kept behind the runner module: this file only translates the stable CLI
arguments into runner calls and serializes their results.  Keeping that seam
small prevents the command layer from becoming a second workflow engine.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from .artifacts import ArtifactError, ArtifactStore, file_digest
from .comparison import ComparisonProbe, run_matched_comparison, summarize_comparison
from .contracts import ContractError, ExperimentSpec, load_spec
from .datasets import DatasetBoundaryError, load_fixture_pack
from .planning import PreflightError, preflight


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def _read_spec(path: Path) -> ExperimentSpec:
    return load_spec(path)


def _fixture_pack_for_spec(path: Path, spec: ExperimentSpec) -> Any:
    """Load the contract's fixture pack relative to the specification file."""

    reference = spec.to_dict().get("fixture_pack")
    if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
        raise PreflightError("fixture_pack.path is required for CLI preflight")
    fixture_path = Path(reference["path"])
    if not fixture_path.is_absolute():
        fixture_path = path.parent / fixture_path
    try:
        pack = load_fixture_pack(fixture_path.resolve())
    except DatasetBoundaryError as exc:
        raise PreflightError(str(exc)) from exc
    if reference.get("sha256") != pack.manifest_digest:
        raise PreflightError("fixture pack digest does not match the contract")
    return pack


def validate(path: Path) -> dict[str, Any]:
    spec = _read_spec(path)
    return {
        "valid": True,
        "identity": {
            "name": spec.name,
            "contract_revision": spec.contract_revision,
            "label": spec.identity_label(),
        },
        "contract_sha256": spec.content_digest,
        "schema_version": spec.schema_version,
    }


def preflight_spec(path: Path, host_name: str) -> dict[str, Any]:
    spec = _read_spec(path)
    _require_declared_host(spec, host_name)
    # Importing the existing host factory here avoids changing P0.1 host APIs.
    from ..cli import _host

    pack = _fixture_pack_for_spec(path, spec)
    plan = preflight(
        spec.to_dict(),
        _host(host_name),
        fixture_pack=pack,
        base_path=path.parent,
        contract_digest=spec.content_digest,
    )
    return {
        "valid": True,
        "identity": {"name": spec.name, "contract_revision": spec.contract_revision},
        "contract_sha256": spec.content_digest,
        "plan": plan.to_dict(),
    }


def create_run(path: Path, lab: Path, run_id: str, host_name: str) -> dict[str, Any]:
    spec = _read_spec(path)
    _require_declared_host(spec, host_name)
    from ..cli import _host

    pack = _fixture_pack_for_spec(path, spec)
    plan = preflight(
        spec.to_dict(),
        _host(host_name),
        fixture_pack=pack,
        base_path=path.parent,
        contract_digest=spec.content_digest,
    )
    store = ArtifactStore(lab)
    fixture_inputs: dict[str, bytes] = {}
    fixture_reference = spec.to_dict().get("fixture_pack")
    if isinstance(fixture_reference, dict) and isinstance(fixture_reference.get("path"), str):
        fixture_path = Path(fixture_reference["path"])
        if not fixture_path.is_absolute():
            fixture_path = path.parent / fixture_path
        fixture_path = fixture_path.resolve()
        fixture_inputs["fixture-pack/pack.json"] = fixture_path.read_bytes()
        manifest = json.loads(fixture_path.read_text(encoding="utf-8"))
        for entry in manifest.get("datasets", []) if isinstance(manifest, dict) else []:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise ArtifactError("fixture manifest contains an invalid dataset path")
            relative = Path(entry["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ArtifactError("fixture dataset path escapes the manifest directory")
            source = (fixture_path.parent / relative).resolve()
            if not source.is_file() or source.is_symlink():
                raise ArtifactError(f"fixture dataset file does not exist: {source}")
            fixture_inputs[str(Path("fixture-pack") / relative)] = source.read_bytes()
    snapshots: dict[str, bytes] = {}
    checkpoint_bindings = spec.to_dict().get("checkpoints", {})
    if isinstance(checkpoint_bindings, dict):
        for label, binding in checkpoint_bindings.items():
            if not isinstance(label, str) or not isinstance(binding, dict):
                continue
            source_value = binding.get("path")
            if not isinstance(source_value, str):
                raise ArtifactError(f"checkpoint binding has no path: {label}")
            checkpoint_path = Path(source_value)
            if not checkpoint_path.is_absolute():
                checkpoint_path = path.parent / checkpoint_path
            checkpoint_path = checkpoint_path.resolve()
            if not checkpoint_path.is_file():
                raise ArtifactError(f"checkpoint file does not exist: {checkpoint_path}")
            snapshots[f"{label}.sqlite3"] = checkpoint_path.read_bytes()
    bindings = {
        "subjects": spec.to_dict().get("subjects", []),
        "checkpoints": {
            str(label): {
                **binding,
                "snapshot_path": f"{label}.sqlite3",
                "snapshot_sha256": file_digest(
                    (path.parent / binding["path"]).resolve()
                    if isinstance(binding.get("path"), str)
                    and not Path(binding["path"]).is_absolute()
                    else Path(binding["path"])
                ),
            }
            for label, binding in checkpoint_bindings.items()
            if isinstance(label, str)
            and isinstance(binding, dict)
            and isinstance(binding.get("path"), str)
        },
    }
    published = store.publish_run(
        experiment=spec.to_dict(),
        preflight={"host": plan.host, "budget": plan.budget.to_dict()},
        study_plan=plan.to_dict(),
        bindings=bindings,
        run_id=run_id,
        inputs=fixture_inputs,
        snapshots=snapshots,
    )
    return {
        "status": "PREPARED",
        "path": str(published.path),
        "experiment_name": published.experiment_name,
        "contract_revision": published.contract_revision,
        "contract_sha256": published.contract_sha256,
        "run_id": published.run_id,
    }


def inspect_run(run_id: str, lab: Path, verify: bool) -> dict[str, Any]:
    return ArtifactStore(lab).inspect_run(run_id, verify=verify)


def reconcile_prepared_run(run_id: str, lab: Path) -> dict[str, Any]:
    store = ArtifactStore(lab)
    result = store.inspect_run(run_id, verify=True)
    result["resumed"] = True
    result["execution_supported"] = False
    result["message"] = "P0.3 resume reconciles artifacts only; no model execution was started."
    return result


def execute_run(run_id: str, lab: Path, host_name: str | None = None) -> dict[str, Any]:
    """Execute one prepared P0.4 run through the integrated runner.

    The import is intentionally lazy.  P0.3 installations can still validate
    and inspect prepared runs without importing the execution machinery, while
    P0.4 owns the actual lifecycle and host construction.  ``host_name`` is an
    optional explicit override used by controlled tests; production execution
    derives the host from the immutable prepared contract.
    """

    runner = importlib.import_module("mneme.experiments.runner")
    run_execute = cast(Callable[..., object], getattr(runner, "execute_run"))
    result = run_execute(run_id=run_id, lab=lab, host_name=host_name)
    if not isinstance(result, dict):
        raise ArtifactError("integrated runner returned a non-object result")
    return result


def resume_execution(run_id: str, lab: Path, host_name: str | None = None) -> dict[str, Any]:
    """Resume a prepared or interrupted P0.4 run through the integrated runner."""

    runner = importlib.import_module("mneme.experiments.runner")
    run_resume = cast(Callable[..., object], getattr(runner, "resume_run"))
    result = run_resume(run_id=run_id, lab=lab, host_name=host_name)
    if not isinstance(result, dict):
        raise ArtifactError("integrated runner returned a non-object result")
    return result


def baseline_report(
    run_id: str,
    lab: Path,
    output: Path | None = None,
) -> dict[str, Any]:
    """Build the machine-readable P0.4 baseline report for a completed run."""

    reporter = importlib.import_module("mneme.experiments.baseline")
    build_report = cast(Callable[..., object], getattr(reporter, "build_report"))
    result = build_report(run_id=run_id, lab=lab)
    if not isinstance(result, dict):
        raise ArtifactError("baseline reporter returned a non-object result")
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_json(result) + "\n", encoding="utf-8")
        result = dict(result)
        result["output"] = str(output)
    return result


def compare_checkpoint(
    checkpoint: Path,
    host_name: str,
    probes_path: Path,
    repetitions: int,
    subject_slot: int | str,
    artifact_dir: Path | None,
) -> dict[str, Any]:
    from ..cli import _host

    try:
        payload = json.loads(probes_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read comparison probes: {probes_path}") from exc
    raw_probes = payload.get("probes") if isinstance(payload, dict) else payload
    if not isinstance(raw_probes, list):
        raise ArtifactError("comparison probes must be an array or an object with probes")
    probes: list[ComparisonProbe] = []
    for ordinal, item in enumerate(raw_probes):
        if not isinstance(item, dict):
            raise ArtifactError("comparison probe must be an object")
        messages = item.get("messages")
        if not isinstance(messages, list):
            raise ArtifactError("comparison probe messages must be an array")
        probes.append(ComparisonProbe(int(item.get("probe_ordinal", ordinal)), tuple(messages)))
    results = run_matched_comparison(
        checkpoint,
        _host(host_name),
        probes,
        subject_slot=subject_slot,
        repetitions=repetitions,
        artifact_dir=artifact_dir,
        provenance={
            "probes_sha256": file_digest(probes_path),
            "host_name": host_name,
            "subject_slot": subject_slot,
        },
    )
    return {
        "checkpoint": str(checkpoint),
        "subject_slot": subject_slot,
        "results": [result.to_dict() for result in results],
        "measurements": summarize_comparison(results),
        "artifact_dir": str(artifact_dir) if artifact_dir is not None else None,
    }


def list_artifacts(run_id: str, lab: Path) -> dict[str, Any]:
    run = ArtifactStore(lab).locate_run(run_id)
    files = sorted(str(path.relative_to(run)) for path in run.rglob("*") if path.is_file())
    return {"run_id": run_id, "path": str(run), "files": files}


def isolation_check(
    run_id: str, lab: Path, check_id: str, slot: int, probe: int, repetition: int
) -> dict[str, Any]:
    """Run one bounded FakeHost probe against the run's frozen checkpoint copy."""

    from ..hosts import FakeHost
    from .evaluation import run_isolation_check

    store = ArtifactStore(lab)
    run = store.locate_run(run_id)
    experiment = store._read_json(run / "experiment.json")
    if not isinstance(experiment.get("host"), dict) or experiment["host"].get("backend") != "fake":
        raise ArtifactError("P0.3 isolation check supports only a prepared FakeHost contract")
    plan = store._read_json(run / "study-plan.json")
    _, snapshot = _subject_checkpoint(run, slot)
    seed = _evaluation_seed(plan, slot, probe, repetition)
    parameters = _generation_parameters(experiment)
    return run_isolation_check(
        run_id=run_id,
        lab=lab,
        check_id=check_id,
        checkpoint=snapshot,
        host=FakeHost(),
        messages=[{"role": "user", "content": f"P0.3 isolation probe {probe}"}],
        seed=seed,
        subject_slot=slot,
        probe_ordinal=probe,
        repetition=repetition,
        parameters=parameters,
    )


def _require_declared_host(spec: ExperimentSpec, host_name: str) -> None:
    host = spec.to_dict().get("host", {})
    if isinstance(host, dict):
        declared = host.get("backend")
        if isinstance(declared, str) and declared != host_name:
            raise PreflightError(
                f"selected host {host_name!r} does not match declared host backend {declared!r}"
            )


def _subject_checkpoint(run: Path, subject_slot: int) -> tuple[dict[str, Any], Path]:
    bindings = ArtifactStore._read_json(run / "bindings.json")
    subjects = bindings.get("subjects")
    checkpoints = bindings.get("checkpoints")
    if not isinstance(subjects, list) or not isinstance(checkpoints, dict):
        raise ArtifactError("prepared run has no subject checkpoint bindings")
    matches = [
        subject
        for subject in subjects
        if isinstance(subject, dict) and subject.get("slot") == subject_slot
    ]
    if len(matches) != 1:
        raise ArtifactError(f"subject slot is not uniquely bound: {subject_slot}")
    start = matches[0].get("start")
    binding = checkpoints.get(start)
    if not isinstance(binding, dict):
        raise ArtifactError(f"subject start checkpoint is not bound: {start!r}")
    snapshot_name = binding.get("snapshot_path")
    if not isinstance(snapshot_name, str):
        raise ArtifactError(f"subject checkpoint has no private snapshot: {start!r}")
    snapshot = run / "snapshots" / snapshot_name
    if not snapshot.is_file() or snapshot.is_symlink():
        raise ArtifactError(f"subject checkpoint snapshot is missing: {snapshot_name}")
    return matches[0], snapshot


def _evaluation_seed(plan: dict[str, Any], subject_slot: int, probe: int, repetition: int) -> int:
    streams = plan.get("streams")
    if not isinstance(streams, list):
        raise ArtifactError("prepared run has no resolved random streams")
    matches = [
        stream
        for stream in streams
        if isinstance(stream, dict)
        and stream.get("domain") == "evaluation_generation"
        and stream.get("subject_slot") == subject_slot
        and stream.get("probe") == probe
        and stream.get("repetition") == repetition
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("seed"), int):
        raise ArtifactError("requested evaluation coordinate has no unique prepared seed")
    return int(matches[0]["seed"])


def _generation_parameters(experiment: dict[str, Any]) -> dict[str, Any]:
    generation = experiment.get("generation", {})
    if not isinstance(generation, dict):
        return {}
    parameters = generation.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ArtifactError("generation.parameters must be an object")
    return dict(parameters)


def dispatch(args: Any) -> int:
    try:
        if args.experiment_action == "validate":
            result = validate(args.spec)
        elif args.experiment_action == "preflight":
            result = preflight_spec(args.spec, args.host)
        elif args.experiment_action == "run_create":
            result = create_run(args.spec, args.lab, args.run_id, args.host)
        elif args.experiment_action == "run_inspect":
            result = inspect_run(args.run_id, args.lab, args.verify)
        elif args.experiment_action == "run_execute":
            result = execute_run(args.run_id, args.lab, args.host)
        elif args.experiment_action == "run_resume":
            result = resume_execution(args.run_id, args.lab, args.host)
        elif args.experiment_action == "baseline_report":
            result = baseline_report(args.run_id, args.lab, args.output)
        elif args.experiment_action == "compare":
            result = compare_checkpoint(
                args.checkpoint,
                args.host,
                args.probes,
                args.repetitions,
                args.subject_slot,
                args.artifact_dir,
            )
        elif args.experiment_action == "artifacts":
            result = list_artifacts(args.run_id, args.lab)
        elif args.experiment_action == "check_isolation":
            result = isolation_check(
                args.run_id,
                args.lab,
                args.check_id,
                args.subject_slot,
                args.probe_ordinal,
                args.repetition,
            )
        else:
            raise ArtifactError(f"unknown experiment action: {args.experiment_action}")
    except (ArtifactError, ContractError, PreflightError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    print(_json(result))
    return 0


def add_parser(sub: Any) -> None:
    experiment = sub.add_parser("experiment")
    esub = experiment.add_subparsers(dest="experiment_action", required=True)
    validate_parser = esub.add_parser("validate")
    validate_parser.add_argument("spec", type=Path)
    validate_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    preflight_parser = esub.add_parser("preflight")
    preflight_parser.add_argument("spec", type=Path)
    preflight_parser.add_argument("--host", default="fake")
    preflight_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    run = esub.add_parser("run")
    rsub = run.add_subparsers(dest="run_action", required=True)
    create = rsub.add_parser("create")
    create.add_argument("spec", type=Path)
    create.add_argument("--lab", type=Path, required=True)
    create.add_argument("--run-id", required=True)
    create.add_argument("--host", default="fake")
    create.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    inspect = rsub.add_parser("inspect")
    inspect.add_argument("run_id")
    inspect.add_argument("--lab", type=Path, required=True)
    inspect.add_argument("--verify", action="store_true")
    inspect.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    resume = rsub.add_parser("resume")
    resume.add_argument("run_id")
    resume.add_argument("--lab", type=Path, required=True)
    resume.add_argument(
        "--host",
        help="optional controlled-test host override; normally read from the prepared contract",
    )
    resume.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    execute = rsub.add_parser("execute")
    execute.add_argument("run_id")
    execute.add_argument("--lab", type=Path, required=True)
    execute.add_argument(
        "--host",
        help="optional controlled-test host override; normally read from the prepared contract",
    )
    execute.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    check = esub.add_parser("check-isolation")
    check.add_argument("run_id")
    check.add_argument("--lab", type=Path, required=True)
    check.add_argument("--subject-slot", type=int, required=True)
    check.add_argument("--probe-ordinal", type=int, required=True)
    check.add_argument("--repetition", type=int, required=True)
    check.add_argument("--check-id", required=True)
    check.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    artifacts = esub.add_parser("artifacts")
    artifacts.add_argument("run_id")
    artifacts.add_argument("--lab", type=Path, required=True)
    artifacts.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    baseline = esub.add_parser("baseline")
    bsub = baseline.add_subparsers(dest="baseline_action", required=True)
    report = bsub.add_parser("report")
    report.add_argument("run_id")
    report.add_argument("--lab", type=Path, required=True)
    report.add_argument("--output", type=Path)
    report.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    compare = esub.add_parser("compare")
    compare.add_argument("checkpoint", type=Path)
    compare.add_argument("--probes", type=Path, required=True)
    compare.add_argument("--host", default="fake")
    compare.add_argument("--repetitions", type=int, default=1)
    compare.add_argument("--subject-slot", default="0")
    compare.add_argument("--artifact-dir", type=Path)
    compare.add_argument("--json", action="store_true", help="emit machine-readable JSON")


def normalize_args(args: Any) -> Any:
    action = getattr(args, "experiment_action", None)
    if action == "run":
        args.experiment_action = f"run_{args.run_action}"
    elif action == "baseline":
        args.experiment_action = f"baseline_{args.baseline_action}"
    elif isinstance(action, str):
        args.experiment_action = action.replace("-", "_")
    return args
