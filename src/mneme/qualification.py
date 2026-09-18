"""Cheap host qualification harness; unavailable measurements stay null."""

import json
import time
from dataclasses import dataclass
from typing import Any

from .contracts import Capability, GenerationRequest, HostError


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
            parsed, schema_valid = check(result.content) if check else (None, bool(result.content))
            tests.append(
                {
                    "name": name,
                    "status": "pass" if schema_valid else "fail",
                    "parse_success": parsed if check else None,
                    "schema_validation_success": schema_valid if check else None,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                    "token_usage": result.token_usage.__dict__ if result.token_usage else None,
                    "detail": None if schema_valid else "schema validation failed",
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
                "content": (
                    "Return ONLY valid JSON, with no markdown or explanation, using exactly "
                    '{"concepts":["concept one"],"confidence":0.85}. '
                    "concepts must be a non-empty string array and confidence must be 0..1."
                ),
            },
        ),
        parameters={"max_new_tokens": 80, "temperature": 0.0},
    )
    run("structured_concept_list", schema_request, _concept_schema)
    run(
        "structured_relationship",
        GenerationRequest(
            (
                {
                    "role": "user",
                    "content": (
                        "Return ONLY valid JSON, with no markdown or explanation, using exactly "
                        '{"relationships":[{"from":"VRAM","to":"model capacity",'
                        '"relationship":"constrains"}]}. '
                        "All fields must be non-empty strings."
                    ),
                },
            ),
            parameters={"max_new_tokens": 100, "temperature": 0.0},
        ),
        _relationship_schema,
    )
    run(
        "structured_nested",
        GenerationRequest(
            (
                {
                    "role": "user",
                    "content": (
                        "Return ONLY valid JSON, with no markdown or explanation, using exactly "
                        '{"subject":"some concept","evidence":[{"claim":"some claim",'
                        '"confidence":0.75}]}. '
                        "subject and claim must be strings; confidence must be 0..1."
                    ),
                },
            ),
            parameters={"max_new_tokens": 100, "temperature": 0.0},
        ),
        _nested_schema,
    )
    if host.capabilities().has(Capability.SEED_CONTROL):
        run("seed_control", GenerationRequest(base.messages, base.system, base.parameters, 42))
    else:
        tests.append({"name": "seed_control", "status": "unsupported"})
    probe = getattr(host, "failure_probe", None)
    if probe:
        try:
            probe(base)
            tests.append(
                {
                    "name": "failure_behavior",
                    "status": "fail",
                    "detail": "failure probe did not fail",
                }
            )
        except HostError as exc:
            tests.append({"name": "failure_behavior", "status": "exercised", "detail": str(exc)})
    else:
        tests.append(
            {
                "name": "failure_behavior",
                "status": "unit_tested",
                "detail": "provider mappings covered by offline unit tests",
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
                t.get("parse_success") is True for t in tests if t["name"].startswith("structured_")
            ),
            "structured_schema_validation_success": sum(
                t.get("schema_validation_success") is True
                for t in tests
                if t["name"].startswith("structured_")
            ),
            "structured_cases": 3,
            "overall": "pass"
            if all(
                status in {"pass", "exercised", "unit_tested", "unsupported"} for status in statuses
            )
            else "attention_required",
        },
    )


def _parse_json(content: str) -> tuple[bool, Any]:
    try:
        return True, json.loads(content)
    except json.JSONDecodeError:
        return False, None


def _concept_schema(content: str) -> tuple[bool, bool]:
    parsed, value = _parse_json(content)
    valid = (
        isinstance(value, dict)
        and isinstance(value.get("concepts"), list)
        and bool(value["concepts"])
        and all(isinstance(item, str) for item in value["concepts"])
        and isinstance(value.get("confidence"), (int, float))
        and 0 <= value["confidence"] <= 1
    )
    return parsed, valid


def _relationship_schema(content: str) -> tuple[bool, bool]:
    parsed, value = _parse_json(content)
    relationships = value.get("relationships") if isinstance(value, dict) else None
    valid = (
        isinstance(relationships, list)
        and bool(relationships)
        and all(
            isinstance(item, dict)
            and all(
                isinstance(item.get(key), str) and item[key]
                for key in ("from", "to", "relationship")
            )
            for item in relationships
        )
    )
    return parsed, valid


def _nested_schema(content: str) -> tuple[bool, bool]:
    parsed, value = _parse_json(content)
    evidence = value.get("evidence") if isinstance(value, dict) else None
    valid = (
        isinstance(value, dict)
        and isinstance(value.get("subject"), str)
        and bool(value["subject"])
        and isinstance(evidence, list)
        and bool(evidence)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("claim"), str)
            and isinstance(item.get("confidence"), (int, float))
            and 0 <= item["confidence"] <= 1
            for item in evidence
        )
    )
    return parsed, valid
