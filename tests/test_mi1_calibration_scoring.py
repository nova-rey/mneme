from __future__ import annotations

from typing import Any

from experiments.mi1.score_calibration import (
    _determinism_ids,
    _is_correct,
    _primary_negative_controls,
)


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


def test_calibration_revision_two_scores_explicit_answer_and_path_lines() -> None:
    reachable = _coordinate("Deyu", ["Aster", "Beryl", "Corda", "Deyu"])
    unknown = _coordinate("unknown", [])
    assert _is_correct(
        "ANSWER: Deyu\nPATH: Aster -> Beryl -> Corda -> Deyu", reachable
    )
    assert not _is_correct("ANSWER: Deyu\nPATH: A -> B -> C -> D", reachable)
    assert not _is_correct(
        "ANSWER: Deyu\nPATH: Aster -> Beryl -> Corda -> Deyu -> Rudo", reachable
    )
    assert _is_correct("ANSWER: unknown\nPATH: none", unknown)
    assert _is_correct("ANSWER: unknown\nPATH: none if unknown", unknown)
    assert not _is_correct("ANSWER: unknown\nPATH: Aster -> Deyu", unknown)


def test_negative_control_rate_excludes_deterministic_replays() -> None:
    rows: list[dict[str, Any]] = [
        {"condition": "no_bank", "duplicate_of": None},
        {"condition": "no_bank", "duplicate_of": "primary-no-bank"},
        {"condition": "latent_irrelevant_sparse_moderate", "duplicate_of": None},
        {"condition": "visible_bank", "duplicate_of": None},
    ]
    assert _primary_negative_controls(rows) == [rows[0], rows[2]]


def test_determinism_ids_read_from_correction_amendment() -> None:
    ids = {
        "primary_no_bank": "C1-primary",
        "same_server_replay": "C1-replay",
        "base_server_replay": "C1-base",
    }
    assert _determinism_ids({"correction": {"determinism_coordinate_ids": ids}}) == ids
