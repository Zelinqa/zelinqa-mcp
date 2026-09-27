"""Live end-to-end suite: the real `zelinqa-mcp` process against the real API.

Opt-in and skipped by default. Run it with:

    ZELINQA_LIVE=1 ZELINQA_LIVE_RUNTIME_KEY=... uv run pytest -m live tests/live

Environment:
- `ZELINQA_LIVE=1` enables the suite;
- `ZELINQA_LIVE_RUNTIME_KEY` — key with the `runtime` scope (required);
- `ZELINQA_LIVE_BASE_URL` — defaults to `https://api.zelinqa.ai`;
- `ZELINQA_LIVE_REVOKED_KEY`, `ZELINQA_LIVE_CONFIG_READ_KEY` — optional negative cases.

The suite prints request ids and error codes only: never a key, never a
verbatim. `/next` calls are deliberately spaced to keep this small functional
recipe inexpensive; this is not a throughput benchmark.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import anyio
import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from mcp.types import CallToolResult, TextContent

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("ZELINQA_LIVE") != "1", reason="set ZELINQA_LIVE=1 to run"),
]

NEXT_CALL_SPACING_SECONDS = 1.0
DEFAULT_BASE_URL = "https://api.zelinqa.ai"


def _server_command() -> tuple[str, list[str]]:
    """Prefer the installed console script, fall back to `python -m zelinqa_mcp`."""

    console_script = shutil.which("zelinqa-mcp")
    if console_script:
        return console_script, []
    return sys.executable, ["-m", "zelinqa_mcp"]


def _server_env(api_key: str | None) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "ZELINQA_BASE_URL": os.environ.get("ZELINQA_LIVE_BASE_URL", DEFAULT_BASE_URL),
    }
    if api_key is not None:
        env["ZELINQA_API_KEY"] = api_key
    return env


def _required_key(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.skip(f"{name} is not set")
    return value


@asynccontextmanager
async def live_session(api_key: str) -> AsyncIterator[Client]:
    """Spawn the real `zelinqa-mcp` process over stdio and connect to it."""

    command, args = _server_command()
    parameters = StdioServerParameters(
        command=command, args=[*args, "--advanced"], env=_server_env(api_key)
    )
    async with Client(parameters) as session:
        yield session


def _text(result: CallToolResult) -> str:
    return "\n".join(block.text for block in result.content if isinstance(block, TextContent))


def _ok(result: CallToolResult, label: str) -> dict[str, Any]:
    assert result.is_error is False, f"{label} failed: {_text(result)}"
    assert result.structured_content is not None
    payload = result.structured_content
    print(f"{label}: request_id={payload.get('request_id')}")
    return payload


def _failed(result: CallToolResult, label: str) -> str:
    assert result.is_error is True, f"{label} unexpectedly succeeded"
    message = _text(result)
    print(f"{label}: {message.splitlines()[0][:160]}")
    return message


def _first_candidate(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates = payload.get("candidates") or []
    return candidates[0] if candidates else None


async def test_full_turn_loop() -> None:
    key = _required_key("ZELINQA_LIVE_RUNTIME_KEY")

    async with live_session(key) as session:
        listed = await session.list_tools()
        names = {tool.name for tool in listed.tools}
        assert names == {
            "zelinqa_create_session",
            "zelinqa_resume_session",
            "zelinqa_next",
            "zelinqa_apply_events",
            "zelinqa_get_session",
            "zelinqa_submit_feedback",
        }
        assert key not in listed.model_dump_json()

        created = _ok(
            await session.call_tool(
                "zelinqa_create_session",
                {"client_reference": "zelinqa-mcp-live", "max_turns": 8},
            ),
            "create_session",
        )
        session_id = created["session_id"]
        assert created["state_version"] == 0
        assert created["status"] == "active"

        # First turn: no previous_turn, and no state_version either — the server
        # sends the version it learned at creation.
        first = _ok(await session.call_tool("zelinqa_next", {"session_id": session_id}), "next#1")
        assert first["action"] in {"ask", "stop"}
        print(f"next#1: action={first['action']} warnings={first['warnings']}")
        candidate = _first_candidate(first)

        if candidate is not None:
            await anyio.sleep(NEXT_CALL_SPACING_SECONDS)
            previous_turn: dict[str, Any] = {"assistant_text": candidate["text"]}
            if candidate["type"] == "open":
                previous_turn["user_text"] = (
                    "Un canapé contemporain pour le salon, nous avons un chat."
                )
            else:
                previous_turn["structured_answer"] = {
                    "choice_ids": [candidate["choices"][0]["choice_id"]]
                }
            second = _ok(
                await session.call_tool(
                    "zelinqa_next", {"session_id": session_id, "previous_turn": previous_turn}
                ),
                "next#2",
            )
            print(
                f"next#2: action={second['action']} degraded={second['degraded']} "
                f"reasons={second['degraded_reasons']} warnings={second['warnings']}"
            )
            assert second["turn_count"] >= first["turn_count"]

        events = _ok(
            await session.call_tool(
                "zelinqa_apply_events",
                {
                    "session_id": session_id,
                    "context_update": {
                        "mode": "summary",
                        "text": "Le visiteur mesure la pièce ce week-end.",
                    },
                },
            ),
            "apply_events",
        )
        assert events["session_id"] == session_id

        state = _ok(
            await session.call_tool("zelinqa_get_session", {"session_id": session_id}),
            "get_session",
        )
        assert state["state_version"] >= events["state_version"]

        resumed = _ok(
            await session.call_tool("zelinqa_resume_session", {"session_id": session_id}),
            "resume_session",
        )
        assert resumed["session_id"] == session_id

        feedback = _ok(
            await session.call_tool(
                "zelinqa_submit_feedback",
                {
                    "session_id": session_id,
                    "result": "success",
                    "label": "achat",
                    "metadata": {"order_id": "MCP-LIVE-1"},
                },
            ),
            "submit_feedback",
        )
        assert feedback["feedback_id"]

        unknown = _failed(
            await session.call_tool("zelinqa_get_session", {"session_id": "ses_does_not_exist"}),
            "unknown_session",
        )
        assert "unknown_session" in unknown


async def test_stale_state_version_is_a_readable_conflict() -> None:
    key = _required_key("ZELINQA_LIVE_RUNTIME_KEY")

    async with live_session(key) as session:
        created = _ok(
            await session.call_tool(
                "zelinqa_create_session", {"client_reference": "zelinqa-mcp-live"}
            ),
            "create_session",
        )
        session_id = created["session_id"]

        _ok(await session.call_tool("zelinqa_next", {"session_id": session_id}), "next#1")
        await anyio.sleep(NEXT_CALL_SPACING_SECONDS)

        message = _failed(
            await session.call_tool(
                "zelinqa_next",
                {
                    "session_id": session_id,
                    "state_version": 0,
                    "previous_turn": {"assistant_text": "Rappel", "user_text": "Oui"},
                },
            ),
            "state_version_conflict",
        )
        assert "state_version_conflict" in message
        assert "current_state_version" in message
        assert "call zelinqa_get_session then retry" in message


async def test_invalid_key_is_reported_as_unauthorized() -> None:
    # The deployed gateway answers 403 `{"message":"Forbidden"}` for an invalid
    # key, with no V1 envelope. The SDK maps that to ZelinqaAuthenticationError.
    async with live_session("zelinqa_live_invalid") as session:
        message = _failed(
            await session.call_tool("zelinqa_create_session", {}),
            "invalid_key",
        )
        assert "unauthorized (HTTP 403):" in message
        assert "ZELINQA_API_KEY" in message


async def test_revoked_key_is_reported_as_unauthorized() -> None:
    key = _required_key("ZELINQA_LIVE_REVOKED_KEY")

    async with live_session(key) as session:
        message = _failed(await session.call_tool("zelinqa_create_session", {}), "revoked_key")
        assert "unauthorized (HTTP 403):" in message
        assert key not in message


async def test_key_without_the_runtime_scope_is_refused() -> None:
    key = _required_key("ZELINQA_LIVE_CONFIG_READ_KEY")

    async with live_session(key) as session:
        message = _failed(await session.call_tool("zelinqa_create_session", {}), "wrong_scope")
        # The authorizer refuses a configuration key on a runtime route with the
        # same 403 `{"message":"Forbidden"}` it uses for a revoked key: from the
        # outside the two are indistinguishable, so the readable refusal names
        # both possibilities instead of claiming insufficient_scope.
        assert "unauthorized (HTTP 403):" in message
        assert "does not carry the `runtime` scope" in message
        assert key not in message


def test_the_server_refuses_to_start_without_a_key() -> None:
    command, args = _server_command()
    completed = subprocess.run(
        [command, *args],
        env=_server_env(None),
        input="",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 2, completed.stderr
    assert completed.stdout == ""
    assert "ZELINQA_API_KEY is not set" in completed.stderr


def test_tool_schemas_are_json_serializable() -> None:
    """A host must be able to forward the schemas verbatim."""

    key = _required_key("ZELINQA_LIVE_RUNTIME_KEY")

    async def run() -> None:
        async with live_session(key) as session:
            listed = await session.list_tools()
            for tool in listed.tools:
                json.dumps(tool.input_schema)
                json.dumps(tool.output_schema)

    anyio.run(run)
