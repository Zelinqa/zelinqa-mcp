<p align="center">
  <a href="https://zelinqa.ai">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/hero-dark.svg">
      <img src="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/hero-light.svg" alt="Zelinqa MCP" width="100%">
    </picture>
  </a>
</p>

<!-- mcp-name: io.github.Zelinqa/zelinqa-mcp -->

<p align="center">
  <a href="https://pypi.org/project/zelinqa-mcp/"><img src="https://img.shields.io/pypi/v/zelinqa-mcp?label=PyPI&color=6B5BD6" alt="PyPI version"></a>
  <a href="https://github.com/Zelinqa/zelinqa-mcp/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Zelinqa/zelinqa-mcp/ci.yml?branch=main&label=CI" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/MCP%20registry-io.github.Zelinqa%2Fzelinqa--mcp-2ABB9F" alt="MCP registry name">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="License Apache-2.0"></a>
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#a-conversation-in-four-tool-calls">Example</a> ·
  <a href="#tools">Tools</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="docs/operations.md">Operations</a> ·
  <a href="README.fr.md">Français</a>
</p>

---

**Your assistant handles the conversation. Zelinqa decides what to ask next.** Describe once, in [Zelinqa Studio](https://client.zelinqa.ai), what a conversation must find out. This server gives any MCP host the tools to run that conversation: start it, pass each reply, get the next question, record the result. The model only ever sees question text, choice labels and a conversation name. Session, decision and state identifiers stay inside the server.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/flow-dark.svg">
  <img src="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/flow-light.svg" alt="An MCP host calls the zelinqa-mcp server over stdio; the server calls the Zelinqa API with the Python SDK and returns question text, choice labels and progress." width="100%">
</picture>

## Fewer tokens, deterministic, explainable

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/stats-dark.svg">
  <img src="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/stats-light.svg" alt="70 percent fewer tokens, measured on 700+ conversations; deterministic: the same state returns the same question and choosing never calls a model; explainable: every question says what it collects and progress is reported per dimension." width="100%">
</picture>

The engine chooses the questions, so the model stops generating them and stops re-asking: fewer tokens for the same dialogue. The choice itself is a selection over your published domain, not a generation: the same state always yields the same question, and each decision carries what the question collects, the progress of every dimension and an explicit stop reason, so a conversation can be audited after the fact. Token figures: internal test bench, September 2026: more than 700 conversations replayed twice with the same assistant, alone then steered by the Zelinqa engine, with simulated respondents replayed identically on both sides. Protocol, figures and limits: [read the test bench report](https://zelinqa.ai/en/blog/banc-essai-moteur-zelinqa). A scientific benchmark with shared data and code is planned before the end of 2026.

## Why

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/why-dark.svg">
  <img src="https://raw.githubusercontent.com/Zelinqa/zelinqa-mcp/main/assets/readme/why-light.svg" alt="Without Zelinqa, the model generates every question and decides with gaps. With Zelinqa, the engine runs the questioning phase from the published domain and the model decides once, with a complete typed state." width="100%">
</picture>

Any assistant that has to ask before it decides, for an interview, a qualification, an orientation, a triage or a recommendation, improvises its questions and decides with gaps. With this server, the engine runs the questioning phase from your published domain and the model decides once, with a complete, typed state.

## Install

You need Python 3.11+ with [uv](https://docs.astral.sh/uv/), and a **runtime API key** for a published domain, created in Zelinqa Studio. A free [Developer edition](https://zelinqa.ai/en/pricing) account is enough.

<p>
  <a href="https://cursor.com/en/install-mcp?name=zelinqa&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJ6ZWxpbnFhLW1jcCJdLCJlbnYiOnsiWkVMSU5RQV9BUElfS0VZIjoiWU9VUl9SVU5USU1FX0FQSV9LRVkifX0%3D"><img src="https://cursor.com/deeplink/mcp-install-dark.svg" alt="Install in Cursor" height="32"></a>
  &nbsp;
  <a href="https://insiders.vscode.dev/redirect/mcp/install?name=zelinqa&config=%7B%22name%22%3A%22zelinqa%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22zelinqa-mcp%22%5D%2C%22env%22%3A%7B%22ZELINQA_API_KEY%22%3A%22%24%7Binput%3Azelinqa_key%7D%22%7D%7D&inputs=%5B%7B%22type%22%3A%22promptString%22%2C%22id%22%3A%22zelinqa_key%22%2C%22description%22%3A%22Zelinqa%20runtime%20API%20key%22%2C%22password%22%3Atrue%7D%5D"><img src="https://img.shields.io/badge/VS_Code-Install_Server-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white" alt="Install in VS Code" height="32"></a>
</p>

Or add the server to your host by hand. The command is the same everywhere: `uvx zelinqa-mcp`, with the key in the host's secret environment.

<table>
<tr>
<th align="left">Claude Code</th>
<th align="left">Claude Desktop · Cursor · Windsurf</th>
</tr>
<tr>
<td valign="top">

```bash
claude mcp add zelinqa \
  -e ZELINQA_API_KEY=YOUR_RUNTIME_API_KEY \
  -- uvx zelinqa-mcp
```

</td>
<td valign="top">

```json
{
  "mcpServers": {
    "zelinqa": {
      "command": "uvx",
      "args": ["zelinqa-mcp"],
      "env": {
        "ZELINQA_API_KEY": "YOUR_RUNTIME_API_KEY"
      }
    }
  }
}
```

</td>
</tr>
<tr>
<th align="left">Codex (<code>~/.codex/config.toml</code>)</th>
<th align="left">From a checkout</th>
</tr>
<tr>
<td valign="top">

```toml
[mcp_servers.zelinqa]
command = "uvx"
args = ["zelinqa-mcp"]
env = { ZELINQA_API_KEY = "YOUR_RUNTIME_API_KEY" }
```

</td>
<td valign="top">

```bash
git clone https://github.com/Zelinqa/zelinqa-mcp.git
cd zelinqa-mcp
uv sync --group dev --locked
uv run zelinqa-mcp --version
```

</td>
</tr>
</table>

Ready-to-copy files for each host are in [`examples/`](examples). Keep your host's tool-approval policy: some calls create sessions and feedback.

## A conversation in four tool calls

The model calls `zelinqa_start`, asks the returned question in its own words, passes the person's reply to `zelinqa_next_question`, and repeats until the engine stops. At the end it records what really happened.

```text
▶ zelinqa_start           {"conversation": "lead-42"}
◀ ask  ·  "Which budget range are you considering this year?"
          choices: Under €10k · €10k to €50k · Over €50k

▶ zelinqa_next_question   {"conversation": "lead-42", "choice_labels": ["€10k to €50k"]}
◀ ask  ·  "When would you like to start?"
          progress: budget covered · timeline not started

▶ zelinqa_next_question   {"conversation": "lead-42", "user_text": "Next quarter, after the sales kickoff."}
◀ stop ·  objective achieved

▶ zelinqa_feedback        {"conversation": "lead-42", "result": "success"}
```

Calling `zelinqa_next_question` without a reply only redisplays the pending question. When a CRM already knows an answer, `zelinqa_adjust` records it without asking. The full answering rules are in [docs/operations.md](docs/operations.md).

## Tools

| Tool | What it does |
|---|---|
| `zelinqa_start` | Start or recover a named conversation and return its first or pending question |
| `zelinqa_next_question` | Record the person's reply and return the next question; without a reply, redisplay the pending question without a new turn |
| `zelinqa_add_context` | Add a context summary without asking a question |
| `zelinqa_adjust` | Apply confirmed data, dimension statuses or an objective override without consuming a turn |
| `zelinqa_status` | Refresh progress and the pending question |
| `zelinqa_feedback` | Record an observed business result: success, partial or failure |
| `zelinqa_forget` | Free the local handle; does **not** delete API data |

Results carry question text, ranks, choice labels, objective progress and counters; next-decision results add warnings, the stop reason and degraded-mode reasons. At `max_turns` the result has `action: "stop"` and `stop_reason: "max_turns_reached"`, and later calls return the same stop. Reaching the turn limit is not proof that the objective was achieved.

| Also available | Purpose |
|---|---|
| Resource `zelinqa://guide` | The same guide supplied as the server's instructions |
| Prompt `zelinqa_integration_check` | User-selected integration test checklist |
| [Skill `zelinqa`](skills/zelinqa/SKILL.md) | Short workflow for hosts that support skills; copy the directory into your host's skills folder |

`zelinqa-mcp --advanced` swaps the business tools for six low-level ones that expose API identifiers and full state. See [docs/operations.md](docs/operations.md#advanced-mode).

## Configuration

| Environment variable | Purpose |
|---|---|
| `ZELINQA_API_KEY` | Required runtime key, scoped to one published domain |
| `ZELINQA_BASE_URL` | Default `https://api.zelinqa.ai` |
| `ZELINQA_TIMEOUT_SECONDS` | Per-attempt timeout, default 30 seconds |
| `ZELINQA_MAX_RETRIES` | Retry count, default 2 |
| `ZELINQA_SESSION_ID` | Optional host-owned session to resume after restart |
| `ZELINQA_CONVERSATION` | Local name of that resumed session; default `conversation` |

## Security and state

- Transport is **stdio**, one isolated process per trusted host and user. HTTP hosting is disabled until authentication and session isolation exist. Logs go to stderr; stdout is reserved for MCP.
- The server holds at most 128 named conversations in memory and never evicts one silently. Names are process-local: to survive a restart, the host keeps the API session id and injects the resume variables above, outside the model.
- Calls that mutate the same conversation must be sequential; a simultaneous call is rejected rather than answered with stale state. After a conflict, call `zelinqa_status` and reconcile before answering again.

Details, retry semantics and the test suites: [docs/operations.md](docs/operations.md). Vulnerability reports: [SECURITY.md](SECURITY.md).

## Related

- [**zelinqa-sdk**](https://github.com/Zelinqa/zelinqa-sdk): the Python and TypeScript clients this server is built on, for applications that call the API directly.
- [**docs.zelinqa.ai**](https://docs.zelinqa.ai): concepts, Studio guide and API reference.

## License

Apache-2.0. Release steps are in [RELEASING.md](RELEASING.md).
