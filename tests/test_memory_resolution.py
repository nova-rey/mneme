from __future__ import annotations

import pytest

from mneme.memory import (
    AmbiguousAliasError,
    ExplicitAliasResolver,
    normalize_lookup_label,
)


def test_normalization_is_nfc_whitespace_casefold_without_synonym_inference() -> None:
    assert normalize_lookup_label("  VRA\u0301M  ") == "vrám"
    assert normalize_lookup_label("memory bandwidth") != normalize_lookup_label("video memory")


def test_exact_labels_and_explicit_aliases_resolve() -> None:
    resolver = ExplicitAliasResolver(
        labels={"vram": "VRAM", "bandwidth": "Memory bandwidth"},
        aliases={"video memory": "vram"},
    )

    exact = resolver.resolve("vRaM")
    alias = resolver.resolve(" Video   Memory ")
    unknown = resolver.resolve("graphics memory")

    assert exact.resolved and exact.canonical_key == "vram" and exact.method == "exact"
    assert alias.resolved and alias.canonical_key == "vram" and alias.method == "explicit_alias"
    assert not unknown.resolved and unknown.method == "unresolved"


def test_ambiguous_alias_remains_unresolved() -> None:
    resolver = ExplicitAliasResolver(labels={"a": "Alpha", "b": "Beta"})
    resolver.add_alias("shared", "a")
    resolver.add_alias("shared", "b")

    result = resolver.resolve("shared")

    assert result.ambiguous
    assert not result.resolved
    assert result.canonical_key is None


def test_colliding_normalized_labels_are_rejected() -> None:
    resolver = ExplicitAliasResolver(labels={"a": "Alpha"})

    with pytest.raises(AmbiguousAliasError):
        resolver.add_label("b", " alpha ")


def test_alias_target_must_be_a_known_concept() -> None:
    resolver = ExplicitAliasResolver(labels={"a": "Alpha"})

    with pytest.raises(ValueError, match="known concept"):
        resolver.add_alias("unbound", "missing")
