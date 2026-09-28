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

## Official MCP Registry

PyPI distributes the executable package. The [MCP Registry](https://registry.modelcontextprotocol.io)
lists metadata pointing to that package; it does not host another copy of the server.

Before building a release, keep the versions in `pyproject.toml` and `server.json`
aligned. Preserve the README ownership marker
`<!-- mcp-name: io.github.Zelinqa/zelinqa-mcp -->`: the registry checks it in the
published PyPI description. The manifest advertises only local stdio transport and
requires a host-supplied secret API key; it must not contain credentials.

After verifying the package on PyPI, run the `Publish Zelinqa MCP to the MCP
Registry` workflow from `main` with confirmation `publish-zelinqa-mcp-registry`.
The `mcp-registry` GitHub environment must first be restricted to `main` and
require a maintainer's approval. Do not run the workflow with an unprotected or
automatically created environment: the registry grants organization-wide publish
permission, not permission limited to this server.

The workflow checks the published PyPI release and ownership marker, then uses
GitHub Actions OIDC to authenticate as the repository owner. No permanent token
or interactive device authorization is needed. It downloads a version-pinned
publisher and verifies its SHA-256 checksum before use. Verify the registered
name and version through the registry API after publication.

See the official [quickstart](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
and [PyPI verification requirements](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx).
