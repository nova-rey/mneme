"""Deterministic, dependency-free host for infrastructure tests."""

import hashlib
import json
import time
from dataclasses import dataclass

from ..contracts import (
    Capability,
    GenerationRequest,
    GenerationResult,
    HostCapabilities,
    HostError,
    HostFingerprint,
    TokenUsage,
)


@dataclass
class FakeHost:
    model_id: str = "mneme-fake-v1"
    fail: bool = False
    delay_seconds: float = 0.0
    omit_capabilities: frozenset[Capability] = frozenset()

    def capabilities(self) -> HostCapabilities:
        all_caps = {
            Capability.TEXT_GENERATION,
            Capability.SEED_CONTROL,
            Capability.STRUCTURED_OUTPUT,
            Capability.TOKEN_USAGE,
        }
        return HostCapabilities(frozenset(all_caps - set(self.omit_capabilities)))

    def fingerprint(self) -> HostFingerprint:
        return HostFingerprint(
            "fake",
            self.model_id,
            "stable",
            "fake-tokenizer",
            "stable",
            "fake-v1",
            None,
            "mneme-fake",
            "0.1.0",
            "builtin",
            {"deterministic": True},
            self.capabilities().supported,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.fail:
            raise HostError("FakeHost configured to fail")
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        self.capabilities().require(Capability.TEXT_GENERATION)
        if request.seed is not None:
            self.capabilities().require(Capability.SEED_CONTROL)
        payload = json.dumps(request.generation_material(), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{request.seed}|{payload}".encode()).hexdigest()[:16]
        if request.response_format and request.response_format.get("type") == "json_schema":
            content = json.dumps(
                {"concepts": ["deterministic fixture"], "confidence": 0.9, "seed_digest": digest}
            )
        elif "concepts" in payload:
            content = json.dumps({"concepts": ["deterministic fixture"], "confidence": 0.9})
        elif "relationships" in payload:
            content = json.dumps(
                {
                    "relationships": [
                        {"from": "VRAM", "to": "model capacity", "relationship": "constrains"}
                    ]
                }
            )
        elif "evidence" in payload:
            content = json.dumps(
                {"subject": "laboratory", "evidence": [{"claim": "testable", "confidence": 0.8}]}
            )
        else:
            content = f"FakeHost response [{digest}]"
        return GenerationResult(
            content,
            self.model_id,
            "builtin",
            dict(request.parameters),
            request.seed,
            TokenUsage(
                len(payload.split()),
                len(content.split()),
                len(payload.split()) + len(content.split()),
            ),
            self.delay_seconds * 1000,
            "stop",
            {"fake": True},
            {
                "host": self.fingerprint().to_dict(),
                "request_hash": hashlib.sha256(payload.encode()).hexdigest(),
            },
        )

    def failure_probe(self, request: GenerationRequest) -> None:
        """Exercise the intentional failure mode for qualification."""
        FakeHost(fail=True).generate(request)
