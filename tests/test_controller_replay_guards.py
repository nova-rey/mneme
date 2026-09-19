from __future__ import annotations

import pytest

from mneme.chat import ChatSession
from mneme.contracts import GenerationRequest
from mneme.controller import ControllerError, ResponseController, TurnIntent
from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


class _CountingHost(FakeHost):
    def __init__(self, *, model_id: str = "mneme-fake-v1") -> None:
        super().__init__(model_id=model_id)
        self.calls = 0

    def generate(self, request: GenerationRequest):
        self.calls += 1
        return super().generate(request)


def _store(tmp_path):
    store = SQLiteStore(tmp_path / "controller.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True, True, True, True))
    return store, instance


def test_stale_prepared_turn_is_rejected_before_dispatch(tmp_path):
    with _store(tmp_path)[0] as store:
        instance = str(store.current()["active_instance_id"])
        host = _CountingHost()
        controller = ResponseController(store, instance, host)
        prepared = controller.prepare(
            TurnIntent("prepared first", memory="off", operation_id="stale")
        )

        advancing = ContinuityService(store, instance, host)
        operation = advancing.prepare_episode(
            GenerationRequest(({"role": "user", "content": "advance"},)),
            operation_id="advance",
        )
        advancing.generate_operation(operation.operation_id)
        advancing.accept_episode(operation.operation_id)
        calls_before = host.calls

        with pytest.raises(ControllerError, match="prepared turn is stale"):
            controller.execute(prepared)
        assert host.calls == calls_before
        assert store.connection.execute(
            "SELECT COUNT(*) FROM operations WHERE operation_id='stale'"
        ).fetchone()[0] == 0


def test_host_fingerprint_drift_is_rejected_before_dispatch(tmp_path):
    with _store(tmp_path)[0] as store:
        instance = str(store.current()["active_instance_id"])
        pinned = _CountingHost(model_id="pinned")
        prepared = ResponseController(store, instance, pinned).prepare(
            TurnIntent("host-bound", memory="off", operation_id="host-bound")
        )
        changed = _CountingHost(model_id="changed")

        with pytest.raises(ControllerError, match="host fingerprint drifted"):
            ResponseController(store, instance, changed).execute(prepared)
        assert changed.calls == 0
        assert store.connection.execute(
            "SELECT COUNT(*) FROM operations WHERE operation_id='host-bound'"
        ).fetchone()[0] == 0


def test_replayed_user_context_is_not_persisted_as_fresh_evidence(tmp_path):
    with _store(tmp_path)[0] as store:
        instance = str(store.current()["active_instance_id"])
        session = ChatSession(store, instance, _CountingHost(), memory="off")
        session.turn("prior user evidence", operation_id="turn-1")
        session.turn("current user evidence", operation_id="turn-2")

        rows = store.connection.execute(
            "SELECT s.ordinal,s.role,b.purpose,b.independent_evidence "
            "FROM sources s JOIN source_bindings b ON b.source_id=s.source_id "
            "WHERE s.operation_id='turn-2' AND s.role <> 'model_output' "
            "ORDER BY s.ordinal"
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            (0, "user", "replayed_context", 0),
            (1, "assistant", "replayed_context", 0),
            (2, "user", "external_evidence", 1),
        ]
