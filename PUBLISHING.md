# Publishing Zelinqa MCP

Farouk approves merges and publication. This branch is a release candidate only.

1. Merge and publish Python **`zelinqa` 1.0.0** first; this is a new PyPI project,
   not a rename of the existing `nbq` distribution.
2. During review, pin `[tool.uv.sources].zelinqa` to the exact SDK Git commit tested.
   Never commit a developer-local path. Before releasing MCP, remove that override,
   regenerate `uv.lock` against PyPI and rerun tests from a clean checkout.
3. Configure a pending Trusted Publisher for **`zelinqa-mcp`** in PyPI with this
   repository's `.github/workflows/publish-pypi.yml` and its configured environment.
   A pending publisher does not reserve the package name.
4. Run `uv sync --locked`, lint, format, mypy, functional tests, `uv build`,
   `uv run twine check dist/*`. Install the wheel in a clean environment and test
   the actual stdio CLI, tools, resource and prompts. Run the opt-in live recipe
   against a dedicated synthetic NBQ; verify feedback and revoke test keys.
5. Merge only after the PR CI is green. Farouk triggers the publication workflow
   with `publish-zelinqa-mcp` after reviewing the package version and files.
6. Verify installation from PyPI (`uvx zelinqa-mcp --version`) and a real stdio
   conversation. Publish/update host examples and public documentation afterwards.

No tokens belong in source, command output or release evidence. Store live-test keys
in protected secret settings. Do not publish a placeholder merely to reserve a name.

The skill lives at `skills/zelinqa` and is included in the source distribution.
It can be distributed from the same repository; it does not require publishing a
second Python package. HTTP hosting is not part of this release.
