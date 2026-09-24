"""Opt-in stdio recipe of the default, identifier-free surface."""

import json
import os
import sys
import uuid

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from .test_live_mcp import _ok, _required_key, _server_env

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("ZELINQA_LIVE") != "1", reason="set ZELINQA_LIVE=1"),
]


async def test_business_conversation_over_real_stdio():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "zelinqa_mcp"],
        env=_server_env(_required_key("ZELINQA_LIVE_RUNTIME_KEY")),
    )
    async with Client(parameters) as client:
        tools = await client.list_tools()
        schemas = json.dumps([t.input_schema for t in tools.tools])
        for forbidden in ["session_id", "decision_id", "question_id", "state_version"]:
            assert forbidden not in schemas
        assert len((await client.list_prompts()).prompts) == 2
        assert (await client.get_prompt("zelinqa_conversation")).messages
        assert (await client.read_resource("zelinqa://guide")).contents
        name = "sdk-business-" + uuid.uuid4().hex[:8]
        args = {"conversation": name}
        started = _ok(await client.call_tool("zelinqa_start", args), "start")
        adjusted = _ok(
            await client.call_tool("zelinqa_adjust", dict(args, objective="not_achieved")),
            "adjust",
        )
        assert adjusted["turn_count"] == started["turn_count"]
        first = _ok(await client.call_tool("zelinqa_next_question", args), "next")
        assert first["questions"]
        replay = _ok(await client.call_tool("zelinqa_next_question", args), "cached next")
        assert first == replay
        question = first["questions"][0]
        answer = dict(args, candidate_rank=question["rank"])
        if question["choices"]:
            answer["choice_labels"] = [question["choices"][0]]
        else:
            answer["user_text"] = "Je cherche un canapé confortable pour mon salon."
        updated = _ok(await client.call_tool("zelinqa_answer", answer), "answer")
        assert updated["turn_count"] > first["turn_count"]
        _ok(await client.call_tool("zelinqa_status", args), "status")
        recorded = _ok(
            await client.call_tool(
                "zelinqa_feedback", dict(args, result="success", label="sdk-mcp-business-recipe")
            ),
            "feedback",
        )
        assert recorded["recorded"] is True
        forgotten = _ok(await client.call_tool("zelinqa_forget", args), "forget")
        assert forgotten["server_data_deleted"] is False
