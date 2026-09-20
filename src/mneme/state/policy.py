"""Explicit Phase One permission state and the local revocation authority.

The base policy lives in the lineage SQLite store.  Revocations and explicit
re-authorizations are append-only records in a small private JSONL authority
file whose path is copied into checkpoints.  A historical copy therefore
consults the same current scope authority instead of being able to revive a
permission that was revoked after the copy was made.

This is a local, single-writer policy boundary.  It is not a multi-user
authorization service and it does not provide erasure for detached copies
whose authority path is unavailable.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import PHASE_ONE_PERMISSIONS

PHASE_TWO_PERMISSIONS = ("learn",)


class PolicyError(RuntimeError):
    """The current policy cannot authorize the requested operation."""


def _utc() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def host_ref(fingerprint: Mapping[str, Any]) -> str:
    """Return the stable host reference used by policy and run bindings."""

    return hashlib.sha256(
        json.dumps(dict(fingerprint), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        .encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class PermissionState:
    """Effective permissions for one lineage scope at read time."""

    policy_id: str
    scope_id: str
    storage_allowed: bool
    export_allowed: bool
    interpretation_allowed: bool
    recall_allowed: bool
    provider_reuse_allowed: bool
    learning_allowed: bool
    policy_version: int
    revocation_revision: int
    authority_path: str | None
    authority_available: bool
    bound_host_ref: str | None
    bound_host_fingerprint: dict[str, Any] | None

    def permits(self, permission: str) -> bool:
        values = {
            "store": self.storage_allowed,
            "storage": self.storage_allowed,
            "export": self.export_allowed,
            "interpret": self.interpretation_allowed,
            "recall": self.recall_allowed,
            "provider_reuse": self.provider_reuse_allowed,
            "learn": self.learning_allowed,
        }
        if permission not in values:
            raise PolicyError(f"unknown permission: {permission}")
        return bool(values[permission])

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "scope_id": self.scope_id,
            "storage": self.storage_allowed,
            "export": self.export_allowed,
            "interpret": self.interpretation_allowed,
            "recall": self.recall_allowed,
            "provider_reuse": self.provider_reuse_allowed,
            "learn": self.learning_allowed,
            "policy_version": self.policy_version,
            "revocation_revision": self.revocation_revision,
            "authority_path": self.authority_path,
            "authority_available": self.authority_available,
            "bound_host_ref": self.bound_host_ref,
            "bound_host_fingerprint": self.bound_host_fingerprint,
        }


class PolicyService:
    """Read and append explicit scope permission transitions."""

    _PERMISSION_COLUMNS = {
        "interpret": "interpretation_allowed",
        "recall": "recall_allowed",
        "provider_reuse": "provider_reuse_allowed",
    }

    def __init__(self, store: Any, instance_id: str | None = None) -> None:
        self.store = store
        self.instance_id = instance_id or str(store.current()["active_instance_id"])

    def _policy_row(self) -> Any:
        current = self.store.connection.execute(
            "SELECT current_manifest_id FROM current_state WHERE active_instance_id=?",
            (self.instance_id,),
        ).fetchone()
        if current is None:
            raise PolicyError("lineage has no current state")
        row = self.store.connection.execute(
            "SELECT p.*,l.scope_id FROM manifests m "
            "JOIN policies p ON p.policy_id=m.policy_id "
            "JOIN lineages l ON l.instance_id=m.instance_id "
            "WHERE m.manifest_id=? AND m.instance_id=?",
            (current[0], self.instance_id),
        ).fetchone()
        if row is None:
            raise PolicyError("lineage policy is missing")
        return row

    def _authority_path(self) -> Path | None:
        try:
            row = self.store.connection.execute(
                "SELECT revocation_ledger_path FROM store_info WHERE singleton=1"
            ).fetchone()
        except sqlite3.OperationalError:
            # Historical read-only P0.2/P1.1 checkpoints predate the
            # authority column and therefore have no current revocation
            # authority.  Their Phase One permissions remain denied.
            return None
        if row is None or row[0] in (None, ""):
            return None
        return Path(str(row[0]))

    def _events(self) -> tuple[list[dict[str, Any]], bool]:
        path = self._authority_path()
        if path is None or not path.is_file():
            return [], False
        events: list[dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise PolicyError(
                            f"revocation authority is corrupt at line {line_number}"
                        ) from exc
                    if not isinstance(event, dict):
                        raise PolicyError("revocation authority contains a non-object record")
                    if event.get("scope_id") != self._policy_row()["scope_id"]:
                        continue
                    if event.get("permission") not in PHASE_ONE_PERMISSIONS:
                        raise PolicyError("revocation authority contains an unknown permission")
                    if event.get("action") not in {"grant", "revoke"}:
                        raise PolicyError("revocation authority contains an unknown action")
                    events.append(event)
        except OSError as exc:
            raise PolicyError("revocation authority cannot be read") from exc
        return events, True

    def current(self) -> PermissionState:
        row = self._policy_row()
        events, authority_available = self._events()
        columns = set(row.keys())
        values = {
            "interpret": bool(row["interpretation_allowed"])
            if "interpretation_allowed" in columns
            else False,
            "recall": bool(row["recall_allowed"]) if "recall_allowed" in columns else False,
            "provider_reuse": bool(row["provider_reuse_allowed"])
            if "provider_reuse_allowed" in columns
            else False,
            "learn": bool(row["learning_allowed"])
            if "learning_allowed" in columns
            else False,
        }
        bound_ref = (
            str(row["bound_host_ref"])
            if "bound_host_ref" in columns and row["bound_host_ref"]
            else None
        )
        bound_fingerprint: dict[str, Any] | None = None
        if "bound_host_fingerprint_json" in columns and row["bound_host_fingerprint_json"]:
            try:
                decoded = json.loads(str(row["bound_host_fingerprint_json"]))
            except json.JSONDecodeError as exc:
                raise PolicyError("bound host fingerprint is invalid") from exc
            if not isinstance(decoded, dict):
                raise PolicyError("bound host fingerprint is not an object")
            bound_fingerprint = decoded
        revision = 0
        for event in events:
            permission = str(event["permission"])
            values[permission] = event["action"] == "grant"
            revision = max(revision, int(event.get("revision", 0)))
            event_host_ref = event.get("host_ref")
            if permission == "provider_reuse" and event["action"] == "grant":
                if not isinstance(event_host_ref, str) or not event_host_ref:
                    raise PolicyError("provider reuse grant has no host binding")
                bound_ref = event_host_ref
                raw_fingerprint = event.get("host_fingerprint")
                if isinstance(raw_fingerprint, dict):
                    bound_fingerprint = dict(raw_fingerprint)
        # A missing authority is an explicit fail-closed condition for every
        # Phase One permission, including copied legacy stores.
        if not authority_available:
            values.update({permission: False for permission in PHASE_ONE_PERMISSIONS})
        return PermissionState(
            policy_id=str(row["policy_id"]),
            scope_id=str(row["scope_id"]),
            storage_allowed=bool(row["storage_allowed"]),
            export_allowed=bool(row["export_allowed"]),
            interpretation_allowed=values["interpret"],
            recall_allowed=values["recall"],
            provider_reuse_allowed=values["provider_reuse"],
            learning_allowed=values["learn"],
            policy_version=int(row["policy_version"]) if "policy_version" in columns else 1,
            revocation_revision=revision,
            authority_path=str(self._authority_path()) if self._authority_path() else None,
            authority_available=authority_available,
            bound_host_ref=bound_ref,
            bound_host_fingerprint=bound_fingerprint,
        )

    def require(self, permission: str) -> PermissionState:
        state = self.current()
        if permission in PHASE_ONE_PERMISSIONS and not state.authority_available:
            raise PolicyError("Phase One permission authority is unavailable")
        if not state.permits(permission):
            raise PolicyError(f"{permission} permission denied")
        return state

    def require_host(self, state: PermissionState, fingerprint: Mapping[str, Any]) -> None:
        if state.bound_host_ref is None:
            raise PolicyError("provider reuse has no selected host binding")
        if host_ref(fingerprint) != state.bound_host_ref:
            raise PolicyError("host fingerprint differs from selected policy host")

    def show(self) -> dict[str, Any]:
        return self.current().to_dict()

    def _append(self, *, action: str, permissions: Iterable[str], host: Mapping[str, Any] | None) -> int:
        if bool(getattr(self.store, "read_only", False)):
            raise PolicyError("policy changes require a writable working store")
        names = tuple(dict.fromkeys(str(item) for item in permissions))
        if not names:
            raise PolicyError("at least one Phase One permission is required")
        unknown = set(names) - set(PHASE_ONE_PERMISSIONS)
        if unknown:
            raise PolicyError(f"unknown permission: {sorted(unknown)[0]}")
        path = self._authority_path()
        if path is None:
            raise PolicyError("legacy store has no permission authority; explicit migration setup is required")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(mode=0o600, exist_ok=True)
        os.chmod(path, 0o600)
        prior, available = self._events()
        if not available and action == "revoke":
            raise PolicyError("permission authority is unavailable")
        # An explicitly requested grant is the legacy re-authorization step.
        # It creates the authority only after the operator has selected the
        # permissions (and, for provider reuse, a host binding).
        if not available:
            prior = []
        revision = max((int(event.get("revision", 0)) for event in prior), default=0) + 1
        row = self._policy_row()
        event_host_ref: str | None = host_ref(host) if host is not None else None
        if "provider_reuse" in names and action == "grant" and event_host_ref is None:
            current = self.current()
            event_host_ref = current.bound_host_ref
            if event_host_ref is None:
                raise PolicyError("provider reuse grant requires a selected host binding")
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            for permission in names:
                event = {
                    "event_id": str(uuid.uuid4()),
                    "scope_id": str(row["scope_id"]),
                    "policy_id": str(row["policy_id"]),
                    "permission": permission,
                    "action": action,
                    "revision": revision,
                    "created_at": _utc(),
                }
                if permission == "provider_reuse" and action == "grant":
                    event["host_ref"] = event_host_ref
                    if host is not None:
                        event["host_fingerprint"] = dict(host)
                encoded = json.dumps(event, sort_keys=True, separators=(",", ":"))
                handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return revision

    def revoke(self, permissions: Iterable[str]) -> int:
        return self._append(action="revoke", permissions=permissions, host=None)

    def grant(
        self,
        permissions: Iterable[str],
        *,
        host_fingerprint: Mapping[str, Any] | None = None,
    ) -> int:
        return self._append(action="grant", permissions=permissions, host=host_fingerprint)


__all__ = [
    "PHASE_ONE_PERMISSIONS",
    "PHASE_TWO_PERMISSIONS",
    "PermissionState",
    "PolicyError",
    "PolicyService",
    "host_ref",
]
