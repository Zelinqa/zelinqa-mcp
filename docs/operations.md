# Operating the server

This page keeps the operational details that the README only summarises: how
replies are validated, how `zelinqa_adjust` behaves, how state and retries work,
and how the test suites are run.

## Answering rules

- An open question requires the person's words in `user_text`. An outcome alone
  is accepted only for `refused` or `asked_no_answer`, for any question type.
- Closed and semi-open questions accept exact `choice_labels`; semi-open choices
  can also include `free_text`.
- `assistant_text` records the wording actually asked. Use `candidate_rank` when
  asking a candidate other than rank 1; it defaults to 1.
- Never invent an answer or outcome. A reply with no pending question is an error.
- Invalid local answers leave the pending question unchanged and can be corrected
  without an API call. Calling `zelinqa_next_question` without reply fields only
  redisplays the pending question and does not consume a turn.
- Session, decision and question IDs, as well as state versions, are never tool
  inputs in the default mode.

## Applying known data with `zelinqa_adjust`

When a CRM already knows an answer, use `zelinqa_adjust` instead of asking again.
It accepts:

- `dimensions: [{"id": "configured_dimension_id", "status": "excluded"}]` with the
  statuses `achieved`, `not_achieved` and `excluded`;
- `data: [{"id": "configured_information_id", "value": 2500}]`, or the operations
  `unset` and `not_applicable` without a value;
- `objective: "not_achieved"`.

These are configured business IDs, not session or decision IDs. Use only verified
information. `adjust` does not consume a turn and returns the usual business view.
After a conflict, call `zelinqa_status` and reconcile before retrying. A question
already pending is not recalculated by `adjust`: inspect the returned view and
prefer adjusting before `zelinqa_next_question`.

## What results contain

Results include question text, ranks, choice labels, objective progress and
counters. Next-decision results also include warnings, the stop reason and
degraded-mode reasons. The full target and ID maps are deliberately absent.

At `max_turns`, the result has `action: "stop"` and
`stop_reason: "max_turns_reached"`, and later calls return the same stop.
Reaching the turn limit is **not** proof of objective completion.

## State, retries and memory

- The registry holds at most **128 conversations**. It never silently evicts one;
  use `zelinqa_forget` when finished. It stores current state, not a transcript.
- Calls mutating the same conversation must be sequential. A simultaneous call is
  rejected, not queued with a stale answer. Different conversations stay separate.
- The SDK reuses one idempotency key across retries of a single HTTP mutation.
  Repeating a tool call manually is a new operation, not an automatic replay.
- On a conflict or interrupted request, call `zelinqa_status` and reconcile with
  the pending question before answering again. Errors are not hidden.
- Names are process-local. For restart persistence the host must retain the API
  session ID and inject `ZELINQA_SESSION_ID` and `ZELINQA_CONVERSATION` outside
  the model.

## Transport and isolation

The supported transport is **stdio**, one isolated process per trusted host and
user. HTTP hosting is disabled pending authentication and session isolation.
Logs use stderr; stdout is reserved for MCP. Do not share one process across
untrusted users, and never paste keys into a chat, repository or report.

## Advanced mode

`zelinqa-mcp --advanced` exposes the six low-level tools instead of the business
tools: `zelinqa_create_session`, `zelinqa_resume_session`, `zelinqa_next`,
`zelinqa_apply_events`, `zelinqa_get_session` and `zelinqa_submit_feedback`.
This mode intentionally exposes API identifiers and full state. Configuration
management is not an MCP tool: use the SDK's separate configuration client and
scopes.

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
Optional revoked and read-only keys exercise authorization failures. Use a
dedicated synthetic domain: the live tests create sessions and feedback. Unit
tests alone do not prove the deployed API or database persistence.
