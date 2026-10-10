from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiments.mi1.c11_execution import build_execution_plan


def test_c11_execution_expands_frozen_matrix_without_changing_treatments() -> None:
    root = Path(__file__).parents[1]
    design_path = (
        root / "docs/receipts/MNEME_Phase_4_MI1_C11_Query_Site_Diagnostic_Freeze_20261010.json"
    )
    selection_path = root / "docs/receipts/MNEME_Phase_4_MI1_C11_Query_Site_Selection_20261010.json"
    design_bytes = design_path.read_bytes()
    selection_bytes = selection_path.read_bytes()
    plan = build_execution_plan(
        json.loads(design_bytes),
        frozen_plan_sha256=hashlib.sha256(design_bytes).hexdigest(),
        site_selection=json.loads(selection_bytes),
        site_selection_sha256=hashlib.sha256(selection_bytes).hexdigest(),
    )
    conditions = {row["condition"] for row in plan["coordinates"]}

    assert len(plan["coordinates"]) == 144
    assert conditions == {
        "no_bank",
        "selected_A",
        "selected_B",
        "old_sparse_A",
        "old_sparse_B",
        "random_A",
        "random_B",
        "visible_A",
        "visible_B",
    }
    for coordinate in plan["coordinates"]:
        request = coordinate["request"]
        assert request["cache_prompt"] is False
        assert request["seed"] == coordinate["seed"]
        assert request["temperature"] == 0.35
        assert request["messages"] == coordinate["messages"]
        assert "harbor" not in json.dumps(request["messages"]).lower()
        assert "tide" not in json.dumps(request["messages"]).lower()
        if coordinate["bank_action"] == "attach":
            source = coordinate["bank_source"]
            assert hashlib.sha256(source.encode()).hexdigest() == coordinate["bank_source_sha256"]
            assert coordinate["bank_config"]["gain"]["logit_bias"] == 0.0
