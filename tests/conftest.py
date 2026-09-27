"""Shared fixtures and helpers for the unit suite."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from mcp.client import Client
from mcp.types import CallToolResult, TextContent

from nbq_mcp.server import build_server

from .fakes import FakeRuntimeClient

_KEY_ENV_VARS = (
    "NBQ_API_KEY",
    "NBQ_BASE_URL",
    "NBQ_TIMEOUT_SECONDS",
    "NBQ_MAX_RETRIES",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """No ambient NBQ configuration leaks into a test."""

    for name in _KEY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture
def client() -> FakeRuntimeClient:
    return FakeRuntimeClient()


@asynccontextmanager
async def connect(client: FakeRuntimeClient) -> AsyncIterator[Client]:
    """Run the server in process and yield a connected MCP client."""

    server = build_server(lambda: client)
    async with Client(server) as session:
        yield session


async def call_tool(session: Client, name: str, **arguments: Any) -> CallToolResult:
    return await session.call_tool(name, arguments)


def structured(result: CallToolResult) -> dict[str, Any]:
    assert result.is_error is False, text_of(result)
    assert result.structured_content is not None
    return result.structured_content


def text_of(result: CallToolResult) -> str:
    return "\n".join(block.text for block in result.content if isinstance(block, TextContent))


def error_text(result: CallToolResult) -> str:
    assert result.is_error is True, f"expected an error, got {result.structured_content}"
    return text_of(result)
