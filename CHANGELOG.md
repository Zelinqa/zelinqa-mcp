# Changelog

## Unreleased — 1.0.0

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

The package is prepared for publication, not yet published.
