"""Model-free oracle for the MI1 Qwen3 bank-prefill batch guard."""

from __future__ import annotations


def validate_single_sequence_bank_prefill(
    *, unique_sequences: int, token_count: int, mask_query_counts: tuple[int, ...]
) -> None:
    """Accept multi-token prefill only when one sequence owns every mask row."""
    if unique_sequences != 1:
        raise ValueError("MI1 bank prefill requires exactly one unique sequence")
    if token_count <= 0:
        raise ValueError("MI1 bank prefill requires at least one prompt token")
    if not mask_query_counts or any(count != token_count for count in mask_query_counts):
        raise ValueError("each MI1 bank mask must have one query row per prompt token")
