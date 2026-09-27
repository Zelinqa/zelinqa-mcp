# NBQ MCP Server

Official [Model Context Protocol](https://modelcontextprotocol.io) server for the Zelinqa
**NBQ** (Next Best Question) API. It gives an LLM host six tools to run a qualification
conversation: your agent asks the questions, NBQ decides which question is worth asking
next.

```text
MCP tool  ->  Python SDK `nbq`  ->  public REST API https://api.zelinqa.ai
```

The server is a protocol adapter and nothing more. It never speaks HTTP itself, never
imports the NBQ engine, never opens a database, and exposes no selection score.

> **Status: not published yet.** `nbq-mcp` is not on PyPI, because the `nbq` SDK 1.0.0 it
> depends on is not published either. Run it from a checkout for now, as described below.
> See [`PUBLISHING.md`](PUBLISHING.md).

## Install

Once published, no install step is needed — `uvx` fetches and runs it:

```bash
uvx nbq-mcp            # not available yet
```

From a checkout, today:

```bash
git clone https://github.com/Zelinqa/nbq-mcp.git
cd nbq-mcp
uv sync --group dev
uv run nbq-mcp --version
```

Requires Python 3.11 or newer.

## Configuration

Everything comes from the server process environment.

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `NBQ_API_KEY` | **yes** | — | NBQ API key carrying the `runtime` scope. The server refuses to start without it (exit code `2`). |
| `NBQ_BASE_URL` | no | `https://api.zelinqa.ai` | Alternate API base URL. |
| `NBQ_TIMEOUT_SECONDS` | no | SDK default (30) | Per-attempt HTTP timeout. |
| `NBQ_MAX_RETRIES` | no | SDK default (2) | Retries on connection errors, 429 and 5xx. |

Command line:

```text
nbq-mcp [--transport stdio|streamable-http] [--host HOST] [--port PORT]
        [--log-level DEBUG|INFO|WARNING|ERROR|CRITICAL] [--version]
```

`stdio` is the default and the transport every desktop host uses. Logs always go to
stderr, never to stdout, which carries the MCP protocol itself.

## Host setup

Ready-to-copy files live in [`examples/`](examples).

### Claude Code

```bash
claude mcp add nbq --env NBQ_API_KEY=$NBQ_API_KEY -- uvx nbq-mcp
```

Or commit a project-scoped [`.mcp.json`](examples/claude-code.mcp.json):

```json
{
  "mcpServers": {
    "nbq": {
      "command": "uvx",
      "args": ["nbq-mcp"],
      "env": { "NBQ_API_KEY": "${NBQ_API_KEY}" }
    }
  }
}
```

`${NBQ_API_KEY}` is expanded by Claude Code from your shell environment, so the file holds
no secret and can be committed.

### Claude Desktop

Add the contents of [`examples/claude-desktop.json`](examples/claude-desktop.json) to
`claude_desktop_config.json`, replacing the placeholder with your key: Claude Desktop does
not expand environment variables. Then restart the app.

### Codex CLI

Add the block from [`examples/codex-config.toml`](examples/codex-config.toml) to
`~/.codex/config.toml`:

```toml
[mcp_servers.nbq]
command = "uvx"
args = ["nbq-mcp"]
# Codex asks before every MCP tool call unless the server approves its tools;
# in `codex exec` (non-interactive) an unapproved call is auto-rejected as
# "user cancelled MCP tool call". The six NBQ tools only act on your own NBQ.
default_tools_approval_mode = "approve"
env = { NBQ_API_KEY = "PASTE_YOUR_RUNTIME_KEY_HERE" }
```

### Cursor

Add [`examples/cursor.mcp.json`](examples/cursor.mcp.json) as `.cursor/mcp.json` in the
project, or as `~/.cursor/mcp.json` globally.

### Running from a checkout

Before the package is on PyPI, point the host at your clone with
[`examples/local-dev.mcp.json`](examples/local-dev.mcp.json) (or
[`examples/local-dev-codex-config.toml`](examples/local-dev-codex-config.toml)):

```json
{
  "mcpServers": {
    "nbq": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/nbq-mcp", "nbq-mcp"],
      "env": { "NBQ_API_KEY": "${NBQ_API_KEY}" }
    }
  }
}
```

## The six tools

| Tool | API route | What it does |
|---|---|---|
| `nbq_create_session` | `POST /v1/sessions` | Start a session for one conversation. Returns the initial state; no question yet. |
| `nbq_resume_session` | `GET /v1/sessions/{id}` | Pick an existing session back up and re-learn its `state_version` and pending candidates. |
| `nbq_next` | `POST /v1/sessions/{id}/next` | Understand the previous turn, then return the ranked next questions. |
| `nbq_apply_events` | `POST /v1/sessions/{id}/events` | Apply context or known data without selecting a question and without consuming a turn. |
| `nbq_get_session` | `GET /v1/sessions/{id}` | Read the public session state. |
| `nbq_submit_feedback` | `POST /v1/sessions/{id}/feedback` | Declare what the conversation really produced. |

Configuration routes are deliberately absent: this server carries the runtime surface
only, so a host needs nothing beyond a `runtime` key.

### The turn protocol

1. `nbq_create_session` once per conversation.
2. `nbq_next` **with no `previous_turn`** for the first turn. Ask the candidate of rank 1,
   in your own words if you prefer.
3. `nbq_next` again, passing what actually happened:

   ```json
   {
     "session_id": "ses_01J8Z",
     "previous_turn": {
       "assistant_text": "And what budget did you have in mind?",
       "user_text": "Around 2000 euros, 2500 at most."
     }
   }
   ```

   `decision_id`, `question_id` and `outcome` are optional helpers, not identifiers to
   invent: NBQ resolves the candidate you used from the pending decision and your text.
   For a choice question, send `structured_answer: {"choice_ids": ["choice_1m"]}` with ids
   copied from the candidate's `choices` — that path is deterministic and costs no LLM
   call. Omitting `user_text` is allowed when a structured answer or `client_updates`
   already carry the information; the turn is then understood in reduced mode, reported in
   `degraded_reasons`.
4. Repeat. **You decide when to stop.** NBQ keeps proposing the best available question and
   reports the situation in `warnings`: `max_turns_reached` (soft limit reached),
   `objective_achieved` (success conditions met), `eligibility_exhausted_fallback`,
   `constraints_relaxed`. An `action: "stop"` with `stop_reason: "no_question_available"`
   is the only hard stop: there is genuinely no question left.
5. `nbq_submit_feedback` once the real outcome is known.

Every result is structured JSON carrying the contract fields — `candidates` with
`rank` / `question_id` / `text` / `type` / `choices` / `target_ids`, `progress`,
`turn_count`, `turns_remaining`, `warnings`, `degraded`, `degraded_reasons`, `request_id`.
Nothing is filtered out.

### `state_version`, without hidden conflicts

Every mutation is guarded by optimistic concurrency. The server keeps the last
`state_version` it saw for each session, so you can omit `state_version` and it sends the
tracked one; if it has never seen the session, it reads it first. Passing `state_version`
explicitly always wins.

A conflict is never resolved silently. When the API rejects the version you get a readable
error naming `supplied_state_version`, `current_state_version` and the instruction *call
nbq_get_session then retry*, and the stale value is dropped rather than replayed.

Each mutating tool call is one logical mutation: the SDK generates its `Idempotency-Key`
and reuses it across its own retries, so a transient network failure never doubles a turn.
Calling the same tool twice on purpose is two mutations, not a replay.

## Error semantics

Failures come back as MCP tool errors whose text is meant to be actionable:

```text
state_version_conflict: The session changed since your last read. (request_id=req_9003)
  — call nbq_get_session then retry
  — {"current_state_version":8,"supplied_state_version":7}
```

- Business errors keep their contract envelope: `<code>: <message> (request_id=<id>)`,
  followed by the relevant `details` as compact JSON — `required_scopes` /
  `granted_scopes`, `supplied_state_version` / `current_state_version`,
  `invalid_choice_ids`, `candidate_question_ids`, and so on.
- An authentication or gateway authorization refusal becomes:

  ```text
  unauthorized (HTTP 403): the NBQ API key is missing, invalid, revoked, expired,
  or does not carry the `runtime` scope (check NBQ_API_KEY)
  ```

  The deployed gateway answers an envelope-less `403` for an invalid, revoked or wrongly
  scoped key, so those cases are genuinely indistinguishable from outside: the message
  names every possibility instead of guessing one. A missing `Authorization` header is the
  same message with `HTTP 401`.
- A network failure after the SDK's retries becomes a readable `connection_error`.
- Arguments that cannot satisfy the contract are rejected before any network call, with the
  offending field named.

## Security

- The API key is read from `NBQ_API_KEY` in the server process only. It never appears in a
  log line, a tool result, an error message or a stack trace; any configured key found in an
  outgoing string is replaced by `[redacted]`.
- Use a key that carries the `runtime` scope only.
- On stdio, stdout is the protocol channel: every log record goes to stderr, and no request
  body or conversation content is logged.
- See [`SECURITY.md`](SECURITY.md) to report a vulnerability.

## Development

```bash
uv sync --group dev
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest            # the live suite is excluded by default
```

The unit suite runs the real server in process through the MCP in-memory transport, against
a fake async SDK client returning the payloads of the V1 contract examples. No network.

### Live tests

The live suite spawns the real `nbq-mcp` process over stdio and talks to the real API. It
is opt-in and skipped unless `NBQ_LIVE=1`:

```bash
NBQ_LIVE=1 \
NBQ_LIVE_RUNTIME_KEY=<runtime key> \
NBQ_LIVE_BASE_URL=https://api.zelinqa.ai \
uv run pytest -m live tests/live -s
```

Optional keys enable the negative cases: `NBQ_LIVE_REVOKED_KEY` and
`NBQ_LIVE_CONFIG_READ_KEY` (a key without the `runtime` scope). Tests needing a key that is
not set are skipped. The suite prints request ids and error codes only, never a key and
never a verbatim, and spaces its `/next` calls by one second to respect the staging Bedrock
quota.

## License

Apache-2.0 — see [`LICENSE`](LICENSE).
