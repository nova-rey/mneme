from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.calibration_c3 import build_c3_plan
from tools.score_mi1_c3 import _has_full_path, _score


def test_c3_plan_is_complete_matched_and_does_not_cue_primary_conditions() -> None:
    plan = build_c3_plan()
    coordinates = plan["coordinates"]
    assert len(coordinates) == 44
    assert len({row["coordinate_id"] for row in coordinates}) == 44
    assert plan["status"] == "FROZEN_BEFORE_CALIBRATION_GENERATION"
    assert plan["calibration_interpretation"]["visible_controls_total"] == 8
    assert plan["calibration_interpretation"]["cue_conditions_are_not_primary_efficacy_evidence"]

    for row in coordinates:
        request = row["request"]
        assert request["cache_prompt"] is False
        assert request["seed"] in plan["seeds"]
        user = request["messages"][1]["content"].lower()
        condition = row["metadata"]["condition"]
        if condition in {
            "no_bank",
            "latent_sparse_moderate",
            "latent_broad_moderate",
            "latent_broad_strong",
        }:
            assert "rules:" not in user
            assert "memory" not in request["messages"][0]["content"].lower()
        if row["bank_action"] == "attach":
            assert row["bank_source"] not in user
            assert row["bank_source_sha256"]
        else:
            assert row["bank_source"] is None

    for fixture_id in {row["metadata"]["fixture_id"] for row in coordinates}:
        visible = [
            row
            for row in coordinates
            if row["metadata"]["fixture_id"] == fixture_id
            and row["metadata"]["condition"] == "visible"
        ]
        assert len(visible) == 2


def test_c3_scoring_requires_full_labeled_path_and_retains_no_bank_control() -> None:
    path = ["Zepi", "Moru", "Kadi", "Velo", "Runi"]
    assert _has_full_path("YES: Zepi -> Moru -> Kadi -> Velo -> Runi", path)
    assert not _has_full_path("YES: Zepi -> Moru -> Kadi -> Velo", path)
    assert not _has_full_path("YES, Runi is reachable through Zepi", path)
    assert _score("YES: Zepi -> Moru -> Kadi -> Velo -> Runi", {"answer": "Runi", "path": path})[
        "correct"
    ]
    assert _score("Not enough information is given.", {"answer": "unknown", "path": []})["correct"]


def test_frozen_c3_manifest_matches_builder_plus_parent_provenance() -> None:
    path = Path("docs/receipts/MNEME_Phase_4_MI1_C3_Calibration_Freeze_20261010.json")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    generated = build_c3_plan()
    frozen_plan = {key: value for key, value in frozen.items() if key != "diagnostic_parent_hashes"}
    assert frozen_plan == generated
    assert set(frozen["diagnostic_parent_hashes"]) == {
        "c2_plan",
        "c2_receipt",
        "pretest_receipt",
    }
