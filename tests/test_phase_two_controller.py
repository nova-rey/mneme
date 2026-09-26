from __future__ import annotations

import json
import uuid

import pytest

from mneme.contracts import GenerationRequest
from mneme.controller import ControllerError, ResponseController, TurnIntent, _phrase
from mneme.development import ConsequenceAssessment, Observation
from mneme.hosts import FakeHost
from mneme.memory import InterpretationPublisher, validate_residue
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


def _graph_store(tmp_path, *, learning: bool = False):
    store = SQLiteStore(tmp_path / "subject.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(True, True, True, True, True, learning),
        host_binding=FakeHost().fingerprint().to_dict(),
    )
    host = FakeHost()
    operation = ContinuityService(store, instance, host).prepare_episode(
        GenerationRequest(
            ({"role": "user", "content": "alpha guides bridge and bridge guides omega"},)
        )
    )
    ContinuityService(store, instance, host).generate_operation(operation.operation_id)
    ContinuityService(store, instance, host).accept_episode(operation.operation_id)
    residue = validate_residue(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "alpha",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 5}],
                    "confidence": 0.9,
                },
                {
                    "key": "b",
                    "label": "bridge",
                    "source_spans": [{"source_slot": "s0", "start": 13, "end": 19}],
                    "confidence": 0.9,
                },
                {
                    "key": "c",
                    "label": "omega",
                    "source_spans": [{"source_slot": "s0", "start": 38, "end": 43}],
                    "confidence": 0.9,
                },
            ],
            "edge_candidates": [
                {
                    "key": "e1",
                    "from": "a",
                    "to": "b",
                    "relationship": "causal",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 19}],
                    "confidence": 0.9,
                },
                {
                    "key": "e2",
                    "from": "b",
                    "to": "c",
                    "relationship": "causal",
                    "source_spans": [{"source_slot": "s0", "start": 13, "end": 43}],
                    "confidence": 0.9,
                },
            ],
        },
        {"s0": "alpha guides bridge and bridge guides omega"},
    )
    publisher = InterpretationPublisher(store, instance)
    publisher.publish(publisher.prepare(operation.episode_id), residue)
    return store, instance


def test_route_query_reachability_accepts_conservative_descriptor_paraphrase():
    assert _phrase("drip irrigation", "Drip Irrigation")
    assert _phrase("drip method", "Drip Irrigation")
    assert _phrase("drip system", "Drip Irrigation")
    assert not _phrase("drip coffee", "Drip Irrigation")
    assert not _phrase("unrelated concept", "Drip Irrigation")


def test_learned_route_reachability_constructs_treatment_payload(tmp_path):
    """A reachable learned route must result in an applied memory payload."""

    store, instance = _graph_store(tmp_path, learning=True)
    source = "alpha guides bridge and bridge guides omega"
    residue = validate_residue(
        {
            "core_concepts": [
                {
                    "key": "a",
                    "label": "alpha",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 5}],
                    "confidence": 0.9,
                },
                {
                    "key": "b",
                    "label": "bridge",
                    "source_spans": [{"source_slot": "s0", "start": 13, "end": 19}],
                    "confidence": 0.9,
                },
                {
                    "key": "c",
                    "label": "omega",
                    "source_spans": [{"source_slot": "s0", "start": 38, "end": 43}],
                    "confidence": 0.9,
                },
            ],
            "edge_candidates": [
                {
                    "key": "e1",
                    "from": "a",
                    "to": "b",
                    "relationship": "causal",
                    "source_spans": [{"source_slot": "s0", "start": 0, "end": 19}],
                    "confidence": 0.9,
                },
                {
                    "key": "e2",
                    "from": "b",
                    "to": "c",
                    "relationship": "causal",
                    "source_spans": [{"source_slot": "s0", "start": 13, "end": 43}],
                    "confidence": 0.9,
                },
            ],
        },
        {"s0": source},
    )
    host = FakeHost()
    continuity = ContinuityService(store, instance, host)
    operation = continuity.prepare_episode(
        GenerationRequest(({"role": "user", "content": source},)),
        operation_id="route-preflight-generation",
    )
    continuity.generate_operation(operation.operation_id)
    continuity.accept_episode(operation.operation_id)
    publisher = InterpretationPublisher(store, instance)
    publisher.publish(
        publisher.prepare(operation.episode_id, operation_id="route-preflight-interpretation"),
        residue,
        observations=(Observation(target_key="e1", occurrence_key="preflight"),),
        development_operation_id="route-preflight-development",
        opportunity=1,
    )

    with store:
        prepared = ResponseController(store, instance, host).prepare(
            TurnIntent("alpha method omega", memory="graph", selection_policy="learned-v1")
        )
    assert prepared.selected
    assert prepared.applied == prepared.selected
    assert any(route.query_coverage >= 1 for route in prepared.selected)
    assert "Memory data:" in (prepared.request.system or "")


def test_controller_discovers_bounded_path_without_route_candidate(tmp_path):
    store, instance = _graph_store(tmp_path)
    with store:
        prepared = ResponseController(store, instance, FakeHost()).prepare(
            TurnIntent("alpha omega", memory="graph")
        )
        paths = [route for route in prepared.considered if route.edge_count == 2]
        assert len(paths) == 1
        assert paths[0].edge_keys == ("e1", "e2")
        assert paths[0] in prepared.selected


def test_controller_preserves_declared_system_and_records_actual_payload(tmp_path):
    store, instance = _graph_store(tmp_path)
    with store:
        prepared = ResponseController(store, instance, FakeHost()).prepare(
            TurnIntent("alpha omega", memory="graph", system="Follow the task exactly.")
        )
        assert prepared.request.system is not None
        assert prepared.request.system.count("Follow the task exactly.") == 1
        assert prepared.applied == prepared.selected
        result = ResponseController(store, instance, FakeHost()).execute(prepared)
        trace = store.connection.execute(
            "SELECT applied_json,request_json FROM turn_traces WHERE operation_id=?",
            (result.operation.operation_id,),
        ).fetchone()
        assert json.loads(trace[0]) == [item.to_dict() for item in prepared.applied]
        assert json.loads(trace[1])["system"].count("Follow the task exactly.") == 1


def test_learned_policy_requires_explicit_learning_permission(tmp_path):
    store, instance = _graph_store(tmp_path)
    with store:
        with pytest.raises(ControllerError, match="learning permission"):
            ResponseController(store, instance, FakeHost()).prepare(
                TurnIntent("alpha omega", memory="graph", selection_policy="learned-v1")
            )


def test_learned_selection_loads_persisted_route_restraint(tmp_path):
    store, instance = _graph_store(tmp_path, learning=True)
    with store:
        snapshot = store.connection.execute(
            "SELECT graph_snapshot_id FROM manifests WHERE manifest_id=?",
            (store.current()["current_manifest_id"],),
        ).fetchone()[0]
        route_key = store.connection.execute(
            "SELECT route_key FROM graph_routes WHERE snapshot_id=? "
            "AND json_array_length(edge_keys_json)=2 ORDER BY route_key LIMIT 1",
            (snapshot,),
        ).fetchone()[0]
        continuity = ContinuityService(store, instance, FakeHost())
        operation = continuity.prepare_episode(
            GenerationRequest(({"role": "user", "content": "recorded consequence"},)),
            operation_id="restraint-generation",
        )
        continuity.generate_operation(operation.operation_id)
        continuity.accept_episode(operation.operation_id)
        empty = validate_residue({}, {"s0": "recorded consequence"})
        publisher = InterpretationPublisher(store, instance)
        publisher.publish(
            publisher.prepare(operation.episode_id, operation_id="restraint-interpretation"),
            empty,
            development_operation_id="restraint-development",
            opportunity=2,
            consequences=tuple(
                ConsequenceAssessment(
                    operation_id=f"restraint-assessment-{index}",
                    route_key=str(route_key),
                    direction=-1,
                    exposure_id=f"restraint-exposure-{index}",
                    opportunity=2,
                )
                for index in range(5)
            ),
        )
        prepared = ResponseController(store, instance, FakeHost()).prepare(
            TurnIntent("alpha omega", memory="graph", selection_policy="learned-v1")
        )
        restrained = next(route for route in prepared.considered if route.route_key == route_key)
        assert restrained not in prepared.selected
        route_payload = store.connection.execute(
            "SELECT configuration_json FROM learner_snapshots "
            "ORDER BY opportunity DESC LIMIT 1"
        ).fetchone()[0]
        assert json.loads(route_payload)["state"]["routes"][f"{route_key}:general"][
            "consequence"
        ] == -250_000


def test_collision_safe_graph_edge_keys_reuse_local_learner_binding(tmp_path):
    store, instance = _graph_store(tmp_path, learning=True)
    with store:
        snapshot = store.connection.execute(
            "SELECT graph_snapshot_id FROM manifests WHERE manifest_id=?",
            (store.current()["current_manifest_id"],),
        ).fetchone()[0]
        interpretation_id = store.connection.execute(
            "SELECT interpretation_id FROM interpretations LIMIT 1"
        ).fetchone()[0]
        canonical = "edge:stable"
        store.connection.execute(
            "INSERT INTO semantic_bindings VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                instance,
                interpretation_id,
                None,
                "e1",
                canonical,
                "causal",
                "test",
                1,
                json.dumps({"local_key": "e1"}),
                "2026-01-01T00:00:00Z",
            ),
        )
        store.connection.execute(
            "INSERT INTO graph_edges VALUES(?,?,?,?,?,?,?,?)",
            (
                snapshot,
                "e1~collision",
                "alpha",
                "bridge",
                "causal",
                "asserted",
                json.dumps({"local_key": "e1"}),
                json.dumps({}),
            ),
        )
        pin = ResponseController(store, instance, FakeHost())._pin()
        mapping = ResponseController(store, instance, FakeHost())._learner_key_map(pin)
        assert mapping["e1"] == canonical
        assert mapping["e1~collision"] == canonical


def test_route_bound_deduplicates_collision_variants_before_discovery(tmp_path):
    store, instance = _graph_store(tmp_path, learning=True)
    with store:
        snapshot = store.connection.execute(
            "SELECT graph_snapshot_id FROM manifests WHERE manifest_id=?",
            (store.current()["current_manifest_id"],),
        ).fetchone()[0]
        interpretation_id = store.connection.execute(
            "SELECT interpretation_id FROM interpretations LIMIT 1"
        ).fetchone()[0]
        store.connection.execute(
            "INSERT INTO graph_concepts VALUES(?,?,?,?,?,?,?,?)",
            (snapshot, "d", "delta", "unknown", "concept", 1.0, 0.0, None),
        )
        store.connection.execute(
            "INSERT INTO graph_edges VALUES(?,?,?,?,?,?,?,?)",
            (
                snapshot,
                "e3",
                "b",
                "d",
                "causal",
                "asserted",
                json.dumps({}),
                json.dumps([{"source_slot": "s0"}]),
            ),
        )
        store.connection.execute(
            "INSERT INTO semantic_bindings VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                instance,
                interpretation_id,
                None,
                "e1",
                "edge:stable",
                "causal",
                "test",
                1,
                json.dumps({"local_key": "e1"}),
                "2026-01-01T00:00:00Z",
            ),
        )
        for index in range(8):
            store.connection.execute(
                "INSERT INTO graph_edges VALUES(?,?,?,?,?,?,?,?)",
                (
                    snapshot,
                    f"e1~variant-{index}",
                    "a",
                    "b",
                    "causal",
                    "asserted",
                    json.dumps({"local_key": "e1"}),
                    json.dumps([{"source_slot": "s0", "variant": index}]),
                ),
            )
        prepared = ResponseController(store, instance, FakeHost()).prepare(
            TurnIntent("alpha delta", memory="graph")
        )
        assert any("delta" in route.labels for route in prepared.considered)
