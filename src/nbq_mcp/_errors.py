"""Translate SDK exceptions into readable MCP tool errors.

Every message is built from the contract error envelope (``code``, ``message``,
``request_id``, ``details``) so that an LLM host can act on it without guessing.
No message ever contains the API key: the payload builder scrubs the configured
keys out of every string it produces.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from nbq.errors import (
    NBQAPIError,
    NBQAuthenticationError,
    NBQConnectionError,
)
from pydantic import ValidationError

from ._payloads import scrub_secrets

_MAX_DETAILS_CHARS = 2000

# The deployed gateway answers 401 for a missing Authorization header and 403
# with no V1 envelope for a key that is invalid, revoked, expired, or lacking the
# scope the authorizer requires for the route. Those cases are indistinguishable
# from outside, so one message covers them and carries the HTTP status.
AUTH_HINT = (
    "the NBQ API key is missing, invalid, revoked, expired, or does not carry the "
    "`runtime` scope (check NBQ_API_KEY)"
)
AUTH_MESSAGE = f"unauthorized: {AUTH_HINT}"
CONFLICT_HINT = "call nbq_get_session then retry"


def auth_message(error: NBQAPIError) -> str:
    """Readable message for an authentication or gateway authorization refusal."""

    status_code = getattr(error, "status_code", None)
    status = f" (HTTP {status_code})" if isinstance(status_code, int) else ""
    request_id = getattr(error, "request_id", None)
    suffix = f" (request_id={request_id})" if request_id else ""
    return f"unauthorized{status}: {AUTH_HINT}{suffix}"


def _compact_details(details: Any) -> str:
    if not isinstance(details, dict) or not details:
        return ""
    try:
        rendered = json.dumps(details, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        rendered = str(details)
    if len(rendered) > _MAX_DETAILS_CHARS:
        rendered = f"{rendered[:_MAX_DETAILS_CHARS]}…(truncated)"
    return scrub_secrets(rendered)


def _envelope_message(error: NBQAPIError) -> str:
    code = getattr(error, "code", None) or str(getattr(error, "status_code", "error"))
    message = getattr(error, "message", None) or str(error)
    request_id = getattr(error, "request_id", None)
    suffix = f" (request_id={request_id})" if request_id else ""
    return scrub_secrets(f"{code}: {message}{suffix}")


def tool_error_for(error: Exception) -> ToolError:
    """Build the ``ToolError`` that describes ``error`` to the host."""

    if isinstance(error, NBQAuthenticationError):
        return ToolError(auth_message(error))

    if isinstance(error, NBQAPIError):
        parts = [_envelope_message(error)]
        details = _compact_details(getattr(error, "details", None))
        if getattr(error, "code", None) == "state_version_conflict":
            parts.append(CONFLICT_HINT)
        if details:
            parts.append(details)
        return ToolError(" — ".join(parts))

    if isinstance(error, NBQConnectionError):
        return ToolError(
            "connection_error: the NBQ API could not be reached after retrying "
            f"({scrub_secrets(str(error)) or type(error).__name__}). "
            "Check network access to https://api.zelinqa.ai and retry."
        )

    if isinstance(error, ValidationError):
        issues = "; ".join(
            f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}"
            for issue in error.errors()[:10]
        )
        return ToolError(f"invalid_request: the arguments do not satisfy the contract — {issues}")

    if isinstance(error, ValueError):
        return ToolError(f"invalid_request: {scrub_secrets(str(error))}")

    return ToolError(scrub_secrets(f"{type(error).__name__}: {error}"))


@contextmanager
def translated_errors() -> Iterator[None]:
    """Re-raise SDK and validation failures as readable tool errors."""

    try:
        yield
    except ToolError:
        raise
    except (NBQAPIError, NBQConnectionError, ValidationError, ValueError) as error:
        raise tool_error_for(error) from error
