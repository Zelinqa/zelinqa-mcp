# Changelog

## Unreleased

- Document that `zelinqa_adjust` and `zelinqa_add_context` can replace the
  pending question when the conversation state changes, for example when the
  information it asked for becomes known. The returned view shows the
  replacement and `zelinqa_next_question` attaches the next reply to it. The
  guide, tool descriptions, READMEs and skill say to ask the returned question,
  and to send an answer to a replaced question with `zelinqa_add_context`.
- Add a test covering a replaced pending question after both tools.
- In advanced mode, `zelinqa_apply_events` and `zelinqa_next` describe the
  replaced `decision_id` that a `previous_turn` may still cite once.

## 1.0.1 — 2026-09-29

- Require `zelinqa>=1.0.1,<2`. That SDK version accepts the
  `max_turns_reached` stop, as well as stop reasons and warnings added by later
  API releases. With `zelinqa` 1.0.0, the response ending a session at
  `max_turns` failed with a validation error.
- Server instructions, tool descriptions, the conversation guide and the
  READMEs describe the stop at `max_turns`: `action: "stop"` with
  `stop_reason: "max_turns_reached"`, and later calls return the same stop.
  `max_turns_reached` is no longer described as a warning.

## 1.0.0 — 2026-09-27

- Rename distribution, executable and environment variables to Zelinqa.
- Default business tools hide API identifiers and preserve independent named conversations.
- Resolve answer choice labels with the official SDK; report the question actually asked.
- Require the person's text for open answers. Explicit no-answer and refusal
  outcomes remain valid without text, as do choices for closed and semi-open questions.
- Merge reply submission into `zelinqa_next_question`; the default surface has
  seven business tools. `zelinqa_start` returns the first or pending question.
- Share one guide between server instructions and `zelinqa://guide`; expose one
  argument-free `zelinqa_integration_check` prompt and a shorter portable skill.
- Add the portable `skills/zelinqa` agent skill.
- Bound the local registry to 128 conversations; reject simultaneous mutations
  of one conversation and require reconciliation after interrupted calls.
- Keep the low-level tools available through `--advanced`.
- Disable HTTP hosting pending authentication and tenant/session isolation.
