"""Build host-local MI1 bank variants from frozen portable banks."""

from __future__ import annotations

from dataclasses import replace

from experiments.mi1.native.bank import MemoryBank


def configure_bank(
    bank: MemoryBank,
    *,
    query_sites: tuple[tuple[int, int], ...],
    bank_logit_bias: float,
) -> MemoryBank:
    """Apply only the frozen query-site and per-slot logit-prior controls."""
    manifest = replace(
        bank.manifest,
        query_groups=(),
        query_sites=query_sites,
        bank_logit_bias=bank_logit_bias,
    )
    configured = replace(bank, manifest=manifest)
    configured.validate()
    return configured
