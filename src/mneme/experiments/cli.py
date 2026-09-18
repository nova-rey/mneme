"""Small P0.3 command handlers used by :mod:`mneme.cli`.

These handlers validate and prepare contracts, but deliberately do not execute a
development schedule.  Keeping them out of the top-level parser also lets the
legacy P0.1/P0.2 state commands remain unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import ArtifactError, ArtifactStore
from .contracts import ContractError, ExperimentSpec, load_spec
from .planning import PreflightError, preflight


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def _read_spec(path: Path) -> ExperimentSpec:
    return load_spec(path)


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
    # Importing the existing host factory here avoids changing P0.1 host APIs.
    from ..cli import _host

    plan = preflight(spec.to_dict(), _host(host_name), contract_digest=spec.content_digest)
    return {
        "valid": True,
        "identity": {"name": spec.name, "contract_revision": spec.contract_revision},
        "contract_sha256": spec.content_digest,
        "plan": plan.to_dict(),
    }


def create_run(path: Path, lab: Path, run_id: str, host_name: str) -> dict[str, Any]:
    spec = _read_spec(path)
    from ..cli import _host

    plan = preflight(spec.to_dict(), _host(host_name), contract_digest=spec.content_digest)
    store = ArtifactStore(lab)
    snapshots: dict[str, bytes] = {}
    checkpoint_bindings = spec.to_dict().get("checkpoints", {})
    if isinstance(checkpoint_bindings, dict):
        for label, binding in checkpoint_bindings.items():
            if not isinstance(label, str) or not isinstance(binding, dict):
                continue
            source = binding.get("path")
            if isinstance(source, str):
                checkpoint_path = (path.parent / source).resolve()
                if checkpoint_path.is_file():
                    snapshots[f"{label}.sqlite3"] = checkpoint_path.read_bytes()
    bindings = {
        "subjects": spec.to_dict().get("subjects", []),
        "checkpoints": checkpoint_bindings,
    }
    published = store.publish_run(
        experiment=spec.to_dict(),
        preflight={"host": plan.host, "budget": plan.budget.to_dict()},
        study_plan=plan.to_dict(),
        bindings=bindings,
        run_id=run_id,
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


def resume_run(run_id: str, lab: Path) -> dict[str, Any]:
    store = ArtifactStore(lab)
    result = store.inspect_run(run_id, verify=True)
    result["resumed"] = True
    result["execution_supported"] = False
    result["message"] = "P0.3 resume reconciles artifacts only; no model execution was started."
    return result


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
    snapshots = sorted((run / "snapshots").glob("*.sqlite3"))
    if not snapshots:
        raise ArtifactError("prepared run has no checkpoint snapshot")
    return run_isolation_check(
        run_id=run_id,
        lab=lab,
        check_id=check_id,
        checkpoint=snapshots[0],
        host=FakeHost(),
        messages=[{"role": "user", "content": f"P0.3 isolation probe {probe}"}],
        seed=repetition,
        subject_slot=slot,
        probe_ordinal=probe,
        repetition=repetition,
    )


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
        elif args.experiment_action == "run_resume":
            result = resume_run(args.run_id, args.lab)
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
    resume.add_argument("--json", action="store_true", help="emit machine-readable JSON")
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


def normalize_args(args: Any) -> Any:
    if getattr(args, "experiment_action", None) == "run":
        args.experiment_action = f"run_{args.run_action}"
    return args
