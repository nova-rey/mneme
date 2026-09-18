"""Immutable, versioned P0.3 experiment contracts.

The declared experiment name and contract revision are the scientific identity.
The content digest is only the identity of the exact serialized contents of that
revision.  Administrative run IDs and paths are deliberately not part of the
contract or its canonical content.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

EXPERIMENT_SCHEMA_VERSION = 1


class ContractError(ValueError):
    """The supplied experiment contract is not a valid P0.3 contract."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _validate_finite(value: Any, path: str = "contract") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError(f"{path} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _validate_finite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_finite(child, f"{path}[{index}]")


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


def canonical_json(value: Any) -> str:
    """Serialize JSON data deterministically and reject NaN/Infinity."""

    _validate_finite(value)
    return json.dumps(
        _thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


@dataclass(frozen=True)
class ExperimentIdentity:
    """Human/scientific identity of one contract revision."""

    name: str
    contract_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ContractError("experiment name must be a non-empty string")
        if "/" in self.name or "\\" in self.name or self.name in {".", ".."}:
            raise ContractError("experiment name cannot contain path separators")
        if (
            isinstance(self.contract_revision, bool)
            or not isinstance(self.contract_revision, int)
            or self.contract_revision < 1
        ):
            raise ContractError("contract_revision must be a positive integer")

    def label(self) -> str:
        return f"{self.name} / revision {self.contract_revision}"


_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "name",
        "contract_revision",
        "purpose",
        "stage",
        "contract",
        "fixture_pack",
        "checkpoints",
        "subjects",
        "conditions",
        "datasets",
        "evaluation",
        "host",
        "generation",
        "randomization",
        "budgets",
        "artifact_location",
        "storage_allowed",
        "versions",
    }
)
_REQUIRED_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "name",
        "contract_revision",
        "purpose",
        "contract",
        "fixture_pack",
        "checkpoints",
        "subjects",
        "conditions",
        "evaluation",
        "host",
        "randomization",
        "budgets",
        "storage_allowed",
    }
)


@dataclass(frozen=True)
class ExperimentSpec:
    """An immutable validated experiment contract.

    The private mapping is recursively immutable.  ``to_dict`` returns a fresh
    mutable copy so callers cannot mutate the contract held by this object.
    """

    _data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ExperimentSpec:
        if not isinstance(value, Mapping):
            raise ContractError("experiment specification must be a JSON object")
        data = copy.deepcopy(dict(value))
        unknown = sorted(set(data) - _TOP_LEVEL_FIELDS)
        missing = sorted(_REQUIRED_TOP_LEVEL_FIELDS - set(data))
        if unknown:
            raise ContractError(f"unknown top-level field(s): {', '.join(unknown)}")
        if missing:
            raise ContractError(f"missing required field(s): {', '.join(missing)}")
        if data.get("schema_version") != EXPERIMENT_SCHEMA_VERSION:
            raise ContractError(
                f"unsupported experiment schema version: {data.get('schema_version')!r}"
            )
        if not isinstance(data.get("name"), str) or not isinstance(
            data.get("contract_revision"), int
        ):
            raise ContractError("name and contract_revision have invalid types")
        ExperimentIdentity(data["name"], data["contract_revision"])
        if not isinstance(data["purpose"], str) or not data["purpose"].strip():
            raise ContractError("purpose must be a non-empty string")
        for key in (
            "contract",
            "fixture_pack",
            "checkpoints",
            "host",
            "randomization",
            "budgets",
        ):
            if not isinstance(data[key], Mapping):
                raise ContractError(f"{key} must be an object")
        if not isinstance(data["subjects"], list) or not data["subjects"]:
            raise ContractError("subjects must be a non-empty array")
        if not isinstance(data["conditions"], Mapping) or not data["conditions"]:
            raise ContractError("conditions must be a non-empty object")
        if not isinstance(data["evaluation"], Mapping):
            raise ContractError("evaluation must be an object")
        if not isinstance(data["storage_allowed"], bool):
            raise ContractError("storage_allowed must be boolean")
        _validate_fixture_pack_reference(data["fixture_pack"])
        _validate_semantic_references(data)
        _validate_inline_datasets(data)
        _validate_finite(data)
        return cls(_freeze(data))

    @classmethod
    def from_json(cls, text: str) -> ExperimentSpec:
        try:
            value = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
        except (json.JSONDecodeError, ContractError) as exc:
            raise ContractError(f"invalid experiment JSON: {exc}") from exc
        return cls.from_dict(value)

    @classmethod
    def from_path(cls, path: str | Path) -> ExperimentSpec:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ContractError(f"cannot read experiment specification: {path}") from exc
        return cls.from_json(text)

    @property
    def identity(self) -> ExperimentIdentity:
        return ExperimentIdentity(self.name, self.contract_revision)

    @property
    def name(self) -> str:
        return str(self._data["name"])

    @property
    def contract_revision(self) -> int:
        return int(self._data["contract_revision"])

    @property
    def schema_version(self) -> int:
        return int(self._data["schema_version"])

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], _thaw(self._data))

    def canonical_json(self) -> str:
        return canonical_json(self._data)

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def identity_label(self) -> str:
        return self.identity.label()


def _validate_semantic_references(data: Mapping[str, Any]) -> None:
    checkpoints = data["checkpoints"]
    if not checkpoints:
        raise ContractError("checkpoints must declare at least one starting checkpoint")
    for name, binding in checkpoints.items():
        if not isinstance(name, str) or not name.strip():
            raise ContractError("checkpoint names must be non-empty strings")
        if not isinstance(binding, Mapping):
            raise ContractError(f"checkpoints.{name} must be an object")
        required_checkpoint_fields = {
            "path",
            "checkpoint_id",
            "instance_id",
            "revision",
            "manifest_id",
            "sha256",
        }
        missing = sorted(required_checkpoint_fields - set(binding))
        if missing:
            raise ContractError(
                f"checkpoint {name} missing required field(s): {', '.join(missing)}"
            )
        for field in ("path", "checkpoint_id", "instance_id", "manifest_id"):
            if not isinstance(binding[field], str) or not binding[field].strip():
                raise ContractError(f"checkpoint {name}.{field} must be a non-empty string")
        revision = binding["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ContractError(f"checkpoint {name}.revision must be a non-negative integer")
        _validate_hex_digest(binding["sha256"], f"checkpoint {name}.sha256")

    subject_slots: set[int] = set()
    for index, subject in enumerate(data["subjects"]):
        if not isinstance(subject, Mapping):
            raise ContractError(f"subjects[{index}] must be an object")
        slot = subject.get("slot")
        if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
            raise ContractError(f"subjects[{index}].slot must be a non-negative integer")
        if slot in subject_slots:
            raise ContractError(f"duplicate subject slot: {slot}")
        subject_slots.add(slot)
        for required in ("start", "cohort", "condition"):
            if not isinstance(subject.get(required), str) or not subject[required]:
                raise ContractError(f"subjects[{index}].{required} must be a non-empty string")
        if subject["start"] not in checkpoints:
            raise ContractError(
                f"subject {slot} references undeclared starting checkpoint: {subject['start']}"
            )
        if "development_sampling_slot" in subject:
            sampling = subject["development_sampling_slot"]
            if isinstance(sampling, bool) or not isinstance(sampling, int) or sampling < 0:
                raise ContractError(
                    f"subjects[{index}].development_sampling_slot must be non-negative integer"
                )
        condition = subject["condition"]
        if condition not in data["conditions"]:
            raise ContractError(f"subject {slot} references unknown condition: {condition}")
    evaluation = data["evaluation"]
    if "repetitions" in evaluation:
        repetitions = evaluation["repetitions"]
        if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 1:
            raise ContractError("evaluation.repetitions must be a positive integer")
    budgets = data["budgets"]
    for key, value in budgets.items():
        if key.startswith("max_") and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0
        ):
            raise ContractError(f"budgets.{key} must be positive")


def _validate_hex_digest(value: Any, path: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ContractError(f"{path} must be a SHA-256 hexadecimal digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ContractError(f"{path} must be a SHA-256 hexadecimal digest") from exc


def _validate_fixture_pack_reference(value: Mapping[str, Any]) -> None:
    required = {"path", "sha256"}
    missing = sorted(required - set(value))
    if missing:
        raise ContractError(f"fixture_pack missing required field(s): {', '.join(missing)}")
    if not isinstance(value["path"], str) or not value["path"].strip():
        raise ContractError("fixture_pack.path must be a non-empty string")
    _validate_hex_digest(value["sha256"], "fixture_pack.sha256")


def _validate_inline_datasets(data: Mapping[str, Any]) -> None:
    """Validate optional inline records with the same schema as fixture JSONL."""

    datasets = data.get("datasets")
    if datasets is None:
        return
    if not isinstance(datasets, Mapping) or not datasets:
        raise ContractError("datasets must be a non-empty mapping of named records")
    # Imported lazily: datasets.py uses ContractError and canonical_json from this
    # module, so a top-level import would create a cycle during package loading.
    from .datasets import DatasetBoundaryError, DatasetRecord

    for name, records in datasets.items():
        if not isinstance(name, str) or not name.strip():
            raise ContractError("dataset names must be non-empty strings")
        if not isinstance(records, list):
            raise ContractError(f"datasets.{name} must be an array of records")
        try:
            for index, record in enumerate(records):
                if not isinstance(record, Mapping):
                    raise ContractError(f"datasets.{name}[{index}] must be an object")
                DatasetRecord.from_dict(record, source_path=f"<inline:{name}>")
        except DatasetBoundaryError as exc:
            raise ContractError(f"invalid inline dataset {name}: {exc}") from exc


def load_spec(path: str | Path) -> ExperimentSpec:
    return ExperimentSpec.from_path(path)
