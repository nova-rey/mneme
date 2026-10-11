from __future__ import annotations

import hashlib
import json

from experiments.mi1.c13_calibration import CONDITIONS, build_c13_plan


def _parent() -> dict[str, object]:
    return {
        "status": "FROZEN_BEFORE_CALIBRATION_GENERATION",
        "sha256": "unused",
        "site_selection_sha256": "site-hash",
        "model": {"name": "model"},
        "generation_config": {"cache_prompt": False},
    }


def test_c13_freezes_expected_calibration_and_holdout_design() -> None:
    raw = json.dumps(_parent(), sort_keys=True).encode()
    plan = build_c13_plan(_parent(), c12_plan_sha256=hashlib.sha256(raw).hexdigest())
    assert len(CONDITIONS) == 9
    assert plan["call_count"] == 72
    assert plan["parent_c12_plan_sha256"] == hashlib.sha256(raw).hexdigest()
    assert plan["heldout_fixture_ids_frozen_but_not_run"] == [
        f"A{number}" for number in range(17, 25)
    ]
    assert len(plan["confirmation_coordinates_frozen_but_not_run"]) == 144
    assert plan["confirmation_call_count_if_one_routing_mode_is_selected"] == 112


def test_c13_latent_targets_never_leak_bank_facts_into_prompt() -> None:
    plan = build_c13_plan(_parent(), c12_plan_sha256="parent")
    for coordinate in plan["coordinates"]:
        condition = coordinate["condition"]
        messages = coordinate["request"]["messages"]
        serialized_prompt = json.dumps(messages)
        if condition.startswith("latent_"):
            assert coordinate["bank_source"] not in serialized_prompt
        if coordinate["bank_config"]["selector"] == "all_heads":
            assert coordinate["condition"] in {
                "latent_A_broad_assertive_fourfold",
                "latent_B_broad_assertive_fourfold",
                "latent_irrelevant_broad_assertive_fourfold",
            }


def test_c13_matched_site_breadth_pairs_hold_cue_and_task_fixed() -> None:
    plan = build_c13_plan(_parent(), c12_plan_sha256="parent")
    rows = {row["coordinate_id"]: row for row in plan["coordinates"]}
    narrow = rows["C13-A13-latent_A_selected_assertive_fourfold-34201"]
    broad = rows["C13-A13-latent_A_broad_assertive_fourfold-34201"]
    assert narrow["request"] == broad["request"]
    assert narrow["bank_source"] == broad["bank_source"]
    assert narrow["bank_config"]["gain"] == broad["bank_config"]["gain"]
    assert narrow["bank_config"]["selector"] == "selected_A"
    assert broad["bank_config"]["selector"] == "all_heads"


def test_c13_heldout_candidate_coordinates_are_frozen_without_leaking_facts() -> None:
    plan = build_c13_plan(_parent(), c12_plan_sha256="parent")
    for coordinate in plan["confirmation_coordinates_frozen_but_not_run"]:
        if coordinate["condition"].startswith("latent_"):
            prompt = json.dumps(coordinate["request"]["messages"])
            assert coordinate["bank_source"] not in prompt
