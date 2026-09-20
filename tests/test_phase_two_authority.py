from __future__ import annotations

import json

import pytest

from mneme.development import AuthorityError, IdentityReviewService, QuarantineService
from mneme.state.contracts import StoragePermissions
from mneme.state.storage import SQLiteStore


def _store(tmp_path):
    store = SQLiteStore(tmp_path / "authority.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True, learn=True))
    return store, instance


def test_quarantine_is_append_only_reversible_and_requires_learning_permission(tmp_path):
    store, instance = _store(tmp_path)
    with store:
        service = QuarantineService(store, instance)
        added = service.add("route", "route-a", "unsupported evidence")
        assert service.is_quarantined("route", "route-a")
        released = service.release(added.event_id)
        assert released.authority_revision == added.authority_revision + 1
        assert not service.is_quarantined("route", "route-a")
        assert store.connection.execute(
            "SELECT COUNT(*) FROM quarantine_events"
        ).fetchone()[0] == 2


def test_identity_review_persists_failed_result_and_requires_explicit_acceptance(tmp_path):
    store, instance = _store(tmp_path)
    with store:
        service = IdentityReviewService(store, instance)
        review = service.prepare({"name": "Candidate"}, operation_key="review-1")
        service.record_attempt(
            review,
            {"name": "not-json"},
            status="INVALID",
            errors=("name schema failed",),
            usage={"input_tokens": 3},
        )
        row = store.connection.execute(
            "SELECT status,result_json,validation_errors_json FROM identity_review_attempts"
        ).fetchone()
        assert row[0] == "INVALID"
        assert json.loads(row[1]) == {"name": "not-json"}
        assert "name schema failed" in row[2]
        with pytest.raises(AuthorityError, match="not ready"):
            service.accept(review, name="Candidate")


def test_identity_review_valid_result_can_be_accepted(tmp_path):
    store, instance = _store(tmp_path)
    with store:
        service = IdentityReviewService(store, instance)
        review = service.prepare({"name": "Candidate"}, operation_key="review-2")
        service.record_attempt(review, {"name": "Candidate"}, status="VALID")
        assert service.accept(review, name="Candidate") == review
        assert store.connection.execute(
            "SELECT stage,decision_json FROM identity_review_operations WHERE review_id=?",
            (review,),
        ).fetchone()[0] == "ACCEPTED"
        event = store.connection.execute(
            "SELECT event_kind,name,accepted_revision FROM identity_events"
        ).fetchone()
        assert tuple(event) == ("adopt", "Candidate", 1)
        view = store.connection.execute(
            "SELECT name,version FROM self_views"
        ).fetchone()
        assert tuple(view) == ("Candidate", 1)
        assert store.current()["current_revision"] == 1


def test_identity_review_acceptance_supersedes_existing_self_view_atomically(tmp_path):
    store = SQLiteStore(tmp_path / "authority-existing.sqlite3")
    instance = store.create_root(
        permissions=StoragePermissions(True, True, True, True, True, True)
    )
    with store:
        from mneme.identity import IdentityService

        IdentityService(store, instance).adopt("First")
        service = IdentityReviewService(store, instance)
        review = service.prepare({"name": "Second"}, operation_key="review-3")
        service.record_attempt(review, {"name": "Second"}, status="VALID")
        service.accept(review, name="Second")
        events = store.connection.execute(
            "SELECT event_id,event_kind,name,supersedes_event_id,accepted_revision "
            "FROM identity_events ORDER BY accepted_revision"
        ).fetchall()
        assert events[1][1:3] == ("supersede", "Second")
        assert events[1][3] == events[0][0]
        assert events[1][4] == 2
        assert tuple(
            store.connection.execute(
                "SELECT name,version FROM self_views ORDER BY version DESC LIMIT 1"
            ).fetchone()
        ) == ("Second", 2)
