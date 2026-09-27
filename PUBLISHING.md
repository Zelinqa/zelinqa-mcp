# Publishing Zelinqa MCP

Merge and publication require maintainer approval.

1. Verify that Python **`zelinqa` 1.0.0** is available on PyPI.
2. Keep the SDK dependency pinned to `zelinqa==1.0.0` from PyPI, with no Git or
   developer-local source override. When updating it, regenerate `uv.lock` and
   rerun tests from a clean checkout before releasing MCP.
3. Configure a pending Trusted Publisher for **`zelinqa-mcp`** in PyPI with owner
   `Zelinqa`, repository `zelinqa-mcp`, workflow `publish-pypi.yml`, and the
   `pypi` environment.
   A pending publisher does not reserve the package name.
4. Run `uv sync --locked`, lint, format, mypy, functional tests, `uv build`,
   `uv run twine check dist/*`. Install the wheel in a clean environment and test
   the actual stdio CLI, tools, resource and prompts. Run the opt-in live recipe
   against a dedicated synthetic test domain; verify feedback and revoke test keys.
5. Merge only after the PR CI is green. A maintainer triggers the publication
   workflow with `publish-zelinqa-mcp` after reviewing the package version and files.
6. Verify installation from PyPI (`uvx zelinqa-mcp --version`) and a real stdio
   conversation. Publish/update host examples and public documentation afterwards.

No tokens belong in source, command output or release evidence. Store live-test keys
in protected secret settings. Do not publish a placeholder merely to reserve a name.

The skill lives at `skills/zelinqa` and is included in the source distribution.
It can be distributed from the same repository; it does not require publishing a
second Python package. HTTP hosting is not part of this release.
