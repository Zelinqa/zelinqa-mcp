# Changelog

## Unreleased — 1.0.0

- Rename distribution, executable and environment variables to Zelinqa.
- Default business tools hide API identifiers and preserve independent named conversations.
- Resolve answer choice labels with the official SDK; report the question actually asked.
- Add two user-controlled prompts and the `zelinqa://guide` resource.
- Add the portable `skills/zelinqa` agent skill.
- Bound the local registry to 128 conversations; reject simultaneous mutations
  of one conversation and require reconciliation after interrupted calls.
- Keep the low-level tools available through `--advanced`.
- Disable HTTP hosting pending authentication and tenant/session isolation.

The package is prepared for publication, not yet published.
