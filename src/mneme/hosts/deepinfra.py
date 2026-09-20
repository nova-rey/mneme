"""DeepInfra's OpenAI-compatible chat-completions hosts.

The transport is shared, but model-family configuration stays explicit so a
Qwen assessor cannot be mislabeled with Gemma provenance.
"""

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
class DeepInfraChatHost:
    """Provider-neutral configuration for one DeepInfra chat model."""

    model_id: str = "google/gemma-4-E4B-it"
    model_family: str = "Gemma 4 E4B IT"
    upstream_model_id: str | None = "google/gemma-4-E4B-it"
    canonical_revision: str | None = None
    tokenizer_id: str | None = None
    tokenizer_revision: str | None = None
    quantization: str | None = "unknown/provider-managed"
    context_length: int | None = None
    token: str | None = None
    endpoint: str = "https://api.deepinfra.com/v1/openai/chat/completions"
    timeout_seconds: float = 120.0

    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.TOKEN_USAGE}))

    def fingerprint(self) -> HostFingerprint:
        execution: dict[str, Any] = {
            "base_url": "https://api.deepinfra.com/v1/openai",
            "endpoint": self.endpoint,
            "rendering_mode": "deepinfra_openai_chat",
            "canonical_upstream_model": self.upstream_model_id,
            "hosted_model_revision": "unknown",
            "catalog_quantization": self.quantization,
            "service_tier": "standard",
        }
        if self.context_length is not None:
            execution["catalog_context_length"] = self.context_length
        return HostFingerprint(
            self.model_family,
            self.model_id,
            None,
            self.tokenizer_id,
            self.tokenizer_revision or self.canonical_revision,
            "deepinfra_openai_chat",
            self.quantization,
            "deepinfra-openai-compatible",
            None,
            "DeepInfra",
            execution,
            self.capabilities().supported,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.capabilities().require(Capability.TEXT_GENERATION)
        if request.seed is not None:
            raise HostError("DeepInfra seed control is not advertised or verified")
        if request.response_format is not None:
            raise HostError(
                "DeepInfra native response_format is not used by this host; "
                "use prompted JSON and local validation"
            )
        token = self.token or os.getenv("DEEPINFRA_TOKEN")
        if not token:
            raise HostError("DEEPINFRA_TOKEN is required for DeepInfra inference")
        params = _parameters(request.parameters)
        body = json.dumps(
            {"model": self.model_id, "messages": _provider_messages(request), **params}
        ).encode()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(self.endpoint, body, headers, method="POST")
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
            raise HostError(f"DeepInfra provider request failed: {exc}") from exc
        content, metadata = _parse_response(raw)
        return GenerationResult(
            content,
            self.model_id,
            "DeepInfra",
            params,
            None,
            _usage(metadata),
            (time.perf_counter() - started) * 1000,
            metadata.get("choices", [{}])[0].get("finish_reason"),
            metadata,
            {
                "host": self.fingerprint().to_dict(),
                "request_chars": sum(
                    len(message["content"]) for message in _provider_messages(request)
                ),
            },
        )


@dataclass
class DeepInfraGemmaHost(DeepInfraChatHost):
    """The existing developing Gemma binding, preserved for compatibility."""

    model_id: str = "google/gemma-4-E4B-it"
    model_family: str = "Gemma 4 E4B IT"
    upstream_model_id: str | None = "google/gemma-4-E4B-it"
    canonical_revision: str | None = "ee0ef6023621cff504d758262d4e04895a5af4a2"
    tokenizer_id: str | None = "google/gemma-4-E4B-it"
    tokenizer_revision: str | None = None
    quantization: str | None = "unknown/provider-managed"
    context_length: int | None = 131072


@dataclass
class DeepInfraQwenAssessorHost(DeepInfraChatHost):
    """The designated semantic assessor binding for P2 role separation."""

    model_id: str = "Qwen/Qwen3-235B-A22B-Instruct-2507"
    model_family: str = "Qwen3 235B A22B Instruct 2507"
    upstream_model_id: str | None = "Qwen/Qwen3-235B-A22B-Instruct-2507"
    canonical_revision: str | None = None
    tokenizer_id: str | None = None
    tokenizer_revision: str | None = None
    quantization: str | None = "fp8"
    context_length: int | None = 262144


def _parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    result = dict(parameters)
    if "max_new_tokens" in result:
        result["max_tokens"] = result.pop("max_new_tokens")
    return result


def _provider_messages(request: GenerationRequest) -> list[dict[str, str]]:
    """Render the provider-visible message list without duplicating ``system``."""

    messages = [dict(message) for message in request.messages]
    if request.system is None:
        return messages

    rendered = {"role": "system", "content": request.system}
    result: list[dict[str, str]] = []
    system_seen = False
    for message in messages:
        if (
            message.get("role") == "system"
            and message.get("content") == request.system
        ):
            if system_seen:
                continue
            system_seen = True
        result.append(message)
    if not system_seen:
        result.insert(0, rendered)
    return result


def _parse_response(raw: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(raw, dict) and raw.get("error"):
        error = raw["error"]
        raise HostError(str(error.get("message", error) if isinstance(error, dict) else error))
    try:
        choice = raw["choices"][0]
        message = choice["message"]
        content = message.get("content")
        if not isinstance(content, str):
            raise TypeError("assistant message content is not text")
        return content, raw
    except (KeyError, IndexError, TypeError) as exc:
        raise HostError("DeepInfra returned an unsupported response shape") from exc


def _usage(metadata: dict[str, Any]) -> TokenUsage | None:
    usage = metadata.get("usage")
    if not isinstance(usage, dict):
        return None
    return TokenUsage(
        usage.get("prompt_tokens"),
        usage.get("completion_tokens"),
        usage.get("total_tokens"),
    )
