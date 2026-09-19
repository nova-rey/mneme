from __future__ import annotations

import pytest

from mneme.memory.cache import AnnotationCache, CacheError, build_cache_key


def _key(
    *,
    output: str = "answer",
    permission: str = "1",
    coordinate: int | None = None,
    template: str = "",
    host: dict[str, str] | None = None,
):
    sources = [
        {"slot": "s0", "role": "user", "content": "same prompt"},
        {"slot": "s1", "role": "model_output", "content": output},
    ]
    return build_cache_key(
        sources,
        context_dependencies=({"kind": "session", "content": "none"},),
        permission_revision=permission,
        host_fingerprint=host or {"provider": "fake", "model_id": "fixture"},
        generation_settings={"temperature": 0},
        template=template,
        scientific_coordinate={"probe": coordinate} if coordinate is not None else None,
        independent_sample=coordinate is not None,
    )


def test_cache_key_changes_when_response_or_permissions_change():
    assert _key() != _key(output="different")
    assert _key() != _key(permission="2")
    assert _key() != _key(template="changed-template")
    assert _key() != _key(host={"provider": "other", "model_id": "fixture"})


def test_cache_hit_rebinds_slot_relative_annotation_without_ids():
    cache = AnnotationCache("working-lineage")
    key = _key()
    residue = {"core_concepts": [{"key": "x", "label": "same"}]}
    cache.put(key, residue)
    hit = cache.get(key)
    assert hit is not None and hit.reused
    rebound = cache.rebind(
        hit,
        [
            {
                "slot": "s0",
                "source_id": "new-a",
                "role": "user",
                "content": "same prompt",
            },
            {
                "slot": "s1",
                "source_id": "new-b",
                "role": "model_output",
                "content": "answer",
            },
        ],
    )
    assert rebound == residue


def test_cache_rejects_wrong_sources_and_unauthorized_writes():
    cache = AnnotationCache("working-lineage")
    key = _key()
    with pytest.raises(CacheError, match="not authorized"):
        cache.put(key, {}, authorized=False)
    cache.put(key, {})
    hit = cache.get(key)
    assert hit is not None
    with pytest.raises(CacheError, match="do not match"):
        cache.rebind(hit, [{"slot": "s0", "content": "changed"}])
    assert cache.get(key, authorized=False) is None


def test_cache_independent_coordinate_is_domain_separated():
    assert _key(coordinate=0) != _key(coordinate=1)
    assert _key() != _key(coordinate=0)


def test_permission_invalidation_removes_old_entries():
    cache = AnnotationCache("working-lineage")
    old, current = _key(permission="1"), _key(permission="2")
    cache.put(old, {})
    cache.put(current, {})
    assert cache.invalidate_permission_revision("2") == 1
    assert cache.get(old) is None
    assert cache.get(current) is not None
