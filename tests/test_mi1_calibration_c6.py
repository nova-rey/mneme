from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.calibration_c5 import build_c5_plan
from experiments.mi1.calibration_c6 import build_c6_plan


def test_c6_reuses_c5_requests_and_changes_only_coordinate_metadata() -> None:
    c5 = build_c5_plan()
    c6 = build_c6_plan()
    assert c6["server_context_size"] == 4096
    assert c6["request_matrix_sha256"]
    assert len(c6["coordinates"]) == len(c5["coordinates"]) == 40
    assert len({row["coordinate_id"] for row in c6["coordinates"]}) == 40
    for old, new in zip(c5["coordinates"], c6["coordinates"], strict=True):
        assert new["coordinate_id"] == old["coordinate_id"].replace("C5-", "C6-", 1)
        assert new["request"] == old["request"]
        assert new["request_sha256"] == old["request_sha256"]
        assert new["expected"] == old["expected"]
        assert new["bank_source"] == old["bank_source"]
        assert new["bank_config"] == old["bank_config"]
        assert new["metadata"]["parent_coordinate_id"] == old["coordinate_id"]


def test_c6_frozen_manifest_matches_builder_and_binds_c5_results() -> None:
    path = Path("docs/receipts/MNEME_Phase_4_MI1_C6_Calibration_Freeze_20261010.json")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    parent_keys = {"c5_plan_sha256", "c5_receipt_sha256", "c5_result_sha256"}
    plan = {key: value for key, value in frozen.items() if key not in parent_keys}
    assert plan == build_c6_plan()
    assert all(len(frozen[key]) == 64 for key in parent_keys)
