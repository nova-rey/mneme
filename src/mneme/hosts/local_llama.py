"""Subprocess-backed local Gemma host for the MSI laboratory runtime."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass

from ..contracts import (
    Capability,
    GenerationRequest,
    GenerationResult,
    HostCapabilities,
    HostError,
    HostFingerprint,
)


@dataclass
class LocalLlamaHost:
    """Run a local GGUF checkpoint through a pinned llama.cpp executable.

    The executable is intentionally configured explicitly.  This keeps model
    and runtime identity in the host fingerprint and makes the adapter usable
    on the headless MSI without adding a daemon or a network dependency.
    """

    model_path: str
    executable: str = "llama-cli"
    model_id: str = "google/gemma-4-E4B-it"
    model_revision: str | None = None
    runtime_version: str | None = None
    quantization: str | None = "UD-Q2_K_XL"
    gpu_layers: str = "all"
    context_size: int = 4096
    timeout_seconds: float = 600.0
    provider: str = "local-msi"

    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            frozenset({Capability.TEXT_GENERATION, Capability.LOCAL_WEIGHTS})
        )

    def fingerprint(self) -> HostFingerprint:
        return HostFingerprint(
            model_family="Gemma 4",
            model_id=self.model_id,
            model_revision=self.model_revision,
            tokenizer_id=self.model_id,
            tokenizer_revision=self.model_revision,
            chat_template="gemma-chat-template",
            quantization=self.quantization,
            runtime="llama.cpp",
            runtime_version=self.runtime_version,
            provider=self.provider,
            execution={
                "model_path": self.model_path,
                "executable": self.executable,
                "gpu_layers": self.gpu_layers,
                "context_size": self.context_size,
            },
            capabilities=self.capabilities().supported,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.capabilities().require(Capability.TEXT_GENERATION)
        max_tokens = int(request.parameters.get("max_new_tokens", 256))
        if max_tokens <= 0:
            raise HostError("max_new_tokens must be positive")
        prompt = _render_prompt(request)
        command = [
            self.executable,
            "-m",
            self.model_path,
            "-st",
            "--no-display-prompt",
            "-n",
            str(max_tokens),
            "-c",
            str(self.context_size),
            "-ngl",
            self.gpu_layers,
            "-p",
            prompt,
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HostError(f"local llama.cpp execution failed: {exc}") from exc
        latency = (time.perf_counter() - started) * 1000
        if completed.returncode != 0:
            raise HostError(
                f"local llama.cpp exited {completed.returncode}: {completed.stderr[-500:]}"
            )
        content = _extract_output(completed.stdout, prompt)
        if not content:
            raise HostError("local llama.cpp returned no usable content")
        return GenerationResult(
            content=content,
            model_id=self.model_id,
            provider=self.provider,
            effective_parameters=dict(request.parameters),
            seed=request.seed,
            token_usage=None,
            latency_ms=latency,
            finish_reason="stop",
            raw_metadata={"stdout_tail": completed.stdout[-1000:]},
            provenance={"host": self.fingerprint().to_dict()},
        )


def _render_prompt(request: GenerationRequest) -> str:
    """Render a compact visible context for llama-cli's user turn."""

    parts: list[str] = []
    if request.system:
        parts.append(f"System instructions:\n{request.system}")
    if request.messages:
        parts.append(
            "Conversation:\n"
            + "\n\n".join(
                f"{message['role']}: {message['content']}" for message in request.messages
            )
        )
    parts.append("Write only the next assistant response.")
    return "\n\n".join(parts)


def _extract_output(stdout: str, prompt: str) -> str:
    """Remove llama-cli's banner and performance footer without normalizing text."""

    text = stdout.replace("\x08", "")
    marker = f"> {prompt}"
    if marker in text:
        text = text.split(marker, 1)[1]
    text = re.split(r"\n\s*\[ Prompt:", text, maxsplit=1)[0]
    return text.replace("\r", "").strip()


__all__ = ["LocalLlamaHost"]
