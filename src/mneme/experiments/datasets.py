"""Fixture-pack loading and development/evaluation contamination checks."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import ContractError, canonical_json

PARTITIONS = frozenset({"engineering", "learner-pilot", "sealed-assessment"})
ROLES = frozenset({"development", "evaluation"})


class DatasetBoundaryError(ContractError):
    """Fixture data violates a P0.3 split or schema boundary."""


def _duplicate_json_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DatasetBoundaryError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def normalized_content_digest(messages: Iterable[Mapping[str, Any]]) -> str:
    """Digest model-visible content after conservative duplicate normalization."""

    normalized: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, Mapping):
            raise DatasetBoundaryError("message must be an object")
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            raise DatasetBoundaryError("message role and content must be strings")
        text = unicodedata.normalize("NFC", content.replace("\r\n", "\n").replace("\r", "\n"))
        text = " ".join(text.split())
        normalized.append({"role": role, "content": text})
    return hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DatasetRecord:
    record_id: str
    ordinal: int
    scenario_family: str
    messages: tuple[dict[str, str], ...]
    partition: str
    role: str
    source_path: str | None = None

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], *, source_path: str | None = None
    ) -> DatasetRecord:
        required = {"record_id", "ordinal", "scenario_family", "messages", "partition", "role"}
        missing = sorted(required - set(value))
        if missing:
            raise DatasetBoundaryError(f"dataset record missing: {', '.join(missing)}")
        record_id = value["record_id"]
        family = value["scenario_family"]
        partition = value["partition"]
        role = value["role"]
        ordinal = value["ordinal"]
        if not isinstance(record_id, str) or not record_id:
            raise DatasetBoundaryError("record_id must be a non-empty string")
        if not isinstance(family, str) or not family:
            raise DatasetBoundaryError(f"{record_id}: scenario_family must be non-empty")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise DatasetBoundaryError(f"{record_id}: ordinal must be non-negative integer")
        if partition not in PARTITIONS:
            raise DatasetBoundaryError(f"{record_id}: unsupported partition {partition!r}")
        if role not in ROLES:
            raise DatasetBoundaryError(f"{record_id}: unsupported dataset role {role!r}")
        messages = value["messages"]
        if not isinstance(messages, list) or not messages:
            raise DatasetBoundaryError(f"{record_id}: messages must be a non-empty array")
        normalized: list[dict[str, str]] = []
        for message in messages:
            if not isinstance(message, Mapping):
                raise DatasetBoundaryError(f"{record_id}: message must be an object")
            msg_role, content = message.get("role"), message.get("content")
            if not isinstance(msg_role, str) or not isinstance(content, str):
                raise DatasetBoundaryError(f"{record_id}: message role/content must be strings")
            normalized.append({"role": msg_role, "content": content})
        return cls(record_id, ordinal, family, tuple(normalized), partition, role, source_path)

    @property
    def content_digest(self) -> str:
        return normalized_content_digest(self.messages)


@dataclass(frozen=True)
class FixturePack:
    records: tuple[DatasetRecord, ...]
    manifest_path: str | None = None
    manifest_digest: str | None = None

    def __post_init__(self) -> None:
        validate_split_boundaries(self.records)

    def by_role(self, role: str) -> tuple[DatasetRecord, ...]:
        return tuple(record for record in self.records if record.role == role)

    def by_partition(self, partition: str) -> tuple[DatasetRecord, ...]:
        return tuple(record for record in self.records if record.partition == partition)


def load_jsonl(
    path: str | Path, *, partition: str | None = None, role: str | None = None
) -> tuple[DatasetRecord, ...]:
    path = Path(path)
    records: list[DatasetRecord] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DatasetBoundaryError(f"cannot read dataset: {path}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, object_pairs_hook=_duplicate_json_pairs)
        except (json.JSONDecodeError, DatasetBoundaryError) as exc:
            raise DatasetBoundaryError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, Mapping):
            raise DatasetBoundaryError(f"dataset record at {path}:{line_number} is not an object")
        record = DatasetRecord.from_dict(value, source_path=str(path))
        if partition is not None and record.partition != partition:
            raise DatasetBoundaryError(f"{record.record_id}: partition does not match manifest")
        if role is not None and record.role != role:
            raise DatasetBoundaryError(f"{record.record_id}: role does not match manifest")
        records.append(record)
    validate_split_boundaries(records)
    return tuple(records)


def validate_split_boundaries(records: Iterable[DatasetRecord]) -> None:
    records = tuple(records)
    seen_ids: set[str] = set()
    seen_content: dict[str, DatasetRecord] = {}
    seen_families: dict[str, tuple[str, str]] = {}
    for record in records:
        if record.record_id in seen_ids:
            raise DatasetBoundaryError(f"duplicate record ID: {record.record_id}")
        seen_ids.add(record.record_id)
        digest = record.content_digest
        prior = seen_content.get(digest)
        if prior is not None:
            raise DatasetBoundaryError(
                f"duplicate normalized content: {prior.record_id} and {record.record_id}"
            )
        seen_content[digest] = record
        boundary = (record.partition, record.role)
        prior_boundary = seen_families.get(record.scenario_family)
        if prior_boundary is not None and prior_boundary != boundary:
            raise DatasetBoundaryError(
                f"scenario family {record.scenario_family!r} crosses split boundary: "
                f"{prior_boundary} and {boundary}"
            )
        seen_families[record.scenario_family] = boundary

    by_group: dict[tuple[str, str], list[int]] = {}
    for record in records:
        by_group.setdefault((record.partition, record.role), []).append(record.ordinal)
    for group, ordinals in by_group.items():
        if len(ordinals) != len(set(ordinals)):
            raise DatasetBoundaryError(f"duplicate ordinal in split {group}")


def load_fixture_pack(path: str | Path) -> FixturePack:
    """Load a manifest with ``datasets`` entries pointing to JSONL files.

    A manifest may also use a single ``records`` array for small synthetic packs.
    Paths are resolved relative to the manifest and aliases are rejected.
    """

    manifest_path = Path(path).resolve()
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(raw, object_pairs_hook=_duplicate_json_pairs)
    except (OSError, json.JSONDecodeError, DatasetBoundaryError) as exc:
        raise DatasetBoundaryError(f"invalid fixture manifest: {path}: {exc}") from exc
    if not isinstance(manifest, Mapping):
        raise DatasetBoundaryError("fixture manifest must be an object")
    if manifest.get("schema_version") != 1:
        raise DatasetBoundaryError("unsupported fixture manifest schema version")
    records: list[DatasetRecord] = []
    if "records" in manifest:
        if not isinstance(manifest["records"], list):
            raise DatasetBoundaryError("fixture records must be an array")
        records.extend(
            DatasetRecord.from_dict(record, source_path=str(manifest_path))
            for record in manifest["records"]
        )
    datasets = manifest.get("datasets", [])
    if not isinstance(datasets, list):
        raise DatasetBoundaryError("fixture datasets must be an array")
    resolved_files: set[Path] = set()
    for entry in datasets:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
            raise DatasetBoundaryError("fixture dataset entry requires path")
        dataset_path = (manifest_path.parent / entry["path"]).resolve()
        if dataset_path in resolved_files:
            raise DatasetBoundaryError(f"fixture dataset alias/reuse: {entry['path']}")
        resolved_files.add(dataset_path)
        records.extend(
            load_jsonl(
                dataset_path,
                partition=entry.get("partition"),
                role=entry.get("role"),
            )
        )
    validate_split_boundaries(records)
    return FixturePack(
        tuple(records),
        str(manifest_path),
        hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )
