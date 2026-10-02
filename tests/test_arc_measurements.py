from __future__ import annotations

import copy
import json
import math

import pytest

from mneme.development.episodes import declared_conversation_arcs
from mneme.experiments.arc_measurements import measure_conversation


def residue(*labels, local_prefix=""):
    return {
        "core_concepts": [
            {"key": f"{local_prefix}{i}", "label": label} for i, label in enumerate(labels)
        ],
        "edge_candidates": [
            {"key": f"quote-hash-{local_prefix}", "from": f"{local_prefix}0",
             "to": f"{local_prefix}1", "relationship": "causal"}
        ] if len(labels) > 1 else [],
        "route_candidates": [],
    }


def records(values, *, ordinals=None, topics=None, conversation="test"):
    ordinals = list(range(len(values))) if ordinals is None else ordinals
    topics = ["same"] * len(values) if topics is None else topics
    arcs = declared_conversation_arcs(list(zip(ordinals, topics)), conversation_id=conversation)
    return [
        {"conversation": conversation, "condition": "fixture", "turn": i + 1,
         "ordinal": ordinal, "arc": arcs[ordinal].to_dict(), "residue": value, "field": None}
        for i, (ordinal, value) in enumerate(zip(ordinals, values))
    ]


def field():
    return {
        "accessibility_distribution": [
            {"candidate": "a", "probability": 750000},
            {"candidate": "b", "probability": 250000},
        ],
        "active_concepts": [
            {"key": "x", "contextual_activation": 3},
            {"key": "y", "contextual_activation": 1},
            {"key": "z", "contextual_activation": 0},
        ],
        "distribution_components": [
            {"candidate": "a", "component": "contextual_and_background"},
            {"candidate": "b", "component": "background"},
        ],
        "selected_landing": "a", "active_neighborhood": ["x", "y"],
        "contributions": [{"path": ["x", "y"]}],
    }


def test_replay_is_deterministic_json_safe_and_does_not_mutate_inputs():
    data = records([residue("alpha", "beta")] * 6)
    for item in data:
        item["field"] = field()
    before = copy.deepcopy(data)
    first = measure_conversation(data)
    assert first == measure_conversation(data)
    assert data == before
    json.dumps(first, allow_nan=False)
    first[0]["concept_labels"].append("output mutation")
    assert data == before


def test_age_uses_membership_not_ordinal_subtraction_and_resets_on_declared_pivot():
    data = records([residue("a")] * 5, ordinals=[2, 5, 9, 12, 20],
                   topics=["same", "same", "same", "next", "next"])
    rows = measure_conversation(data)
    assert [row["arc_age"] for row in rows] == [1, 2, 3, 1, 2]
    assert [row["ordinal_span"] for row in rows] == [1, 4, 8, 1, 9]
    assert [row["arc_pivot"] for row in rows] == [False, False, False, True, False]
    assert rows[3]["concept_arc_novelty"] is None
    assert rows[3]["concept_adjacent_movement"] is None


def test_explicit_tracker_membership_ids_and_interleaved_conversations():
    a = records([residue("a")] * 2)
    for i, item in enumerate(a):
        item["arc"]["turn_ids"] = ["custom-a", "custom-b"]
        item["accepted_turn_id"] = ["custom-a", "custom-b"][i]
    b = records([residue("b")] * 2, conversation="other")
    rows = measure_conversation([a[0], b[0], a[1], b[1]])
    assert [row["arc_age"] for row in rows] == [1, 1, 2, 2]


def test_productive_and_repeating_synthetic_structure_and_frozen_composites():
    productive = records([residue("problem", f"evidence {i}") for i in range(7)])
    repeated = records([residue("problem", "evidence")] * 7)
    for item in productive + repeated:
        item["field"] = field()
    f, s = measure_conversation(productive), measure_conversation(repeated)
    assert f[0]["concept_arc_novelty"] is None
    assert f[0]["concept_new_count"] is None
    assert [row["warmup"] for row in f[:4]] == [True, True, False, False]
    assert all(row["c1_concept_persistence_proxy"] is None for row in f[:3])
    assert f[-1]["concept_rolling_new_per_turn"] == 1
    assert f[-1]["relationship_rolling_new_per_turn"] == 1
    assert s[-1]["concept_rolling_new_per_turn"] == 0
    assert f[-1]["concept_rolling_novelty_mean"] == 0.5
    assert f[-1]["relationship_rolling_novelty_mean"] == 1
    assert f[-1]["c1_concept_persistence_proxy"] == 0.5
    assert f[-1]["c2_structure_persistence_proxy"] == 0.25
    assert f[-1]["c3_context_persistence_proxy"] == 0.25 * 0.625
    assert s[-1]["c2_structure_persistence_proxy"] == 1
    assert s[-1]["concept_rolling_saturation"] == pytest.approx(2 / 3)
    assert f[-1]["concept_rolling_saturation"] == pytest.approx(1 / 3)
    assert s[3]["c2_structure_persistence_proxy"] == 0.6


def test_local_ids_quote_hash_and_label_normalization_do_not_create_novelty():
    data = records([residue("CAFÉ", " Beta ", local_prefix="old"),
                    residue("cafe\u0301", "beta", local_prefix="new")])
    rows = measure_conversation(data)
    assert rows[1]["concept_count"] == 2
    assert rows[1]["concept_arc_novelty"] == 0
    assert rows[1]["relationship_arc_novelty"] == 0
    assert rows[1]["relationship_adjacent_movement"] == 0


@pytest.mark.parametrize("invalid", [None, {}, {"core_concepts": None},
                                       {"core_concepts": [None]},
                                       {"core_concepts": [{"key": "x", "label": ""}]}])
def test_missing_or_malformed_semantics_are_unavailable(invalid):
    row = measure_conversation(records([invalid]))[0]
    assert row["concept_count"] is None
    assert row["relationship_count"] is None
    assert row["concept_rolling_saturation"] is None
    assert row["c1_concept_persistence_proxy"] is None


def test_empty_and_partial_semantics_are_not_fabricated_novelty():
    empty = measure_conversation(records([residue()] * 6))[-1]
    assert empty["concept_count"] == 0
    assert empty["concept_window_coverage"] == 1
    assert empty["concept_new_count"] == 0
    assert empty["concept_rolling_new_per_turn"] == 0
    assert empty["concept_window_novelty"] is None
    assert empty["concept_rolling_saturation"] is None
    assert empty["c1_concept_persistence_proxy"] is None
    data = records([residue("a", "b")] * 4)
    data[-1]["residue"] = {"core_concepts": [{"key": "a", "label": "a"}]}
    row = measure_conversation(data)[-1]
    assert row["concept_count"] == 1
    assert row["relationship_count"] is None
    assert row["c2_structure_persistence_proxy"] is None


def test_missing_semantics_do_not_bridge_gaps_and_cumulative_claims_stay_unknown():
    values = [residue("a", "b")] * 10
    values[2] = None
    rows = measure_conversation(records(values))
    assert rows[3]["concept_adjacent_movement"] is None
    assert rows[3]["concept_window_novelty"] is None
    assert rows[3]["concept_window_coverage"] == pytest.approx(2 / 3)
    assert all(row["concept_arc_novelty"] is None for row in rows[3:])
    assert rows[-1]["concept_window_novelty"] == 0
    assert rows[-1]["c2_structure_persistence_proxy"] == 1
    assert rows[-1]["concept_rolling_new_per_turn"] is None


def test_missing_accepted_members_do_not_become_adjacent_or_complete_windows():
    data = records([residue("a", "b")] * 7)
    rows = measure_conversation(data[:2] + data[3:])
    assert rows[2]["arc_age"] == 4
    assert rows[2]["concept_adjacent_movement"] is None
    assert rows[2]["concept_rolling_saturation"] is None
    assert all(not row["membership_prefix_complete"] for row in rows[2:])
    assert all(row["concept_arc_novelty"] is None for row in rows[2:])


def test_field_distribution_context_and_reuse_statistics():
    data = records([None] * 4)
    for item in data:
        item["field"] = field()
    row = measure_conversation(data)[-1]
    h = -0.75 * math.log(0.75) - 0.25 * math.log(0.25)
    assert row["saa_entropy_nats"] == pytest.approx(h)
    assert row["saa_effective_candidate_count"] == pytest.approx(math.exp(h))
    assert row["saa_max_mass"] == 0.75
    assert row["contextual_hhi"] == 0.625
    assert row["background_candidate_count"] == 1
    assert row["background_mass"] == 0.25
    assert row["background_unselected_count"] == 1
    assert row["candidates_adjacent_jaccard"] == 1
    assert row["neighborhood_adjacent_jaccard"] == 1
    assert row["routes_adjacent_jaccard"] == 1
    assert row["selected_landing_rolling_repeat"] == pytest.approx(2 / 3)


@pytest.mark.parametrize("distribution", [None, [], [{"candidate": "a", "probability": 0}],
                                           [{"candidate": "a", "probability": float("nan")}],
                                           [{"candidate": "a", "probability": -1}]])
def test_unavailable_distributions_are_not_singleton_or_zero_entropy(distribution):
    data = records([None])
    data[0]["field"] = {"accessibility_distribution": distribution}
    row = measure_conversation(data)[0]
    assert row["saa_candidate_count"] is None
    assert row["saa_entropy_nats"] is None
    assert row["contextual_hhi"] is None


def test_singleton_is_valid_and_zero_context_is_unavailable():
    data = records([None])
    data[0]["field"] = {"accessibility_distribution": [{"candidate": "a", "probability": 7}],
                        "active_concepts": [{"contextual_activation": 0}]}
    row = measure_conversation(data)[0]
    assert row["saa_entropy_nats"] == 0
    assert row["saa_effective_candidate_count"] == 1
    assert row["contextual_hhi"] is None
    assert row["background_mass"] is None
    assert row["route_count"] is None


@pytest.mark.parametrize("mutation", ["order", "membership", "bounds", "changed_arc"])
def test_identity_errors_fail_closed(mutation):
    data = records([None] * 3)
    if mutation == "order":
        data[1]["ordinal"] = data[0]["ordinal"]
    elif mutation == "membership":
        data[1]["accepted_turn_id"] = "not-a-member"
    elif mutation == "bounds":
        data[1]["ordinal"] = 999
    else:
        data[1]["arc"]["topic_keys"] = ["changed"]
    with pytest.raises(ValueError):
        measure_conversation(data)


def test_offline_measurements_between_real_controller_turns_preserve_calls_and_database(tmp_path):
    from mneme.controller import ResponseController, TurnIntent
    from mneme.hosts import FakeHost
    from mneme.state.contracts import StoragePermissions
    from mneme.state.storage import SQLiteStore

    class CountingHost(FakeHost):
        def __init__(self):
            super().__init__()
            self.requests = []

        def generate(self, request):
            self.requests.append(copy.deepcopy(request.generation_material()))
            return super().generate(request)

    outcomes = []
    for enabled in (False, True):
        with SQLiteStore(tmp_path / f"{enabled}.sqlite3") as store:
            host = CountingHost()
            instance = store.create_root(
                permissions=StoragePermissions(True, True, True, True, True, True),
                host_binding=host.fingerprint().to_dict(),
            )
            controller = ResponseController(store, instance, host)
            data = records([None] * 4)
            responses = []
            for i in range(4):
                prepared = controller.prepare(TurnIntent(f"Evidence round {i}", memory="graph"))
                result = controller.execute(prepared)
                responses.append(result.generation.content)
                data[i]["field"] = (
                    None if prepared.field_result is None else prepared.field_result.to_dict()
                )
                before = list(store.connection.iterdump())
                calls = copy.deepcopy(host.requests)
                if enabled:
                    measure_conversation(data[:i + 1])
                assert list(store.connection.iterdump()) == before
                assert host.requests == calls
            outcomes.append((host.requests, responses, store.current()["current_revision"]))
    assert outcomes[0] == outcomes[1]
    assert len(outcomes[0][0]) == 4
