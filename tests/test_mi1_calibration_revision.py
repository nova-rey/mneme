from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.mi1.calibration import (
    CALIBRATION_SYSTEM_REVISION_2,
    build_calibration_framing_revision,
)


def test_framing_revision_changes_only_generic_instruction_and_uses_fresh_ids() -> None:
    parent_path = Path("docs/receipts/MNEME_Phase_4_MI1_Calibration_Correction_20261010.json")
    parent_bytes = parent_path.read_bytes()
    parent = json.loads(parent_bytes)
    revised = build_calibration_framing_revision(
        parent, parent_sha256=hashlib.sha256(parent_bytes).hexdigest()
    )

    assert revised["status"] == "FROZEN_CALIBRATION_REVISION"
    assert len(revised["coordinates"]) == 44
    assert revised["variant_source_plan_sha256"] == parent["parent_plan_sha256"]
    assert all(row["coordinate_id"].startswith("C2-") for row in revised["coordinates"])
    assert all(row["request"]["cache_prompt"] is False for row in revised["coordinates"])
    assert all(
        row["request"]["messages"][0]["content"] == CALIBRATION_SYSTEM_REVISION_2
        for row in revised["coordinates"]
    )

    old = {row["coordinate_id"]: row for row in parent["coordinates"]}
    for row in revised["coordinates"]:
        prior = old[row["metadata"]["parent_coordinate_id"]]
        assert row["request"]["messages"][1] == prior["request"]["messages"][1]
        assert row["bank_source"] == prior["bank_source"]
        assert row["expected"] == prior["expected"]
        assert row["metadata"]["condition"] == prior["metadata"]["condition"]
        assert row["metadata"]["seed"] == prior["metadata"]["seed"]
    assert revised["generation_budget"]["calibration_calls_after_c2"] == 97
