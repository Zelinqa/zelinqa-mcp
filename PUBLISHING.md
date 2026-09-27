# Publishing `nbq-mcp`

The package is **not published yet**. It cannot be released before `nbq` 1.0.0 is on PyPI:
`pyproject.toml` currently resolves the SDK from `Zelinqa/nbq-sdk` at a pinned commit
through `[tool.uv.sources]`, and a published wheel must depend on a published `nbq`.
`uv lock` cannot resolve `nbq>=1.0.0` from PyPI while only 0.9.0 exists there, so the
switch below is deliberately the first step *after* the SDK release, not before.

Once a registry version exists it is immutable and must never be reused.

## Before the first release

1. Publish `nbq` 1.0.0 to PyPI (see `PUBLISHING.md` in `Zelinqa/nbq-sdk`) and wait until
   `https://pypi.org/pypi/nbq/1.0.0/json` answers 200.
2. Switch the dependency to PyPI, on a branch, in one go:

   ```bash
   python3 - <<'EOF'
   import pathlib, re
   p = pathlib.Path("pyproject.toml")
   p.write_text(re.sub(r"\[tool\.uv\.sources\]\n(#[^\n]*\n)*nbq = \{[^\n]*\}\n\n", "", p.read_text()))
   EOF
   uv lock && uv sync --group dev --locked && uv run pytest && uv build && uv run twine check dist/*
   git add pyproject.toml uv.lock && git commit -m "NBQ-240 dépendre de nbq 1.0.0 publié sur PyPI"
   ```

   The resulting `uv.lock` must show `source = { registry = "https://pypi.org/simple" }`
   for `nbq`. The CI and release workflows already run `uv sync --group dev --locked`,
   nothing changes there. This switch was rehearsed on 2026-09-13 against the locally
   built `nbq` 1.0.0 wheel (`uv lock --find-links`): resolution and tests pass.
3. Open the PR, let CI pass, merge.
4. Run the live suite against staging once (`NBQ_LIVE=1`, see `README.md`).

## One-time GitHub setup

In `Zelinqa/nbq-mcp`, create a GitHub Actions environment named `pypi`, add the release maintainer as a
required reviewer, and restrict deployments to the `main` branch.

## PyPI Trusted Publisher

While logged in to PyPI, open **Account settings → Publishing → Add a new pending
publisher** and enter exactly:

| Field | Value |
|---|---|
| PyPI project name | `nbq-mcp` |
| GitHub owner | `Zelinqa` |
| GitHub repository | `nbq-mcp` |
| Workflow name | `publish-pypi.yml` |
| Environment | `pypi` |

A pending publisher does **not** reserve the name. The first successful upload creates the
PyPI project and claims it. No API token is ever created or stored: the release job
authenticates with OIDC and holds `id-token: write` only in the `publish` job, which
downloads the artifact built by the unprivileged job.

## Release

1. Update the version in `pyproject.toml` and `src/nbq_mcp/__init__.py` — both must match.
2. Merge the reviewed release changes into `main`. Only the release maintainer performs this merge.
3. Run **Publish nbq-mcp to PyPI** from `main` with confirmation `publish-nbq-mcp`.
4. Approve the protected `pypi` environment deployment.
5. Verify <https://pypi.org/project/nbq-mcp/>, then check the published artefact in a clean
   environment: `uvx nbq-mcp --version`, and one real tool call through a host.
6. Add at least one additional trusted Zelinqa owner to the PyPI project.
