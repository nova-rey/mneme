import json

import pytest

from mneme.contracts import (
    Capability,
    GenerationRequest,
    HostCapabilities,
    UnsupportedCapabilityError,
)
from mneme.hosts import FakeHost


def request(seed=None):
    return GenerationRequest(({"role": "user", "content": "hello"},), seed=seed)


def test_fake_is_deterministic_and_fingerprinted():
    host = FakeHost()
    assert host.generate(request(7)).content == host.generate(request(7)).content
    assert host.fingerprint().to_dict() == host.fingerprint().to_dict()


def test_capabilities_and_explicit_unsupported():
    caps = HostCapabilities(frozenset({Capability.TEXT_GENERATION}))
    with pytest.raises(UnsupportedCapabilityError):
        caps.require(Capability.SEED_CONTROL)
    with pytest.raises(UnsupportedCapabilityError):
        FakeHost(omit_capabilities=frozenset({Capability.TEXT_GENERATION})).generate(request())


def test_contracts_serialize_without_provider_objects():
    result = FakeHost().generate(request(1))
    encoded = json.dumps(result.to_dict())
    assert "object at 0x" not in encoded
    assert json.loads(encoded)["model_id"] == "mneme-fake-v1"


def test_admin_metadata_is_not_visible():
    result = FakeHost().generate(
        GenerationRequest(
            ({"role": "user", "content": "hi"},), run_metadata={"instance_id": "secret-admin-id"}
        )
    )
    assert "secret-admin-id" not in result.content


def test_seed_requires_declared_capability():
    with pytest.raises(UnsupportedCapabilityError):
        FakeHost(omit_capabilities=frozenset({Capability.SEED_CONTROL})).generate(request(2))
