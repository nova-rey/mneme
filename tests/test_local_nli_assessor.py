from __future__ import annotations

import json
from collections.abc import Sequence

from mneme.development.assessment import (
    AssessorMonitor,
    AssessorRequest,
    AssessorSource,
    assessor_generation_request,
    qualification_cases,
    validate_qualification_case,
)
from mneme.hosts.local_nli import (
    LOCAL_NLI_VERSION,
    LocalNliAssessorHost,
    NliScores,
)


class QualificationBackend:
    model_id = "cross-encoder/nli-deberta-v3-xsmall"
    model_revision = "fixture-revision"
    runtime_version = "fixture"

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
        results: list[NliScores] = []
        for premise, hypothesis in pairs:
            lower_premise = premise.casefold()
            lower_hypothesis = hypothesis.casefold()
            if "unrelated" in lower_hypothesis or "rain_jacket" in lower_hypothesis:
                results.append(NliScores(0.02, 0.03, 0.95))
            elif "did not stop" in lower_premise:
                results.append(NliScores(0.01, 0.96, 0.03))
            elif "released the latch" in lower_premise or "raises the shade" in lower_premise:
                results.append(NliScores(0.96, 0.01, 0.03))
            else:
                results.append(NliScores(0.02, 0.03, 0.95))
        return tuple(results)


def test_local_nli_assessor_adapts_the_frozen_qualification_contract() -> None:
    host = LocalNliAssessorHost(QualificationBackend())
    for case in qualification_cases():
        generated = host.generate(assessor_generation_request(case.request))
        validated = validate_qualification_case(case, json.loads(generated.content))
        assert len(validated) == len(case.request.monitors)
    assert generated.raw_metadata["assessor_version"] == LOCAL_NLI_VERSION


def test_local_nli_assessor_distinguishes_negation_and_missing_coverage() -> None:
    host = LocalNliAssessorHost(QualificationBackend())
    case = next(case for case in qualification_cases() if case.case_id == "Q3")
    result = json.loads(host.generate(assessor_generation_request(case.request)).content)
    dial = next(row for row in result["assessments"] if row["monitor_id"] == "dial")
    unavailable = next(
        row for row in result["assessments"] if row["monitor_id"] == "unavailable_output"
    )
    assert dial["relation_support"] == "contradicted"
    assert dial["expression_status"] == "negated"
    assert unavailable["status"] == "unknown"


def test_local_nli_assessor_preserves_multi_window_coverage() -> None:
    host = LocalNliAssessorHost(QualificationBackend(), max_window_chars=20, overlap_chars=5)
    case = next(case for case in qualification_cases() if case.case_id == "Q1")
    result = json.loads(host.generate(assessor_generation_request(case.request)).content)
    latch = next(row for row in result["assessments"] if row["monitor_id"] == "latch")
    assert latch["status"] == "present"
    assert latch["evidence"]["source_slot"] == "s0"


def test_local_nli_assessor_keeps_addressed_but_unsupported_relation() -> None:
    class NeutralBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            return tuple(NliScores(0.02, 0.03, 0.95) for _ in pairs)

    request = AssessorRequest(
        candidate={"from": "cloth wick", "relation": "maintains", "to": "soil moisture"},
        sources=(
            AssessorSource(
                "s0",
                "external",
                True,
                "The cloth wick measured the soil moisture.",
            ),
        ),
        monitors=(
            AssessorMonitor(
                "candidate",
                {"from": "cloth wick", "relation": "maintains", "to": "soil moisture"},
                ("s0",),
                ("s0",),
            ),
        ),
    )
    result = json.loads(
        LocalNliAssessorHost(NeutralBackend()).generate(
            assessor_generation_request(request)
        ).content
    )
    row = result["assessments"][0]
    assert row["status"] == "present"
    assert row["relation_support"] == "unsupported"
    assert row["expression_status"] == "unknown"
