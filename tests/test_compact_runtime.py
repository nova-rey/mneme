"""CompactStore-backed descendant runtime tests."""

from mneme.development.field import SAA_FIELD_VERSION, FieldConfig
from mneme.development.learner import EdgeState, LearnerState
from mneme.memory.graph import GraphConcept, GraphEdge, GraphRoute
from mneme.state.compact import CompactStore
from mneme.state.compact_runtime import CompactGraphView, CompactRuntime


def _state() -> tuple[
    tuple[GraphConcept, ...], tuple[GraphEdge, ...], tuple[GraphRoute, ...], LearnerState
]:
    concepts = (
        GraphConcept("garden", "garden", "topic"),
        GraphConcept("water", "water", "resource"),
    )
    edges = (GraphEdge("edge-garden-water", "garden", "water", "needs"),)
    routes = (GraphRoute("route-garden-water", ("edge-garden-water",)),)
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
    return concepts, edges, routes, learner


def test_compact_runtime_publishes_and_reloads_complete_state(tmp_path):
    path = tmp_path / "descendant.sqlite3"
    concepts, edges, routes, learner = _state()
    with CompactStore.create(path, telemetry=True, telemetry_retention=4) as store:
        runtime = CompactRuntime(store)
        receipt = runtime.publish_state(
            CompactGraphView(concepts, edges, routes),
            learner,
            operation_id="thread-1",
            metadata={"saa_config": {"version": SAA_FIELD_VERSION}},
        )
        assert receipt["learner_changed"] == 1
        assert receipt["state_digest"] == store.state_digest()
        assert runtime.verify() == []
        metric = runtime.record_thread_metrics(1)
        assert metric["label"] == "thread-1"
        assert metric["table_rows"]["learner_state"] == 1
        assert metric["database_bytes"] > 0

    with CompactStore(path, read_only=True) as reopened:
        runtime = CompactRuntime(reopened)
        view = runtime.graph()
        assert [item.key for item in view.concepts] == ["garden", "water"]
        assert [item.key for item in view.edges] == ["edge-garden-water"]
        assert runtime.learner().global_opportunity == 3
        assert runtime.learner().edge_states[0].accessibility == 120_000
        assert reopened.metadata("saa_config") == {"version": SAA_FIELD_VERSION}
        assert runtime.verify() == []


def test_compact_runtime_saa_uses_current_state_and_health_gate(tmp_path):
    path = tmp_path / "descendant.sqlite3"
    concepts, edges, routes, learner = _state()
    with CompactStore.create(path) as store:
        runtime = CompactRuntime(store)
        runtime.publish_state(
            CompactGraphView(concepts, edges, routes), learner, operation_id="thread-1"
        )
        evaluation = runtime.evaluate_saa(
            "The garden needs water while I am away.",
            field_seed=77,
            config=FieldConfig(version=SAA_FIELD_VERSION, exploration="on"),
        )
        assert evaluation.health["status"] == "healthy"
        assert evaluation.field.selected_landing is not None
        assert evaluation.field.total_pressure > 0
        assert evaluation.field.payload.strip()


def test_compact_runtime_unrelated_context_retains_bounded_background_field(tmp_path):
    path = tmp_path / "descendant.sqlite3"
    concepts, edges, routes, learner = _state()
    with CompactStore.create(path) as store:
        runtime = CompactRuntime(store)
        runtime.publish_state(
            CompactGraphView(concepts, edges, routes), learner, operation_id="thread-1"
        )
        evaluation = runtime.evaluate_saa("An unfamiliar astronomy problem.", field_seed=78)
        assert evaluation.health["status"] == "healthy"
        assert len(evaluation.field.accessibility_distribution) >= 1


def test_compact_runtime_resolves_migrated_local_edge_to_canonical_learner_key(tmp_path):
    path = tmp_path / "migrated.sqlite3"
    with CompactStore.create(path) as store:
        store.put_graph(
            nodes={"garden": {"label": "garden"}, "water": {"label": "water"}},
            edges={
                "e-local": {
                    "edge_key": "e-local",
                    "source_key": "garden",
                    "target_key": "water",
                    "relationship": "needs",
                    "evidence_json": "[]",
                    "context_json": "{}",
                }
            },
            routes={},
        )
        store.put_learner(
            "edge:canonical", "general", {"accessibility": 120_000, "support": 90_000}
        )
        store.set_metadata("edge_bindings", {"e-local": "edge:canonical"})
        evaluation = CompactRuntime(store).evaluate_saa(
            "The garden needs water.", field_seed=79
        )
        assert evaluation.health["status"] == "healthy"
        assert evaluation.field.selected_landing == "edge:canonical"


def test_compact_runtime_unchanged_publication_does_not_duplicate_learner_journal(tmp_path):
    path = tmp_path / "descendant.sqlite3"
    concepts, edges, routes, learner = _state()
    with CompactStore.create(path, journal_retention=8) as store:
        runtime = CompactRuntime(store)
        graph = CompactGraphView(concepts, edges, routes)
        runtime.publish_state(graph, learner, operation_id="thread-1")
        runtime.publish_state(graph, learner, operation_id="thread-2")
        assert store.connection.execute("SELECT COUNT(*) FROM learner_journal").fetchone()[0] == 1
        assert store.connection.execute("SELECT COUNT(*) FROM graph_revisions").fetchone()[0] == 1
