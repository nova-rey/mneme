"""Small, slot-relative interpretation cache contract for Phase One.

The cache stores validated annotations outside the developmental ledger.  Its
key is made from the complete scientific input/configuration, while source
identifiers and filesystem paths are deliberately excluded.  A hit can
therefore be rebound to a new episode's source identifiers without becoming a
new extraction sample.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class CacheError(ValueError):
    """A cache entry cannot be read or written under the requested scope."""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CacheKey:
    """Content key and source-slot digests used for safe rebinding."""

    digest: str
    source_digests: tuple[tuple[str, str, str], ...]
    permission_revision: str


def build_cache_key(
    sources: Sequence[Mapping[str, Any]],
    *,
    context_dependencies: Sequence[Mapping[str, Any]] = (),
    source_selection_version: str = "1",
    permission_revision: str = "1",
    extractor_schema: str = "residue-v1",
    template: str = "",
    configuration: Mapping[str, Any] | None = None,
    host_fingerprint: Mapping[str, Any],
    generation_settings: Mapping[str, Any] | None = None,
    sampling_treatment: str = "provider_managed",
    scientific_coordinate: Mapping[str, Any] | None = None,
    independent_sample: bool = False,
) -> CacheKey:
    """Derive a deterministic key from complete slot-relative content.

    ``scientific_coordinate`` is included only when the caller declares that
    the coordinate represents an independent sample.  Administrative source
    IDs, lineage IDs and operation IDs are never part of the key.
    """

    ordered_sources = []
    source_digests: list[tuple[str, str, str]] = []
    for index, source in enumerate(sources):
        slot = str(source.get("slot", f"s{index}"))
        role = str(source.get("role", ""))
        content = str(source.get("content", ""))
        content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        source_digests.append((slot, role, content_digest))
        ordered_sources.append({"slot": slot, "role": role, "content": content})
    material: dict[str, Any] = {
        "sources": ordered_sources,
        "context_dependencies": [dict(item) for item in context_dependencies],
        "source_selection_version": source_selection_version,
        "permission_revision": permission_revision,
        "extractor_schema": extractor_schema,
        "template": template,
        "configuration": dict(configuration or {}),
        "host_fingerprint": dict(host_fingerprint),
        "generation_settings": dict(generation_settings or {}),
        "sampling_treatment": sampling_treatment,
    }
    if independent_sample:
        material["scientific_coordinate"] = dict(scientific_coordinate or {})
    return CacheKey(_digest(material), tuple(source_digests), permission_revision)


@dataclass(frozen=True)
class CacheHit:
    """A cache result explicitly marked as reuse rather than a new sample."""

    key: CacheKey
    residue: Mapping[str, Any]
    reused: bool = True


class AnnotationCache:
    """In-process authorized-scope cache with immutable entry semantics.

    Persistence and evaluation workspaces can wrap this contract with an
    external artifact store later.  Reads do not update recency or any
    developmental record.
    """

    def __init__(self, scope: str):
        if not scope:
            raise CacheError("cache scope is required")
        self.scope = scope
        self._entries: dict[str, tuple[CacheKey, dict[str, Any]]] = {}

    def put(
        self,
        key: CacheKey,
        residue: Mapping[str, Any],
        *,
        authorized: bool = True,
    ) -> None:
        if not authorized:
            raise CacheError("cache write is not authorized")
        payload = copy.deepcopy(dict(residue))
        existing = self._entries.get(key.digest)
        if existing is not None and existing[1] != payload:
            raise CacheError("cache key collision with different residue")
        self._entries[key.digest] = (key, payload)

    def get(self, key: CacheKey, *, authorized: bool = True) -> CacheHit | None:
        if not authorized:
            return None
        entry = self._entries.get(key.digest)
        if entry is None or entry[0] != key:
            return None
        return CacheHit(entry[0], copy.deepcopy(entry[1]))

    def rebind(
        self,
        hit: CacheHit,
        sources: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Rebind slot-relative annotations to a new episode's source IDs."""

        actual: list[tuple[str, str, str]] = []
        for index, source in enumerate(sources):
            slot = str(source.get("slot", f"s{index}"))
            role = str(source.get("role", ""))
            content = str(source.get("content", ""))
            actual.append((slot, role, hashlib.sha256(content.encode("utf-8")).hexdigest()))
        if tuple(actual) != hit.key.source_digests:
            raise CacheError("cache hit source slots do not match the requested episode")
        return copy.deepcopy(dict(hit.residue))

    def invalidate_permission_revision(self, permission_revision: str) -> int:
        """Drop entries made under a revoked permission revision."""

        removed = 0
        for digest, (key, _) in list(self._entries.items()):
            if key.permission_revision != permission_revision:
                del self._entries[digest]
                removed += 1
        return removed


__all__ = ["AnnotationCache", "CacheError", "CacheHit", "CacheKey", "build_cache_key"]
