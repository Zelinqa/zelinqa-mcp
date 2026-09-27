# Security policy

## Supported versions

Security fixes are provided for the latest released version of `nbq-mcp`.

## Reporting a vulnerability

Report suspected vulnerabilities privately to `support@zelinqa.ai`. Do not open a public
GitHub issue, and do not include API keys, conversation content or other customer data in
the report.

We acknowledge the report, investigate it, and coordinate disclosure with the reporter.

## What this server does with your data

- The NBQ API key is read once from the `NBQ_API_KEY` environment variable of the server
  process. It is never written to a log, a tool result, an error message or a stack trace,
  and any configured key found in an outgoing string is replaced by `[redacted]`.
- The server is a protocol adapter. It calls the official `nbq` Python SDK, which calls the
  public REST API at `https://api.zelinqa.ai`. It never opens a database connection, never
  imports the NBQ engine, and exposes no selection score or semantic evidence.
- On the stdio transport, stdout is the MCP channel. Every log record goes to stderr, and
  the server logs no request body and no conversation content.
- Session identifiers, question texts and answers pass through the tool results, because
  that is the point of the protocol. Treat an MCP host's transcript with the same care as
  the conversation itself.

## Key hygiene

- Use a key that carries the `runtime` scope only. The six tools need nothing else, and a
  management key in an MCP host is an unnecessary blast radius.
- Never commit a key. `.env*` and `*.local` are ignored, and the example host
  configurations in `examples/` contain placeholders only.
- Rotate a key from NBQ Studio as soon as it may have been exposed; a revoked key is
  refused by the gateway on the next call.
