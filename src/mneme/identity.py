"""Deliberate Phase One identity and self-view transitions.

Administrative lineage UUIDs never enter this module's model requests.  A
name exists only after an explicit adoption transition and is projected from
an immutable self-view record at cold start.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import GenerationRequest
from .host import Host
from .state.storage import SQLiteStore, _utc


class IdentityError(RuntimeError):
    """The requested deliberate identity transition is invalid."""


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not name or len(name) > 64:
        raise IdentityError("name must contain 1 to 64 characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise IdentityError("name contains a control character")
    if "\n" in name or "\r" in name or "\t" in name:
        raise IdentityError("name contains a control character")
    return name


@dataclass(frozen=True)
class SelfView:
    instance_id: str
    version: int
    name: str | None
    self_view_id: str
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "version": self.version,
            "name": self.name,
            "self_view_id": self.self_view_id,
            "content_digest": self.content_digest,
        }


class IdentityService:
    """Append-only identity transitions with manifest-bound self views."""

    def __init__(self, store: SQLiteStore, instance_id: str):
        self.store = store
        self.instance_id = instance_id

    def current(self) -> SelfView | None:
        row = self.store.connection.execute(
            "SELECT m.self_view_id,m.self_view_version,s.name,s.content_digest "
            "FROM current_state c JOIN manifests m ON m.manifest_id=c.current_manifest_id "
            "LEFT JOIN self_views s ON s.self_view_id=m.self_view_id "
            "AND s.instance_id=m.instance_id "
            "WHERE c.active_instance_id=?",
            (self.instance_id,),
        ).fetchone()
        if row is None:
            raise IdentityError("lineage has no current state")
        if row[0] is None:
            return None
        if row[2] is None or row[3] is None:
            raise IdentityError("current self-view binding is missing")
        return SelfView(self.instance_id, int(row[1]), row[2], str(row[0]), str(row[3]))

    def adopt_from_host(
        self,
        host: Host,
        *,
        source: Mapping[str, Any] | None = None,
    ) -> SelfView:
        """Make one bounded structured naming call, then adopt its result.

        The provider boundary does not advertise native structured output for
        all Phase One hosts, so the contract is a prompted JSON object and a
        strict local validator.  A malformed response is terminal: this
        method never resamples or silently falls back to an operator name.
        """

        current = self.store.current()
        manifest = self.store.connection.execute(
            "SELECT self_view_id,policy_id FROM manifests WHERE manifest_id=?",
            (current["current_manifest_id"],),
        ).fetchone()
        if manifest is None:
            raise IdentityError("current manifest is missing")
        policy = self.store.connection.execute(
            "SELECT recall_allowed,provider_reuse_allowed FROM policies WHERE policy_id=?",
            (manifest["policy_id"],),
        ).fetchone()
        if manifest["self_view_id"] is not None:
            raise IdentityError("identity is already adopted")
        if policy is None or not bool(policy[0]) or not bool(policy[1]):
            raise IdentityError("identity adoption permission is denied")
        request = GenerationRequest(
            messages=(
                {
                    "role": "user",
                    "content": (
                        "Choose one concise name for this model instance. "
                        'Return exactly one JSON object with one string field: {"name":"…"}. '
                        "Do not include markdown or any other fields."
                    ),
                },
            ),
            system=(
                "You are performing a deliberate naming operation. "
                "The result is an administrative self-view label, not a personality claim."
            ),
            parameters={"max_new_tokens": 64, "temperature": 0.0},
        )
        result = host.generate(request)
        try:
            decoded = json.loads(result.content)
        except json.JSONDecodeError as exc:
            raise IdentityError("naming response is not valid JSON") from exc
        if (
            not isinstance(decoded, dict)
            or set(decoded) != {"name"}
            or not isinstance(decoded.get("name"), str)
        ):
            raise IdentityError("naming response must contain only a string name")
        fingerprint = host.fingerprint().to_dict()
        provenance = {
            "operation": "identity_adoption",
            "host": fingerprint,
            "model_id": result.model_id,
            "provider": result.provider,
            "response_digest": hashlib.sha256(result.content.encode()).hexdigest(),
        }
        if source:
            provenance["source"] = dict(source)
        return self.adopt(str(decoded["name"]), source=provenance)

    def adopt(self, name: str, *, source: Mapping[str, Any] | None = None) -> SelfView:
        """Adopt one deliberate name; generic extraction cannot call this."""

        name = validate_name(name)
        with self.store.transaction() as db:
            current = db.execute(
                "SELECT * FROM current_state WHERE active_instance_id=?", (self.instance_id,)
            ).fetchone()
            if current is None:
                raise IdentityError("lineage has no current state")
            manifest = db.execute(
                "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
            ).fetchone()
            if manifest is None:
                raise IdentityError("current manifest is missing")
            policy = db.execute(
                "SELECT recall_allowed,provider_reuse_allowed FROM policies WHERE policy_id=?",
                (manifest["policy_id"],),
            ).fetchone()
            if policy is None or not bool(policy[0]) or not bool(policy[1]):
                raise IdentityError("identity adoption permission is denied")
            if manifest["self_view_id"] is not None:
                raise IdentityError("identity is already adopted")
            version = int(manifest["self_view_version"]) + 1
            event_id = str(uuid.uuid4())
            view_id = str(uuid.uuid4())
            now = _utc()
            content = {"name": name}
            content_json = json.dumps(content, sort_keys=True, separators=(",", ":"))
            content_digest = _digest(content)
            db.execute(
                "INSERT INTO identity_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    self.instance_id,
                    "adopt",
                    name,
                    None,
                    json.dumps(dict(source or {}), sort_keys=True),
                    int(current["current_revision"]) + 1,
                    version,
                    None,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO self_views VALUES(?,?,?,?,?,?,?,?)",
                (
                    view_id,
                    self.instance_id,
                    version,
                    name,
                    event_id,
                    content_json,
                    content_digest,
                    now,
                ),
            )
            revision = int(current["current_revision"]) + 1
            manifest_id = str(uuid.uuid4())
            integrity = _digest(
                {
                    "instance_id": self.instance_id,
                    "revision": revision,
                    "self_view_id": view_id,
                    "self_view_version": version,
                }
            )
            db.execute(
                "INSERT INTO manifests(manifest_id,instance_id,revision,parent_manifest_id,"
                "inherited_base_manifest_id,policy_id,self_ref_id,format_version,"
                "controller_version,integrity_digest,accepted_history_digest,graph_snapshot_id,"
                "graph_revision,accepted_episode_count,self_view_id,self_view_version) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    manifest_id,
                    self.instance_id,
                    revision,
                    manifest["manifest_id"],
                    manifest["inherited_base_manifest_id"],
                    manifest["policy_id"],
                    manifest["self_ref_id"],
                    manifest["format_version"],
                    "mneme-p1.2",
                    integrity,
                    manifest["accepted_history_digest"],
                    manifest["graph_snapshot_id"],
                    manifest["graph_revision"],
                    manifest["accepted_episode_count"],
                    view_id,
                    version,
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.instance_id,
                    revision,
                    current["current_revision"],
                    event_id,
                    "identity_adopted",
                    None,
                    manifest_id,
                    now,
                ),
            )
            db.execute(
                "UPDATE current_state SET current_revision=?,current_manifest_id=? "
                "WHERE singleton=1",
                (revision, manifest_id),
            )
            return SelfView(self.instance_id, version, name, view_id, content_digest)

    def add_alias(self, alias: str, *, source: Mapping[str, Any] | None = None) -> str:
        alias = validate_name(alias)
        with self.store.transaction() as db:
            current = db.execute(
                "SELECT * FROM current_state WHERE active_instance_id=?", (self.instance_id,)
            ).fetchone()
            if current is None:
                raise IdentityError("lineage has no current state")
            manifest = db.execute(
                "SELECT * FROM manifests WHERE manifest_id=?", (current["current_manifest_id"],)
            ).fetchone()
            if manifest is None or manifest["self_view_id"] is None:
                raise IdentityError("adopt a name before adding an alias")
            event_id, now = str(uuid.uuid4()), _utc()
            revision = int(current["current_revision"]) + 1
            db.execute(
                "INSERT INTO identity_events VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id,
                    self.instance_id,
                    "alias",
                    None,
                    alias,
                    json.dumps(dict(source or {}), sort_keys=True),
                    revision,
                    manifest["self_view_version"],
                    None,
                    now,
                ),
            )
            new_manifest = str(uuid.uuid4())
            db.execute(
                "INSERT INTO manifests(manifest_id,instance_id,revision,parent_manifest_id,"
                "inherited_base_manifest_id,policy_id,self_ref_id,format_version,"
                "controller_version,integrity_digest,accepted_history_digest,graph_snapshot_id,"
                "graph_revision,accepted_episode_count,self_view_id,self_view_version) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    new_manifest,
                    self.instance_id,
                    revision,
                    manifest["manifest_id"],
                    manifest["inherited_base_manifest_id"],
                    manifest["policy_id"],
                    manifest["self_ref_id"],
                    manifest["format_version"],
                    "mneme-p1.2",
                    _digest(
                        {
                            "instance_id": self.instance_id,
                            "revision": revision,
                            "self_view_id": manifest["self_view_id"],
                            "alias": alias,
                        }
                    ),
                    manifest["accepted_history_digest"],
                    manifest["graph_snapshot_id"],
                    manifest["graph_revision"],
                    manifest["accepted_episode_count"],
                    manifest["self_view_id"],
                    manifest["self_view_version"],
                ),
            )
            db.execute(
                "INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.instance_id,
                    revision,
                    current["current_revision"],
                    event_id,
                    "identity_alias_added",
                    None,
                    new_manifest,
                    now,
                ),
            )
            db.execute(
                "UPDATE current_state SET current_revision=?,current_manifest_id=? "
                "WHERE singleton=1",
                (revision, new_manifest),
            )
            return event_id


__all__ = ["IdentityError", "IdentityService", "SelfView", "validate_name"]
