from __future__ import annotations

import json
from dataclasses import replace

import pytest

from mneme.development import (
    AssessorValidationError,
    assessor_generation_request,
    qualification_cases,
    validate_assessor_result,
    validate_qualification_case,
)
from mneme.hosts import FakeHost


def _row(
    monitor_id: str,
    *,
    status: str,
    support: str,
    expression: str,
    dependence: str,
    slots: list[str],
    complete: bool,
    reason: str | None = None,
    source_slot: str | None = None,
    quote: str | None = None,
) -> dict[str, object]:
    evidence = None
    if source_slot is not None or quote is not None:
        evidence = {"source_slot": source_slot, "quote": quote}
    return {
        "monitor_id": monitor_id,
        "status": status,
        "relation_support": support,
        "expression_status": expression,
        "dependence": dependence,
        "coverage": {"complete": complete, "source_slots": slots, "reason": reason},
        "evidence": evidence,
        "dependence_group": None,
    }


def _valid_result(case_id: str) -> dict[str, object]:
    if case_id == "Q1":
        return {
            "schema_version": "p2-assessor-v1",
            "assessments": [
                _row(
                    "latch", status="present", support="supported", expression="expressed",
                    dependence="external_supported", slots=["s0"], complete=True,
                    source_slot="s0", quote="Pulling the lever released the latch.",
                ),
                _row(
                    "echo", status="present", support="supported", expression="expressed",
                    dependence="current_input_echo", slots=["s1"], complete=True,
                    source_slot="s1", quote="Pulling the lever released the latch.",
                ),
                _row(
                    "unrelated", status="absent", support="unsupported", expression="not_expressed",
                    dependence="external_supported", slots=["s0"], complete=True,
                    reason="The source does not mention the unrelated target.",
                ),
            ],
        }
    if case_id == "Q2":
        return {
            "schema_version": "p2-assessor-v1",
            "assessments": [
                _row(
                    "jacket_direction", status="absent", support="unsupported",
                    expression="not_expressed", dependence="external_supported", slots=["s0"],
                    complete=True,
                    reason="The rain-jacket source does not express the candidate direction.",
                ),
                _row(
                    "shade", status="present", support="supported", expression="expressed",
                    dependence="exposure_linked", slots=["s1", "s2"], complete=True,
                    source_slot="s1", quote="Turning the handle raises the shade.",
                ),
            ],
        }
    return {
        "schema_version": "p2-assessor-v1",
        "assessments": [
            _row(
                "dial", status="present", support="unsupported", expression="expressed",
                dependence="external_supported", slots=["s0"], complete=True,
                source_slot="s0", quote="did not stop the ticking",
            ),
            _row(
                "unavailable_output", status="unknown", support="unknown", expression="unknown",
                dependence="unknown",
                slots=[],
                complete=False,
                reason="The model-output source was unavailable.",
            ),
        ],
    }


def test_qualification_cases_use_production_shape_and_fakehost() -> None:
    host = FakeHost()
    for case in qualification_cases():
        request = assessor_generation_request(case.request)
        # The request is the same host boundary used by the pilot; no run ID or
        # filesystem coordinate is placed in model-visible generation material.
        assert request.run_metadata == {}
        assert request.response_format is None
        payload = request.messages[0]["content"]
        assert "source" in payload and "monitors" in payload
        fake_result = host.generate(request)
        result = replace(fake_result, content=json.dumps(_valid_result(case.case_id)))
        validated = validate_qualification_case(case, json.loads(result.content))
        assert len(validated) == len(case.request.monitors)
        assert result.provenance["host"]["provider"] == "builtin"


def test_q1_echo_and_q2_exposure_ancestry_are_classified() -> None:
    cases = {case.case_id: case for case in qualification_cases()}
    q1 = validate_qualification_case(cases["Q1"], _valid_result("Q1"))
    assert {row.monitor_id: row.dependence for row in q1}["echo"] == "current_input_echo"
    q2 = validate_qualification_case(cases["Q2"], _valid_result("Q2"))
    assert {row.monitor_id: row.dependence for row in q2}["shade"] == "exposure_linked"


def test_q3_negation_quote_and_unavailable_source_are_fail_closed() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q3")
    rows = validate_qualification_case(case, _valid_result("Q3"))
    dial = next(row for row in rows if row.monitor_id == "dial")
    assert dial.evidence is not None
    assert dial.evidence.start == case.request.sources[0].text.index("did not stop")
    unknown = next(row for row in rows if row.monitor_id == "unavailable_output")
    assert unknown.status == "unknown"
    assert unknown.evidence is None


def test_missing_monitor_and_false_absence_fail_closed() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    result = _valid_result("Q1")
    result["assessments"] = result["assessments"][:2]  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="every required monitor"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]

    result = _valid_result("Q1")
    row = result["assessments"][2]  # type: ignore[index]
    row["coverage"] = {"complete": False, "source_slots": [], "reason": "unknown"}  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="absent requires complete"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]


def test_quote_must_be_unique_verbatim_and_from_declared_slot() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    result = _valid_result("Q1")
    result["assessments"][0]["evidence"]["quote"] = "hinge"  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="does not occur|ambiguous"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]

    result = _valid_result("Q1")
    result["assessments"][0]["evidence"]["source_slot"] = "s1"  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="wrong source slot"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]

    ambiguous_request = replace(
        case.request,
        sources=(
            replace(case.request.sources[0], text="latch latch"),
            case.request.sources[1],
        ),
    )
    ambiguous_result = _valid_result("Q1")
    ambiguous_result["assessments"][0]["evidence"]["quote"] = "latch"  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="ambiguous"):
        validate_assessor_result(ambiguous_request, ambiguous_result)  # type: ignore[arg-type]


def test_unicode_quote_offsets_are_code_point_offsets() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q3")
    unicode_request = replace(
        case.request,
        sources=(
            replace(
                case.request.sources[0],
                text="🙂 Dialing the wheel stopped the ticking.",
            ),
            case.request.sources[1],
        ),
    )
    result = _valid_result("Q3")
    result["assessments"][0]["evidence"]["quote"] = "🙂 Dialing the wheel"  # type: ignore[index]
    rows = validate_assessor_result(unicode_request, result)  # type: ignore[arg-type]
    quote = rows[0].evidence
    assert quote is not None
    assert unicode_request.sources[0].text[quote.start : quote.end] == quote.quote
    assert quote.start == 0


def test_recorded_ancestry_rejects_claimed_independence() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q2")
    result = _valid_result("Q2")
    result["assessments"][1]["dependence"] = "no_identified_link"  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="despite recorded ancestry"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]
