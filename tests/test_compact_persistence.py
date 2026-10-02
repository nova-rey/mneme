"""Bounded persistence mode tests."""

import subprocess
import sys

from mneme.state.compact import CompactStore, migrate_sqlite
from mneme.state.contracts import StoragePermissions
from mneme.state.storage import SQLiteStore


def test_unchanged_learner_opportunities_do_not_grow_journal(tmp_path):
    path = tmp_path / "compact.sqlite3"
    with CompactStore.create(path, journal_retention=4) as store:
        value = {"accessibility": 1, "support": 2}
        assert store.put_learner("edge", "general", value, operation_id="1")
        for number in range(100):
            assert not store.put_learner("edge", "general", value, operation_id=str(number + 2))
        assert store.connection.execute("SELECT COUNT(*) FROM learner_state").fetchone()[0] == 1
        assert store.connection.execute("SELECT COUNT(*) FROM learner_journal").fetchone()[0] == 1
        assert store.verify() == []


def test_graph_revisions_store_deltas_and_reconstruct_history(tmp_path):
    path = tmp_path / "compact.sqlite3"
    with CompactStore.create(path) as store:
        assert store.put_graph(nodes={"a": {"label": "A"}}, edges={}, routes={}) == 1
        assert (
            store.put_graph(
                nodes={"a": {"label": "A2"}, "b": {"label": "B"}}, edges={}, routes={}
            )
            == 2
        )
        assert store.graph_at(1) == {"nodes": {"a": {"label": "A"}}, "edges": {}, "routes": {}}
        assert store.graph_at(2)["nodes"]["a"] == {"label": "A2"}
        assert store.connection.execute("SELECT COUNT(*) FROM graph_revisions").fetchone()[0] == 2
        assert store.verify() == []


def test_compact_checkpoint_is_atomic_and_restartable(tmp_path):
    path = tmp_path / "compact.sqlite3"
    checkpoint = tmp_path / "checkpoint.sqlite3"
    with CompactStore.create(path) as store:
        store.put_graph(nodes={"a": {"label": "A"}}, edges={}, routes={})
        store.put_learner("edge", "general", {"accessibility": 4}, operation_id="1")
        digest = store.state_digest()
        checkpoint_id = store.checkpoint(checkpoint, checkpoint_id="cp-1")
        assert checkpoint_id == "cp-1"
    with CompactStore(checkpoint, read_only=True) as restored:
        assert restored.state_digest() == digest
        assert restored.verify() == []


def test_interrupted_transaction_recovers_prior_state(tmp_path):
    path = tmp_path / "compact.sqlite3"
    with CompactStore.create(path) as store:
        store.put_learner("edge", "general", {"accessibility": 1}, operation_id="1")
    code = (
        "import sqlite3,sys,os; c=sqlite3.connect(sys.argv[1]); "
        "c.execute('BEGIN IMMEDIATE'); "
        "c.execute(\"UPDATE learner_state SET value_json='bad'\"); os._exit(9)"
    )
    assert subprocess.run([sys.executable, "-c", code, str(path)], check=False).returncode == 9
    with CompactStore(path, read_only=True) as restored:
        assert restored.learner_state()[("edge", "general")] == {"accessibility": 1}
        assert restored.verify() == []


def test_migration_preserves_current_graph_and_learner_state(tmp_path):
    source_path = tmp_path / "research.sqlite3"
    compact_path = tmp_path / "compact.sqlite3"
    with SQLiteStore(source_path) as source:
        instance = source.create_root(permissions=StoragePermissions(store=True, export=True))
        # A compact migration of a root is intentionally valid even with no
        # graph or learner material; this guards the read-only path and digest.
        assert source.current()["active_instance_id"] == instance
    report = migrate_sqlite(source_path, compact_path)
    assert report["nodes"] == report["edges"] == report["routes"] == 0
    with CompactStore(compact_path, read_only=True) as compact:
        assert compact.state_digest() == report["state_digest"]
        assert compact.verify() == []
