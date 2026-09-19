from __future__ import annotations

import sqlite3

import pytest

from mneme.contracts import GenerationRequest
from mneme.controller import ResponseController, TurnIntent
from mneme.hosts import FakeHost
from mneme.memory.interpretation import InterpretationError, InterpretationService
from mneme.state.contracts import StoragePermissions
from mneme.state.policy import PolicyError, PolicyService
from mneme.state.reader import CheckpointReader
from mneme.state.service import ContinuityError, ContinuityService
from mneme.state.snapshots import create_checkpoint
from mneme.state.storage import SQLiteStore


def _dev_store(tmp_path):
    host = FakeHost()
    store = SQLiteStore(tmp_path / "subject.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(True, True, True, True, True),
        host_binding=host.fingerprint().to_dict(),
    )
    return store, instance, host


def _episode(store, instance, host, text="source"):
    operation = ContinuityService(store, instance, host).prepare_episode(
        GenerationRequest(({"role": "user", "content": text},))
    )
    ContinuityService(store, instance, host).generate_operation(operation.operation_id)
    return ContinuityService(store, instance, host).accept_episode(operation.operation_id)


def test_creation_records_selected_host_and_permission_inspection(tmp_path):
    store, instance, host = _dev_store(tmp_path)
    with store:
        state = PolicyService(store, instance).current()
        assert state.provider_reuse_allowed
        assert state.bound_host_ref
        assert state.bound_host_fingerprint == host.fingerprint().to_dict()
        assert state.authority_available
        assert PolicyService(store, instance).show()["scope_id"] == "local"


def test_revocation_is_persistent_and_old_checkpoint_cannot_bypass_it(tmp_path):
    store, instance, _host = _dev_store(tmp_path)
    checkpoint = tmp_path / "before-revocation.sqlite3"
    with store:
        create_checkpoint(store, checkpoint)
        revision = PolicyService(store, instance).revoke(("recall",))
        assert revision == 1
        assert not PolicyService(store, instance).current().recall_allowed
    with CheckpointReader(checkpoint) as reader:
        state = PolicyService(reader.store, instance).current()
        assert not state.recall_allowed
        assert state.revocation_revision == 1


def test_revoke_blocks_interpretation_and_memory_recall(tmp_path):
    store, instance, host = _dev_store(tmp_path)
    with store:
        _episode(store, instance, host)
        PolicyService(store, instance).revoke(("interpret", "recall"))
        with pytest.raises(InterpretationError, match="permission"):
            InterpretationService(store, instance, host).prepare(
                str(store.connection.execute("SELECT episode_id FROM episodes").fetchone()[0])
            )
        prepared = ResponseController(store, instance, host).prepare(
            TurnIntent("source", memory="graph")
        )
        assert prepared.selected == ()


def test_revoke_blocks_bound_provider_reuse_before_host_call(tmp_path):
    store, instance, host = _dev_store(tmp_path)
    with store:
        PolicyService(store, instance).revoke(("provider_reuse",))
        with pytest.raises(ContinuityError, match="provider_reuse"):
            ContinuityService(store, instance, host).prepare_episode(
                GenerationRequest(
                    (
                        {"role": "assistant", "content": "retained context"},
                        {"role": "user", "content": "new input"},
                    )
                )
            )


def test_missing_authority_fails_closed_but_explicit_grant_reauthorizes(tmp_path):
    store, instance, host = _dev_store(tmp_path)
    with store:
        authority = store.connection.execute(
            "SELECT revocation_ledger_path FROM store_info"
        ).fetchone()[0]
        assert authority
        store.close()
    path = tmp_path / "subject.sqlite3.policy.jsonl"
    path.unlink()
    with SQLiteStore(tmp_path / "subject.sqlite3") as reopened:
        state = PolicyService(reopened, instance).current()
        assert not state.interpretation_allowed
        with pytest.raises(PolicyError, match="authority"):
            PolicyService(reopened, instance).require("interpret")
        PolicyService(reopened, instance).grant(
            ("interpret", "recall", "provider_reuse"),
            host_fingerprint=host.fingerprint().to_dict(),
        )
        granted = PolicyService(reopened, instance).current()
        assert granted.interpretation_allowed
        assert granted.recall_allowed
        assert granted.provider_reuse_allowed


def test_v3_migration_denies_phase_one_permissions_until_grant(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with SQLiteStore(path) as store:
        instance = store.create_root(
            permissions=StoragePermissions(True, True, True, True, True)
        )
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA user_version=3")
    raw.execute("UPDATE store_info SET schema_version=3")
    raw.execute("ALTER TABLE store_info DROP COLUMN revocation_ledger_path")
    raw.execute("ALTER TABLE policies DROP COLUMN bound_host_ref")
    raw.execute("ALTER TABLE policies DROP COLUMN bound_host_fingerprint_json")
    raw.commit()
    raw.close()
    backup = tmp_path / "legacy.before-v4.sqlite3"
    SQLiteStore.migrate(path, backup=backup)
    with SQLiteStore(path) as migrated:
        assert not PolicyService(migrated, instance).current().recall_allowed
