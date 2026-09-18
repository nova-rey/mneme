"""Resolve P0.3 study plans without making model calls.

This module deliberately works on the serializable mapping produced by the
experiment-contract layer.  Keeping planning independent of storage and host
execution makes it possible to inspect a complete plan before any call is
made, and keeps administrative identifiers out of scientific randomness.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from ..contracts import Capability, HostCapabilities, HostFingerprint
from .datasets import FixturePack, load_fixture_pack


class PreflightError(ValueError):
    """The experiment cannot be safely prepared for the selected host."""


class SeedDomain(StrEnum):
    DEVELOPMENT_GENERATION = "development_generation"
    EVALUATION_GENERATION = "evaluation_generation"
    CONDITION_ASSIGNMENT = "condition_assignment"
    DATASET_ORDERING = "dataset_ordering"


class PlanningHost(Protocol):
    def capabilities(self) -> HostCapabilities: ...

    def fingerprint(self) -> HostFingerprint: ...


@dataclass(frozen=True)
class BudgetEstimate:
    development_calls: int
    evaluation_calls: int
    isolation_calls: int
    total_calls: int
    input_tokens: int | None
    output_tokens: int
    max_seconds: float | None
    estimated_cost: float | None
    cost_currency: str | None
    unknowns: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "development_calls": self.development_calls,
            "evaluation_calls": self.evaluation_calls,
            "isolation_calls": self.isolation_calls,
            "total_calls": self.total_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "max_seconds": self.max_seconds,
            "estimated_cost": self.estimated_cost,
            "cost_currency": self.cost_currency,
            "unknowns": list(self.unknowns),
        }


@dataclass(frozen=True)
class ResolvedPlan:
    """JSON-safe output of preflight, suitable for an immutable run manifest."""

    experiment_name: str
    contract_revision: int
    contract_digest: str | None
    assignments: tuple[dict[str, Any], ...]
    streams: tuple[dict[str, Any], ...]
    host: dict[str, Any]
    budget: BudgetEstimate
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment": {
                "name": self.experiment_name,
                "contract_revision": self.contract_revision,
                "content_digest": self.contract_digest,
            },
            "assignments": [dict(item) for item in self.assignments],
            "streams": [dict(item) for item in self.streams],
            "host": dict(self.host),
            "budgets": self.budget.to_dict(),
            "warnings": list(self.warnings),
        }


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def derive_seed(master_seed: int, domain: SeedDomain | str, **coordinates: int | str) -> int:
    """Derive a stable 63-bit seed from explicit scientific coordinates.

    HMAC gives domain separation and makes the operation independent of Python's
    process-randomized hash implementation.  Callers must provide scientific
    coordinates; administrative IDs are rejected by convention and are not part
    of this API.
    """
    if not isinstance(master_seed, int) or master_seed < 0:
        raise PreflightError("master_seed must be a non-negative integer")
    if not coordinates:
        raise PreflightError("seed derivation requires explicit scientific coordinates")
    try:
        seed_domain = SeedDomain(str(domain))
    except ValueError as exc:
        raise PreflightError(f"unsupported seed domain: {domain}") from exc
    allowed = {
        SeedDomain.DEVELOPMENT_GENERATION: {"sampling_slot", "episode", "repetition"},
        SeedDomain.EVALUATION_GENERATION: {"probe", "checkpoint_boundary", "repetition"},
        SeedDomain.CONDITION_ASSIGNMENT: {"assignment_slot"},
        SeedDomain.DATASET_ORDERING: {"ordering_group", "entry"},
    }[seed_domain]
    if set(coordinates) != allowed:
        forbidden = {"id", "uuid", "run_id", "experiment_id", "path", "timestamp", "name"}
        if forbidden.intersection(coordinates):
            raise PreflightError("administrative identifiers cannot be seed coordinates")
        raise PreflightError(
            f"{seed_domain.value} seed coordinates must be exactly {sorted(allowed)}"
        )
    for key, value in coordinates.items():
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise PreflightError(f"seed coordinate {key} must be an integer or string")
        if isinstance(value, int) and value < 0:
            raise PreflightError(f"seed coordinate {key} must be non-negative")
        if isinstance(value, str) and not value:
            raise PreflightError(f"seed coordinate {key} must not be empty")
    message = _canonical({"version": "mneme-seeds-v1", "domain": str(domain),
                          "coordinates": coordinates})
    digest = hmac.new(str(master_seed).encode("ascii"), message, hashlib.sha256).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def _lookup(mapping: Mapping[str, Any], key: str, default: Any = None) -> Any:
    return mapping[key] if key in mapping else default


def _host_dict(host: PlanningHost) -> tuple[HostCapabilities, HostFingerprint, dict[str, Any]]:
    capabilities = host.capabilities()
    fingerprint = host.fingerprint()
    return capabilities, fingerprint, fingerprint.to_dict()


def _capability(value: Any) -> Capability:
    try:
        return value if isinstance(value, Capability) else Capability(str(value))
    except ValueError as exc:
        raise PreflightError(f"unknown host capability: {value}") from exc


def _record_mapping(record: Any) -> Mapping[str, Any]:
    if isinstance(record, Mapping):
        return record
    if isinstance(record, object) and hasattr(record, "record_id"):
        return {
            "record_id": getattr(record, "record_id"),
            "id": getattr(record, "record_id"),
            "ordinal": getattr(record, "ordinal"),
            "scenario_family": getattr(record, "scenario_family"),
            "messages": [dict(message) for message in getattr(record, "messages")],
            "partition": getattr(record, "partition"),
            "role": getattr(record, "role"),
            "input_tokens": getattr(record, "input_tokens", None),
            "max_output_tokens": getattr(record, "max_output_tokens", None),
        }
    raise PreflightError("dataset records must be mappings or fixture records")


def _datasets(spec: Mapping[str, Any], fixture_pack: Any | None) -> Mapping[str, Any]:
    if isinstance(fixture_pack, FixturePack):
        datasets = fixture_pack.datasets
    elif fixture_pack is not None:
        datasets = fixture_pack.get("datasets", fixture_pack)
    else:
        datasets = spec.get("datasets", {})
    if not isinstance(datasets, Mapping):
        raise PreflightError("datasets must be a mapping of dataset name to records")
    return datasets


def _records(datasets: Mapping[str, Any], name: str, role: str) -> list[Any]:
    if name not in datasets:
        raise PreflightError(f"{role} dataset is not present: {name}")
    records = datasets[name]
    if not isinstance(records, (list, tuple)):
        raise PreflightError(f"dataset {name} must be a list of records")
    result = [_record_mapping(record) for record in records]
    for record in result:
        declared_role = record.get("role")
        if declared_role is not None and declared_role != role:
            raise PreflightError(
                f"dataset {name} record role {declared_role!r} does not match {role!r}"
            )
    return result


def _dataset_names(spec: Mapping[str, Any], subject: Mapping[str, Any]) -> tuple[str, str]:
    conditions = spec.get("conditions", {})
    condition_name = str(subject.get("condition", ""))
    condition = conditions.get(condition_name)
    if not isinstance(condition, Mapping):
        raise PreflightError(f"subject refers to unknown condition: {condition_name}")
    development = condition.get("development_dataset")
    evaluation = spec.get("evaluation", {}).get("dataset")
    if not isinstance(development, str) or not isinstance(evaluation, str):
        raise PreflightError("condition development_dataset and evaluation.dataset are required")
    return development, evaluation


def _resolve_order(
    records: list[Mapping[str, Any]],
    *,
    condition: Mapping[str, Any],
    master_seed: int,
    ordering_group: int,
    domain: SeedDomain,
) -> list[Mapping[str, Any]]:
    """Return the declared order and persistable record order.

    ``listed`` is the default and follows explicit record ordinals.  A contract
    may request ``shuffle``; its permutation is derived only from the numeric
    scientific ordering group and entry coordinates, never record IDs or paths.
    """

    ordering = condition.get("ordering", "listed")
    if ordering not in {"listed", "shuffle"}:
        raise PreflightError(f"unsupported dataset ordering: {ordering}")
    listed = sorted(
        records,
        key=lambda record: (
            record.get("ordinal", 0),
            str(record.get("record_id", record.get("id", ""))),
        ),
    )
    if ordering == "listed":
        return listed
    return sorted(
        listed,
        key=lambda record: derive_seed(
            master_seed,
            domain,
            ordering_group=ordering_group,
            entry=listed.index(record),
        ),
    )


def _validate_checkpoint_bindings(
    spec: Mapping[str, Any], *, base_path: str | Path | None = None
) -> None:
    checkpoints = spec.get("checkpoints", {})
    if checkpoints is None:
        return
    if not isinstance(checkpoints, Mapping):
        raise PreflightError("checkpoints must be a mapping")
    for subject in spec.get("subjects", []):
        start = subject.get("start") if isinstance(subject, Mapping) else None
        if checkpoints and start not in checkpoints:
            raise PreflightError(f"subject start checkpoint is not declared: {start}")
    for name, binding in checkpoints.items():
        if not isinstance(binding, Mapping):
            raise PreflightError(f"checkpoint binding must be an object: {name}")
        path_value, checkpoint_id = binding.get("path"), binding.get("checkpoint_id")
        if not isinstance(path_value, str) or not isinstance(checkpoint_id, str):
            raise PreflightError(f"checkpoint {name} requires path and checkpoint_id")
        required_binding_fields = ("instance_id", "revision", "manifest_id", "sha256")
        missing_binding_fields = [
            field for field in required_binding_fields if field not in binding
        ]
        if missing_binding_fields:
            raise PreflightError(
                f"checkpoint {name} requires exact binding fields: "
                f"{', '.join(missing_binding_fields)}"
            )
        path = Path(path_value)
        if not path.is_absolute() and base_path is not None:
            path = Path(base_path) / path
        path = path.resolve()
        if not path.is_file():
            raise PreflightError(f"checkpoint file does not exist: {path}")
        expected_digest = binding.get("sha256")
        if expected_digest is not None:
            actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_digest != expected_digest:
                raise PreflightError(f"checkpoint digest does not match: {name}")
        try:
            from ..state.reader import CheckpointReader

            with CheckpointReader(path, checkpoint_id=checkpoint_id) as reader:
                manifest = reader.manifest()
                expected_instance = binding.get("instance_id")
                expected_revision = binding.get("revision")
                expected_manifest = binding.get("manifest_id")
                required = {
                    "instance_id": expected_instance,
                    "revision": expected_revision,
                    "manifest_id": expected_manifest,
                }
                missing = [key for key, value in required.items() if value is None]
                if missing:
                    raise PreflightError(
                        f"checkpoint {name} requires exact binding fields: {', '.join(missing)}"
                    )
                if manifest.get("checkpoint_id") != checkpoint_id:
                    raise PreflightError(f"checkpoint ID does not match: {name}")
                if manifest.get("source_instance_id") != expected_instance:
                    raise PreflightError(f"checkpoint lineage does not match: {name}")
                if manifest.get("source_revision") != expected_revision:
                    raise PreflightError(f"checkpoint revision does not match: {name}")
                if manifest.get("manifest_id") != expected_manifest:
                    raise PreflightError(f"checkpoint manifest does not match: {name}")
                export = reader.store.connection.execute(
                    "SELECT export_allowed FROM policies WHERE policy_id=?",
                    (manifest["policy_id"],),
                ).fetchone()
                if not export or not bool(export[0]):
                    raise PreflightError(f"checkpoint export permission denied: {name}")
        except PreflightError:
            raise
        except Exception as exc:
            raise PreflightError(f"invalid checkpoint binding {name}: {exc}") from exc


def _token_bound(records: list[Any], field: str) -> int | None:
    total = 0
    for record in records:
        if not isinstance(record, Mapping):
            return None
        value = record.get(field)
        if not isinstance(value, int) or value < 0:
            return None
        total += value
    return total


def _check_budget(spec: Mapping[str, Any], estimate: BudgetEstimate) -> None:
    limits = spec.get("budgets")
    if not isinstance(limits, Mapping):
        raise PreflightError("budgets are required")
    integer_limits = (
        "max_model_calls",
        "max_input_tokens",
        "max_output_tokens",
        "max_isolation_check_calls",
    )
    for key in integer_limits:
        if key not in limits:
            continue
        value = limits[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise PreflightError(f"budgets.{key} must be a positive integer")
    max_calls = limits.get("max_model_calls")
    if max_calls is not None and estimate.total_calls > max_calls:
        raise PreflightError(
            f"planned calls {estimate.total_calls} exceed max_model_calls {max_calls}"
        )
    max_input = limits.get("max_input_tokens")
    if estimate.input_tokens is None and max_input is not None:
        raise PreflightError("cannot prove max_input_tokens without token bounds")
    if (
        max_input is not None
        and estimate.input_tokens is not None
        and estimate.input_tokens > max_input
    ):
        raise PreflightError("planned input tokens exceed max_input_tokens")
    max_output = limits.get("max_output_tokens")
    if max_output is not None and estimate.output_tokens > max_output:
        raise PreflightError("planned output tokens exceed max_output_tokens")


def preflight(
    spec: Mapping[str, Any] | Any,
    host: PlanningHost,
    *,
    fixture_pack: Any | None = None,
    contract_digest: str | None = None,
    base_path: str | Path | None = None,
) -> ResolvedPlan:
    """Validate and resolve a spec without invoking ``host.generate``.

    ``ExperimentSpec`` instances are accepted directly; their immutable mapping
    is copied once at this boundary so the planner remains independent of the
    contract module's concrete class.
    """
    if not isinstance(spec, Mapping):
        to_dict = getattr(spec, "to_dict", None)
        if not callable(to_dict):
            raise PreflightError("spec must be a mapping or expose to_dict()")
        spec = to_dict()
    if not isinstance(spec, Mapping):
        raise PreflightError("spec.to_dict() must return a mapping")
    name = spec.get("name")
    revision = spec.get("contract_revision")
    if not isinstance(name, str) or not name:
        raise PreflightError("experiment name is required")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise PreflightError("contract_revision must be a positive integer")
    randomization = spec.get("randomization", {})
    master_seed = randomization.get("master_seed") if isinstance(randomization, Mapping) else None
    if isinstance(master_seed, bool) or not isinstance(master_seed, int) or master_seed < 0:
        raise PreflightError("randomization.master_seed is required")
    subjects = spec.get("subjects")
    if not isinstance(subjects, list) or not subjects:
        raise PreflightError("at least one subject is required")
    _validate_checkpoint_bindings(spec, base_path=base_path)
    if fixture_pack is None:
        fixture_reference = spec.get("fixture_pack")
        if isinstance(fixture_reference, Mapping) and isinstance(
            fixture_reference.get("path"), str
        ):
            fixture_path = Path(str(fixture_reference["path"]))
            if not fixture_path.is_absolute() and base_path is not None:
                fixture_path = Path(base_path) / fixture_path
            fixture_path = fixture_path.resolve()
            try:
                loaded = load_fixture_pack(fixture_path)
            except Exception as exc:
                raise PreflightError(f"invalid fixture pack: {fixture_path}: {exc}") from exc
            expected_pack_digest = fixture_reference.get("sha256")
            if expected_pack_digest != loaded.manifest_digest:
                raise PreflightError("fixture pack digest does not match the contract")
            fixture_pack = loaded
    datasets = _datasets(spec, fixture_pack)
    capabilities, fingerprint, fingerprint_dict = _host_dict(host)
    host_spec = spec.get("host", {})
    if not isinstance(host_spec, Mapping):
        raise PreflightError("host must be a mapping")
    required = [_capability(value) for value in host_spec.get("requires", ["text_generation"])]
    missing = [item.value for item in required if not capabilities.has(item)]
    if missing:
        raise PreflightError(f"host is missing required capabilities: {', '.join(missing)}")
    revision_requirement = host_spec.get("revision_requirement", "any")
    if revision_requirement == "known" and not fingerprint.model_revision:
        raise PreflightError("hosted model revision is unknown but a known revision is required")
    expected_digest = host_spec.get("fingerprint_sha256")
    actual_digest = hashlib.sha256(_canonical(fingerprint_dict)).hexdigest()
    if expected_digest is not None and expected_digest != actual_digest:
        raise PreflightError("execution host fingerprint does not match the contract")
    generation = spec.get("generation", {})
    if not isinstance(generation, Mapping):
        raise PreflightError("generation must be a mapping")
    sampling_mode = host_spec.get(
        "sampling", generation.get("sampling", randomization.get("sampling"))
    )
    controlled_sampling = sampling_mode == "controlled" or Capability.SEED_CONTROL in required
    if controlled_sampling and not capabilities.has(Capability.SEED_CONTROL):
        raise PreflightError("controlled sampling requires host capability: seed_control")
    assignments: list[dict[str, Any]] = []
    streams: list[dict[str, Any]] = []
    development_calls = evaluation_calls = 0
    input_tokens: int | None = 0
    output_per_call = 0
    evaluation = spec.get("evaluation", {})
    if not isinstance(evaluation, Mapping):
        raise PreflightError("evaluation must be a mapping")
    repetitions = evaluation.get("repetitions", 1)
    if not isinstance(repetitions, int) or repetitions < 1:
        raise PreflightError("evaluation.repetitions must be positive")
    cohort_groups: dict[str, int] = {}
    evaluation_groups: dict[str, int] = {}
    for ordinal, subject in enumerate(subjects):
        if not isinstance(subject, Mapping):
            raise PreflightError("subject entries must be mappings")
        development_name, evaluation_name = _dataset_names(spec, subject)
        cohort_name = str(subject.get("cohort", ""))
        cohort_group = cohort_groups.setdefault(cohort_name, len(cohort_groups))
        evaluation_group = evaluation_groups.setdefault(evaluation_name, len(evaluation_groups))
        development = _records(datasets, development_name, "development")
        evaluation_records = _records(datasets, evaluation_name, "evaluation")
        development_calls += len(development)
        evaluation_calls += len(evaluation_records) * repetitions
        for record in development:
            bound = _token_bound([record], "input_tokens")
            input_tokens = None if bound is None or input_tokens is None else input_tokens + bound
            output = record.get("max_output_tokens")
            if isinstance(output, int) and output >= 0:
                output_per_call += output
            else:
                configured = (
                    spec.get("generation", {}).get("parameters", {}).get("max_new_tokens", 0)
                )
                output_per_call += configured if isinstance(configured, int) else 0
        for record in evaluation_records:
            bound = _token_bound([record], "input_tokens")
            if bound is None:
                input_tokens = None
            elif input_tokens is not None:
                input_tokens += bound * repetitions
            output = record.get("max_output_tokens")
            if isinstance(output, int) and output >= 0:
                output_per_call += output * repetitions
            else:
                configured = (
                    spec.get("generation", {}).get("parameters", {}).get("max_new_tokens", 0)
                )
                output_per_call += (configured if isinstance(configured, int) else 0) * repetitions
        development_order = _resolve_order(
            development,
            condition=spec["conditions"][subject["condition"]],
            master_seed=master_seed,
            ordering_group=cohort_group,
            domain=SeedDomain.DATASET_ORDERING,
        )
        evaluation_order = _resolve_order(
            evaluation_records,
            condition=evaluation,
            master_seed=master_seed,
            ordering_group=evaluation_group,
            domain=SeedDomain.DATASET_ORDERING,
        )
        assignments.append({
            "subject_slot": subject.get("slot", ordinal),
            "cohort": subject.get("cohort"),
            "condition": subject.get("condition"),
            "development_dataset": development_name,
            "evaluation_dataset": evaluation_name,
            "condition_assignment": subject.get("condition"),
            "assignment_slot": ordinal,
            "assignment_seed": derive_seed(
                master_seed,
                SeedDomain.CONDITION_ASSIGNMENT,
                assignment_slot=ordinal,
            ),
            "development_ordering_group": cohort_group,
            "evaluation_ordering_group": evaluation_group,
            "development_order": [
                record.get("record_id", record.get("id")) for record in development_order
            ],
            "evaluation_order": [
                record.get("record_id", record.get("id")) for record in evaluation_order
            ],
        })
        streams.append(
            {
                "domain": SeedDomain.CONDITION_ASSIGNMENT.value,
                "assignment_slot": ordinal,
                "seed": derive_seed(
                    master_seed,
                    SeedDomain.CONDITION_ASSIGNMENT,
                    assignment_slot=ordinal,
                ),
            }
        )
        dev_slot = subject.get("development_sampling_slot", ordinal)
        if not isinstance(dev_slot, int) or dev_slot < 0:
            raise PreflightError("development_sampling_slot must be a non-negative integer")
        for episode in range(len(development)):
            streams.append(
                {
                    "domain": SeedDomain.DEVELOPMENT_GENERATION.value,
                    "subject_slot": subject.get("slot", ordinal),
                    "episode": episode,
                    "seed": derive_seed(
                        master_seed,
                        SeedDomain.DEVELOPMENT_GENERATION,
                        sampling_slot=dev_slot,
                        episode=episode,
                        repetition=0,
                    ),
                }
            )
        for entry in range(len(development_order)):
            streams.append(
                {
                    "domain": SeedDomain.DATASET_ORDERING.value,
                    "dataset": "development",
                    "subject_slot": subject.get("slot", ordinal),
                    "entry": entry,
                    "seed": derive_seed(
                        master_seed,
                        SeedDomain.DATASET_ORDERING,
                        ordering_group=ordinal,
                        entry=entry,
                    ),
                }
            )
        for probe in range(len(evaluation_records)):
            for repetition in range(repetitions):
                streams.append({"domain": SeedDomain.EVALUATION_GENERATION.value,
                                "subject_slot": subject.get("slot", ordinal), "probe": probe,
                                "repetition": repetition,
                                "seed": derive_seed(master_seed, SeedDomain.EVALUATION_GENERATION,
                                                    probe=probe, checkpoint_boundary=0,
                                                    repetition=repetition)})
    raw_isolation_calls = spec.get("budgets", {}).get("max_isolation_check_calls", 0)
    if isinstance(raw_isolation_calls, bool) or not isinstance(raw_isolation_calls, int):
        raise PreflightError("budgets.max_isolation_check_calls must be a positive integer")
    isolation_calls = raw_isolation_calls
    estimate = BudgetEstimate(
        development_calls, evaluation_calls, isolation_calls,
        development_calls + evaluation_calls + isolation_calls,
        input_tokens,
        output_per_call,
        spec.get("budgets", {}).get("max_seconds"),
        None,
        None,
        ("cost unavailable",) if spec.get("budgets", {}).get("max_cost") is not None else (),
    )
    _check_budget(spec, estimate)
    return ResolvedPlan(name, revision, contract_digest, tuple(assignments), tuple(streams),
                        {
                            "fingerprint": fingerprint_dict,
                            "fingerprint_sha256": actual_digest,
                            "capabilities": capabilities.to_dict(),
                            "sampling": "controlled" if controlled_sampling else "provider_managed",
                        }, estimate)
