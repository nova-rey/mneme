from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.calibration_c3 import build_c3_plan
from experiments.mi1.calibration_c8 import build_c8_plan


def test_c8_retains_exact_c3_requests_with_new_ids() -> None:
    c3 = build_c3_plan()
    c8 = build_c8_plan()
    assert c8["server_context_size"] == 8192
    assert len(c8["coordinates"]) == len(c3["coordinates"]) == 44
    assert len({row["coordinate_id"] for row in c8["coordinates"]}) == 44
    for old, new in zip(c3["coordinates"], c8["coordinates"], strict=True):
        assert new["coordinate_id"] == old["coordinate_id"].replace("C3-", "C8-", 1)
        assert new["request"] == old["request"]
        assert new["request_sha256"] == old["request_sha256"]
        assert new["bank_source"] == old["bank_source"]
        assert new["bank_config"] == old["bank_config"]
        assert new["expected"] == old["expected"]
        assert new["metadata"]["parent_coordinate_id"] == old["coordinate_id"]


def test_c8_frozen_manifest_matches_builder_and_binds_parents() -> None:
    path = Path("docs/receipts/MNEME_Phase_4_MI1_C8_Calibration_Freeze_20261010.json")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    parent_keys = {"c3_plan_sha256", "c3_result_sha256", "c7_plan_sha256", "c7_result_sha256"}
    plan = {key: value for key, value in frozen.items() if key not in parent_keys}
    assert plan == build_c8_plan()
    assert all(len(frozen[key]) == 64 for key in parent_keys)
