"""Production persistence selection and bounded-growth promotion tests."""

from __future__ import annotations

import json
import uuid

import pytest

from mneme.cli import main
from mneme.development.learner import EdgeState, LearnerState
from mneme.memory.graph import GraphConcept, GraphEdge, GraphRoute
from mneme.state.compact import CompactStore
from mneme.state.compact_runtime import CompactGraphView, CompactRuntime
from mneme.state.persistence import (
    PersistenceMode,
    PersistenceModeError,
    create_compact_instance,
    detect_persistence_mode,
    require_legacy_research_store,
)


def _developed_state() -> tuple[CompactGraphView, LearnerState]:
    graph = CompactGraphView(
        concepts=(
            GraphConcept("garden", "garden", "topic"),
            GraphConcept("water", "water", "resource"),
        ),
        edges=(GraphEdge("edge-garden-water", "garden", "water", "needs"),),
        routes=(GraphRoute("route-garden-water", ("edge-garden-water",)),),
    )
    learner = LearnerState(
        edge_states=(
            EdgeState(
                target_key="edge-garden-water",
                context="general",
                accessibility=120_000,
                support=90_000,
            ),
        ),
        global_opportunity=3,
    )
    return graph, learner


def test_new_instance_factory_selects_compact_and_marks_role(tmp_path):
    path = tmp_path / "adult.compact.sqlite3"
    with create_compact_instance(path, instance_id="adult") as store:
        assert store.metadata("instance")["persistence_mode"] == PersistenceMode.COMPACT.value
        assert store.metadata("instance")["developmental_writable"] is True
        assert store.verify() == []
    assert detect_persistence_mode(path) is PersistenceMode.COMPACT


def test_cli_new_instance_defaults_to_compact(tmp_path, capsys):
    assert main(["--store", str(tmp_path), "instance", "create", "--id", "new"]) == 0
    assert capsys.readouterr().out.strip() == "new"
    assert detect_persistence_mode(tmp_path / "new.compact.sqlite3") is PersistenceMode.COMPACT


def test_cli_legacy_creation_requires_explicit_compatibility_flag(tmp_path):
    instance_id = str(uuid.uuid4())
    with pytest.raises(SystemExit, match="compatibility"):
        main(
            [
                "--store",
                str(tmp_path),
                "instance",
                "create",
                "--id",
                instance_id,
                "--persistence",
                "legacy",
            ]
        )
    assert (
        main(
            [
                "--store",
                str(tmp_path),
                "instance",
                "create",
                "--id",
                instance_id,
                "--persistence",
                "legacy",
                "--legacy-research-store",
            ]
        )
        == 0
    )
    assert (
        detect_persistence_mode(tmp_path / f"{instance_id}.sqlite3")
        is PersistenceMode.LEGACY_RESEARCH
    )


def test_legacy_compatibility_boundary_rejects_compact_store(tmp_path):
    path = tmp_path / "adult.compact.sqlite3"
    with create_compact_instance(path, instance_id="adult"):
        pass
    with pytest.raises(PersistenceModeError, match="historical copy"):
        require_legacy_research_store(path, operation="historical reproduction")


def test_fresh_compact_runtime_develops_restarts_and_reconstructs_saa(tmp_path):
    path = tmp_path / "adult.compact.sqlite3"
    graph, learner = _developed_state()
    with create_compact_instance(path, instance_id="adult") as store:
        runtime = CompactRuntime(store)
        receipt = runtime.publish_state(graph, learner, operation_id="turn-1")
        assert receipt["learner_changed"] == 1
        first = runtime.evaluate_saa("The garden needs water.", field_seed=11)
        assert first.health["status"] == "healthy"
    with CompactStore(path, read_only=True) as store:
        runtime = CompactRuntime(store)
        second = runtime.evaluate_saa("The garden needs water.", field_seed=11)
        assert second.field.selected_landing == first.field.selected_landing
        assert second.field.payload == first.field.payload
        assert runtime.verify() == []


def test_repeated_small_graph_updates_store_deltas_not_full_snapshots(tmp_path):
    path = tmp_path / "growth.compact.sqlite3"
    with CompactStore.create(path, journal_retention=32, telemetry_retention=16) as store:
        graph, learner = _developed_state()
        runtime = CompactRuntime(store)
        runtime.publish_state(graph, learner, operation_id="initial")
        for index in range(100):
            nodes = {
                item.key: item.content_dict()
                for item in graph.concepts
            }
            nodes["garden"]["annotation"] = index
            runtime.publish_state(
                {
                    "nodes": nodes,
                    "edges": {item.key: item.content_dict() for item in graph.edges},
                    "routes": {item.key: item.content_dict() for item in graph.routes},
                },
                learner,
                operation_id=f"turn-{index}",
            )
        revision_rows = store.connection.execute(
            "SELECT changes_json FROM graph_revisions ORDER BY revision"
        ).fetchall()
        change_counts = [len(json.loads(str(row[0]))) for row in revision_rows]
        assert len(revision_rows) == 101
        assert change_counts[0] == 4
        assert max(change_counts[1:]) == 1
        assert store.connection.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0] == 2
        assert store.connection.execute("SELECT COUNT(*) FROM learner_journal").fetchone()[0] == 1
        assert store.verify() == []
