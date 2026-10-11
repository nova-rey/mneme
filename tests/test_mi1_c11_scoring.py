from __future__ import annotations

from experiments.mi1.c11_scoring import _parse_answer, _path_supported


def test_c11_answer_parser_accepts_frozen_label_forms() -> None:
    assert _parse_answer("unknown", ["Davo", "Kiri"]) == "unknown"
    assert _parse_answer("Davo.", ["Davo", "Kiri"]) == "Davo"
    assert _parse_answer("**Label:** Kiri", ["Davo", "Kiri"]) == "Kiri"
    assert _parse_answer("The active label is **Davo**.", ["Davo", "Kiri"]) == "Davo"
    assert _parse_answer("**Kiri** can become active.", ["Davo", "Kiri"]) == "Kiri"


def test_c11_path_parser_handles_plain_and_latex_arrows() -> None:
    path = ["Yaro", "Ceni", "Fuma", "Davo"]
    assert _path_supported("Yaro -> Ceni -> Fuma -> Davo", path)
    assert _path_supported(r"Yaro $\rightarrow$ Ceni $\rightarrow$ Fuma $\rightarrow$ Davo", path)
    assert not _path_supported("Davo", path)
