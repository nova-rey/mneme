from __future__ import annotations

import json
from dataclasses import replace

import pytest

from mneme.development import (
    AssessorMonitor,
    AssessorValidationError,
    assessor_generation_request,
    qualification_cases,
    read_historical_assessor_result,
    resolve_provenance,
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
    slots: list[str],
    complete: bool,
    reason: str | None = None,
    source_slot: str | None = None,
    quote: str | None = None,
    corresponding: list[str] | None = None,
) -> dict[str, object]:
    evidence = None
    if source_slot is not None or quote is not None:
        evidence = {"source_slot": source_slot, "quote": quote}
    return {
        "monitor_id": monitor_id,
        "status": status,
        "relation_support": support,
        "expression_status": expression,
        "coverage": {"complete": complete, "source_slots": slots, "reason": reason},
        "evidence": evidence,
        "corresponding_source_slots": corresponding or [],
    }


def _valid_result(case_id: str) -> dict[str, object]:
    if case_id == "Q1":
        return {
            "schema_version": "p2-assessor-v5",
            "assessments": [
                _row(
                    "latch", status="present", support="supported", expression="affirmed",
                    slots=["s0"], complete=True,
                    source_slot="s0", quote="Pulling the lever released the latch.",
                ),
                _row(
                    "echo", status="present", support="supported", expression="affirmed",
                    slots=["s0", "s1"], complete=True,
                    source_slot="s1", quote="Pulling the lever released the latch.",
                    corresponding=["s0"],
                ),
                _row(
                    "unrelated", status="absent", support="unsupported", expression="not_expressed",
                    slots=["s0"], complete=True,
                    reason="The source does not mention the unrelated target.",
                ),
            ],
        }
    if case_id == "Q2":
        return {
            "schema_version": "p2-assessor-v5",
            "assessments": [
                _row(
                    "jacket_direction", status="absent", support="unsupported",
                    expression="not_expressed", slots=["s0"],
                    complete=True,
                    reason="The rain-jacket source does not express the candidate direction.",
                ),
                _row(
                    "shade", status="present", support="supported", expression="affirmed",
                    slots=["s1", "s2"], complete=True,
                    source_slot="s2", quote="Turning the handle raises the shade.",
                    corresponding=["s1"],
                ),
            ],
        }
    return {
        "schema_version": "p2-assessor-v5",
        "assessments": [
            _row(
                "dial", status="present", support="contradicted", expression="negated",
                slots=["s0"], complete=True,
                source_slot="s0", quote="did not stop the ticking",
            ),
            _row(
                "unavailable_output", status="unknown", support="unknown", expression="unknown",
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


def test_assessor_prompt_exposes_complete_enum_and_json_contract() -> None:
    request = assessor_generation_request(qualification_cases()[0].request)
    prompt = request.messages[0]["content"]

    assert "Return raw JSON only" in prompt
    assert "Do not use Markdown fences" in prompt
    assert '"schema_version": "p2-assessor-v5"' in prompt
    assert '"assessments": [' in prompt
    for value in ("present", "absent", "unknown"):
        assert value in prompt
    for value in ("supported", "contradicted", "unsupported", "unknown"):
        assert value in prompt
    for value in ("affirmed", "negated", "not_expressed", "unknown"):
        assert value in prompt
    for field in (
        '"monitor_id"',
        '"status"',
        '"relation_support"',
        '"expression_status"',
        '"coverage"',
        '"complete"',
        '"source_slots"',
        '"reason"',
        '"evidence"',
        '"source_slot"',
        '"quote"',
        '"corresponding_source_slots"',
    ):
        assert field in prompt
    assert "evidence_source_slots" in prompt
    assert "correspondence_source_slots" in prompt
    assert "quote the model-output occurrence" in prompt
    assert "no omitted or duplicated monitor IDs" in prompt
    assert "Do not invent enum values" in prompt
    assert "Do not emit dependence labels" in prompt
    assert '"dependence":' not in prompt
    assert "MNEME resolves" in prompt
    assert "Every source with available=true is available" in prompt
    assert "current_input_source_slots" in prompt
    assert "complete monitor proposition" in prompt
    assert "does not support a different target" in prompt
    assert "explicit negation is present evidence, not absence" in prompt


def test_q1_echo_and_q2_exposure_ancestry_are_deterministically_resolved() -> None:
    cases = {case.case_id: case for case in qualification_cases()}
    q1 = validate_qualification_case(cases["Q1"], _valid_result("Q1"))
    echo = {row.monitor_id: row for row in q1}["echo"]
    assert echo.dependence == "current_input_echo"
    assert echo.provenance.credit_eligible is False
    q2 = validate_qualification_case(cases["Q2"], _valid_result("Q2"))
    shade = {row.monitor_id: row for row in q2}["shade"]
    assert shade.dependence == "exposure_linked"
    assert shade.provenance.applicable_categories == ("exposure_linked", "replay_linked")


def test_qualification_requests_preserve_complete_proposition_and_source_roles() -> None:
    cases = {case.case_id: case for case in qualification_cases()}
    q1 = cases["Q1"].request.to_dict()
    assert q1["candidate"] == {"from": "lever", "relation": "causes", "to": "latch_release"}
    assert q1["sources"] == [
        {
            "slot": "s0",
            "role": "external",
            "available": True,
            "text": "Pulling the lever released the latch.",
            "source_id": None,
        },
        {
            "slot": "s1",
            "role": "model_output",
            "available": True,
            "text": "Pulling the lever released the latch.",
            "source_id": None,
        },
    ]
    q2 = cases["Q2"].request.to_dict()
    assert q2["candidate"] == {"from": "rain_jacket", "relation": "raises", "to": "shade"}
    assert {monitor["monitor_id"] for monitor in q2["monitors"]} == {
        "jacket_direction",
        "shade",
    }
    assert q2["memory_exposure"] == [{"source_slot": "s1", "exposure_id": "memory-1"}]
    q3 = cases["Q3"].request.to_dict()
    assert q3["sources"][1]["available"] is False
    assert q3["sources"][1]["role"] == "model_output"
    assert q1["monitors"][1]["relation"] == {
        "from": "lever", "to": "latch_release", "relation": "causes"
    }
    assert q1["monitors"][2]["relation"] == {
        "from": "lever", "to": "unrelated", "relation": "causes"
    }
    assert q2["monitors"][0]["relation"] == {
        "from": "rain_jacket", "to": "shade", "relation": "raises"
    }
    assert q2["monitors"][1]["relation"] == {
        "from": "handle", "to": "shade", "relation": "raises"
    }
    assert q3["monitors"][0]["relation"] == {
        "from": "dial", "to": "ticking", "relation": "stops"
    }
    assert q1["monitors"][0]["evidence_source_slots"] == ["s0"]
    assert q1["monitors"][1]["evidence_source_slots"] == ["s1"]
    assert q1["monitors"][1]["correspondence_source_slots"] == ["s0"]
    assert q2["monitors"][1]["evidence_source_slots"] == ["s2"]
    assert q2["monitors"][1]["correspondence_source_slots"] == ["s1"]


def test_partial_monitor_proposition_is_rejected_before_provider_dispatch() -> None:
    with pytest.raises(AssessorValidationError, match="complete proposition"):
        AssessorMonitor("partial", {"relation": "causes"}, ("s0",), ("s0",))


def test_historical_v4_result_is_readable_only_through_explicit_archive_reader() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    historical = _valid_result("Q1")
    historical["schema_version"] = "p2-assessor-v4"
    for row in historical["assessments"]:  # type: ignore[union-attr]
        if row["expression_status"] == "affirmed":  # type: ignore[index]
            row["expression_status"] = "expressed"  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="unsupported assessor result schema"):
        validate_assessor_result(case.request, historical)  # type: ignore[arg-type]
    rows = read_historical_assessor_result(case.request, historical)  # type: ignore[arg-type]
    assert next(row for row in rows if row.monitor_id == "latch").expression_status == "expressed"


def test_present_requires_complete_available_coverage() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    result = _valid_result("Q1")
    echo = result["assessments"][1]  # type: ignore[index]
    echo["coverage"] = {  # type: ignore[index]
        "complete": False,
        "source_slots": ["s1"],
        "reason": "s0 was omitted",
    }
    with pytest.raises(AssessorValidationError, match="present requires complete coverage"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]


def test_monitor_proposition_is_frozen_before_provider_serialization() -> None:
    relation = {"from": "lever", "to": "latch_release", "relation": "causes"}
    monitor = AssessorMonitor("latch", relation, ("s0",), ("s0",))
    relation.pop("to")
    assert monitor.to_dict()["relation"] == {
        "from": "lever", "to": "latch_release", "relation": "causes"
    }


def test_all_qualification_monitors_serialize_complete_propositions() -> None:
    for case in qualification_cases():
        for monitor in case.request.monitors:
            assert set(monitor.relation) >= {"from", "to", "relation"}


def test_monitor_source_roles_are_fail_closed() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    invalid_evidence = _valid_result("Q1")
    echo = invalid_evidence["assessments"][1]  # type: ignore[index]
    echo["evidence"]["source_slot"] = "s0"  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="non-evidence source slot"):
        validate_assessor_result(case.request, invalid_evidence)  # type: ignore[arg-type]

    invalid_correspondence = _valid_result("Q1")
    echo = invalid_correspondence["assessments"][1]  # type: ignore[index]
    echo["corresponding_source_slots"] = ["s1"]  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="undeclared source slot"):
        validate_assessor_result(case.request, invalid_correspondence)  # type: ignore[arg-type]


def test_q3_negation_quote_and_unavailable_source_are_fail_closed() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q3")
    rows = validate_qualification_case(case, _valid_result("Q3"))
    dial = next(row for row in rows if row.monitor_id == "dial")
    assert dial.evidence is not None
    assert dial.evidence.start == case.request.sources[0].text.index("did not stop")
    assert dial.relation_support == "contradicted"
    assert dial.expression_status == "negated"
    assert dial.provenance.credit_eligible is False
    unknown = next(row for row in rows if row.monitor_id == "unavailable_output")
    assert unknown.status == "unknown"
    assert unknown.evidence is None


def test_semantic_matrix_distinguishes_affirmation_negation_absence_and_unknown() -> None:
    cases = {case.case_id: case for case in qualification_cases()}
    positive = validate_assessor_result(cases["Q1"].request, _valid_result("Q1"))
    latch = next(row for row in positive if row.monitor_id == "latch")
    assert (latch.status, latch.relation_support, latch.expression_status) == (
        "present",
        "supported",
        "affirmed",
    )
    negated = validate_assessor_result(cases["Q3"].request, _valid_result("Q3"))
    dial = next(row for row in negated if row.monitor_id == "dial")
    assert (dial.status, dial.relation_support, dial.expression_status) == (
        "present",
        "contradicted",
        "negated",
    )
    absent = next(row for row in positive if row.monitor_id == "unrelated")
    assert (absent.status, absent.relation_support, absent.expression_status) == (
        "absent",
        "unsupported",
        "not_expressed",
    )
    unknown = next(row for row in negated if row.monitor_id == "unavailable_output")
    assert (unknown.status, unknown.relation_support, unknown.expression_status) == (
        "unknown",
        "unknown",
        "unknown",
    )


@pytest.mark.parametrize(
    ("status", "support", "expression"),
    (
        ("absent", "supported", "not_expressed"),
        ("absent", "contradicted", "not_expressed"),
        ("present", "unsupported", "not_expressed"),
        ("present", "supported", "negated"),
        ("present", "contradicted", "affirmed"),
        ("unknown", "unsupported", "unknown"),
    ),
)
def test_semantic_matrix_rejects_cross_field_contradictions(
    status: str, support: str, expression: str
) -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q3")
    result = _valid_result("Q3")
    row = result["assessments"][0]  # type: ignore[index]
    row["status"] = status  # type: ignore[index]
    row["relation_support"] = support  # type: ignore[index]
    row["expression_status"] = expression  # type: ignore[index]
    if status != "present":
        row["evidence"] = None  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="requires"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]


def test_present_unsupported_can_record_ambiguous_addressing_without_false_absence() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q3")
    request = replace(
        case.request,
        sources=(
            replace(case.request.sources[0], text="I turned the dial."),
            case.request.sources[1],
        ),
    )
    result = _valid_result("Q3")
    row = result["assessments"][0]  # type: ignore[index]
    row["status"] = "present"  # type: ignore[index]
    row["relation_support"] = "unsupported"  # type: ignore[index]
    row["expression_status"] = "unknown"  # type: ignore[index]
    row["evidence"]["quote"] = "I turned the dial."  # type: ignore[index]
    validated = validate_assessor_result(request, result)  # type: ignore[arg-type]
    dial = next(item for item in validated if item.monitor_id == "dial")
    assert dial.status == "present"
    assert dial.relation_support == "unsupported"
    assert dial.expression_status == "unknown"


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
    with pytest.raises(AssessorValidationError, match="non-evidence source slot"):
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


def test_assessor_cannot_supply_or_override_provenance_labels() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q2")
    result = _valid_result("Q2")
    result["assessments"][1]["dependence"] = "no_identified_link"  # type: ignore[index]
    with pytest.raises(AssessorValidationError, match="unknown field.*dependence"):
        validate_assessor_result(case.request, result)  # type: ignore[arg-type]


def test_recorded_ancestry_is_scoped_to_referenced_monitor_sources() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q2")
    result = _valid_result("Q2")
    rows = validate_qualification_case(case, result)
    jacket = next(row for row in rows if row.monitor_id == "jacket_direction")
    assert jacket.dependence == "unknown"


def test_external_precedence_ignores_replay_metadata_on_other_slots() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    request = replace(
        case.request,
        replay_ancestry=(
            {"source_slot": "s1", "root": "replay-root"},
            {"source_slot": "s0", "root": "carryover-metadata"},
        ),
    )
    rows = validate_qualification_case(replace(case, request=request), _valid_result("Q1"))
    assert {row.monitor_id: row.dependence for row in rows} == {
        "latch": "external_supported",
        "echo": "current_input_echo",
        "unrelated": "unknown",
    }


def test_missing_correspondence_is_no_identified_link_without_optimistic_credit() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    result = _valid_result("Q1")
    result["assessments"][1]["corresponding_source_slots"] = []  # type: ignore[index]
    semantic = validate_assessor_result(case.request, result)
    rows = resolve_provenance(case.request, semantic)
    echo = next(row for row in rows if row.monitor_id == "echo")
    assert echo.dependence == "no_identified_link"


def test_external_antecedent_not_marked_echo_without_current_input_binding() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    request = replace(case.request, context={})
    semantic = validate_assessor_result(request, _valid_result("Q1"))
    rows = resolve_provenance(request, semantic)
    echo = next(row for row in rows if row.monitor_id == "echo")
    assert echo.dependence == "no_identified_link"


def test_replay_only_and_multiple_ancestry_roots_are_preserved() -> None:
    case = next(case for case in qualification_cases() if case.case_id == "Q2")
    request = replace(
        case.request,
        memory_exposure=(),
        replay_ancestry=({"source_slot": "s1", "root": "replay-root"},),
    )
    semantic = validate_assessor_result(request, _valid_result("Q2"))
    rows = resolve_provenance(request, semantic)
    shade = next(row for row in rows if row.monitor_id == "shade")
    assert shade.dependence == "replay_linked"
    assert shade.provenance.ancestry == ({"source_slot": "s1", "root": "replay-root"},)
