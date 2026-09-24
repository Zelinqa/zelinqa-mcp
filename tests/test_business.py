import copy
import json

import anyio
from mcp.client import Client
from zelinqa.errors import ZelinqaStateVersionConflictError

from zelinqa_mcp.business import build_business_server
from zelinqa_mcp.server import build_server

from .conftest import error_text, structured
from .contract_examples import DECISION_NORMALE, SESSION_NEUVE
from .fakes import FakeRuntimeClient


def fixture_client():
    return (
        FakeRuntimeClient().queue("create_session", SESSION_NEUVE).queue("next", DECISION_NORMALE)
    )


async def test_default_tools_do_not_expose_ids_and_loop_has_no_extra_reads():
    fake = fixture_client()
    async with Client(build_server(lambda: fake)) as client:
        tools = await client.list_tools()
        schemas = json.dumps([t.input_schema for t in tools.tools])
        for forbidden in ["session_id", "decision_id", "state_version", "question_id", "choice_id"]:
            assert forbidden not in schemas
        started = structured(await client.call_tool("zelinqa_start", {"conversation": "demo"}))
        assert started["questions"] == []
        result = structured(
            await client.call_tool("zelinqa_next_question", {"conversation": "demo"})
        )
        assert result["questions"][0]["text"]
        assert "warnings" in result and "degraded_reasons" in result
        for hidden in ["session_id", "decision_id", "target_ids", "choice_id", "state_version"]:
            assert hidden not in json.dumps(result)
        await client.call_tool("zelinqa_next_question", {"conversation": "demo"})
        assert len(fake.calls_to("next")) == 1
        structured(
            await client.call_tool(
                "zelinqa_answer", {"conversation": "demo", "user_text": "Pour mon salon"}
            )
        )
        call = fake.calls_to("next")[-1].kwargs
        turn = call["previous_turn"].model_dump(exclude_none=True)
        assert turn["decision_id"] == DECISION_NORMALE["decision_id"]
        assert "outcome" not in turn
        assert not fake.calls_to("get_session")


async def test_adjust_maps_business_updates_without_consuming_a_turn():
    updated = copy.deepcopy(SESSION_NEUVE)
    updated["versions"]["state_version"] = 1
    updated["progress"]["objective"]["client_override"] = {"status": "achieved"}
    updated["progress"]["objective"]["effective_status"] = "covered"
    fake = FakeRuntimeClient().queue("create_session", SESSION_NEUVE).queue("apply_events", updated)

    async with Client(build_server(lambda: fake)) as client:
        structured(await client.call_tool("zelinqa_start", {"conversation": "demo"}))
        result = structured(
            await client.call_tool(
                "zelinqa_adjust",
                {
                    "conversation": "demo",
                    "dimensions": [
                        {"id": "so_besoin", "status": "achieved"},
                        {"id": "so_budget", "status": "not_achieved"},
                        {"id": "so_livraison", "status": "excluded"},
                    ],
                    "data": [
                        {"id": "annual_budget", "value": 2500},
                        {"id": "old_value", "operation": "unset"},
                        {"id": "not_relevant", "operation": "not_applicable"},
                    ],
                    "objective": "achieved",
                },
            )
        )

    assert result["turn_count"] == 0
    assert result["progress"]["effective_status"] == "covered"
    assert "state_version" not in json.dumps(result)
    assert not fake.calls_to("next")
    sent = fake.calls_to("apply_events")[0].kwargs
    assert sent["state_version"] == 0
    assert sent["context_update"] is None
    assert sent["client_updates"] == {
        "dimensions": [
            {"id": "so_besoin", "operation": "set", "status": "achieved"},
            {"id": "so_budget", "operation": "set", "status": "not_achieved"},
            {"id": "so_livraison", "operation": "exclude"},
        ],
        "data": [
            {"id": "annual_budget", "operation": "set", "value": 2500},
            {"id": "old_value", "operation": "unset"},
            {"id": "not_relevant", "operation": "not_applicable"},
        ],
        "objective": {"operation": "set", "status": "achieved"},
    }


async def test_adjust_preserves_a_pending_question_in_the_returned_view():
    updated = copy.deepcopy(SESSION_NEUVE)
    updated["pending_decision"] = {
        "decision_id": DECISION_NORMALE["decision_id"],
        "candidates": DECISION_NORMALE["candidates"],
    }
    updated["turn_count"] = DECISION_NORMALE["turn_count"]
    updated["turns_remaining"] = DECISION_NORMALE["turns_remaining"]
    updated["versions"]["state_version"] = 5
    fake = (
        FakeRuntimeClient()
        .queue("create_session", SESSION_NEUVE)
        .queue("next", DECISION_NORMALE)
        .queue("apply_events", updated)
    )

    async with Client(build_server(lambda: fake)) as client:
        structured(await client.call_tool("zelinqa_start", {"conversation": "demo"}))
        pending = structured(
            await client.call_tool("zelinqa_next_question", {"conversation": "demo"})
        )
        adjusted = structured(
            await client.call_tool(
                "zelinqa_adjust", {"conversation": "demo", "objective": "not_achieved"}
            )
        )

    assert adjusted["questions"] == pending["questions"]
    assert adjusted["turn_count"] == pending["turn_count"]
    assert len(fake.calls_to("next")) == 1


async def test_adjust_rejects_missing_or_ambiguous_updates_before_api_call():
    fake = FakeRuntimeClient().queue("create_session", SESSION_NEUVE)
    async with Client(build_server(lambda: fake)) as client:
        structured(await client.call_tool("zelinqa_start", {"conversation": "demo"}))
        for arguments in [{}, {"dimensions": [{"id": "so_budget", "status": "excluded"}] * 2}]:
            assert "invalid_request" in error_text(
                await client.call_tool("zelinqa_adjust", {"conversation": "demo", **arguments})
            )
        for arguments in [
            {"data": [{"id": "budget", "operation": "unset", "value": 5}]},
            {"data": [{"id": "budget", "operation": "set"}]},
            {"data": [{"id": "", "value": 5}]},
        ]:
            assert "validation error" in error_text(
                await client.call_tool("zelinqa_adjust", {"conversation": "demo", **arguments})
            )
    assert not fake.calls_to("apply_events")


async def test_adjust_conflict_requires_refresh_before_retry():
    conflict = ZelinqaStateVersionConflictError(
        "session has changed", status_code=409, code="state_version_conflict"
    )
    refreshed = copy.deepcopy(SESSION_NEUVE)
    refreshed["versions"]["state_version"] = 2
    fake = (
        FakeRuntimeClient()
        .queue("create_session", SESSION_NEUVE)
        .queue("apply_events", conflict, refreshed)
        .queue("get_session", refreshed)
    )
    arguments = {"conversation": "demo", "objective": "not_achieved"}

    async with Client(build_server(lambda: fake)) as client:
        structured(await client.call_tool("zelinqa_start", {"conversation": "demo"}))
        assert "call zelinqa_status" in error_text(
            await client.call_tool("zelinqa_adjust", arguments)
        )
        assert "refresh_required" in error_text(await client.call_tool("zelinqa_adjust", arguments))
        structured(await client.call_tool("zelinqa_status", {"conversation": "demo"}))
        structured(await client.call_tool("zelinqa_adjust", arguments))

    assert len(fake.calls_to("apply_events")) == 2
    assert [call.kwargs["state_version"] for call in fake.calls_to("apply_events")] == [0, 2]


async def test_capacity_no_silent_eviction_and_forget_not_delete():
    fake = fixture_client()
    async with Client(build_business_server(lambda: fake, capacity=1)) as client:
        await client.call_tool("zelinqa_start", {"conversation": "a"})
        await client.call_tool("zelinqa_start", {"conversation": "a"})
        assert len(fake.calls_to("create_session")) == 1
        assert "capacity_reached" in error_text(
            await client.call_tool("zelinqa_start", {"conversation": "b"})
        )
        result = structured(await client.call_tool("zelinqa_forget", {"conversation": "a"}))
        assert result == {"forgotten_locally": True, "server_data_deleted": False}
        structured(await client.call_tool("zelinqa_start", {"conversation": "b"}))
        assert "unknown_conversation" in error_text(
            await client.call_tool("zelinqa_status", {"conversation": "a"})
        )


async def test_two_conversations_never_mix():
    a, b = copy.deepcopy(SESSION_NEUVE), copy.deepcopy(SESSION_NEUVE)
    a["session_id"], b["session_id"] = "session-a", "session-b"
    da, db = copy.deepcopy(DECISION_NORMALE), copy.deepcopy(DECISION_NORMALE)
    da["session_id"], db["session_id"] = "session-a", "session-b"
    da["decision_id"], db["decision_id"] = "decision-a", "decision-b"
    fake = FakeRuntimeClient().queue("create_session", a, b).queue("next", da, db, da, db)
    async with Client(build_server(lambda: fake)) as client:
        for name in ["a", "b"]:
            await client.call_tool("zelinqa_start", {"conversation": name})
            await client.call_tool("zelinqa_next_question", {"conversation": name})
        for name in ["a", "b"]:
            structured(
                await client.call_tool(
                    "zelinqa_answer", {"conversation": name, "user_text": "Hello"}
                )
            )
        answers = fake.calls_to("next")[-2:]
        assert [c.kwargs["session_id"] for c in answers] == ["session-a", "session-b"]
        assert [c.kwargs["previous_turn"].decision_id for c in answers] == [
            "decision-a",
            "decision-b",
        ]


async def test_invalid_answer_requires_refresh_and_does_not_send():
    fake = fixture_client().queue("get_session", SESSION_NEUVE)
    async with Client(build_server(lambda: fake)) as client:
        await client.call_tool("zelinqa_start", {"conversation": "demo"})
        assert "No pending" in error_text(
            await client.call_tool("zelinqa_answer", {"conversation": "demo", "user_text": "Hi"})
        )
        assert not fake.calls_to("next")
        assert "refresh_required" in error_text(
            await client.call_tool("zelinqa_next_question", {"conversation": "demo"})
        )
        structured(await client.call_tool("zelinqa_status", {"conversation": "demo"}))
        structured(await client.call_tool("zelinqa_next_question", {"conversation": "demo"}))


async def test_host_resumes_by_environment_not_model_id(monkeypatch):
    monkeypatch.setenv("ZELINQA_SESSION_ID", "host-owned-id")
    monkeypatch.setenv("ZELINQA_CONVERSATION", "resume-demo")
    fake = fixture_client().queue("get_session", SESSION_NEUVE)
    async with Client(build_server(lambda: fake)) as client:
        structured(await client.call_tool("zelinqa_start", {"conversation": "resume-demo"}))
        assert fake.calls_to("get_session")[0].kwargs["session_id"] == "host-owned-id"
        assert not fake.calls_to("create_session")


async def test_prompts_and_resource_are_readable_without_api_calls():
    fake = FakeRuntimeClient()
    async with Client(build_server(lambda: fake)) as client:
        prompts = await client.list_prompts()
        assert {p.name for p in prompts.prompts} == {
            "zelinqa_conversation",
            "zelinqa_integration_check",
        }
        prompt = await client.get_prompt("zelinqa_conversation")
        assert prompt.messages
        resources = await client.list_resources()
        assert str(resources.resources[0].uri) == "zelinqa://guide"
        resource = await client.read_resource("zelinqa://guide")
        assert resource.contents
        assert not fake.calls


async def test_same_conversation_concurrent_requests_are_rejected():
    entered, release = anyio.Event(), anyio.Event()

    class SlowClient(FakeRuntimeClient):
        async def next(self, *args, **kwargs):
            entered.set()
            await release.wait()
            return await super().next(*args, **kwargs)

    fake = SlowClient().queue("create_session", SESSION_NEUVE).queue("next", DECISION_NORMALE)
    async with Client(build_server(lambda: fake)) as client:
        await client.call_tool("zelinqa_start", {"conversation": "demo"})

        async def first():
            structured(await client.call_tool("zelinqa_next_question", {"conversation": "demo"}))

        async with anyio.create_task_group() as group:
            group.start_soon(first)
            await entered.wait()
            try:
                assert "conversation_busy" in error_text(
                    await client.call_tool("zelinqa_next_question", {"conversation": "demo"})
                )
            finally:
                release.set()
        assert len(fake.calls_to("next")) == 1
