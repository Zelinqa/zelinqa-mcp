"""The NBQ MCP server.

Architecture, not negotiable:

    MCP tool -> Python SDK `nbq` -> public REST API https://api.zelinqa.ai

The server never speaks HTTP itself, never imports the engine, never touches a
database, and never exposes a selection score.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Annotated, Any, Protocol

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from nbq.errors import NBQAPIError, NBQConnectionError
from pydantic import Field, ValidationError

from . import __version__
from ._errors import AUTH_MESSAGE, tool_error_for
from ._inputs import (
    ClientUpdatesInput,
    ContextUpdateInput,
    FeedbackResult,
    InitialHistoryItemInput,
    MetadataValue,
    PreviousTurnInput,
    SelectionInput,
)
from ._payloads import state_version_of, to_payload, with_state_version

SERVER_NAME = "nbq"

SERVER_INSTRUCTIONS = """\
NBQ (Next Best Question) qualifies a conversation: you ask the questions, NBQ \
decides which question is worth asking next.

Turn loop:
1. nbq_create_session once per conversation (or nbq_resume_session to pick an \
existing one back up).
2. nbq_next with no previous_turn for the first turn. Ask the candidate of rank 1 \
in your own words.
3. nbq_next again with previous_turn = what you asked and what the user answered.
4. Repeat. You decide when to stop: NBQ keeps proposing and reports \
max_turns_reached / objective_achieved in `warnings`. `action: "stop"` means no \
question is left at all.
5. nbq_submit_feedback once the conversation produced its real outcome.

Use nbq_apply_events to feed context or known data without consuming a turn."""

_CREATE_SESSION_DESCRIPTION = """\
Start an NBQ session for one conversation.

Returns the initial session state, including `state_version` (0) and \
`max_turns`. No question yet: call nbq_next next.

`initial_history` is only for a conversation that started outside NBQ; it is \
consumed once to build the initial state and is never stored or returned."""

_RESUME_SESSION_DESCRIPTION = """\
Pick an existing NBQ session back up and re-learn its `state_version`.

Call this when you did not create the session in this process, after a crash, or \
whenever you are unsure of the current `state_version`. The response carries \
`pending_decision` with the exact candidates that were last proposed, so you can \
resume the conversation without any resume token."""

_NEXT_DESCRIPTION = """\
Understand the previous turn and get the next best questions. The main runtime \
call: it applies what happened, recomputes progress, then ranks the eligible \
questions.

First turn of a new session: call it with no `previous_turn`.

Every later turn: pass `previous_turn` describing the turn that just happened —
  previous_turn = {"assistant_text": <the question you actually asked>, \
"user_text": <the user's reply>}
Reformulating the published wording is fine; NBQ reattaches your text to its \
question. `decision_id`, `question_id` and `outcome` are optional helpers, not \
identifiers to invent. For a choice question, send \
`structured_answer: {"choice_ids": [...]}` with ids copied from the candidate's \
`choices`: that path is deterministic and costs no LLM call. Omitting `user_text` \
is allowed when a structured answer or `client_updates` carry the information; \
the turn is then understood in reduced mode, reported by `degraded_reasons`.

Reading the response:
- `candidates` are ordered, rank 1 first; ask the one you judge best, usually \
rank 1. `text` is the published wording, `type` is open / single_choice / \
multiple_choice / semi_open, `choices` is empty for an open question.
- `warnings` may contain `max_turns_reached` (soft limit reached) or \
`objective_achieved` (success conditions met). NBQ still proposes a question: \
deciding whether to stop asking is YOUR call, not NBQ's.
- `action: "stop"` with `stop_reason: "no_question_available"` means no question \
is left; there is nothing more to ask.
- `state_version` is the version to send on the next mutation. It is tracked for \
you, so you may omit `state_version`.

Send `selection` only when you need to constrain this one call, for instance to \
force closed questions or to stay inside a sub-objective."""

_APPLY_EVENTS_DESCRIPTION = """\
Apply context or known data to the session without selecting a question.

Same reducer as nbq_next, without the selection phase, so it does not consume a \
turn and does not replace the pending decision. Use it to catch up on messages \
that did not go through NBQ (`context_update`), to inject a value your own system \
already knows so the question is not asked (`client_updates.data`), to correct a \
value, or to exclude a sub-objective. At least one of `context_update` or \
`client_updates` is required."""

_GET_SESSION_DESCRIPTION = """\
Read the public state of a session: status, turn counters, question outcomes, \
touched targets, progress, client overrides, and the pending decision with all \
its candidates. Read-only, no turn consumed, no LLM call.

Never returns prompts, embeddings, selection scores or detailed semantic \
evidence: those do not exist in the public contract."""

_SUBMIT_FEEDBACK_DESCRIPTION = """\
Declare what the conversation really produced. Does not modify the session state \
and does not retroactively change any scoring.

`result` is success, partial or failure. `label` names your own business outcome \
("purchase", "appointment", "application_completed"). `metadata` holds short \
correlation facts only — an id, an amount, a flag. Never put messages, answers, \
summaries or transcripts in it."""

_SESSION_ID_FIELD = Field(description="Session id returned by nbq_create_session.")
_STATE_VERSION_FIELD = Field(
    default=None,
    ge=0,
    description=(
        "Version read before this mutation, for optimistic concurrency. Omit it and "
        "the last version seen for this session is used (read first if unknown). "
        "Pass it explicitly to control the check yourself."
    ),
)

SessionId = Annotated[str, _SESSION_ID_FIELD]
StateVersion = Annotated[int | None, _STATE_VERSION_FIELD]


class NBQRuntimeClient(Protocol):
    """The slice of `nbq.AsyncNBQClient` this server uses."""

    async def create_session(
        self,
        *,
        client_reference: str | None = ...,
        max_turns: int | None = ...,
        initial_history: Sequence[Mapping[str, Any]] | None = ...,
    ) -> Any: ...

    async def next(
        self,
        session_id: str,
        *,
        state_version: int,
        previous_turn: Mapping[str, Any] | None = ...,
        context_update: Mapping[str, Any] | None = ...,
        client_updates: Mapping[str, Any] | None = ...,
        selection: Mapping[str, Any] | None = ...,
    ) -> Any: ...

    async def apply_events(
        self,
        session_id: str,
        *,
        state_version: int,
        context_update: Mapping[str, Any] | None = ...,
        client_updates: Mapping[str, Any] | None = ...,
    ) -> Any: ...

    async def get_session(self, session_id: str) -> Any: ...

    async def submit_feedback(
        self,
        session_id: str,
        *,
        result: FeedbackResult,
        label: str | None = ...,
        metadata: Mapping[str, Any] | None = ...,
    ) -> Any: ...

    async def aclose(self) -> None: ...


ClientFactory = Callable[[], NBQRuntimeClient]


class MissingAPIKeyError(RuntimeError):
    """`NBQ_API_KEY` is absent from the server environment."""


def _env_float(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a number, got {raw!r}") from error


def _env_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from error


def api_key_is_configured() -> bool:
    """True when `NBQ_API_KEY` holds something usable."""

    return bool(os.environ.get("NBQ_API_KEY", "").strip())


def default_client_factory() -> NBQRuntimeClient:
    """Build the async SDK client from the environment.

    `NBQ_API_KEY` is required. `NBQ_BASE_URL`, `NBQ_TIMEOUT_SECONDS` and
    `NBQ_MAX_RETRIES` are optional and fall back to the SDK defaults. The key is
    read here and nowhere else, and is never logged or returned.
    """

    if not api_key_is_configured():
        raise MissingAPIKeyError("NBQ_API_KEY is not set")

    from nbq import AsyncNBQClient  # imported lazily: tests inject a fake client

    options: dict[str, Any] = {}
    base_url = os.environ.get("NBQ_BASE_URL", "").strip()
    if base_url:
        options["base_url"] = base_url
    timeout = _env_float("NBQ_TIMEOUT_SECONDS")
    if timeout is not None:
        options["timeout"] = timeout
    max_retries = _env_int("NBQ_MAX_RETRIES")
    if max_retries is not None:
        options["max_retries"] = max_retries

    # No cast: mypy checks structurally that the SDK client still satisfies
    # NBQRuntimeClient, so a signature drift in `nbq` fails the type check here.
    return AsyncNBQClient(**options)


class _ServerState:
    """Lazily built SDK client plus the last `state_version` per session.

    The version map is an ergonomic convenience, never a way to hide a conflict:
    a rejected version is surfaced to the host and the stale entry is dropped so
    the next call reads the session again instead of replaying it.
    """

    def __init__(self, client_factory: ClientFactory) -> None:
        self._client_factory = client_factory
        self._client: NBQRuntimeClient | None = None
        self._lock = anyio.Lock()
        self._versions: dict[str, int] = {}

    async def client(self) -> NBQRuntimeClient:
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    try:
                        self._client = self._client_factory()
                    except MissingAPIKeyError as error:
                        raise ToolError(AUTH_MESSAGE) from error
                    except ImportError as error:
                        raise ToolError(
                            "sdk_unavailable: the official NBQ SDK could not be loaded "
                            f"({error}). Reinstall nbq-mcp so that `nbq` 1.x is present."
                        ) from error
                    except (ValueError, NBQAPIError, NBQConnectionError) as error:
                        raise tool_error_for(error) from error
        return self._client

    async def aclose(self) -> None:
        client = self._client
        self._client = None
        if client is not None:
            await client.aclose()

    def tracked_version(self, session_id: str) -> int | None:
        return self._versions.get(session_id)

    def forget(self, session_id: str) -> None:
        self._versions.pop(session_id, None)

    def remember(self, payload: Mapping[str, Any]) -> None:
        session_id = payload.get("session_id")
        version = state_version_of(payload)
        if isinstance(session_id, str) and session_id and version is not None:
            self._versions[session_id] = version


async def _resolve_state_version(
    state: _ServerState,
    client: NBQRuntimeClient,
    session_id: str,
    explicit: int | None,
) -> int:
    """Explicit wins; otherwise use the tracked version, else read the session."""

    if explicit is not None:
        return explicit
    tracked = state.tracked_version(session_id)
    if tracked is not None:
        return tracked
    payload = await _invoke(state, client.get_session(session_id))
    version = state_version_of(payload)
    if version is None:
        raise ToolError(
            "unknown_state_version: the session state carried no versions.state_version; "
            "call nbq_get_session and pass state_version explicitly"
        )
    return version


async def _invoke(
    state: _ServerState,
    call: Awaitable[Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Await an SDK call, translate its failures, track the returned version."""

    try:
        response = await call
    except NBQAPIError as error:
        if session_id is not None and getattr(error, "code", None) == "state_version_conflict":
            state.forget(session_id)
        raise tool_error_for(error) from error
    except (NBQConnectionError, ValidationError, ValueError) as error:
        raise tool_error_for(error) from error

    payload = to_payload(response)
    state.remember(payload)
    return with_state_version(payload)


def build_server(
    client_factory: ClientFactory | None = None,
    *,
    log_level: str | None = None,
) -> MCPServer[None]:
    """Build the MCP server.

    `client_factory` is the injection point: tests pass a fake async client, and
    production uses `default_client_factory`, which reads `NBQ_API_KEY` from the
    environment. The client is created on the first tool call and closed on
    shutdown.

    Bind address and port are not settings of the server: they belong to the
    streamable-http transport and are passed to `run()`.
    """

    state = _ServerState(client_factory or default_client_factory)

    @asynccontextmanager
    async def lifespan(_: MCPServer[None]) -> AsyncIterator[None]:
        try:
            yield None
        finally:
            await state.aclose()

    settings: dict[str, Any] = {"lifespan": lifespan}
    if log_level is not None:
        settings["log_level"] = log_level

    server: MCPServer[None] = MCPServer(
        SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
        **settings,
    )

    @server.tool(name="nbq_create_session", description=_CREATE_SESSION_DESCRIPTION)
    async def nbq_create_session(
        client_reference: Annotated[
            str | None,
            Field(
                default=None,
                max_length=128,
                description="Your own opaque reference, returned as is for correlation.",
            ),
        ] = None,
        max_turns: Annotated[
            int | None,
            Field(
                default=None,
                ge=1,
                le=100,
                description="Overrides the configured soft turn limit for this session.",
            ),
        ] = None,
        initial_history: Annotated[
            list[InitialHistoryItemInput] | None,
            Field(default=None, max_length=100, description="Conversation started outside NBQ."),
        ] = None,
    ) -> dict[str, Any]:
        client = await state.client()
        return await _invoke(
            state,
            client.create_session(
                client_reference=client_reference,
                max_turns=max_turns,
                initial_history=(
                    [item.wire() for item in initial_history]
                    if initial_history is not None
                    else None
                ),
            ),
        )

    @server.tool(name="nbq_resume_session", description=_RESUME_SESSION_DESCRIPTION)
    async def nbq_resume_session(session_id: SessionId) -> dict[str, Any]:
        client = await state.client()
        return await _invoke(state, client.get_session(session_id))

    @server.tool(name="nbq_next", description=_NEXT_DESCRIPTION)
    async def nbq_next(
        session_id: SessionId,
        state_version: StateVersion = None,
        previous_turn: PreviousTurnInput | None = None,
        context_update: ContextUpdateInput | None = None,
        client_updates: ClientUpdatesInput | None = None,
        selection: SelectionInput | None = None,
    ) -> dict[str, Any]:
        client = await state.client()
        version = await _resolve_state_version(state, client, session_id, state_version)
        return await _invoke(
            state,
            client.next(
                session_id,
                state_version=version,
                previous_turn=previous_turn.wire() if previous_turn else None,
                context_update=context_update.wire() if context_update else None,
                client_updates=client_updates.wire() if client_updates else None,
                selection=selection.wire() if selection else None,
            ),
            session_id=session_id,
        )

    @server.tool(name="nbq_apply_events", description=_APPLY_EVENTS_DESCRIPTION)
    async def nbq_apply_events(
        session_id: SessionId,
        state_version: StateVersion = None,
        context_update: ContextUpdateInput | None = None,
        client_updates: ClientUpdatesInput | None = None,
    ) -> dict[str, Any]:
        if context_update is None and client_updates is None:
            raise ToolError(
                "invalid_request: nbq_apply_events needs context_update or client_updates"
            )
        client = await state.client()
        version = await _resolve_state_version(state, client, session_id, state_version)
        return await _invoke(
            state,
            client.apply_events(
                session_id,
                state_version=version,
                context_update=context_update.wire() if context_update else None,
                client_updates=client_updates.wire() if client_updates else None,
            ),
            session_id=session_id,
        )

    @server.tool(name="nbq_get_session", description=_GET_SESSION_DESCRIPTION)
    async def nbq_get_session(session_id: SessionId) -> dict[str, Any]:
        client = await state.client()
        return await _invoke(state, client.get_session(session_id))

    @server.tool(name="nbq_submit_feedback", description=_SUBMIT_FEEDBACK_DESCRIPTION)
    async def nbq_submit_feedback(
        session_id: SessionId,
        result: Annotated[
            FeedbackResult,
            Field(description="success, partial or failure."),
        ],
        label: Annotated[
            str | None,
            Field(default=None, max_length=128, description="Your own business outcome name."),
        ] = None,
        metadata: Annotated[
            dict[str, MetadataValue] | None,
            Field(
                default=None,
                description=(
                    "Short correlation facts only: string, number, boolean or null values. "
                    "No conversation content."
                ),
            ),
        ] = None,
    ) -> dict[str, Any]:
        client = await state.client()
        return await _invoke(
            state,
            client.submit_feedback(
                session_id,
                result=result,
                label=label,
                metadata=metadata,
            ),
        )

    # The decorators register the tools; the names are kept for introspection.
    _ = (
        nbq_create_session,
        nbq_resume_session,
        nbq_next,
        nbq_apply_events,
        nbq_get_session,
        nbq_submit_feedback,
    )
    return server
