"""DeepInfra's OpenAI-compatible chat-completions backend for Gemma 4 E4B IT."""

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
class DeepInfraGemmaHost:
    model_id: str = "google/gemma-4-E4B-it"
    canonical_revision: str = "ee0ef6023621cff504d758262d4e04895a5af4a2"
    token: str | None = None
    endpoint: str = "https://api.deepinfra.com/v1/openai/chat/completions"
    timeout_seconds: float = 120.0

    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(frozenset({Capability.TEXT_GENERATION, Capability.TOKEN_USAGE}))

    def fingerprint(self) -> HostFingerprint:
        return HostFingerprint(
            "Gemma 4 E4B IT",
            self.model_id,
            None,
            "google/gemma-4-E4B-it",
            self.canonical_revision,
            "deepinfra_openai_chat",
            "unknown/provider-managed",
            "deepinfra-openai-compatible",
            None,
            "DeepInfra",
            {
                "base_url": "https://api.deepinfra.com/v1/openai",
                "endpoint": self.endpoint,
                "rendering_mode": "deepinfra_openai_chat",
                "canonical_upstream_model": "google/gemma-4-E4B-it",
                "hosted_model_revision": "unknown",
                "context_length": 131072,
            },
            self.capabilities().supported,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.capabilities().require(Capability.TEXT_GENERATION)
        if request.seed is not None:
            raise HostError("DeepInfra Gemma seed control is not advertised or verified")
        if request.response_format is not None:
            raise HostError(
                "DeepInfra Gemma does not support native response_format; "
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


def _parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    result = dict(parameters)
    if "max_new_tokens" in result:
        result["max_tokens"] = result.pop("max_new_tokens")
    return result


def _provider_messages(request: GenerationRequest) -> list[dict[str, str]]:
    """Render the provider-visible message list without duplicating ``system``.

    ``GenerationRequest.messages`` remains authoritative for message-only calls.
    When the separate controller system field is present, it is represented by one
    provider ``system`` message.  A legacy caller that already placed the same
    system message in ``messages`` is accepted and deduplicated.
    """

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
