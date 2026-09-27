"""Tool surface, turn protocol, state_version ergonomics and error semantics."""

from __future__ import annotations

import pytest
from nbq.errors import (
    NBQAuthenticationError,
    NBQConnectionError,
    NBQInsufficientScopeError,
    NBQInvalidPreviousTurnError,
    NBQStateVersionConflictError,
    NBQUnknownSessionError,
)

from nbq_mcp import __version__

from .conftest import call_tool, connect, error_text, structured
from .contract_examples import (
    ARRET_SANS_QUESTION,
    DECISION_APRES_MAX_TURNS,
    DECISION_NORMALE,
    FEEDBACK_ENREGISTRE,
    SESSION_NEUVE,
    session_state,
)
from .fakes import FakeRuntimeClient

SESSION_ID = SESSION_NEUVE["session_id"]

EXPECTED_TOOLS = {
    "nbq_create_session",
    "nbq_resume_session",
    "nbq_next",
    "nbq_apply_events",
    "nbq_get_session",
    "nbq_submit_feedback",
}


async def test_lists_exactly_the_six_runtime_tools(client: FakeRuntimeClient) -> None:
    async with connect(client) as session:
        listed = await session.list_tools()

    tools = {tool.name: tool for tool in listed.tools}
    assert set(tools) == EXPECTED_TOOLS
    for tool in tools.values():
        assert tool.description
        assert tool.input_schema["type"] == "object"
        assert tool.output_schema is not None

    assert tools["nbq_create_session"].input_schema.get("required", []) == []
    assert tools["nbq_get_session"].input_schema["required"] == ["session_id"]
    assert set(tools["nbq_submit_feedback"].input_schema["required"]) == {"session_id", "result"}
    next_properties = tools["nbq_next"].input_schema["properties"]
    assert set(next_properties) == {
        "session_id",
        "state_version",
        "previous_turn",
        "context_update",
        "client_updates",
        "selection",
    }


async def test_the_server_announces_its_own_name_and_version(
    client: FakeRuntimeClient,
) -> None:
    async with connect(client) as session:
        info = session.server_info
        instructions = session.instructions or ""

    assert info.name == "nbq"
    assert info.version == __version__
    assert "nbq_create_session" in instructions
    assert "previous_turn" in instructions


async def test_tool_descriptions_teach_the_turn_protocol(client: FakeRuntimeClient) -> None:
    async with connect(client) as session:
        listed = await session.list_tools()

    description = next(tool.description or "" for tool in listed.tools if tool.name == "nbq_next")
    assert "no `previous_turn`" in description
    assert "assistant_text" in description
    assert "user_text" in description
    assert "structured_answer" in description
    assert "max_turns_reached" in description
    assert "objective_achieved" in description
    assert 'action: "stop"' in description


async def test_create_session_returns_the_contract_state(client: FakeRuntimeClient) -> None:
    client.queue("create_session", SESSION_NEUVE)

    async with connect(client) as session:
        result = structured(await call_tool(session, "nbq_create_session"))

    assert result["session_id"] == SESSION_ID
    assert result["status"] == "active"
    assert result["max_turns"] == 10
    assert result["turns_remaining"] == 10
    assert result["question_state"] == {"outcomes": []}
    assert result["targets"] == {}
    assert result["pending_decision"] is None
    assert result["progress"]["objective"]["effective_status"] == "not_started"
    assert result["state_version"] == 0
    assert result["versions"]["state_version"] == 0
    assert result["request_id"] == "req_1001"


async def test_create_session_forwards_its_arguments(client: FakeRuntimeClient) -> None:
    client.queue("create_session", SESSION_NEUVE)

    async with connect(client) as session:
        structured(
            await call_tool(
                session,
                "nbq_create_session",
                client_reference="crm-lead-8842",
                max_turns=10,
                initial_history=[
                    {"role": "assistant", "message_id": "msg_1", "text": "Bonjour ?"},
                    {"role": "user", "message_id": "msg_2", "text": "Un canapé."},
                ],
            )
        )

    sent = client.calls_to("create_session")[0].kwargs
    assert sent["client_reference"] == "crm-lead-8842"
    assert sent["max_turns"] == 10
    assert sent["initial_history"] == [
        {"role": "assistant", "message_id": "msg_1", "text": "Bonjour ?"},
        {"role": "user", "message_id": "msg_2", "text": "Un canapé."},
    ]


async def test_next_first_turn_uses_the_version_learned_at_creation(
    client: FakeRuntimeClient,
) -> None:
    client.queue("create_session", SESSION_NEUVE).queue("next", DECISION_NORMALE)

    async with connect(client) as session:
        await call_tool(session, "nbq_create_session")
        result = structured(await call_tool(session, "nbq_next", session_id=SESSION_ID))

    assert client.calls_to("get_session") == []
    sent = client.calls_to("next")[0].kwargs
    assert sent["state_version"] == 0
    assert sent["previous_turn"] is None
    assert result["action"] == "ask"
    assert result["decision_id"] == "dec_7f2a"
    assert result["stop_reason"] is None
    assert [candidate["rank"] for candidate in result["candidates"]] == [1, 2]
    assert result["candidates"][0]["question_id"] == "q_budget"
    assert result["candidates"][0]["type"] == "open"
    assert result["candidates"][0]["choices"] == []
    assert result["candidates"][0]["target_ids"] == ["annual_budget"]
    assert [choice["choice_id"] for choice in result["candidates"][1]["choices"]] == [
        "choice_1m",
        "choice_3m",
        "choice_later",
    ]
    assert result["turn_count"] == 2
    assert result["turns_remaining"] == 8
    assert result["state_version"] == 4


async def test_next_reads_the_session_when_the_version_is_unknown(
    client: FakeRuntimeClient,
) -> None:
    client.queue("get_session", session_state()).queue("next", DECISION_NORMALE)

    async with connect(client) as session:
        structured(await call_tool(session, "nbq_next", session_id=SESSION_ID))

    assert [call.method for call in client.calls] == ["get_session", "next"]
    assert client.calls_to("next")[0].kwargs["state_version"] == 0


async def test_next_prefers_an_explicit_state_version(client: FakeRuntimeClient) -> None:
    client.queue("create_session", SESSION_NEUVE).queue("next", DECISION_NORMALE)

    async with connect(client) as session:
        await call_tool(session, "nbq_create_session")
        await call_tool(session, "nbq_next", session_id=SESSION_ID, state_version=3)

    assert client.calls_to("next")[0].kwargs["state_version"] == 3
    assert client.calls_to("get_session") == []


async def test_next_forwards_the_previous_turn_in_contract_shape(
    client: FakeRuntimeClient,
) -> None:
    client.queue("next", DECISION_NORMALE)

    async with connect(client) as session:
        await call_tool(
            session,
            "nbq_next",
            session_id=SESSION_ID,
            state_version=3,
            previous_turn={
                "assistant_text": "Et côté budget ?",
                "user_text": "Autour de 2 000 euros.",
                "message_id": "msg_18",
            },
        )

    assert client.calls_to("next")[0].kwargs["previous_turn"] == {
        "assistant_text": "Et côté budget ?",
        "user_text": "Autour de 2 000 euros.",
        "message_id": "msg_18",
    }


async def test_next_forwards_a_structured_answer_and_selection(
    client: FakeRuntimeClient,
) -> None:
    client.queue("next", DECISION_NORMALE)

    async with connect(client) as session:
        await call_tool(
            session,
            "nbq_next",
            session_id=SESSION_ID,
            state_version=4,
            previous_turn={
                "decision_id": "dec_7f2a",
                "question_id": "q_style",
                "outcome": "asked_answered",
                "structured_answer": {"choice_ids": ["choice_contemporain"]},
            },
            selection={
                "candidate_count": 2,
                "allowed_question_types": ["single_choice", "multiple_choice"],
                "sub_objectives": {"ids": ["so_besoin"], "mode": "restrict"},
            },
        )

    sent = client.calls_to("next")[0].kwargs
    assert sent["previous_turn"] == {
        "decision_id": "dec_7f2a",
        "question_id": "q_style",
        "outcome": "asked_answered",
        "structured_answer": {"choice_ids": ["choice_contemporain"]},
    }
    assert sent["selection"] == {
        "candidate_count": 2,
        "allowed_question_types": ["single_choice", "multiple_choice"],
        "sub_objectives": {"ids": ["so_besoin"], "mode": "restrict"},
    }


async def test_warnings_and_degradation_reach_the_host(client: FakeRuntimeClient) -> None:
    client.queue("next", DECISION_APRES_MAX_TURNS)

    async with connect(client) as session:
        result = structured(
            await call_tool(session, "nbq_next", session_id=SESSION_ID, state_version=20)
        )

    assert result["warnings"] == ["max_turns_reached"]
    assert result["degraded"] is True
    assert result["degraded_reasons"] == ["missing_user_text"]
    assert result["action"] == "ask"
    assert result["turns_remaining"] == 0
    assert result["candidates"]


async def test_stop_carries_no_candidate_and_a_stop_reason(client: FakeRuntimeClient) -> None:
    client.queue("next", ARRET_SANS_QUESTION)

    async with connect(client) as session:
        result = structured(
            await call_tool(session, "nbq_next", session_id=SESSION_ID, state_version=24)
        )

    assert result["action"] == "stop"
    assert result["stop_reason"] == "no_question_available"
    assert result["decision_id"] is None
    assert result["candidates"] == []
    assert result["warnings"] == ["objective_achieved", "max_turns_reached"]
    overrides = result["progress"]["sub_objectives"][2]["client_override"]
    assert overrides["status"] == "excluded"


async def test_apply_events_reuses_the_version_returned_by_next(
    client: FakeRuntimeClient,
) -> None:
    client.queue("next", DECISION_NORMALE).queue(
        "apply_events", session_state(versions={**SESSION_NEUVE["versions"], "state_version": 5})
    )

    async with connect(client) as session:
        await call_tool(session, "nbq_next", session_id=SESSION_ID, state_version=3)
        result = structured(
            await call_tool(
                session,
                "nbq_apply_events",
                session_id=SESSION_ID,
                client_updates={"data": [{"id": "annual_budget", "value": 2500}]},
            )
        )

    sent = client.calls_to("apply_events")[0].kwargs
    assert sent["state_version"] == 4
    assert sent["client_updates"] == {
        "data": [{"id": "annual_budget", "operation": "set", "value": 2500}]
    }
    assert result["state_version"] == 5
    assert client.calls_to("get_session") == []


async def test_apply_events_accepts_a_summary_context(client: FakeRuntimeClient) -> None:
    client.queue("apply_events", SESSION_NEUVE)

    async with connect(client) as session:
        await call_tool(
            session,
            "nbq_apply_events",
            session_id=SESSION_ID,
            state_version=3,
            context_update={"mode": "summary", "text": "Le visiteur emménage en mars."},
        )

    assert client.calls_to("apply_events")[0].kwargs["context_update"] == {
        "mode": "summary",
        "text": "Le visiteur emménage en mars.",
    }


async def test_apply_events_requires_an_update(client: FakeRuntimeClient) -> None:
    async with connect(client) as session:
        message = error_text(
            await call_tool(session, "nbq_apply_events", session_id=SESSION_ID, state_version=2)
        )

    assert "context_update or client_updates" in message
    assert client.calls == []


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"mode": "summary"}, "needs text"),
        ({"mode": "messages"}, "needs messages"),
        (
            {"mode": "summary", "text": "x", "messages": [{"role": "user", "text": "x"}]},
            "must not carry messages",
        ),
        ({"mode": "messages", "messages": [{"role": "user"}]}, "text or structured_answer"),
        (
            {
                "mode": "messages",
                "messages": [{"role": "user", "structured_answer": {"choice_ids": ["c1"]}}],
            },
            "also needs question_id",
        ),
    ],
)
async def test_context_update_branches_are_validated(
    client: FakeRuntimeClient, arguments: dict[str, object], expected: str
) -> None:
    async with connect(client) as session:
        message = error_text(
            await call_tool(
                session,
                "nbq_apply_events",
                session_id=SESSION_ID,
                state_version=2,
                context_update=arguments,
            )
        )

    assert expected in message
    assert client.calls == []


async def test_data_update_without_value_is_rejected(client: FakeRuntimeClient) -> None:
    async with connect(client) as session:
        message = error_text(
            await call_tool(
                session,
                "nbq_apply_events",
                session_id=SESSION_ID,
                state_version=2,
                client_updates={"data": [{"id": "annual_budget"}]},
            )
        )

    assert "needs a value" in message
    assert client.calls == []


async def test_get_session_and_resume_session_return_the_state(
    client: FakeRuntimeClient,
) -> None:
    client.queue("get_session", SESSION_NEUVE)

    async with connect(client) as session:
        read = structured(await call_tool(session, "nbq_get_session", session_id=SESSION_ID))
        resumed = structured(await call_tool(session, "nbq_resume_session", session_id=SESSION_ID))

    assert read["session_id"] == resumed["session_id"] == SESSION_ID
    assert read["state_version"] == 0
    assert resumed["pending_decision"] is None


async def test_submit_feedback_returns_the_receipt(client: FakeRuntimeClient) -> None:
    client.queue("submit_feedback", FEEDBACK_ENREGISTRE)

    async with connect(client) as session:
        result = structured(
            await call_tool(
                session,
                "nbq_submit_feedback",
                session_id=SESSION_ID,
                result="success",
                label="achat",
                metadata={"order_id": "SO-99120"},
            )
        )

    assert result["feedback_id"] == "fbk_02K1"
    assert result["request_id"] == "req_5f31"
    assert result["recorded_at"].startswith("2026-09-01T09:14:22")
    assert "state_version" not in result
    sent = client.calls_to("submit_feedback")[0].kwargs
    assert sent["result"] == "success"
    assert sent["label"] == "achat"
    assert sent["metadata"] == {"order_id": "SO-99120"}


async def test_unknown_feedback_result_is_rejected_before_the_api(
    client: FakeRuntimeClient,
) -> None:
    async with connect(client) as session:
        message = error_text(
            await call_tool(
                session, "nbq_submit_feedback", session_id=SESSION_ID, result="converted"
            )
        )

    assert "result" in message
    assert client.calls == []


async def test_state_version_conflict_is_readable_and_never_retried(
    client: FakeRuntimeClient,
) -> None:
    client.queue(
        "next",
        NBQStateVersionConflictError(
            "La session a été modifiée depuis votre dernière lecture.",
            status_code=409,
            code="state_version_conflict",
            request_id="req_9003",
            details={"supplied_state_version": 7, "current_state_version": 8},
        ),
    )

    async with connect(client) as session:
        message = error_text(
            await call_tool(session, "nbq_next", session_id=SESSION_ID, state_version=7)
        )

    assert "state_version_conflict" in message
    assert "request_id=req_9003" in message
    assert "call nbq_get_session then retry" in message
    assert '"supplied_state_version":7' in message
    assert '"current_state_version":8' in message
    assert len(client.calls_to("next")) == 1


async def test_a_rejected_version_is_not_replayed_on_the_next_call(
    client: FakeRuntimeClient,
) -> None:
    client.queue("create_session", SESSION_NEUVE)
    client.queue(
        "next",
        NBQStateVersionConflictError(
            "conflit",
            status_code=409,
            code="state_version_conflict",
            request_id="req_9003",
            details={"supplied_state_version": 0, "current_state_version": 8},
        ),
        DECISION_NORMALE,
    )
    client.queue(
        "get_session",
        session_state(versions={**SESSION_NEUVE["versions"], "state_version": 8}),
    )

    async with connect(client) as session:
        await call_tool(session, "nbq_create_session")
        error_text(await call_tool(session, "nbq_next", session_id=SESSION_ID))
        structured(await call_tool(session, "nbq_next", session_id=SESSION_ID))

    assert [call.method for call in client.calls] == [
        "create_session",
        "next",
        "get_session",
        "next",
    ]
    assert [call.kwargs["state_version"] for call in client.calls_to("next")] == [0, 8]


async def test_missing_header_is_reported_as_unauthorized(client: FakeRuntimeClient) -> None:
    client.queue(
        "get_session",
        NBQAuthenticationError(
            "Unauthorized",
            status_code=401,
            code=None,
            request_id=None,
            details={},
        ),
    )

    async with connect(client) as session:
        message = error_text(await call_tool(session, "nbq_get_session", session_id=SESSION_ID))

    assert "unauthorized (HTTP 401):" in message
    assert "missing, invalid, revoked, expired" in message
    assert "does not carry the `runtime` scope" in message
    assert "check NBQ_API_KEY" in message


async def test_gateway_403_without_envelope_is_the_same_readable_refusal(
    client: FakeRuntimeClient,
) -> None:
    """The deployed gateway cannot tell a revoked key from a wrong scope."""

    client.queue(
        "create_session",
        NBQAuthenticationError(
            "Forbidden by the API gateway: the key is invalid, revoked, expired, or does "
            "not carry the scope required for this route.",
            status_code=403,
            code=None,
            request_id=None,
            details={},
        ),
    )

    async with connect(client) as session:
        message = error_text(await call_tool(session, "nbq_create_session"))

    assert "unauthorized (HTTP 403):" in message
    assert "does not carry the `runtime` scope" in message
    assert "check NBQ_API_KEY" in message


async def test_missing_api_key_is_reported_as_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nbq_mcp.server import build_server, default_client_factory

    monkeypatch.delenv("NBQ_API_KEY", raising=False)
    server = build_server(default_client_factory)

    from mcp.client import Client

    async with Client(server) as session:
        message = error_text(await call_tool(session, "nbq_get_session", session_id=SESSION_ID))

    assert "check NBQ_API_KEY" in message


async def test_insufficient_scope_lists_the_scopes(client: FakeRuntimeClient) -> None:
    client.queue(
        "get_session",
        NBQInsufficientScopeError(
            "Cette clé ne permet pas cette opération.",
            status_code=403,
            code="insufficient_scope",
            request_id="req_9001",
            details={
                "required_scopes": ["runtime"],
                "granted_scopes": ["configuration:read"],
            },
        ),
    )

    async with connect(client) as session:
        message = error_text(await call_tool(session, "nbq_get_session", session_id=SESSION_ID))

    assert "insufficient_scope" in message
    assert '"required_scopes":["runtime"]' in message
    assert '"granted_scopes":["configuration:read"]' in message


async def test_invalid_previous_turn_keeps_the_candidate_ids(client: FakeRuntimeClient) -> None:
    client.queue(
        "next",
        NBQInvalidPreviousTurnError(
            "Les identifiants fournis ne correspondent pas à la décision en attente.",
            status_code=422,
            code="invalid_previous_turn",
            request_id="req_9011",
            details={
                "pending_decision_id": "dec_7f2a",
                "supplied_decision_id": "dec_7f29",
                "candidate_question_ids": ["q_style", "q_budget"],
            },
        ),
    )

    async with connect(client) as session:
        message = error_text(
            await call_tool(
                session,
                "nbq_next",
                session_id=SESSION_ID,
                state_version=4,
                previous_turn={"decision_id": "dec_7f29"},
            )
        )

    assert "invalid_previous_turn" in message
    assert '"candidate_question_ids":["q_style","q_budget"]' in message


async def test_unknown_session_is_readable(client: FakeRuntimeClient) -> None:
    client.queue(
        "get_session",
        NBQUnknownSessionError(
            "La session demandée est inconnue.",
            status_code=404,
            code="unknown_session",
            request_id="req_9007",
            details={"session_id": "ses_inconnue"},
        ),
    )

    async with connect(client) as session:
        message = error_text(await call_tool(session, "nbq_get_session", session_id="ses_inconnue"))

    assert "unknown_session: La session demandée est inconnue. (request_id=req_9007)" in message


async def test_connection_failure_is_readable(client: FakeRuntimeClient) -> None:
    client.queue("get_session", NBQConnectionError("timed out after 3 attempts"))

    async with connect(client) as session:
        message = error_text(await call_tool(session, "nbq_get_session", session_id=SESSION_ID))

    assert "connection_error" in message
    assert "timed out after 3 attempts" in message
    assert "api.zelinqa.ai" in message


async def test_the_api_key_never_reaches_a_tool_result(
    client: FakeRuntimeClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = "nbq_live_thisisafakekeyvalue"
    monkeypatch.setenv("NBQ_API_KEY", key)
    client.queue("create_session", session_state(client_reference=key))
    client.queue(
        "get_session",
        NBQUnknownSessionError(
            f"Clé {key} refusée.",
            status_code=404,
            code="unknown_session",
            request_id="req_9007",
            details={"echo": key},
        ),
    )

    async with connect(client) as session:
        created = structured(await call_tool(session, "nbq_create_session"))
        message = error_text(await call_tool(session, "nbq_get_session", session_id=SESSION_ID))
        listed = await session.list_tools()

    assert key not in str(created)
    assert created["client_reference"] == "[redacted]"
    assert key not in message
    assert "[redacted]" in message
    assert key not in listed.model_dump_json()


async def test_the_client_is_closed_on_shutdown(client: FakeRuntimeClient) -> None:
    client.queue("get_session", SESSION_NEUVE)

    async with connect(client) as session:
        await call_tool(session, "nbq_get_session", session_id=SESSION_ID)
        assert client.closed is False

    assert client.closed is True


async def test_the_client_is_built_once_and_only_on_demand() -> None:
    built: list[FakeRuntimeClient] = []

    def factory() -> FakeRuntimeClient:
        created = FakeRuntimeClient()
        created.queue("get_session", SESSION_NEUVE)
        built.append(created)
        return created

    from nbq_mcp.server import build_server

    server = build_server(factory)  # type: ignore[arg-type]

    from mcp.client import Client

    async with Client(server) as session:
        await session.list_tools()
        assert built == []
        await call_tool(session, "nbq_get_session", session_id=SESSION_ID)
        await call_tool(session, "nbq_get_session", session_id=SESSION_ID)

    assert len(built) == 1
