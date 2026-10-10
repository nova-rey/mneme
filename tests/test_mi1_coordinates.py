from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from experiments.mi1.coordinates import build_ongoing_turn_two_messages, build_scored_coordinates


def _suite() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "experiments/mi1/fixtures/mi1_frozen_suite.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_expansion_has_exact_stable_count_and_unique_ids() -> None:
    coordinates = build_scored_coordinates(_suite())
    assert len(coordinates) == 268
    assert len({row["coordinate_id"] for row in coordinates}) == 268
    assert sum(row["suite"] == "test_a" for row in coordinates) == 144
    assert sum(row["suite"] == "test_b" for row in coordinates) == 108
    assert sum(row["suite"].startswith("test_c") for row in coordinates) == 16


def test_latent_test_a_pairs_have_identical_prompt_and_separate_bank_source() -> None:
    coordinates = build_scored_coordinates(_suite())
    by_id = {row["coordinate_id"]: row for row in coordinates}
    first_seed = _suite()["test_a"]["seeds"][0]
    latent_a = by_id[f"A-A01-latent_A-{first_seed}"]
    latent_b = by_id[f"A-A01-latent_B-{first_seed}"]
    irrelevant = by_id[f"A-A01-latent_irrelevant-{first_seed}"]
    assert latent_a["request"]["messages"] == latent_b["request"]["messages"]
    assert latent_a["request"]["messages"] == irrelevant["request"]["messages"]
    assert latent_a["bank_source"] != latent_b["bank_source"]
    assert latent_a["bank_source"] not in json.dumps(latent_a["request"]["messages"])
    assert latent_a["bank_action"] == "attach"


def test_test_c_orders_removal_restore_and_marks_ongoing_dependency() -> None:
    coordinates = build_scored_coordinates(_suite())
    fresh = [row for row in coordinates if row["metadata"].get("mode") == "fresh_context"]
    assert [row["metadata"]["condition"] for row in fresh[:4]] == [
        "bank_A",
        "bank_B",
        "disabled",
        "restored_A",
    ]
    ongoing = [row for row in coordinates if row["metadata"].get("mode") == "ongoing"]
    assert len(ongoing) == 2
    assert ongoing[1]["depends_on_attempt"] == ongoing[0]["coordinate_id"]
    assert ongoing[1]["request"]["messages"] is None


def test_test_c_ongoing_turn_two_uses_durable_visible_answer_only() -> None:
    suite = _suite()
    messages = build_ongoing_turn_two_messages(suite, "Feli via Neri -> Vako -> Feli.")
    assert [row["role"] for row in messages] == ["system", "user", "assistant", "user"]
    assert messages[2]["content"] == "Feli via Neri -> Vako -> Feli."
    exchange = suite["test_c"]["ongoing_exchange"]
    assert messages[1]["content"] == exchange["turn1_user_prompt"]
    assert messages[3]["content"] == exchange["turn2_user_prompt"]
    assert "reasoning" not in messages[2]["content"].lower()
