"""Command line entry point for the NBQ MCP server.

Logging goes to stderr only: on the stdio transport, stdout is the MCP channel
and a stray print would corrupt the protocol. No request body, no conversation
content and no API key is ever logged.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from mcp.server.mcpserver import MCPServer

from . import __version__
from .server import api_key_is_configured, build_server

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
TRANSPORTS = ("stdio", "streamable-http")
EXIT_MISSING_API_KEY = 2

MISSING_KEY_MESSAGE = (
    "nbq-mcp: NBQ_API_KEY is not set.\n"
    "Set it to an NBQ API key carrying the `runtime` scope, for example in the "
    "`env` block of your MCP host configuration. The server refuses to start "
    "without it."
)

_logger = logging.getLogger("nbq_mcp")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbq-mcp",
        description=(
            "MCP server for the Zelinqa NBQ API. Reads NBQ_API_KEY (required), "
            "NBQ_BASE_URL, NBQ_TIMEOUT_SECONDS and NBQ_MAX_RETRIES from the environment."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default="stdio",
        help="MCP transport to serve (default: stdio).",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address for --transport streamable-http (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for --transport streamable-http (default: 8000).",
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default="WARNING",
        help="Log level, written to stderr (default: WARNING).",
    )
    parser.add_argument("--version", action="version", version=f"nbq-mcp {__version__}")
    return parser


def configure_logging(level: str) -> None:
    """Send every log record to stderr, before the MCP server configures anything."""

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)


def run_server(server: MCPServer[None], transport: str, *, host: str, port: int) -> None:
    """Run the server. Separated so tests can drive `main` without serving.

    `host` and `port` are transport options in the MCP SDK, and only the
    streamable-http transport accepts them; stdio would silently ignore them.
    """

    if transport == "streamable-http":
        server.run(transport="streamable-http", host=host, port=port)
    else:
        server.run(transport="stdio")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)

    if not api_key_is_configured():
        print(MISSING_KEY_MESSAGE, file=sys.stderr)
        return EXIT_MISSING_API_KEY

    server = build_server(log_level=args.log_level)
    _logger.info("nbq-mcp %s serving on transport %s", __version__, args.transport)
    run_server(server, args.transport, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
