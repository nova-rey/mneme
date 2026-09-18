import pytest

from mneme.contracts import GenerationRequest
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService, IdempotencyConflict, StaleRevision
from mneme.state.storage import SQLiteStore


def _request(text="hello"):
    return GenerationRequest(({"role": "user", "content": text},), seed=7)


def test_lifecycle_is_atomic_and_idempotent(tmp_path):
    with SQLiteStore(tmp_path / "a.sqlite3") as store:
        instance = store.create_root(permissions=StoragePermissions(True, True))
        service = ContinuityService(store, instance, FakeHost())
        prepared = service.prepare_episode(_request(), operation_id="11111111-1111-4111-8111-111111111111")
        assert prepared.status == "PREPARED"
        assert service.generate_operation(prepared.operation_id).status == "RESULT_READY"
        accepted = service.accept_episode(prepared.operation_id)
        assert accepted.revision == 1
        assert service.accept_episode(prepared.operation_id) == accepted
        assert store.current()["current_revision"] == 1
        with pytest.raises(IdempotencyConflict):
            service.prepare_episode(_request("different"), operation_id=prepared.operation_id)


def test_stale_result_cannot_be_rebased(tmp_path):
    with SQLiteStore(tmp_path / "a.sqlite3") as store:
        instance = store.create_root(permissions=StoragePermissions(True, True))
        first = ContinuityService(store, instance, FakeHost())
        a = first.prepare_episode(_request("a"), operation_id="11111111-1111-4111-8111-111111111111")
        first.generate_operation(a.operation_id)
        first.accept_episode(a.operation_id)
        b = first.prepare_episode(_request("b"), operation_id="22222222-2222-4222-8222-222222222222")
        first.generate_operation(b.operation_id)
        with store.transaction() as db:
            db.execute("UPDATE current_state SET current_revision=2")
        with pytest.raises(StaleRevision):
            first.accept_episode(b.operation_id)


def test_administrative_ids_do_not_enter_fake_generation(tmp_path):
    with SQLiteStore(tmp_path / "a.sqlite3") as store:
        instance = store.create_root(permissions=StoragePermissions(True, True))
        service = ContinuityService(store, instance, FakeHost())
        operation = service.prepare_episode(_request())
        service.generate_operation(operation.operation_id)
        output = store.connection.execute(
            "SELECT content FROM sources WHERE operation_id=? AND role='model_output'",
            (operation.operation_id,),
        ).fetchone()[0]
        baseline = FakeHost().generate(_request()).content
        assert output == baseline
        assert instance not in output


def test_failed_remote_call_is_uncertain_without_revision_advance(tmp_path):
    with SQLiteStore(tmp_path / "a.sqlite3") as store:
        instance = store.create_root(permissions=StoragePermissions(True, True))
        service = ContinuityService(store, instance, FakeHost(fail=True))
        operation = service.prepare_episode(_request())
        with pytest.raises(Exception):
            service.generate_operation(operation.operation_id)
        status = store.connection.execute(
            "SELECT status FROM operations WHERE operation_id=?", (operation.operation_id,)
        ).fetchone()[0]
        assert status == "UNCERTAIN"
        assert store.current()["current_revision"] == 0
