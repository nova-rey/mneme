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


def test_local_nli_assessor_uses_relation_cues_for_supported_paraphrase() -> None:
    class EntailingBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            return tuple(NliScores(0.96, 0.01, 0.03) for _ in pairs)

    relation = {"from": "cloth wick", "relation": "maintains", "to": "soil moisture"}
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource(
                "s0",
                "external",
                True,
                "A strip of fabric kept the potting mix moist.",
            ),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0",), ("s0",)),),
    )
    result = json.loads(
        LocalNliAssessorHost(EntailingBackend()).generate(
            assessor_generation_request(request)
        ).content
    )["assessments"][0]
    assert result["relation_support"] == "supported"


def test_local_nli_assessor_preserves_contradicted_outcome_without_nli_margin() -> None:
    class NeutralBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            return tuple(NliScores(0.20, 0.10, 0.70) for _ in pairs)

    relation = {"from": "cloth wick", "relation": "maintains", "to": "soil moisture"}
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource("s0", "external", True, "The wick failed and the soil dried out."),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0",), ("s0",)),),
    )
    result = json.loads(
        LocalNliAssessorHost(NeutralBackend()).generate(
            assessor_generation_request(request)
        ).content
    )["assessments"][0]
    assert result["relation_support"] == "contradicted"
    assert result["expression_status"] == "negated"


def test_local_nli_assessor_does_not_turn_lexical_overlap_into_causal_support() -> None:
    class EntailingBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            return tuple(NliScores(0.96, 0.01, 0.03) for _ in pairs)

    relation = {"from": "cloth wick", "relation": "causes", "to": "soil moisture"}
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource(
                "s0",
                "external",
                True,
                "The cloth wick was made from cotton, and the soil was damp.",
            ),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0",), ("s0",)),),
    )
    result = json.loads(
        LocalNliAssessorHost(EntailingBackend()).generate(
            assessor_generation_request(request)
        ).content
    )["assessments"][0]
    assert result["relation_support"] == "unsupported"


def test_local_nli_assessor_prefers_relevant_source_over_unrelated_question_context() -> None:
    class MixedBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            values = []
            for premise, _ in pairs:
                if "balcony" in premise:
                    values.append(NliScores(0.01, 0.68, 0.31))
                else:
                    values.append(NliScores(0.59, 0.02, 0.39))
            return tuple(values)

    relation = {"from": "Drip Irrigation", "relation": "causes", "to": "Slow Leak"}
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource(
                "s0",
                "external",
                True,
                "My balcony pots dry out. How would you make watering reliable?",
            ),
            AssessorSource(
                "s1",
                "model_output",
                True,
                "Drip Irrigation (The Slow Leak) creates a slow-release system.",
            ),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0", "s1"), ("s0", "s1")),),
    )
    result = json.loads(
        LocalNliAssessorHost(MixedBackend()).generate(
            assessor_generation_request(request)
        ).content
    )["assessments"][0]
    assert result["relation_support"] == "supported"
    assert result["evidence"]["source_slot"] == "s1"


def test_local_nli_scopes_uncertainty_to_the_selected_evidence_window() -> None:
    class EntailingBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            return tuple(NliScores(0.97, 0.01, 0.02) for _ in pairs)

    relation = {"from": "reliable enough", "relation": "depends_on", "to": "load"}
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource("s0", "external", True, "I am planning a remote workshop."),
            AssessorSource(
                "s1",
                "model_output",
                True,
                'However, "reliable enough" really depends on the *load*.',
            ),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0", "s1"), ("s0", "s1")),),
    )
    row = json.loads(
        LocalNliAssessorHost(EntailingBackend()).generate(
            assessor_generation_request(request)
        ).content
    )["assessments"][0]
    assert row["relation_support"] == "supported"
    assert row["evidence"]["source_slot"] == "s1"


def test_local_nli_normalizes_markdown_residue_without_mutating_evidence() -> None:
    class RecordingBackend(QualificationBackend):
        seen: list[str] = []

        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            self.seen.extend(hypothesis for _premise, hypothesis in pairs)
            return tuple(NliScores(0.97, 0.01, 0.02) for _ in pairs)

    backend = RecordingBackend()
    relation = {"from": "success", "relation": "depends_on", "to": "usage* profile"}
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource(
                "s0",
                "model_output",
                True,
                "The success of that entire setup depends heavily on your *usage* profile.",
            ),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0",), ("s0",)),),
    )
    row = json.loads(
        LocalNliAssessorHost(backend).generate(assessor_generation_request(request)).content
    )["assessments"][0]
    assert row["relation_support"] == "supported"
    assert any("usage profile" in hypothesis for hypothesis in backend.seen)
    assert "*usage* profile" in row["evidence"]["quote"]


def test_local_nli_recognizes_holds_as_retention() -> None:
    class EntailingBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            return tuple(NliScores(0.98, 0.01, 0.01) for _ in pairs)

    relation = {"from": "saturated soil", "relation": "retains", "to": "moisture"}
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource(
                "s0", "model_output", True, "Deep, saturated soil holds moisture much longer."
            ),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0",), ("s0",)),),
    )
    row = json.loads(
        LocalNliAssessorHost(EntailingBackend()).generate(assessor_generation_request(request)).content
    )["assessments"][0]
    assert row["relation_support"] == "supported"


def test_local_nli_does_not_accept_part_of_from_cooccurrence_alone() -> None:
    class EntailingBackend(QualificationBackend):
        def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[NliScores, ...]:
            return tuple(NliScores(0.97, 0.01, 0.02) for _ in pairs)

    relation = {
        "from": "Drip Irrigation",
        "relation": "part_of",
        "to": "ordinary household materials",
    }
    request = AssessorRequest(
        candidate=relation,
        sources=(
            AssessorSource(
                "s0",
                "model_output",
                True,
                (
                    "Drip Irrigation is a slow-release system; ordinary household materials "
                    "can make a wick."
                ),
            ),
        ),
        monitors=(AssessorMonitor("candidate", relation, ("s0",), ("s0",)),),
    )
    row = json.loads(
        LocalNliAssessorHost(EntailingBackend()).generate(assessor_generation_request(request)).content
    )["assessments"][0]
    assert row["relation_support"] == "unsupported"
