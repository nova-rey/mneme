from __future__ import annotations

import json

import pytest

from mneme.contracts import GenerationRequest, GenerationResult, TokenUsage
from mneme.experiments.evidence_review import (
    EvidenceReview,
    EvidenceReviewError,
    apply_replacements,
    collect_unresolved_evidence,
    resolve_review,
    reviewer_request,
    validate_reviewer_result,
)
from mneme.hosts import FakeHost
from mneme.memory.interpretation import (
    InterpretationService,
    InterpretationValidationError,
)
from mneme.memory.residue import validate_residue
from mneme.state.contracts import StoragePermissions
from mneme.state.service import ContinuityService
from mneme.state.storage import SQLiteStore


def _concept(quote: str, *, label: str = "rain jacket") -> dict[str, object]:
    return {
        "core_concepts": [
            {
                "key": "rain_jacket",
                "label": label,
                "kind": "object",
                "evidence": [{"source": "s0", "evidence": quote}],
                "confidence": 0.9,
            }
        ]
    }


def _source_records(text: str) -> list[dict[str, object]]:
    return [{"slot": "s0", "role": "user", "content": text}]


def test_exact_quote_fast_path_has_no_review_candidate() -> None:
    payload = _concept("* **rain jacket** kept my shoulders dry.")
    assert collect_unresolved_evidence(
        payload, _source_records("* **rain jacket** kept my shoulders dry.")
    ) == ()


def test_reviewer_request_has_bounded_json_output_allowance() -> None:
    candidate = collect_unresolved_evidence(
        _concept("rendered"), _source_records("source text")
    )[0]
    request = reviewer_request(candidate)
    assert request.parameters["max_new_tokens"] == 768


def test_markdown_omission_review_replacement_resolves_canonical_span() -> None:
    source = "🙂 * **rain jacket** kept my shoulders dry, even in curly ‘rain’."
    payload = _concept("rain jacket kept my shoulders dry, even in curly ‘rain’.")
    candidates = collect_unresolved_evidence(payload, _source_records(source))
    assert len(candidates) == 1
    request = reviewer_request(candidates[0])
    body = json.loads(request.messages[0]["content"])
    assert set(body) == {"source", "source_role", "source_slot", "proposition", "proposed_evidence"}
    assert body["source"] == source
    assert "offset" not in json.dumps(body)
    review = validate_reviewer_result(
        json.dumps(
            {
                "grounded": True,
                "evidence": "* **rain jacket** kept my shoulders dry, even in curly ‘rain’.",
            }
        )
    )
    quote = resolve_review(candidates[0], review)
    corrected = apply_replacements(payload, {candidates[0].paths[0]: quote})
    residue = validate_residue(corrected, {"s0": source})
    assert residue.core_concepts[0]["source_spans"] == (
        {"source_slot": "s0", "start": 2, "end": len(source)},
    )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"grounded": false, "evidence": "anything"}', "must not include evidence"),
        ('{"grounded": "unknown", "evidence": "anything"}', "must not include evidence"),
        ('{"grounded": true}', "requires evidence"),
        ('{"grounded": true, "evidence": "missing"}', "missing or ambiguous"),
        ('{"grounded": "maybe"}', "true, false, or unknown"),
        ('{"grounded": true, "evidence": "x", "offset": 1}', "invalid shape"),
    ],
)
def test_reviewer_contract_fails_closed(content: str, message: str) -> None:
    if "missing or ambiguous" in message:
        candidate = collect_unresolved_evidence(
            _concept("rendered"), _source_records("source text")
        )[0]
        with pytest.raises(EvidenceReviewError, match=message):
            resolve_review(candidate, validate_reviewer_result(content))
    else:
        with pytest.raises(EvidenceReviewError, match=message):
            validate_reviewer_result(content)


def test_duplicate_quote_is_not_resolved_by_first_occurrence() -> None:
    payload = _concept("rain jacket")
    candidates = collect_unresolved_evidence(payload, _source_records("rain jacket; rain jacket"))
    assert len(candidates) == 1
    review = validate_reviewer_result('{"grounded": true, "evidence": "rain jacket"}')
    with pytest.raises(EvidenceReviewError, match="missing or ambiguous"):
        resolve_review(candidates[0], review)


def test_false_and_unknown_review_never_create_residue() -> None:
    source = "The dial did not stop the ticking."
    payload = _concept("dial stopped ticking", label="dial stops ticking")
    candidate = collect_unresolved_evidence(payload, _source_records(source))[0]
    for content in ('{"grounded": false}', '{"grounded": "unknown"}'):
        review = validate_reviewer_result(content)
        with pytest.raises(EvidenceReviewError, match="did not ground"):
            resolve_review(candidate, review)


@pytest.mark.parametrize("grounded", ["false", '"unknown"'])
@pytest.mark.parametrize("evidence", [None, "", {}, []])
def test_empty_placeholder_is_canonicalized_to_no_replacement(
    grounded: str, evidence: object
) -> None:
    payload: dict[str, object] = {"grounded": json.loads(grounded), "evidence": evidence}
    review = validate_reviewer_result(json.dumps(payload))
    assert review.quote is None


def test_historical_q3_empty_string_is_accepted_as_no_evidence() -> None:
    review = validate_reviewer_result('{"grounded": false, "evidence": ""}')
    assert review == EvidenceReview(False, None)


@pytest.mark.parametrize("grounded", [True, False, "unknown"])
@pytest.mark.parametrize("evidence", [{"placeholder": True}, ["not empty"], 0, 1])
def test_nonempty_evidence_is_never_normalized_away(
    grounded: bool | str, evidence: object
) -> None:
    content = json.dumps({"grounded": grounded, "evidence": evidence})
    if grounded is True:
        with pytest.raises(EvidenceReviewError, match="requires evidence"):
            validate_reviewer_result(content)
    else:
        with pytest.raises(EvidenceReviewError, match="must not include evidence"):
            validate_reviewer_result(content)


class _InvalidResidueHost(FakeHost):
    def generate(self, request: GenerationRequest) -> GenerationResult:
        content = json.dumps(_concept("not in source"))
        return GenerationResult(
            content,
            self.model_id,
            "builtin",
            dict(request.parameters),
            request.seed,
            TokenUsage(5, 5, 10),
            0.0,
            "stop",
            {"fixture": True},
            {"host": self.fingerprint().to_dict()},
        )


def test_reviewed_result_preserves_failed_extractor_attempt(tmp_path) -> None:
    host = _InvalidResidueHost()
    store = SQLiteStore(tmp_path / "lineage.sqlite3")
    instance = store.create_root(permissions=StoragePermissions(True, True, True))
    continuity = ContinuityService(store, instance, host)
    operation = continuity.prepare_episode(
        GenerationRequest(({"role": "user", "content": "hello world"},)),
        operation_id="development-1",
    )
    continuity.generate_operation(operation.operation_id)
    continuity.accept_episode(operation.operation_id)
    service = InterpretationService(store, instance, host)
    prepared = service.prepare(operation.episode_id, operation_id="extract-1")
    service.execute(prepared)
    with pytest.raises(InterpretationValidationError):
        service.validate(prepared)
    recovery = service.prepare(
        operation.episode_id,
        operation_id="extract-1-review",
        recovery_of="extract-1",
        recovery_version="semantic-evidence-reconciliation-v2",
    )
    service.record_reviewed_result(recovery, _concept("hello"))
    residue = service.validate(recovery)
    assert residue.core_concepts[0]["source_spans"] == (
        {"source_slot": "s0", "start": 0, "end": 5},
    )
    old = store.connection.execute(
        "SELECT status FROM interpretation_attempts WHERE operation_id='extract-1'"
    ).fetchone()
    assert old[0] == "INVALID"
