"""Offline checks for resumable MI1 scored-suite conversation construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from experiments.mi1.coordinates import build_scored_coordinates
from tools.run_mi1_test_abc import ongoing_messages


@pytest.fixture
def suite() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(Path("experiments/mi1/fixtures/mi1_frozen_suite.json").read_text()),
    )


def test_ongoing_test_c_uses_durable_final_answer_only(
    suite: dict[str, Any], tmp_path: Path
) -> None:
    coordinate = next(
        row
        for row in build_scored_coordinates(suite)
        if row["coordinate_id"] == "C-ONGOING-A02-turn-2"
    )
    attempt_id = coordinate["depends_on_attempt"]
    attempts = tmp_path / "attempts"
    attempts.mkdir()
    payload = {
        "attempt_id": attempt_id,
        "status": "COMPLETE",
        "payload": {
            "choices": [
                {
                    "message": {
                        "content": "The visible turn-one answer.",
                        "reasoning_content": "Private reasoning must not enter the conversation.",
                    }
                }
            ]
        },
    }
    (attempts / f"{attempt_id}.complete.json").write_text(json.dumps(payload))

    messages = ongoing_messages(coordinate, suite, tmp_path)

    assert messages[2] == {"role": "assistant", "content": "The visible turn-one answer."}
    assert len(messages) == 4
    assert "Private reasoning" not in json.dumps(messages)


def test_ongoing_test_c_rejects_missing_or_wrong_dependency(
    suite: dict[str, Any], tmp_path: Path
) -> None:
    coordinate = next(
        row
        for row in build_scored_coordinates(suite)
        if row["coordinate_id"] == "C-ONGOING-A02-turn-2"
    )
    with pytest.raises(ValueError, match="unexpected dynamic Test-C dependency"):
        ongoing_messages({**coordinate, "depends_on_attempt": "other"}, suite, tmp_path)
