from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.mi4.coordinates import build_heldout_coordinates, validate_heldout_coordinate

PROTOCOL = json.loads(Path("experiments/mi4/frozen_protocol.json").read_text(encoding="utf-8"))


def test_frozen_heldout_matrix_has_96_cache_disabled_coordinates() -> None:
    rows = build_heldout_coordinates(PROTOCOL)
    assert len(rows) == 96
    assert len({row["coordinate_id"] for row in rows}) == 96
    for row in rows:
        validate_heldout_coordinate(PROTOCOL, row)
        assert row["request"]["cache_prompt"] is False
        assert row["request"]["seed"] in PROTOCOL["heldout"]["seeds"]


def test_latent_prompt_rejects_explicit_bank_word() -> None:
    row = build_heldout_coordinates(PROTOCOL)[0]
    row["bank"] = "A_resilience"
    row["request"]["messages"][1]["content"] += " harbor"
    with pytest.raises(ValueError, match="forbidden target material"):
        validate_heldout_coordinate(PROTOCOL, row)


def test_prompt_contamination_guard_does_not_reject_word_substrings() -> None:
    row = next(
        r for r in build_heldout_coordinates(PROTOCOL) if r["condition"] == "latent_A_resilience"
    )
    row["request"]["messages"][1]["content"] += " Important support may matter."
    validate_heldout_coordinate(PROTOCOL, row)
