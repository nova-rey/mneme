"""Durable, cache-disabled MI1 coordinate execution against a local server."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write


class BankResolver(Protocol):
    """Resolve exact frozen bank text to a host-local native bank file."""

    def __call__(self, source_text: str, source_sha256: str) -> ResolvedBank: ...


@dataclass(frozen=True)
class ResolvedBank:
    """Host-local compiled bank identity and frozen selector provenance."""

    path: Path
    native_sha256: str
    selector_sha256: str
    selector: dict[str, Any]

    def __post_init__(self) -> None:
        for label, digest in (
            ("native bank", self.native_sha256),
            ("selector", self.selector_sha256),
        ):
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError(f"{label} SHA-256 must be lowercase hexadecimal")


Transport = Callable[[str, dict[str, Any]], dict[str, Any]]


def http_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=1800) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object from {url}")
    return value


class GenerationBudget:
    """Durable experiment-wide generation counter including prior calibration."""

    def __init__(
        self,
        path: Path,
        *,
        prior_calibration_calls: int = 8,
        calibration_limit: int = 120,
        hard_limit: int = 800,
    ) -> None:
        self.path = path
        self.prior_calibration_calls = prior_calibration_calls
        self.calibration_limit = calibration_limit
        self.hard_limit = hard_limit
        if path.exists():
            current = json.loads(path.read_text(encoding="utf-8"))
            expected = {
                "schema_version": 1,
                "prior_calibration_calls": prior_calibration_calls,
                "calibration_limit": calibration_limit,
                "hard_limit": hard_limit,
            }
            if any(current.get(key) != value for key, value in expected.items()):
                raise ValueError("MI1 generation budget contract mismatch")
        else:
            atomic_json_write(
                path,
                {
                    "schema_version": 1,
                    "prior_calibration_calls": prior_calibration_calls,
                    "calibration_limit": calibration_limit,
                    "hard_limit": hard_limit,
                    "prior_calibration_evidence": {
                        "path": (
                            "/home/nyx/mneme-artifacts/phase4-mi1/calibration/"
                            "visible-calibration-20261010.json"
                        ),
                        "sha256": (
                            "8e87bb6a841310e6562795cf92291807fd321d6f9aea809d6c9fa5dd838dc513"
                        ),
                    },
                    "reservations": [],
                },
            )

    def reserve(self, attempt_id: str, phase: str) -> None:
        if phase not in {"calibration", "scored", "confirmation"}:
            raise ValueError("phase must be calibration, scored, or confirmation")
        value = json.loads(self.path.read_text(encoding="utf-8"))
        reservations = value["reservations"]
        if any(row["attempt_id"] == attempt_id for row in reservations):
            raise FileExistsError(f"generation ID already reserved: {attempt_id}")
        if self.prior_calibration_calls + len(reservations) >= self.hard_limit:
            raise RuntimeError("MI1 authorized hard generation limit reached")
        calibration_count = self.prior_calibration_calls + sum(
            row["phase"] == "calibration" for row in reservations
        )
        if phase == "calibration" and calibration_count >= self.calibration_limit:
            raise RuntimeError("MI1 calibration generation ceiling reached")
        reservations.append({"attempt_id": attempt_id, "phase": phase})
        atomic_json_write(self.path, value)

    def counts(self) -> dict[str, int]:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        reservations = value["reservations"]
        return {
            "total": self.prior_calibration_calls + len(reservations),
            "calibration": self.prior_calibration_calls
            + sum(row["phase"] == "calibration" for row in reservations),
            "scored": sum(row["phase"] == "scored" for row in reservations),
            "confirmation": sum(row["phase"] == "confirmation" for row in reservations),
        }


class MI1CoordinateRunner:
    """Run frozen coordinates while journaling exact prompts and raw outputs."""

    def __init__(
        self,
        *,
        base_url: str,
        journal: EvidenceJournal,
        budget: GenerationBudget,
        bank_resolver: BankResolver,
        transport: Transport = http_json,
    ) -> None:
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            raise ValueError("base_url must use http(s)")
        self.base_url = base_url.rstrip("/")
        self.journal = journal
        self.budget = budget
        self.bank_resolver = bank_resolver
        self.transport = transport

    def _post(self, route: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.transport(self.base_url + route, payload)

    def _bank_state(
        self, operation: str, bank_text: str | None, bank_sha: str | None
    ) -> dict[str, Any]:
        artifact: ResolvedBank | None = None
        if operation == "clear":
            payload: dict[str, Any] = {"operation": "clear"}
        elif operation in {"attach", "replace", "encode_and_attach"}:
            if bank_text is None or bank_sha is None:
                raise ValueError(f"{operation} requires frozen bank text and its hash")
            artifact = self.bank_resolver(bank_text, bank_sha)
            payload = {"operation": "attach" if operation == "encode_and_attach" else operation,
                       "path": str(artifact.path)}
        else:
            raise ValueError(f"unsupported bank action: {operation}")
        result = self._post("/mi1/bank", payload)
        if result.get("enabled") != (operation != "clear"):
            raise ValueError("native bank endpoint returned an inconsistent enabled state")
        if not isinstance(result.get("revision"), int):
            raise ValueError("native bank endpoint omitted its revision")
        return {
            "request": payload,
            "response": result,
            "source_sha256": bank_sha,
            "artifact": None
            if artifact is None
            else {
                "path": str(artifact.path),
                "native_sha256": artifact.native_sha256,
                "selector_sha256": artifact.selector_sha256,
                "selector": artifact.selector,
            },
        }

    def execute(
        self,
        coordinate: dict[str, Any],
        *,
        phase: str,
        messages: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Execute one coordinate; caller supplies C-turn-2 dynamic messages."""
        coordinate_id = coordinate["coordinate_id"]
        request_template = dict(coordinate["request"])
        if messages is None:
            frozen_messages = request_template.get("messages")
            if not isinstance(frozen_messages, list):
                raise ValueError("coordinate requires explicit messages")
            messages = [dict(row) for row in frozen_messages]
        if request_template.get("cache_prompt") is not False:
            raise ValueError("MI1 matched generations require cache_prompt=false")
        request_template["messages"] = messages

        bank = self._bank_state(
            coordinate["bank_action"],
            coordinate.get("bank_source"),
            coordinate.get("bank_source_sha256"),
        )
        template_request = {
            "messages": messages,
            "add_generation_prompt": True,
            "chat_template_kwargs": request_template.get("chat_template_kwargs", {}),
        }
        template = self._post("/apply-template", template_request)
        prompt = template.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("llama.cpp template endpoint returned no exact prompt")
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        request_template["model_visible_prompt"] = prompt
        request_template["model_visible_prompt_sha256"] = prompt_hash

        self.budget.reserve(coordinate_id, phase)
        self.journal.begin(
            coordinate_id,
            request_template,
            {
                "coordinate": coordinate,
                "bank_state": bank,
                "template_request": template_request,
                "template_response": template,
                "phase": phase,
                "generation_budget": self.budget.counts(),
            },
        )
        try:
            response = self._post("/v1/chat/completions", request_template)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            failure = {"error_type": type(exc).__name__, "message": str(exc)}
            self.journal.fail(coordinate_id, failure, {"phase": phase})
            raise
        self.journal.complete(coordinate_id, response, {"phase": phase})
        return response


def load_completed_response(journal_root: Path, attempt_id: str) -> dict[str, Any]:
    """Read a dependency response from durable journal files, never RAM-only state."""
    path = journal_root / "attempts" / f"{attempt_id}.complete.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("attempt_id") != attempt_id or value.get("status") != "COMPLETE":
        raise ValueError("dependency output is not a valid completed durable attempt")
    payload = value.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("dependency response payload is malformed")
    return payload
