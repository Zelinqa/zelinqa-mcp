"""Exercise the packaged MCP protocol through a real local subprocess."""

from __future__ import annotations

import os
import sys

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from mcp.types import TextContent


async def test_default_stdio_surface_and_network_error() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "zelinqa_mcp"],
        env={
            "PATH": os.environ.get("PATH", ""),
            "ZELINQA_API_KEY": "not-a-real-api-key",
            "ZELINQA_BASE_URL": "http://127.0.0.1:1",
            "ZELINQA_TIMEOUT_SECONDS": "1",
            "ZELINQA_MAX_RETRIES": "0",
        },
    )
    async with Client(parameters) as client:
        tools = await client.list_tools()
        assert len(tools.tools) == 7
        assert "zelinqa_answer" not in {t.name for t in tools.tools}
        prompts = (await client.list_prompts()).prompts
        assert [p.name for p in prompts] == ["zelinqa_integration_check"]
        assert not prompts[0].arguments
        resource = await client.read_resource("zelinqa://guide")
        assert resource.contents[0].text == client.instructions

        result = await client.call_tool("zelinqa_start", {"conversation": "stdio-smoke"})
        assert result.is_error is True
        message = " ".join(block.text for block in result.content if isinstance(block, TextContent))
        assert "connection_error" in message
        assert "ZELINQA_BASE_URL" in message
        assert "not-a-real-api-key" not in message
