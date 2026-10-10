from __future__ import annotations

from typing import Any

from experiments.mi1.score_calibration import _is_correct, _primary_negative_controls


def _coordinate(answer: str, path: list[str]) -> dict[str, Any]:
    return {"expected": {"answer": answer, "path": path}}


def test_calibration_known_answer_requires_answer_first_and_complete_ordered_path() -> None:
    coord = _coordinate("Deyu", ["Aster", "Beryl", "Corda", "Deyu"])
    assert _is_correct("Deyu\nAster -> Beryl -> Corda -> Deyu", coord)
    assert not _is_correct("Aster -> Beryl -> Corda -> Deyu", coord)
    assert not _is_correct("Deyu\nAster -> Corda -> Beryl -> Deyu", coord)
    assert not _is_correct("Deyu is likely, but I am not certain", coord)


def test_calibration_unknown_requires_unknown_as_the_final_answer() -> None:
    coord = _coordinate("unknown", [])
    assert _is_correct("unknown; the facts do not specify a path", coord)
    assert not _is_correct("I do not know; perhaps Deyu", coord)
    assert not _is_correct("Deyu", coord)


def test_negative_control_rate_excludes_deterministic_replays() -> None:
    rows: list[dict[str, Any]] = [
        {"condition": "no_bank", "duplicate_of": None},
        {"condition": "no_bank", "duplicate_of": "primary-no-bank"},
        {"condition": "latent_irrelevant_sparse_moderate", "duplicate_of": None},
        {"condition": "visible_bank", "duplicate_of": None},
    ]
    assert _primary_negative_controls(rows) == [rows[0], rows[2]]
