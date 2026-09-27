"""Turn SDK return values into plain JSON-serializable dictionaries.

The SDK returns pydantic models. MCP structured output needs plain JSON, and the
contract field names are already the wire names, so the conversion is a dump
with no renaming: nothing is dropped, including ``warnings``, ``degraded`` and
``degraded_reasons``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, cast

_MIN_SECRET_CHARS = 8
_REDACTED = "[redacted]"

#: Environment variables that may hold an API key. Their values are scrubbed out
#: of every string this module produces, so that a server-side echo or a
#: misconfigured integration can never leak a key through a tool result.
_SECRET_ENV_VARS = (
    "NBQ_API_KEY",
    "NBQ_LIVE_RUNTIME_KEY",
    "NBQ_LIVE_CONFIG_READ_KEY",
    "NBQ_LIVE_CONFIG_WRITE_KEY",
    "NBQ_LIVE_CONFIG_PUBLISH_KEY",
    "NBQ_LIVE_REVOKED_KEY",
)


def scrub_secrets(text: str) -> str:
    """Replace any configured API key appearing in ``text``."""

    scrubbed = text
    for name in _SECRET_ENV_VARS:
        secret = os.environ.get(name)
        if secret and len(secret.strip()) >= _MIN_SECRET_CHARS:
            scrubbed = scrubbed.replace(secret.strip(), _REDACTED)
    return scrubbed


def jsonable(value: Any) -> Any:
    """Convert ``value`` to something ``json.dumps`` accepts."""

    dump = getattr(value, "model_dump", None)
    if callable(dump):  # pydantic v2 model
        return jsonable(dump(mode="json"))
    if isinstance(value, Enum):
        return jsonable(value.value)
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return scrub_secrets(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence | set | frozenset):
        return [jsonable(item) for item in value]
    return scrub_secrets(str(value))


def to_payload(value: Any) -> dict[str, Any]:
    """Convert an SDK response model to a JSON-serializable dictionary."""

    payload = jsonable(value)
    if not isinstance(payload, dict):
        raise TypeError(f"expected an object response from the NBQ SDK, got {type(value).__name__}")
    return cast("dict[str, Any]", payload)


def state_version_of(payload: Mapping[str, Any]) -> int | None:
    """Read ``versions.state_version`` from a contract payload."""

    versions = payload.get("versions")
    if not isinstance(versions, Mapping):
        return None
    value = versions.get("state_version")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def with_state_version(payload: dict[str, Any]) -> dict[str, Any]:
    """Mirror ``versions.state_version`` at the top level.

    The nested ``versions`` block is kept as the contract defines it; the mirror
    exists so a host does not have to dig for the value it must send back on the
    next mutation.
    """

    version = state_version_of(payload)
    if version is not None:
        payload["state_version"] = version
    return payload
