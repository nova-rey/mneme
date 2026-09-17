"""Cheap host qualification harness; unavailable measurements stay null."""

import json
import time
from dataclasses import dataclass
from typing import Any

from .contracts import Capability, GenerationRequest


@dataclass
class QualificationReport:
    host: dict[str, Any]
    capabilities: list[str]
    tests: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "qualification_version": "0.1",
            "host": self.host,
            "capabilities": self.capabilities,
            "tests": self.tests,
            "summary": self.summary,
        }

    def text(self) -> str:
        lines = [
            "MNEME host qualification",
            f"Model: {self.host['model_id']}",
            f"Provider: {self.host['provider']}",
            f"Capabilities: {', '.join(self.capabilities) or 'none'}",
            "",
        ]
        for test in self.tests:
            lines.append(
                f"- {test['name']}: {test['status']}"
                + (f" ({test.get('detail')})" if test.get("detail") else "")
            )
        lines += [
            "",
            "Measurements are reported only when the host exposes them.",
            json.dumps(self.summary, sort_keys=True),
        ]
        return "\n".join(lines) + "\n"


def qualify(host: Any) -> QualificationReport:
    tests: list[dict[str, Any]] = []

    def run(name: str, request: GenerationRequest, check: Any = None) -> None:
        started = time.perf_counter()
        try:
            result = host.generate(request)
            ok = check(result.content) if check else bool(result.content)
            tests.append(
                {
                    "name": name,
                    "status": "pass" if ok else "fail",
                    "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                    "token_usage": result.token_usage.__dict__ if result.token_usage else None,
                    "detail": None if ok else "validation failed",
                }
            )
        except Exception as exc:  # qualification must report provider failures
            tests.append(
                {
                    "name": name,
                    "status": "error",
                    "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                    "error": str(exc),
                }
            )

    base = GenerationRequest(
        ({"role": "user", "content": "Reply with one short sentence about a laboratory."},),
        parameters={"max_new_tokens": 64},
        seed=None,
    )
    run("basic_generation", base)
    run(
        "multi_turn",
        GenerationRequest(
            (
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "Four."},
                {"role": "user", "content": "Answer with just the number."},
            ),
            parameters={"max_new_tokens": 8},
        ),
    )
    schema_request = GenerationRequest(
        (
            {
                "role": "user",
                "content": "Return JSON with concepts and confidence.",
            },
        ),
        parameters={"max_new_tokens": 80},
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "concepts", "schema": {"type": "object"}},
        },
    )
    run("structured_concept_list", schema_request, _json_object)
    run(
        "structured_relationship",
        GenerationRequest(
            ({"role": "user", "content": "Return JSON with relationships as an array."},),
            response_format=schema_request.response_format,
        ),
        _json_object,
    )
    run(
        "structured_nested",
        GenerationRequest(
            ({"role": "user", "content": "Return nested JSON with a subject and evidence."},),
            response_format=schema_request.response_format,
        ),
        _json_object,
    )
    if host.capabilities().has(Capability.SEED_CONTROL):
        run("seed_control", GenerationRequest(base.messages, base.system, base.parameters, 42))
    else:
        tests.append({"name": "seed_control", "status": "unsupported"})
    tests.append(
        {
            "name": "failure_behavior",
            "status": "not_exercised",
            "detail": "provider errors are mapped by the host boundary",
        }
    )
    statuses = [t["status"] for t in tests]
    return QualificationReport(
        host.fingerprint().to_dict(),
        host.capabilities().to_dict(),
        tests,
        {
            "latency_ms": [t.get("latency_ms") for t in tests if t.get("latency_ms") is not None],
            "structured_parse_success": sum(
                t["status"] == "pass" for t in tests if t["name"].startswith("structured_")
            ),
            "structured_cases": 3,
            "overall": "pass"
            if "error" not in statuses and "fail" not in statuses
            else "attention_required",
        },
    )


def _json_object(content: str) -> bool:
    try:
        value = json.loads(content)
        return isinstance(value, dict)
    except json.JSONDecodeError:
        return False
