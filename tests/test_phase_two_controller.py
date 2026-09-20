from __future__ import annotations

import json

import pytest

from mneme.contracts import GenerationRequest
from mneme.controller import ControllerError, ResponseController, TurnIntent
from mneme.development import ConsequenceAssessment
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
