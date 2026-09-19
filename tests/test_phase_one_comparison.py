from pathlib import Path

import pytest

from mneme.contracts import GenerationRequest
from mneme.experiments.comparison import (
    ComparisonError,
    ComparisonProbe,
    FrozenComparator,
    run_matched_comparison,
)
from mneme.experiments.inspection import inspect_checkpoint, inspect_store, inspect_turn
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore


def _checkpoint(tmp_path: Path) -> Path:
    store = SQLiteStore(tmp_path / "subject.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True))
    service = ContinuityService(store, instance, FakeHost())
    operation = service.prepare_episode(
        GenerationRequest(({"role": "user", "content": "VRAM constrains capacity"},))
    )
    service.generate_operation(operation.operation_id)
    service.accept_episode(operation.operation_id)
    checkpoint = tmp_path / "subject.checkpoint.sqlite3"
    create_checkpoint(store, checkpoint)
    store.close()
    return checkpoint


def test_matched_comparison_is_read_only_and_coordinates_treatments(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path)
    probe = ComparisonProbe(0, ({"role": "user", "content": "Explain VRAM"},))
    results = run_matched_comparison(checkpoint, FakeHost(), [probe], repetitions=2)
    assert len(results) == 6
    assert {result.treatment for result in results} == {"no_memory", "lexical", "graph"}
    assert all(result.state_digest_before == result.state_digest_after for result in results)


def test_administrative_subject_slot_does_not_enter_generation_material(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path)
    probe = ComparisonProbe(0, ({"role": "user", "content": "same probe"},))
    first = FrozenComparator(checkpoint, FakeHost()).generate(
        subject_slot="subject-a",
        probe=probe,
        repetition=0,
        treatment="no_memory",
        seed=7,
    )
    second = FrozenComparator(checkpoint, FakeHost()).generate(
        subject_slot="subject-b",
        probe=probe,
        repetition=0,
        treatment="no_memory",
        seed=7,
    )
    assert first.output == second.output


def test_comparison_artifact_is_sanitized_and_idempotent(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path)
    artifact_dir = tmp_path / "comparison"
    probe = ComparisonProbe(0, ({"role": "user", "content": "Explain VRAM"},))
    results = run_matched_comparison(
        checkpoint,
        FakeHost(),
        [probe],
        seeds={(0, 0, "no_memory"): 7},
        artifact_dir=artifact_dir,
        provenance={"contract_sha256": "contract"},
    )
    assert len(results) == 3
    report = (artifact_dir / "comparison.json").read_text()
    assert "FakeHost response" not in report
    run_matched_comparison(
        checkpoint,
        FakeHost(),
        [probe],
        seeds={(0, 0, "no_memory"): 7},
        artifact_dir=artifact_dir,
        provenance={"contract_sha256": "contract"},
    )
    with pytest.raises(ComparisonError, match="conflicting content"):
        run_matched_comparison(
            checkpoint,
            FakeHost(),
            [probe],
            seeds={(0, 0, "no_memory"): 8},
            artifact_dir=artifact_dir,
            provenance={"contract_sha256": "contract"},
        )


def test_inspection_labels_independent_counters_and_turn_trace(tmp_path: Path) -> None:
    checkpoint = _checkpoint(tmp_path)
    inspected_checkpoint = inspect_checkpoint(checkpoint)
    assert "lineage_revision" in inspected_checkpoint["counters"]
    assert "accepted_episode_count" in inspected_checkpoint["counters"]
    assert "graph_revision" in inspected_checkpoint["counters"]

    store = SQLiteStore(tmp_path / "inspect.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True, True, True, True))
    from mneme.controller import ResponseController, TurnIntent

    with store:
        ResponseController(store, instance, FakeHost()).execute(
            ResponseController(store, instance, FakeHost()).prepare(
                TurnIntent("inspect", memory="off", operation_id="inspect-op")
            )
        )
    inspected = inspect_store(tmp_path / "inspect.sqlite3")
    assert inspected["counters"]["lineage_revision"] == 1
    assert inspected["counters"]["accepted_episode_count"] == 1
    trace = inspect_turn(tmp_path / "inspect.sqlite3", "inspect-op")
    assert trace["operation_id"] == "inspect-op"


def test_inspection_labels_lineage_episode_graph_and_self_view_counters(
    tmp_path: Path,
) -> None:
    checkpoint = _checkpoint(tmp_path)
    store_view = inspect_store(tmp_path / "subject.sqlite3")
    checkpoint_view = inspect_checkpoint(checkpoint)
    for payload in (store_view, checkpoint_view):
        counters = payload["counters"]
        assert set(counters) >= {
            "lineage_revision",
            "accepted_episode_count",
            "accepted_episode_ordinal",
            "graph_revision",
            "self_view_version",
        }
    assert store_view["counters"]["lineage_revision"] == 1
    assert store_view["counters"]["accepted_episode_count"] == 1
