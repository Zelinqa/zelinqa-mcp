# Releasing

Releases are published from `main` by a maintainer, through the GitHub Actions
workflows and trusted publishing (OIDC). No registry token is stored in this
repository.

1. Require the published `zelinqa` SDK version in `pyproject.toml`, refresh
   `uv.lock`, and run lint, types and tests from a clean checkout.
2. Keep the versions in `pyproject.toml` and `server.json` aligned, date the
   entry in `CHANGELOG.md`, and keep the ownership marker
   `<!-- mcp-name: io.github.Zelinqa/zelinqa-mcp -->` in the README.
3. Merge the release pull request once CI is green.
4. Run the `Publish Zelinqa MCP to PyPI` workflow on `main` with the
   confirmation `publish-zelinqa-mcp`, approve the `pypi` environment, then
   verify `uvx zelinqa-mcp --version` and a real stdio conversation.
5. Run the `Publish Zelinqa MCP to the MCP Registry` workflow on `main` with
   the confirmation `publish-zelinqa-mcp-registry`, approve the `mcp-registry`
   environment, then check the listing in the registry.

A published version number is never reused. Security fixes follow
[SECURITY.md](SECURITY.md).
