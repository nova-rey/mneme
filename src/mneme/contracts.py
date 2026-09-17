"""Provider-neutral records at the MNEME host boundary."""

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Capability(StrEnum):
    TEXT_GENERATION = "text_generation"
    SEED_CONTROL = "seed_control"
    STRUCTURED_OUTPUT = "structured_output"
    TOKEN_USAGE = "token_usage"
    LOGPROBS = "logprobs"
    TOKENIZER = "tokenizer"
    HIDDEN_STATES = "hidden_states"
    ATTENTION_KV = "attention_kv"
    INTERVENTION_HOOKS = "intervention_hooks"
    LOCAL_WEIGHTS = "local_weights"


@dataclass(frozen=True)
class GenerationRequest:
    messages: tuple[dict[str, str], ...]
    system: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    response_format: dict[str, Any] | None = None
    run_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"messages": [dict(m) for m in self.messages]}


@dataclass(frozen=True)
class HostCapabilities:
    supported: frozenset[Capability]

    def has(self, capability: Capability) -> bool:
        return capability in self.supported

    def require(self, capability: Capability) -> None:
        if not self.has(capability):
            raise UnsupportedCapabilityError(capability.value)

    def to_dict(self) -> list[str]:
        return sorted(c.value for c in self.supported)


@dataclass(frozen=True)
class HostFingerprint:
    model_family: str
    model_id: str
    model_revision: str | None
    tokenizer_id: str | None
    tokenizer_revision: str | None
    chat_template: str | None
    quantization: str | None
    runtime: str
    runtime_version: str | None
    provider: str
    execution: dict[str, Any] = field(default_factory=dict)
    capabilities: frozenset[Capability] = frozenset()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"capabilities": sorted(c.value for c in self.capabilities)}


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class GenerationResult:
    content: str
    model_id: str
    provider: str
    effective_parameters: dict[str, Any]
    seed: int | None
    token_usage: TokenUsage | None
    latency_ms: float
    finish_reason: str | None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        return result


class HostError(RuntimeError):
    """A provider/backend failure at the host boundary."""


class UnsupportedCapabilityError(HostError):
    """The configured host cannot truthfully provide a requested capability."""
