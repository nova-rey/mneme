"""The fixed, production-shaped Phase Two assessor qualification gate."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from ..contracts import GenerationResult
from ..development.assessment import (
    AssessorValidationError,
    ResolvedAssessment,
    assessor_generation_request,
    qualification_cases,
    validate_qualification_case,
)
from ..host import Host
from .pilot import PilotError, PilotRun


def _result_payload(
    result: GenerationResult,
) -> tuple[dict[str, Any], dict[str, Any] | None, int | None]:
    usage = asdict(result.token_usage) if result.token_usage is not None else None
    output_tokens = usage.get("output_tokens") if usage is not None else None
    return (
        {
            "content": result.content,
            "model_id": result.model_id,
            "provider": result.provider,
            "finish_reason": result.finish_reason,
            "seed": result.seed,
            "usage": usage,
            "provenance": result.provenance,
        },
        usage,
        output_tokens if isinstance(output_tokens, int) else None,
    )


def run_assessor_qualification(
    pilot: PilotRun,
    host: Host | None = None,
    *,
    assessor_host: Host | None = None,
    max_output_tokens: int = 1_536,
) -> dict[str, Any]:
    """Run the fixed Q1/Q2/Q3 qualification in order, stopping on failure.

    Each returned provider result is durably recorded before local semantic
    validation. Developmental provenance is resolved afterward from the
    immutable request/runtime records and is persisted separately. A provider
    exception is uncertain and terminal; it is never regenerated. Invalid
    results are retained and qualification completes immediately after the
    failing case.
    """

    if host is not None and assessor_host is not None:
        raise PilotError("supply host or assessor_host, not both")
    selected_host = assessor_host or host
    if selected_host is None:
        raise PilotError("assessor host is required")
    configured = pilot.require_role_host("assessor", selected_host)
    pilot.begin_qualification()
    case_results: list[dict[str, Any]] = []
    all_valid = True
    for case in qualification_cases():
        call_id = f"assessor-{case.case_id.lower()}"
        request = assessor_generation_request(case.request, max_new_tokens=max_output_tokens)
        pilot.reserve_call(
            call_id=call_id,
            role="assessor-qualification",
            coordinate={"case": case.case_id},
            max_output_tokens=max_output_tokens,
        )
        expected_fingerprint = configured.get("fingerprint")
        pilot.dispatch_call(
            call_id,
            expected_host_fingerprint=expected_fingerprint
            if isinstance(expected_fingerprint, dict)
            else None,
        )
        try:
            generated = selected_host.generate(request)
        except Exception as exc:
            pilot.mark_uncertain(call_id, f"provider outcome uncertain: {type(exc).__name__}")
            pilot.fail(
                "qualification provider outcome is uncertain",
                details={"case": case.case_id},
            )
            raise PilotError(f"qualification call {case.case_id} is UNCERTAIN") from exc
        payload, usage, output_tokens = _result_payload(generated)
        pilot.return_call(
            call_id,
            result=payload,
            usage=usage,
            output_tokens=output_tokens,
            actual_host_fingerprint=(
                generated.provenance.get("host")
                if isinstance(generated.provenance.get("host"), dict)
                else None
            ),
        )
        valid = True
        error: str | None = None
        validated: tuple[ResolvedAssessment, ...] = ()
        try:
            pilot.assert_returned_host(call_id)
            decoded = json.loads(generated.content)
            if not isinstance(decoded, dict):
                raise AssessorValidationError("assessor result must be a JSON object")
            validated = validate_qualification_case(case, decoded)
            canonical = [item.to_dict() for item in validated]
        except (AssessorValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
            valid = False
            all_valid = False
            error = str(exc)
            canonical = []
        pilot.publish_artifact(
            "qualification",
            f"{case.case_id.lower()}.json",
            {
                "case_id": case.case_id,
                "assessor_binding": configured,
                "request": case.request.to_dict(),
                "result": payload,
                "valid": valid,
                "validation_error": error,
                "validated": canonical,
                "semantic_observations": [item.semantic.to_dict() for item in validated]
                if valid
                else [],
                "provenance_resolution": [item.provenance.to_dict() for item in validated]
                if valid
                else [],
            },
        )
        case_results.append(
            {"case_id": case.case_id, "valid": valid, "validation_error": error}
        )
        if not valid:
            final = pilot.complete_qualification(
                passed=False,
                details={"cases": case_results, "stopped_after": case.case_id},
            )
            return {"status": final["status"], "cases": case_results}
    final = pilot.complete_qualification(passed=all_valid, details={"cases": case_results})
    return {"status": final["status"], "cases": case_results}


__all__ = ["run_assessor_qualification"]
