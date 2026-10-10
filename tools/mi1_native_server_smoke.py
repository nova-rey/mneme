#!/usr/bin/env python3
"""Exercise the isolated MI1 HTTP bank lifecycle without model generation.

The only request sent to a generation route is a deliberately rejected
cache_prompt=true request. It must fail in the server gate before the regular
completion handler runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class EvidenceClient:
    def __init__(self, base_url: str, events_path: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.events_path = events_path
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self.events_path.write_text("", encoding="utf-8")

    def request(
        self, method: str, route: str, payload: dict[str, Any] | None = None
    ) -> tuple[int, Any]:
        body = (
            None
            if payload is None
            else json.dumps(payload, separators=(",", ":")).encode()
        )
        headers = {} if body is None else {"Content-Type": "application/json"}
        request = urllib.request.Request(
            f"{self.base_url}{route}", data=body, headers=headers, method=method
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        elapsed = time.monotonic() - started
        text = raw.decode("utf-8", errors="replace")
        try:
            result: Any = json.loads(text)
        except json.JSONDecodeError:
            result = text
        event = {
            "method": method,
            "route": route,
            "request": payload,
            "status": status,
            "response": result,
            "elapsed_seconds": elapsed,
        }
        with self.events_path.open("a", encoding="utf-8") as events:
            events.write(json.dumps(event, sort_keys=True) + "\n")
        return status, result


def expect_state(
    client: EvidenceClient,
    expected_revision: int,
    expected_enabled: bool,
    expected_fingerprint: str,
) -> dict[str, Any]:
    status, result = client.request("GET", "/mi1/bank")
    assert status == 200, (status, result)
    assert result == {
        "revision": expected_revision,
        "enabled": expected_enabled,
        "bank_fingerprint": expected_fingerprint,
    }, result
    return cast(dict[str, Any], result)


def apply_operation(
    client: EvidenceClient,
    operation: str,
    revision: int,
    enabled: bool,
    fingerprint: str,
    bank_path: Path | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"operation": operation}
    if bank_path is not None:
        payload["path"] = str(bank_path)
    status, result = client.request("POST", "/mi1/bank", payload)
    assert status == 200, (status, result)
    assert result == {
        "operation": operation,
        "revision": revision,
        "enabled": enabled,
        "bank_fingerprint": fingerprint,
    }, result
    return cast(dict[str, Any], result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--bank-a", required=True, type=Path)
    parser.add_argument("--bank-b", required=True, type=Path)
    parser.add_argument("--events", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    for bank in (args.bank_a, args.bank_b):
        if not bank.is_file():
            raise FileNotFoundError(bank)

    client = EvidenceClient(args.base_url, args.events)
    initial = expect_state(client, 0, False, "")
    attached_status, attached_raw = client.request(
        "POST", "/mi1/bank", {"operation": "attach", "path": str(args.bank_a)}
    )
    assert attached_status == 200 and isinstance(attached_raw, dict), (
        attached_status,
        attached_raw,
    )
    fingerprint_a = str(attached_raw["bank_fingerprint"])
    assert fingerprint_a
    assert attached_raw == {
        "operation": "attach",
        "revision": 1,
        "enabled": True,
        "bank_fingerprint": fingerprint_a,
    }, attached_raw
    attached = cast(dict[str, Any], attached_raw)
    disabled = apply_operation(client, "disable", 2, False, fingerprint_a)
    disabled_state = expect_state(client, 2, False, fingerprint_a)
    replaced_status, replaced_raw = client.request(
        "POST", "/mi1/bank", {"operation": "replace", "path": str(args.bank_b)}
    )
    assert replaced_status == 200 and isinstance(replaced_raw, dict), (
        replaced_status,
        replaced_raw,
    )
    fingerprint_b = str(replaced_raw["bank_fingerprint"])
    assert fingerprint_b and fingerprint_b != fingerprint_a
    assert replaced_raw == {
        "operation": "replace",
        "revision": 3,
        "enabled": True,
        "bank_fingerprint": fingerprint_b,
    }, replaced_raw
    replaced = cast(dict[str, Any], replaced_raw)
    cleared = apply_operation(client, "clear", 4, False, "")
    final_before_gate = expect_state(client, 4, False, "")

    # Negative probes only: missing/true cache_prompt must be rejected before
    # either route reaches its handler, tokenization, decode, or sampling.
    gate_probes: list[dict[str, Any]] = []
    for route in ("/completion", "/v1/messages", "/v1/chat/completions"):
        for payload in ({"cache_prompt": True}, {}):
            status, result = client.request("POST", route, payload)
            assert status == 400, (route, payload, status, result)
            assert "cache_prompt=false" in json.dumps(result), result
            gate_probes.append(
                {
                    "route": route,
                    "request": payload,
                    "status": status,
                    "response": result,
                }
            )
    final_after_gate = expect_state(client, 4, False, "")

    receipt = {
        "schema": "mi1-native-server-smoke-v1",
        "generation_requests_accepted": 0,
        "sampled_tokens": 0,
        "rejected_generation_gate_probes": gate_probes,
        "source_review": {
            "covered_generation_routes": [
                "/completion",
                "/v1/messages",
                "/v1/chat/completions",
            ],
            "initial_pre_patch_source_bypassed_guard": True,
        },
        "banks": {
            "a": {"path": str(args.bank_a), "sha256": sha256(args.bank_a)},
            "b": {"path": str(args.bank_b), "sha256": sha256(args.bank_b)},
            "fingerprint_a": fingerprint_a,
            "fingerprint_b": fingerprint_b,
        },
        "states": {
            "initial": initial,
            "attached": attached,
            "disabled": disabled,
            "disabled_readback": disabled_state,
            "replaced": replaced,
            "cleared": cleared,
            "final_before_gate_probe": final_before_gate,
            "final_after_gate_probe": final_after_gate,
        },
        "events_path": str(args.events),
        "events_sha256": sha256(args.events),
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    args.receipt.write_text(serialized, encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
