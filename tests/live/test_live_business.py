"""Opt-in stdio recipe of the default, identifier-free surface."""

import json
import os
import sys
import uuid

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from .test_live_mcp import _failed, _ok, _required_key, _server_env

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
        assert {tool.name for tool in tools.tools} == {
            "zelinqa_start",
            "zelinqa_next_question",
            "zelinqa_add_context",
            "zelinqa_adjust",
            "zelinqa_status",
            "zelinqa_feedback",
            "zelinqa_forget",
        }
        schemas = json.dumps([t.input_schema for t in tools.tools])
        for forbidden in ["session_id", "decision_id", "question_id", "state_version"]:
            assert forbidden not in schemas
        assert len((await client.list_prompts()).prompts) == 1
        assert (await client.get_prompt("zelinqa_integration_check")).messages
        guide = await client.read_resource("zelinqa://guide")
        assert guide.contents[0].text == client.instructions
        name = "sdk-business-" + uuid.uuid4().hex[:8]
        args = {"conversation": name}
        started = _ok(await client.call_tool("zelinqa_start", args), "start")
        assert started["questions"]
        assert _ok(await client.call_tool("zelinqa_start", args), "reuse start") == started
        assert _ok(await client.call_tool("zelinqa_next_question", args), "cached first") == started
        adjusted = _ok(
            await client.call_tool("zelinqa_adjust", dict(args, objective="not_achieved")),
            "adjust",
        )
        assert adjusted["turn_count"] == started["turn_count"]
        assert adjusted["questions"] == started["questions"]
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
        updated = _ok(await client.call_tool("zelinqa_next_question", answer), "answer")
        assert updated["turn_count"] == first["turn_count"] + 1
        contextual = _ok(
            await client.call_tool(
                "zelinqa_add_context",
                dict(
                    args,
                    summary="Synthetic setup: the visitor will measure the room tomorrow.",
                ),
            ),
            "context",
        )
        assert contextual["questions"] == updated["questions"]
        assert contextual["turn_count"] == updated["turn_count"]
        current = _ok(await client.call_tool("zelinqa_status", args), "status")
        assert current == contextual
        second_args = {"conversation": name + "-second"}
        second = _ok(await client.call_tool("zelinqa_start", second_args), "second start")
        assert second["questions"]
        assert _ok(await client.call_tool("zelinqa_start", args), "first unchanged") == current
        recorded = _ok(
            await client.call_tool(
                "zelinqa_feedback", dict(args, result="partial", label="sdk-mcp-business-recipe")
            ),
            "feedback",
        )
        assert recorded["recorded"] is True
        after_feedback = _ok(await client.call_tool("zelinqa_status", args), "after feedback")
        assert after_feedback["progress"] == current["progress"]
        for conversation in (args, second_args):
            forgotten = _ok(await client.call_tool("zelinqa_forget", conversation), "forget")
            assert forgotten["server_data_deleted"] is False
            assert "unknown_conversation" in _failed(
                await client.call_tool("zelinqa_status", conversation),
                "forgotten name",
            )


@pytest.mark.parametrize("kind", ["open", "choices"])
async def test_rejected_reply_can_be_corrected_without_refresh(kind):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "zelinqa_mcp"],
        env=_server_env(_required_key("ZELINQA_LIVE_RUNTIME_KEY")),
    )
    async with Client(parameters) as client:
        args = {"conversation": "sdk-rejected-" + uuid.uuid4().hex[:8]}
        first = _ok(await client.call_tool("zelinqa_start", args), "start")
        try:
            question = next(
                (
                    q
                    for q in first["questions"]
                    if (q["type"] == "open" if kind == "open" else bool(q["choices"]))
                ),
                None,
            )
            if question is None:
                pytest.skip(f"Dedicated published corpus must propose a {kind} candidate")
            invalid = dict(args, candidate_rank=question["rank"])
            valid = dict(invalid)
            if kind == "open":
                invalid["outcome"] = "asked_answered"
                valid["user_text"] = "I need a comfortable sofa for the living room."
            else:
                invalid["choice_labels"] = ["unlisted-" + uuid.uuid4().hex]
                valid["choice_labels"] = [question["choices"][0]]
            assert "invalid_request" in _failed(
                await client.call_tool("zelinqa_next_question", invalid),
                "invalid reply",
            )
            unchanged = _ok(
                await client.call_tool("zelinqa_next_question", args), "pending unchanged"
            )
            assert unchanged == first
            corrected = _ok(
                await client.call_tool("zelinqa_next_question", valid), "corrected reply"
            )
            assert corrected["turn_count"] == first["turn_count"] + 1
        finally:
            _ok(await client.call_tool("zelinqa_forget", args), "forget")
