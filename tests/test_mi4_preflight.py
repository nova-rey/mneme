from __future__ import annotations

import pytest

from experiments.mi4.qwen_preflight import _attempt_resolution


def test_preflight_attempt_resolution_uses_frozen_id_when_new() -> None:
    assert _attempt_resolution({}, "coord") == (None, "coord")


def test_preflight_attempt_resolution_never_reuses_incomplete_attempt_id() -> None:
    indexed = {"coord": {"status": "REQUEST_DURABLE"}}
    assert _attempt_resolution(indexed, "coord") == (None, "coord_retry1")


def test_preflight_attempt_resolution_reads_complete_recovery_attempt() -> None:
    indexed = {
        "coord": {"status": "REQUEST_DURABLE"},
        "coord_retry1": {"status": "COMPLETE"},
    }
    assert _attempt_resolution(indexed, "coord") == ("coord_retry1", None)


def test_preflight_attempt_resolution_advances_after_incomplete_recovery() -> None:
    indexed = {
        "coord": {"status": "REQUEST_DURABLE"},
        "coord_retry1": {"status": "REQUEST_DURABLE"},
    }
    assert _attempt_resolution(indexed, "coord") == (None, "coord_retry2")


def test_preflight_attempt_resolution_refuses_automatic_retry_after_failure() -> None:
    indexed = {"coord": {"status": "FAILED"}}
    with pytest.raises(RuntimeError, match="requires review"):
        _attempt_resolution(indexed, "coord")
