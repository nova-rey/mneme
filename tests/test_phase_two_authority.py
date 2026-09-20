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
