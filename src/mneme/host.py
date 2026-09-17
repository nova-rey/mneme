"""Small, deployment-neutral host protocol."""

from typing import Protocol

from .contracts import GenerationRequest, GenerationResult, HostCapabilities, HostFingerprint


class Host(Protocol):
    def capabilities(self) -> HostCapabilities: ...
    def fingerprint(self) -> HostFingerprint: ...
    def generate(self, request: GenerationRequest) -> GenerationResult: ...
