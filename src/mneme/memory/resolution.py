"""Deterministic, explicit concept resolution for Phase One.

Resolution is intentionally conservative.  Exact normalized labels resolve
without a model call; other labels resolve only through an explicitly supplied
alias table.  Conflicting aliases remain unresolved instead of being merged
on lexical overlap or an embedding suggestion.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .residue import normalize_label


def normalize_lookup_label(label: str) -> str:
    """Return the lookup key used for exact labels and explicit aliases."""

    return normalize_label(label).casefold()


class AmbiguousAliasError(ValueError):
    """Raised when an alias is registered for more than one canonical key."""


@dataclass(frozen=True)
class ResolutionDecision:
    """One auditable resolution result."""

    input_label: str
    normalized_label: str
    canonical_key: str | None
    method: str
    ambiguous: bool = False

    @property
    def resolved(self) -> bool:
        return self.canonical_key is not None and not self.ambiguous

    def to_dict(self) -> dict[str, object]:
        return {
            "input_label": self.input_label,
            "normalized_label": self.normalized_label,
            "canonical_key": self.canonical_key,
            "method": self.method,
            "ambiguous": self.ambiguous,
        }


class ExplicitAliasResolver:
    """Resolve labels against a fixed set of concept labels and aliases."""

    def __init__(
        self,
        labels: Mapping[str, str] | Iterable[tuple[str, str]] = (),
        aliases: Mapping[str, str] | Iterable[tuple[str, str]] = (),
    ) -> None:
        self._labels: dict[str, str] = {}
        self._aliases: dict[str, set[str]] = {}
        label_items = labels.items() if isinstance(labels, Mapping) else labels
        for key, label in label_items:
            self.add_label(key, label)
        alias_items = aliases.items() if isinstance(aliases, Mapping) else aliases
        for alias, key in alias_items:
            self.add_alias(alias, key)

    @property
    def labels(self) -> Mapping[str, str]:
        return dict(self._labels)

    @property
    def aliases(self) -> Mapping[str, frozenset[str]]:
        return {alias: frozenset(keys) for alias, keys in self._aliases.items()}

    def add_label(self, key: str, label: str) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("concept key must be a non-empty string")
        display = normalize_label(label)
        lookup = normalize_lookup_label(display)
        existing = self._labels.get(lookup)
        if existing is not None and existing != key:
            raise AmbiguousAliasError(f"normalized labels collide: {display!r}")
        self._labels[lookup] = key

    def add_alias(self, alias: str, canonical_key: str) -> None:
        if not isinstance(canonical_key, str) or not canonical_key:
            raise ValueError("canonical key must be a non-empty string")
        if canonical_key not in self._labels.values():
            raise ValueError(f"alias target is not a known concept key: {canonical_key!r}")
        normalized = normalize_lookup_label(alias)
        self._aliases.setdefault(normalized, set()).add(canonical_key)

    def resolve(self, label: str) -> ResolutionDecision:
        display = normalize_label(label)
        normalized = normalize_lookup_label(display)
        key = self._labels.get(normalized)
        if key is not None:
            return ResolutionDecision(display, normalized, key, "exact")
        candidates = self._aliases.get(normalized, set())
        if len(candidates) == 1:
            return ResolutionDecision(display, normalized, next(iter(candidates)), "explicit_alias")
        if len(candidates) > 1:
            return ResolutionDecision(display, normalized, None, "ambiguous_alias", ambiguous=True)
        return ResolutionDecision(display, normalized, None, "unresolved")

    def resolve_many(self, labels: Iterable[str]) -> tuple[ResolutionDecision, ...]:
        return tuple(self.resolve(label) for label in labels)


def resolve_label(
    label: str,
    *,
    labels: Mapping[str, str],
    aliases: Mapping[str, str] | None = None,
) -> ResolutionDecision:
    """Convenience wrapper for one exact/explicit-alias lookup."""

    return ExplicitAliasResolver(labels, aliases or {}).resolve(label)


__all__ = [
    "AmbiguousAliasError",
    "ExplicitAliasResolver",
    "ResolutionDecision",
    "normalize_lookup_label",
    "resolve_label",
]
