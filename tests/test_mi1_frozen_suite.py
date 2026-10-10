"""Guard the immutable MI1 synthetic evaluation design."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "experiments" / "mi1" / "fixtures"
SPEC = importlib.util.spec_from_file_location("mi1_freeze_suite", FIXTURES / "freeze_suite.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_frozen_suite_has_predeclared_bounded_coordinate_count() -> None:
    suite = json.loads((FIXTURES / "mi1_frozen_suite.json").read_text(encoding="utf-8"))
    assert suite["test_a"]["generation_count"] == 12 * 2 * 6 == 144
    assert suite["test_b"]["generation_count"] == 3 * 3 * 2 * 6 == 108
    assert suite["test_c"]["generation_count"] == 16
    assert suite["untouched_confirmation"]["generation_count"] == 48
    assert suite["generation_budget"]["total_preplanned"] == 436
    assert (
        suite["generation_budget"]["total_preplanned"]
        < suite["generation_budget"]["authorized_hard_max"]
    )


def test_counterfactual_banks_use_same_labels_and_switch_answer() -> None:
    suite = json.loads((FIXTURES / "mi1_frozen_suite.json").read_text(encoding="utf-8"))
    fixtures = suite["test_a"]["fixtures"]
    assert len(fixtures) == 12
    for fixture in fixtures:
        assert fixture["bank_A"]["expected_answer"] != fixture["bank_B"]["expected_answer"]
        assert set(fixture["bank_A"]["statements"]) != set(fixture["bank_B"]["statements"])
        assert len(fixture["nodes"]) == 6
        assert fixture["checks"]["same_nodes_different_edges"]
        assert fixture["checks"]["includes_reverse_direction_decoy"]
        assert fixture["checks"]["includes_inactive_exception"]
        assert fixture["expected_by_condition"]["visible_A"] == fixture["bank_A"]["expected_answer"]
        assert fixture["expected_by_condition"]["visible_B"] == fixture["bank_B"]["expected_answer"]
        assert fixture["expected_by_condition"]["no_bank"] == "unknown"
    assert {
        fixture["bank_A"]["expected_answer"] == fixture["nodes"][3] for fixture in fixtures
    } == {True, False}


def reachable(bank: dict[str, object], starts: set[str]) -> set[str]:
    edges = bank["activation_edges"]
    lock = bank["lock"]
    active = set(starts)
    while True:
        before = set(active)
        for source, target in edges:
            denied = (
                target == lock["node"]
                and lock["while_active"] in active
                and lock["unless_active"] not in active
            )
            if source in active and not denied:
                active.add(target)
        if active == before:
            return active


def test_answer_key_matches_directed_prerequisite_and_exception_rules() -> None:
    suite = json.loads((FIXTURES / "mi1_frozen_suite.json").read_text(encoding="utf-8"))
    for fixture in suite["test_a"]["fixtures"]:
        for bank_name in ("bank_A", "bank_B"):
            bank = fixture[bank_name]
            active = reachable(bank, set(fixture["initial_active"]))
            targets = set(fixture["nodes"][3:5])
            assert active.intersection(targets) == {bank["expected_answer"]}


def test_latent_conditions_use_identical_requests_without_bank_text() -> None:
    suite = json.loads((FIXTURES / "mi1_frozen_suite.json").read_text(encoding="utf-8"))
    for fixture in suite["test_a"]["fixtures"]:
        request = fixture["recipient_request"]
        assert (
            suite["test_a"]["condition_wrappers"]["latent_A"].format(recipient_request=request)
            == request
        )
        assert (
            suite["test_a"]["condition_wrappers"]["latent_B"].format(recipient_request=request)
            == request
        )
        assert (
            suite["test_a"]["condition_wrappers"]["latent_irrelevant"].format(
                recipient_request=request
            )
            == request
        )
        assert " ".join(fixture["bank_A"]["statements"]) not in request
        assert " ".join(fixture["bank_B"]["statements"]) not in request
    for pack in suite["test_b"]["packs"]:
        for task in pack["tasks"]:
            request = suite["test_b"]["condition_wrappers"]["latent_correct"].format(
                task_prompt=task["prompt"]
            )
            assert request == task["prompt"]
            assert " ".join(pack["statements"]) not in request


def test_harbor_and_other_pack_tasks_do_not_name_their_concept() -> None:
    suite = json.loads((FIXTURES / "mi1_frozen_suite.json").read_text(encoding="utf-8"))
    forbidden_by_pack = {
        "B-HARBOR": ("harbor", "tide", "dock", "maritime", "port"),
        "B-STAGED-CHANGE": ("succession", "pioneer", "ecosystem", "mature stage"),
        "B-LAYERED-RESILIENCE": ("immune", "antibody", "pathogen", "infection"),
    }
    for pack in suite["test_b"]["packs"]:
        for task in pack["tasks"]:
            lowered = task["prompt"].lower()
            assert not any(
                re.search(rf"\b{re.escape(token)}\b", lowered)
                for token in forbidden_by_pack[pack["pack_id"]]
            )
    for pack_id, tasks in suite["untouched_confirmation"]["tasks_by_pack"].items():
        for task in tasks:
            lowered = task["prompt"].lower()
            assert not any(
                re.search(rf"\b{re.escape(token)}\b", lowered)
                for token in forbidden_by_pack[pack_id]
            )


def test_calibration_is_separate_and_seeded() -> None:
    suite = json.loads((FIXTURES / "mi1_frozen_suite.json").read_text(encoding="utf-8"))
    assert suite["calibration"]["separate_from_scored"] is True
    assert suite["test_a"]["seeds"] == [34001, 34019]
    assert suite["test_b"]["seeds"] == [34001, 34019]
    assert suite["cache_prompt"] is False


def test_update_and_new_bank_coordinates_are_fully_frozen() -> None:
    suite = json.loads((FIXTURES / "mi1_frozen_suite.json").read_text(encoding="utf-8"))
    test_c = suite["test_c"]
    exchange = test_c["ongoing_exchange"]
    assert exchange["fixture_id"] == "A02"
    assert exchange["turns"] == 2
    assert exchange["turn1_user_prompt"] == suite["test_a"]["fixtures"][1]["recipient_request"]
    assert exchange["turn2_user_prompt"]
    new_bank = test_c["new_bank"]
    assert len(new_bank["source_text"]) == 4
    assert len(new_bank["recipient_contexts"]) == 2
    assert set(new_bank["expected_path"]) <= {"Daxi", "Bero", "Cuni", "Efo", "Gaxi"}
    for recipient in new_bank["recipient_contexts"]:
        assert not any(statement in recipient for statement in new_bank["source_text"])
