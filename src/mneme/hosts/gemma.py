"""Gemma host with an optional hosted Hugging Face inference backend."""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

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
class GemmaHost:
    model_id: str = "google/gemma-4-E4B-it"
    token: str | None = None
    provider: str | None = None
    revision: str | None = None
    endpoint: str | None = None
    timeout_seconds: float = 120.0

    def capabilities(self) -> HostCapabilities:
        caps = {Capability.TEXT_GENERATION}
        # The hosted API can report usage, but seed/logprob/tokenizer support is provider-specific.
        return HostCapabilities(frozenset(caps))

    def fingerprint(self) -> HostFingerprint:
        return HostFingerprint(
            "Gemma 4",
            self.model_id,
            self.revision,
            self.model_id,
            self.revision,
            "mneme_fallback_transcript_v1",
            None,
            "huggingface-inference",
            None,
            self.provider or "huggingface",
            {
                "endpoint": self.endpoint
                or f"https://api-inference.huggingface.co/models/{self.model_id}",
                "rendering_mode": "mneme_fallback_transcript_v1",
            },
            self.capabilities().supported,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.capabilities().require(Capability.TEXT_GENERATION)
        if request.seed is not None:
            self.capabilities().require(Capability.SEED_CONTROL)
        endpoint = self.endpoint or f"https://api-inference.huggingface.co/models/{self.model_id}"
        token = self.token or os.getenv("MNEME_HF_TOKEN")
        if not token:
            raise HostError("MNEME_HF_TOKEN is required for hosted Gemma inference")
        prompt = _render_messages(request)
        params = dict(request.parameters)
        # response_format is intentionally not forwarded: this backend has no verified
        # native schema-constrained generation contract.
        body = json.dumps({"inputs": prompt, "parameters": params}).encode()
        req = urllib.request.Request(
            endpoint,
            body,
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read())
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            raise HostError(f"Gemma provider request failed: {exc}") from exc
        latency = (time.perf_counter() - started) * 1000
        content, metadata = _parse_response(raw)
        return GenerationResult(
            content,
            self.model_id,
            self.provider or "huggingface",
            params,
            None,
            _usage(metadata),
            latency,
            metadata.get("finish_reason"),
            metadata,
            {"host": self.fingerprint().to_dict(), "request_chars": len(prompt)},
        )


def _render_messages(request: GenerationRequest) -> str:
    parts = ([request.system] if request.system else []) + [
        f"{m['role']}: {m['content']}" for m in request.messages
    ]
    return "\n".join(parts)


def _parse_response(raw: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        item = raw[0]
        return str(item.get("generated_text", item.get("text", ""))), item
    if isinstance(raw, dict) and "error" in raw:
        raise HostError(str(raw["error"]))
    if isinstance(raw, dict):
        return str(raw.get("generated_text", raw.get("text", ""))), raw
    raise HostError("Gemma provider returned an unsupported response shape")


def _usage(metadata: dict[str, Any]) -> TokenUsage | None:
    usage = metadata.get("usage") or metadata.get("details")
    if not isinstance(usage, dict):
        return None
    return TokenUsage(
        usage.get("prompt_tokens") or usage.get("input_tokens"),
        usage.get("completion_tokens") or usage.get("output_tokens"),
        usage.get("total_tokens"),
    )
