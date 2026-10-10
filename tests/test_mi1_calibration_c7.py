from __future__ import annotations

import json
from pathlib import Path

from experiments.mi1.calibration_c5 import build_c5_plan
from experiments.mi1.calibration_c7 import build_c7_plan


def test_c7_preserves_c5_semantics_banks_and_seeds_with_only_cap_change() -> None:
    c5 = build_c5_plan()
    c7 = build_c7_plan()
    assert c7["server_context_size"] == 8192
    assert c7["request_max_tokens"] == 4096
    assert len(c7["coordinates"]) == len(c5["coordinates"]) == 40
    for old, new in zip(c5["coordinates"], c7["coordinates"], strict=True):
        assert new["coordinate_id"] == old["coordinate_id"].replace("C5-", "C7-", 1)
        assert new["request"]["messages"] == old["request"]["messages"]
        assert new["request"]["seed"] == old["request"]["seed"]
        assert new["request"]["max_tokens"] == 4096
        assert {k: v for k, v in new["request"].items() if k != "max_tokens"} == {
            k: v for k, v in old["request"].items() if k != "max_tokens"
        }
        assert new["bank_source"] == old["bank_source"]
        assert new["bank_config"] == old["bank_config"]
        assert new["expected"] == old["expected"]


def test_c7_frozen_manifest_matches_builder_and_binds_parent_receipts() -> None:
    path = Path("docs/receipts/MNEME_Phase_4_MI1_C7_Calibration_Freeze_20261010.json")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    parent_keys = {
        "c5_plan_sha256",
        "c6_plan_sha256",
        "c6_receipt_sha256",
        "c6_result_sha256",
    }
    plan = {key: value for key, value in frozen.items() if key not in parent_keys}
    assert plan == build_c7_plan()
    assert all(len(frozen[key]) == 64 for key in parent_keys)
