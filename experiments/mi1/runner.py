"""Durable, cache-disabled MI1 coordinate execution against a local server."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.mi1.native.evidence import EvidenceJournal, atomic_json_write


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


BankResolver = Callable[[str, str, dict[str, Any]], ResolvedBank]
Transport = Callable[[str, dict[str, Any]], dict[str, Any]]
StreamEventSink = Callable[[bytes], int]
StreamTransport = Callable[[str, dict[str, Any], StreamEventSink], dict[str, Any]]


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


def http_sse(url: str, payload: dict[str, Any], on_event: StreamEventSink) -> dict[str, Any]:
    """Consume an OpenAI-compatible SSE response while journaling each raw event."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    response: dict[str, Any] = {"choices": []}
    choices: dict[int, dict[str, Any]] = {}
    event_lines: list[bytes] = []
    saw_done = False

    def consume(raw_event: bytes) -> None:
        nonlocal saw_done
        on_event(raw_event)
        data_lines = [
            line[5:].lstrip(b" ")
            for line in raw_event.splitlines()
            if line.startswith(b"data:")
        ]
        if not data_lines:
            return
        data = b"\n".join(data_lines)
        if data == b"[DONE]":
            saw_done = True
            return
        chunk = json.loads(data.decode("utf-8"))
        if not isinstance(chunk, dict):
            raise ValueError("SSE data must contain a JSON object")
        for key in ("id", "object", "created", "model", "system_fingerprint"):
            if key in chunk:
                response[key] = chunk[key]
        if "usage" in chunk:
            response["usage"] = chunk["usage"]
        for item in chunk.get("choices", []):
            index = item.get("index", 0)
            state = choices.setdefault(index, {"index": index, "message": {"role": "assistant"}})
            delta = item.get("delta", {})
            message = state["message"]
            for field, value in delta.items():
                if isinstance(value, str) and field in {
                    "content",
                    "reasoning_content",
                    "reasoning",
                }:
                    message[field] = message.get(field, "") + value
                elif field not in message:
                    message[field] = value
            if item.get("finish_reason") is not None:
                state["finish_reason"] = item["finish_reason"]

    with urllib.request.urlopen(request, timeout=1800) as stream:
        for line in stream:
            event_lines.append(line)
            if line in (b"\n", b"\r\n"):
                consume(b"".join(event_lines))
                event_lines.clear()
                if saw_done:
                    break
        if event_lines:
            consume(b"".join(event_lines))
    if not saw_done:
        raise EOFError("SSE response closed before [DONE]")
    response["choices"] = [choices[index] for index in sorted(choices)]
    if not response["choices"]:
        raise ValueError("SSE response contained no assistant choices")
    return response


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
        base_server_url: str | None = None,
        journal: EvidenceJournal,
        budget: GenerationBudget,
        bank_resolver: BankResolver,
        transport: Transport = http_json,
        stream_transport: StreamTransport = http_sse,
    ) -> None:
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            raise ValueError("base_url must use http(s)")
        self.base_url = base_url.rstrip("/")
        self.base_server_url = (
            None if base_server_url is None else base_server_url.rstrip("/")
        )
        self.journal = journal
        self.budget = budget
        self.bank_resolver = bank_resolver
        self.transport = transport
        self.stream_transport = stream_transport

    def _post(
        self, route: str, payload: dict[str, Any], *, base_url: str | None = None
    ) -> dict[str, Any]:
        return self.transport((base_url or self.base_url) + route, payload)

    def _bank_state(
        self,
        operation: str,
        bank_text: str | None,
        bank_sha: str | None,
        bank_config: dict[str, Any],
    ) -> dict[str, Any]:
        artifact: ResolvedBank | None = None
        if operation == "clear":
            payload: dict[str, Any] = {"operation": "clear"}
        elif operation in {"attach", "replace", "encode_and_attach"}:
            if bank_text is None or bank_sha is None:
                raise ValueError(f"{operation} requires frozen bank text and its hash")
            artifact = self.bank_resolver(bank_text, bank_sha, bank_config)
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
        metadata = coordinate.get("metadata", {})
        server_role = metadata.get("server_role", "mi1_server")
        if server_role == "mi1_server":
            server_url = self.base_url
        elif server_role == "base_server" and self.base_server_url is not None:
            server_url = self.base_server_url
        else:
            raise ValueError(f"unsupported or unconfigured MI1 server role: {server_role}")
        if messages is None:
            frozen_messages = request_template.get("messages")
            if not isinstance(frozen_messages, list):
                raise ValueError("coordinate requires explicit messages")
            messages = [dict(row) for row in frozen_messages]
        if request_template.get("cache_prompt") is not False:
            raise ValueError("MI1 matched generations require cache_prompt=false")
        if request_template.get("stream") is not True:
            raise ValueError("MI1 generation must stream to its durable journal")
        request_template["messages"] = messages
        generation_request = dict(request_template)

        if server_role == "base_server":
            if (
                coordinate.get("bank_action") != "clear"
                or coordinate.get("bank_source") is not None
            ):
                raise ValueError("base server coordinates must not attach an MI1 bank")
            bank = {"status": "not_applicable_base_server"}
        else:
            bank = self._bank_state(
                coordinate["bank_action"],
                coordinate.get("bank_source"),
                coordinate.get("bank_source_sha256"),
                coordinate.get("bank_config", {}),
            )
        template_request = {
            "messages": messages,
            "add_generation_prompt": True,
            "chat_template_kwargs": request_template.get("chat_template_kwargs", {}),
        }
        template = self._post("/apply-template", template_request, base_url=server_url)
        prompt = template.get("prompt")
        if not isinstance(prompt, str):
            raise ValueError("llama.cpp template endpoint returned no exact prompt")
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        journal_request = {
            **generation_request,
            "model_visible_prompt": prompt,
            "model_visible_prompt_sha256": prompt_hash,
        }

        self.budget.reserve(coordinate_id, phase)
        self.journal.begin(
            coordinate_id,
            journal_request,
            {
                "coordinate": coordinate,
                "bank_state": bank,
                "template_request": template_request,
                "template_response": template,
                "phase": phase,
                "generation_budget": self.budget.counts(),
                "stream_file": f"{coordinate_id}.stream.jsonl",
            },
        )
        try:
            response = self.stream_transport(
                server_url + "/v1/chat/completions",
                generation_request,
                lambda raw_event: self.journal.append_stream_event(coordinate_id, raw_event),
            )
        except (OSError, urllib.error.URLError, TimeoutError, EOFError, ValueError) as exc:
            failure = {"error_type": type(exc).__name__, "message": str(exc)}
            self.journal.fail(
                coordinate_id,
                failure,
                {"phase": phase, "stream": self.journal.stream_summary(coordinate_id)},
            )
            raise
        self.journal.complete(
            coordinate_id,
            response,
            {"phase": phase, "stream": self.journal.stream_summary(coordinate_id)},
        )
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
