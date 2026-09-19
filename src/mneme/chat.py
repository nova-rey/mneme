"""Small interactive chat seam over the Phase One response controller.

The session is deliberately process-local.  It carries only the bounded
conversation context supplied to the next request; developmental state remains
owned by ``ResponseController`` and ``ContinuityService``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .controller import ControllerError, ResponseController, TurnIntent
from .host import Host
from .state.storage import SQLiteStore


class ChatError(RuntimeError):
    """The requested chat turn cannot be executed safely."""


@dataclass(frozen=True)
class ChatTurn:
    input_text: str
    output_text: str
    operation_id: str
    mode: str
    memory: str
    revision: int | None
    selected_routes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input": self.input_text,
            "output": self.output_text,
            "operation_id": self.operation_id,
            "mode": self.mode,
            "memory": self.memory,
            "revision": self.revision,
            "selected_routes": list(self.selected_routes),
        }


class ChatSession:
    """Process-local bounded session using the shared controller boundary."""

    def __init__(
        self,
        store: SQLiteStore,
        instance_id: str,
        host: Host,
        *,
        mode: str = "develop",
        memory: str = "graph",
        system: str | None = None,
    ) -> None:
        if mode not in {"develop", "observe", "evaluate"}:
            raise ChatError("mode must be develop, observe, or evaluate")
        if memory not in {"graph", "episodic", "off"}:
            raise ChatError("memory must be graph, episodic, or off")
        self.store = store
        self.instance_id = instance_id
        self.host = host
        self.mode = mode
        self.memory = memory
        self.system = system
        self._messages: list[dict[str, str]] = []

    @property
    def messages(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(message) for message in self._messages)

    def fresh(self) -> None:
        """Discard process-local context without changing developmental state."""

        self._messages.clear()

    def turn(self, text: str, *, operation_id: str | None = None) -> ChatTurn:
        if not isinstance(text, str) or not text:
            raise ChatError("chat input must be non-empty text")
        operation_id = operation_id or str(uuid.uuid4())
        try:
            prepared = ResponseController(self.store, self.instance_id, self.host).prepare(
                TurnIntent(
                    current_input=text,
                    mode=self.mode,
                    memory=self.memory,
                    session_messages=tuple(self._messages),
                    system=self.system,
                    operation_id=operation_id,
                )
            )
            result = ResponseController(self.store, self.instance_id, self.host).execute(prepared)
        except ControllerError as exc:
            raise ChatError(str(exc)) from exc
        self._messages.extend(({"role": "user", "content": text},))
        self._messages.extend(({"role": "assistant", "content": result.generation.content},))
        return ChatTurn(
            text,
            result.generation.content,
            operation_id,
            self.mode,
            self.memory,
            result.operation.revision,
            tuple(route.route_key for route in prepared.selected),
        )


__all__ = ["ChatError", "ChatSession", "ChatTurn"]
