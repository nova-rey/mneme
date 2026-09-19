"""Read-only accounting for provider calls retained in a Phase One lineage."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ..state.storage import SQLiteStore

_TOKEN_FIELDS = ("input_tokens", "output_tokens", "total_tokens")


def _usage(value: object) -> dict[str, int | None] | None:
    if not isinstance(value, Mapping):
        return None
    result: dict[str, int | None] = {}
    for field in _TOKEN_FIELDS:
        item = value.get(field)
        if item is None:
            result[field] = None
        elif isinstance(item, int) and not isinstance(item, bool) and item >= 0:
            result[field] = item
        else:
            return None
    return result


def _sum_usage(records: list[object]) -> tuple[dict[str, int], dict[str, int]]:
    totals = {field: 0 for field in _TOKEN_FIELDS}
    unknown = {field: 0 for field in _TOKEN_FIELDS}
    for record in records:
        parsed = _usage(record)
        for field in _TOKEN_FIELDS:
            value = None if parsed is None else parsed[field]
            if value is None:
                unknown[field] += 1
            else:
                totals[field] += value
    return totals, unknown


def _decode_usage(value: object) -> object:
    if value is None:
        return None
    try:
        decoded: Any = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return None
    return decoded


def summarize_lineage_usage(store: SQLiteStore) -> dict[str, Any]:
    """Summarize retained provider usage without inventing unknown values.

    Developmental response generations, interpretation attempts (including
    invalid repairs), and identity naming generations are separate categories.
    Interpretation attempts are counted from their persisted result payloads,
    so an attempt is never double-counted through a second generation table.
    """

    connection = store.connection
    development = [
        row[0]
        for row in connection.execute(
            "SELECT usage_json FROM generation_records ORDER BY rowid"
        ).fetchall()
    ]
    interpretation = [
        _decode_usage(row[0])
        for row in connection.execute(
            "SELECT result_json FROM interpretation_attempts "
            "WHERE result_json IS NOT NULL ORDER BY rowid"
        ).fetchall()
    ]
    naming = [
        row[0]
        for row in connection.execute(
            "SELECT usage_json FROM identity_generation_records ORDER BY rowid"
        ).fetchall()
    ]
    categories = {
        "development": development,
        "extraction": interpretation,
        "naming": naming,
    }
    totals: dict[str, int] = {field: 0 for field in _TOKEN_FIELDS}
    unknown: dict[str, int] = {field: 0 for field in _TOKEN_FIELDS}
    category_calls: dict[str, int] = {}
    category_usage: dict[str, dict[str, int]] = {}
    category_unknown: dict[str, dict[str, int]] = {}
    for name, records in categories.items():
        category_calls[name] = len(records)
        category_totals, category_missing = _sum_usage(
            [_decode_usage(record) if isinstance(record, str) else record for record in records]
        )
        category_usage[name] = category_totals
        category_unknown[name] = category_missing
        for field in _TOKEN_FIELDS:
            totals[field] += category_totals[field]
            unknown[field] += category_missing[field]
    return {
        "calls": {
            **category_calls,
            "total": sum(category_calls.values()),
        },
        "token_usage": totals,
        "unknown_token_usage": unknown,
        "by_role": {
            name: {
                "calls": category_calls[name],
                "token_usage": category_usage[name],
                "unknown_token_usage": category_unknown[name],
            }
            for name in categories
        },
    }


__all__ = ["summarize_lineage_usage"]
