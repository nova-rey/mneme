from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.calibration_c5 import CONDITIONS, SYSTEM, build_c5_plan


def test_c5_reuses_c2_answer_contract_and_pairs_bank_with_identical_context() -> None:
    plan = build_c5_plan()
    assert plan["coordinate_count"] == 40
    assert tuple(plan["conditions"]) == CONDITIONS
    assert len({row["coordinate_id"] for row in plan["coordinates"]}) == 40
    for fixture in {row["metadata"]["fixture_id"] for row in plan["coordinates"]}:
        for seed in plan["seeds"]:
            rows = {
                row["metadata"]["condition"]: row
                for row in plan["coordinates"]
                if row["metadata"]["fixture_id"] == fixture
                and row["metadata"]["seed"] == seed
            }
            assert set(rows) == set(CONDITIONS)
            assert rows["no_bank"]["request"]["messages"] == rows[
                "latent_sparse_no_cue"
            ]["request"]["messages"]
            assert rows["no_bank_memory_cue"]["request"]["messages"] == rows[
                "latent_sparse_memory_cue"
            ]["request"]["messages"]
            assert rows["visible"]["request"]["messages"][0]["content"] == SYSTEM
            assert rows["no_bank"]["bank_action"] == "clear"
            assert rows["visible"]["bank_action"] == "clear"
            assert rows["latent_sparse_no_cue"]["bank_action"] == "attach"
            for row in rows.values():
                assert row["request"]["cache_prompt"] is False
                assert row["request"]["seed"] == seed
                assert row["request"]["max_tokens"] == 2048


def test_c5_frozen_manifest_matches_builder_and_parent_hashes() -> None:
    path = Path("docs/receipts/MNEME_Phase_4_MI1_C5_Calibration_Freeze_20261010.json")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    plan = {key: value for key, value in frozen.items() if key != "diagnostic_parent_hashes"}
    assert plan == build_c5_plan()
    assert set(frozen["diagnostic_parent_hashes"]) == {"c4_plan", "c4_receipt", "c2_plan"}
