"""A fake async NBQ client, used to drive the server without any network call.

The fake returns the SDK's own response models, built from the contract example
payloads, and raises the SDK's own typed exceptions: the translation the server
performs is exercised against the real classes, not against look-alikes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from nbq.models import FeedbackResponse, NextResponse, SessionStateResponse


@dataclass(frozen=True)
class RecordedCall:
    method: str
    kwargs: dict[str, Any]


_MODELS: dict[str, Any] = {
    "create_session": SessionStateResponse,
    "apply_events": SessionStateResponse,
    "get_session": SessionStateResponse,
    "next": NextResponse,
    "submit_feedback": FeedbackResponse,
}


@dataclass
class FakeRuntimeClient:
    """Queue one result per expected call; the last one repeats."""

    results: dict[str, list[Any]] = field(default_factory=lambda: defaultdict(list))
    calls: list[RecordedCall] = field(default_factory=list)
    closed: bool = False

    def queue(self, method: str, *results: Any) -> FakeRuntimeClient:
        self.results[method].extend(results)
        return self

    def calls_to(self, method: str) -> list[RecordedCall]:
        return [call for call in self.calls if call.method == method]

    def _resolve(self, method: str, kwargs: dict[str, Any]) -> Any:
        self.calls.append(RecordedCall(method, kwargs))
        queued = self.results[method]
        if not queued:
            raise AssertionError(f"unexpected call to {method}({kwargs})")
        result = queued.pop(0) if len(queued) > 1 else queued[0]
        if isinstance(result, BaseException):
            raise result
        return _MODELS[method].model_validate(result)

    async def create_session(
        self,
        *,
        client_reference: str | None = None,
        max_turns: int | None = None,
        initial_history: Any = None,
    ) -> Any:
        return self._resolve(
            "create_session",
            {
                "client_reference": client_reference,
                "max_turns": max_turns,
                "initial_history": initial_history,
            },
        )

    async def next(
        self,
        session_id: str,
        *,
        state_version: int,
        previous_turn: Any = None,
        context_update: Any = None,
        client_updates: Any = None,
        selection: Any = None,
    ) -> Any:
        return self._resolve(
            "next",
            {
                "session_id": session_id,
                "state_version": state_version,
                "previous_turn": previous_turn,
                "context_update": context_update,
                "client_updates": client_updates,
                "selection": selection,
            },
        )

    async def apply_events(
        self,
        session_id: str,
        *,
        state_version: int,
        context_update: Any = None,
        client_updates: Any = None,
    ) -> Any:
        return self._resolve(
            "apply_events",
            {
                "session_id": session_id,
                "state_version": state_version,
                "context_update": context_update,
                "client_updates": client_updates,
            },
        )

    async def get_session(self, session_id: str) -> Any:
        return self._resolve("get_session", {"session_id": session_id})

    async def submit_feedback(
        self,
        session_id: str,
        *,
        result: str,
        label: str | None = None,
        metadata: Any = None,
    ) -> Any:
        return self._resolve(
            "submit_feedback",
            {
                "session_id": session_id,
                "result": result,
                "label": label,
                "metadata": metadata,
            },
        )

    async def aclose(self) -> None:
        self.closed = True
