# Zelinqa MCP

<!-- mcp-name: io.github.Zelinqa/zelinqa-mcp -->

The official MCP adapter for goal-oriented question selection. The model handles
the conversation; the SDK handles session IDs, pending decisions and state versions.

Python 3.11+ required. Release prerequisites are in [PUBLISHING.md](PUBLISHING.md).

```text
MCP host → zelinqa-mcp → Python SDK zelinqa → api.zelinqa.ai
```

## Start

Run the published package:

```bash
uvx zelinqa-mcp
```

To run from source:

```bash
git clone https://github.com/Zelinqa/zelinqa-mcp.git
cd zelinqa-mcp
uv sync --group dev --locked
uv run zelinqa-mcp --version
```

Configure `ZELINQA_API_KEY` in the host's secret environment (runtime scope).
Never paste keys into a chat, repository or report. Host examples are in
[examples/](examples); replace local checkout paths where necessary.

| Environment variable | Purpose |
|---|---|
| `ZELINQA_API_KEY` | Required runtime key, scoped to one published domain |
| `ZELINQA_BASE_URL` | Default `https://api.zelinqa.ai` |
| `ZELINQA_TIMEOUT_SECONDS` | Per-attempt timeout, default 30 seconds |
| `ZELINQA_MAX_RETRIES` | Retry count, default 2 |
| `ZELINQA_SESSION_ID` | Optional host-owned session to resume after restart |
| `ZELINQA_CONVERSATION` | Local name of that resumed session; default `conversation` |

The supported transport is **stdio**, one isolated process per trusted host/user.
HTTP hosting is disabled pending authentication and session isolation. Logs use stderr;
stdout is reserved for MCP. Do not share one process across untrusted users.

## Business tools (default)

| Tool | What it does |
|---|---|
| `zelinqa_start` | Start or recover a named conversation and return its first or pending question |
| `zelinqa_next_question` | Record the person's reply and return the next question; without a reply, redisplay the pending question without a new turn |
| `zelinqa_add_context` | Add a context summary without asking a question |
| `zelinqa_adjust` | Apply confirmed data, dimension statuses or an objective override without consuming a turn |
| `zelinqa_status` | Refresh progress and the pending question |
| `zelinqa_feedback` | Record an observed business result: success, partial or failure |
| `zelinqa_forget` | Free the local handle; does **not** delete API data |

The seven business tools use this loop: start, ask the returned question, then
pass the person's reply to `zelinqa_next_question`. Repeat until stopped or the
objective is achieved, then report the real business result with `zelinqa_feedback`.

Example tool sequence (the second call only redisplays the pending question):

```json
{"tool":"zelinqa_start","arguments":{"conversation":"demo-42"}}
{"tool":"zelinqa_next_question","arguments":{"conversation":"demo-42"}}
{"tool":"zelinqa_next_question","arguments":{"conversation":"demo-42","user_text":"For my living room"}}
```

For a displayed choice use `choice_labels: ["Contemporary"]`. Use `candidate_rank`
when asking a candidate other than rank 1. Session, decision and question IDs,
as well as state versions, are not tool inputs.
An open question requires the person's words in `user_text`. An outcome alone is
accepted only for `refused` or `asked_no_answer`, for any question type. Closed
and semi-open questions accept exact `choice_labels`; semi-open choices can also
include `free_text`. `assistant_text` records the wording actually asked.
Never invent an answer or outcome. A reply with no pending question is an error.
Invalid local answers leave the pending question unchanged and can be corrected
without an API call. Calling without reply fields only redisplays the pending
question; `candidate_rank` defaults to 1.

When a CRM already knows an answer, use `zelinqa_adjust` instead of asking again.
It accepts `dimensions: [{"id":"configured_dimension_id","status":"excluded"}]`,
`data: [{"id":"configured_information_id","value":2500}]`, or
`objective: "not_achieved"`. Dimension statuses are `achieved`, `not_achieved`,
and `excluded`; data also supports `operation: "unset"` and
`operation: "not_applicable"` without a value. These are configured business IDs,
not session or decision IDs. Use only verified information; `adjust` does not
consume a turn and returns the usual business view. After a conflict, call `status`
and reconcile before retrying. A question already pending is not recalculated by
`adjust`; inspect the returned view and prefer adjusting before `next_question`.

Results include question text, ranks, choice labels, objective progress and counters.
Next-decision results also include warnings, stop reason and degraded-mode reasons.
The full target/ID maps are deliberately absent. A turn-limit warning is **not**
proof of objective completion.

## State, retries and memory

- The registry holds at most **128 conversations**. It never silently evicts one;
  use `forget` when finished. It stores current state, not a conversation transcript.
- Calls mutating the same conversation must be sequential. A simultaneous call is
  rejected, not queued with a stale answer. Different conversations stay separate.
- The SDK reuses one idempotency key across retries of a single HTTP mutation.
  Repeating a tool call manually is a new operation, not an automatic replay.
- On a conflict or interrupted request, call `zelinqa_status` and reconcile with
  the pending question before answering again. Errors are not hidden.
- Names are process-local. For restart persistence the host must retain the API
  session ID and inject the resume variables above outside the model.

`zelinqa-mcp --advanced` exposes the six low-level tools instead: `create_session`,
`resume_session`, `next`, `apply_events`, `get_session`, `submit_feedback` (all prefixed
`zelinqa_`). This mode intentionally exposes API identifiers and full state. Configuration
management is not a MCP tool: use the SDK's separate configuration client/scopes.

## Prompts, resource and skill

| Item | Purpose |
|---|---|
| Resource `zelinqa://guide` | The same guide supplied as the server's instructions |
| Prompt `zelinqa_integration_check` | User-selected integration test checklist |
| [Skill `zelinqa`](skills/zelinqa/SKILL.md) | Short MCP workflow pointing to the guide as the reference |

Reading these does not call the Zelinqa API or start a conversation. Copy the
`skills/zelinqa` directory into your host's supported skills directory. No installation
or credentials are granted by the skill itself.

## Tests

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
uv build
uv run twine check dist/*
```

CI runs functional tests over the in-memory MCP transport with a fake SDK, plus
lint, types and packaging. Live tests are separate and opt-in: `ZELINQA_LIVE=1`
with `ZELINQA_LIVE_RUNTIME_KEY`, then `uv run pytest -m live tests/live`.
Optional revoked/read-only keys exercise authorization failures. Use a dedicated
synthetic Zelinqa: the live tests create sessions and feedback. Unit tests alone do not
prove the deployed API or database persistence.

Apache-2.0. See [SECURITY.md](SECURITY.md) for vulnerability reporting.
