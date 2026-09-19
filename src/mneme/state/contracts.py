"""Small, serializable contracts for MNEME's durable P0.2 state.

These contracts describe bookkeeping and accepted history only.  They do not
model learning, recall, identity development, or future mechanism contracts.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = 3
ACCEPTED_HISTORY_DIGEST_VERSION = 2
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ArtifactKind(StrEnum):
    WORKING = "working"
    CHECKPOINT = "checkpoint"


class OperationStatus(StrEnum):
    PREPARED = "PREPARED"
    STARTED = "STARTED"
    RESULT_READY = "RESULT_READY"
    ACCEPTED = "ACCEPTED"
    UNCERTAIN = "UNCERTAIN"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True)
class StoragePermissions:
    """Storage permissions plus the Phase One interpretation opt-in."""

    store: bool = True
    export: bool = False
    interpret: bool = False
    recall: bool = False
    provider_reuse: bool = False

    def to_json(self) -> str:
        return canonical_json(
            {
                "export": self.export,
                "interpret": self.interpret,
                "provider_reuse": self.provider_reuse,
                "recall": self.recall,
                "store": self.store,
            }
        )


PHASE_ONE_PERMISSIONS = ("interpret", "recall", "provider_reuse")


@dataclass(frozen=True)
class LineageRecord:
    instance_id: str
    created_at: str
    scope_id: str
    self_ref_id: str
    parent_instance_id: str | None = None
    fork_checkpoint_id: str | None = None
    fork_manifest_id: str | None = None


@dataclass(frozen=True)
class ManifestRecord:
    manifest_id: str
    instance_id: str
    revision: int
    parent_manifest_id: str | None
    inherited_base_manifest_id: str | None
    policy_id: str
    self_ref_id: str
    format_version: int
    controller_version: str
    integrity_digest: str
    accepted_history_digest: str


def new_id() -> str:
    """Return an opaque administrative UUID; it is never model input."""

    return str(uuid.uuid4())


def validate_id(value: str, *, field: str = "id") -> str:
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{field} must be a UUID string") from exc
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def accepted_history_digest(records: list[Mapping[str, Any]]) -> str:
    """Digest ordered accepted history, excluding administrative/timing fields.

    Equality is a content comparison only.  It does not establish behavioral
    equivalence between model instances.

    The reducer is deliberately ancestry/order aware: callers supply records
    in authoritative history order, while stable source and generation content
    is retained.  Administrative identifiers, timestamps and host bookkeeping
    are excluded so a fork can be compared with its parent without claiming
    behavioral equivalence.
    """

    administrative = {
        "instance_id",
        "origin_instance_id",
        "episode_id",
        "operation_id",
        "generation_id",
        "event_id",
        "manifest_id",
        "checkpoint_id",
        "created_at",
        "occurred_at",
        "accepted_at",
        "timestamp",
        "host_ref",
        "provider",
        "model_id",
        "model_revision",
        "runtime",
    }
    normalized: list[dict[str, Any]] = []
    for ordinal, record in enumerate(records):
        stable = {
            key: value
            for key, value in record.items()
            if key not in administrative
        }
        # The list position is the canonical ancestry order.  Do not retain a
        # child-local revision, which is an administrative coordinate after a
        # fork and can differ even when accepted content is identical.
        stable["history_ordinal"] = ordinal
        normalized.append(stable)
    return canonical_digest(normalized)


def validate_digest(value: str, *, field: str = "digest") -> str:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value
