from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.calibration_c4 import CONDITIONS, build_c4_plan


def test_c4_plan_pairs_prompt_cue_and_bank_factors() -> None:
    plan = build_c4_plan()
    assert plan["coordinate_count"] == 56
    assert len({row["coordinate_id"] for row in plan["coordinates"]}) == 56
    assert tuple(plan["conditions"]) == CONDITIONS
    assert plan["status"] == "FROZEN_BEFORE_CALIBRATION_GENERATION"
    for fixture in {row["metadata"]["fixture_id"] for row in plan["coordinates"]}:
        for seed in plan["seeds"]:
            rows = {
                row["metadata"]["condition"]: row
                for row in plan["coordinates"]
                if row["metadata"]["fixture_id"] == fixture and row["metadata"]["seed"] == seed
            }
            assert set(rows) == set(CONDITIONS)
            assert (
                rows["no_bank"]["request"]["messages"]
                == rows["latent_sparse_no_cue"]["request"]["messages"]
            )
            assert (
                rows["no_bank_memory_cue"]["request"]["messages"]
                == rows["latent_sparse_memory_cue"]["request"]["messages"]
            )
            assert rows["no_bank"]["bank_action"] == "clear"
            assert rows["latent_sparse_no_cue"]["bank_action"] == "attach"
            assert rows["visible"]["bank_action"] == "clear"
            for row in rows.values():
                assert row["request"]["cache_prompt"] is False
                assert row["request"]["seed"] == seed
                assert row["request"]["max_tokens"] == 2048
            for name in ("no_bank", "visible", "latent_sparse_no_cue", "latent_broad_no_cue"):
                assert "memory" not in rows[name]["request"]["messages"][0]["content"].lower()


def test_c4_frozen_manifest_matches_builder_and_c3_parent_hashes() -> None:
    path = Path("docs/receipts/MNEME_Phase_4_MI1_C4_Calibration_Freeze_20261010.json")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    plan = {key: value for key, value in frozen.items() if key != "diagnostic_parent_hashes"}
    assert plan == build_c4_plan()
    assert set(frozen["diagnostic_parent_hashes"]) == {"c3_plan", "c3_receipt"}
