# NBQ-240 — Zelinqa MCP validation

Release candidate, not published. Built on Claude's NBQ-240 implementation, with
new default business tools; the original low-level tools remain behind `--advanced`.

- 52 functional/unit tests passed using the real MCP in-memory transport.
- 8 live tests passed against a dedicated synthetic staging NBQ, including the
  default business loop over an actual stdio subprocess and legacy advanced tools.
- The combined SDK/MCP recipe recorded 6 feedback rows, verified directly in
  PostgreSQL. Temporary API keys were revoked; the synthetic NBQ/tenant disabled.
- mypy, Ruff, wheel/sdist build and Twine metadata validation passed.
- Wheels installed in a clean Python environment; stdio discovery returned 7 tools,
  2 prompts and the guide resource. No source-checkout import required.
- The skill passes the skill-creator structural validator. It is not a claim that
  every third-party LLM host has been tested with this new business interface.

CI runs functional tests on Python 3.11 and 3.13. It does not run live calls on PRs.
See the SDK's RELEASE-VALIDATION.md for its independent tests and packaging checks.

## Deliberate limits

- stdio only; no unauthenticated shared HTTP service.
- 128 local business handles; no transcript history cached. Advanced version cache
  is also bounded to 128 entries (a miss rereads the API).
- Same-conversation mutations are sequential. Conflicts/cancellation require refresh
  and reconciliation; no silent replay of an uncertain answer.
- Restart recovery requires a host-persisted session ID. Desktop-only conversations
  do not automatically recover after the process is lost.
- No sustained-load benchmark or total-RSS measurement; do not promise a concurrency
  capacity from these functional tests.
- Review dependency is pinned to SDK commit 82fe9f30897dcb585be2d0a0ba2a72f1a5b25812.
  Remove that Git override after publishing `zelinqa` on PyPI and before MCP release.
  The publication workflow refuses to release while the override remains.
