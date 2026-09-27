"""Official MCP server for the Zelinqa NBQ API.

The server is a thin protocol adapter: every tool call goes through the official
Python SDK ``nbq``, which talks to the public REST API at
``https://api.zelinqa.ai``. No raw HTTP, no database, no engine internals.
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = ["__version__", "build_server"]


def __getattr__(name: str) -> object:
    # Lazy re-export so that `python -c "import nbq_mcp; nbq_mcp.__version__"`
    # never imports the SDK or the MCP runtime.
    if name == "build_server":
        from .server import build_server

        return build_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
