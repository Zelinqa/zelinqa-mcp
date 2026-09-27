"""Release-critical behavior required from the pinned Python SDK."""

from __future__ import annotations

import pickle

from zelinqa.errors import ZelinqaAPIError


def test_sdk_errors_survive_serialization() -> None:
    original = ZelinqaAPIError("temporary failure", status_code=503, code="idempotency_contention")

    restored = pickle.loads(pickle.dumps(original))

    assert isinstance(restored, ZelinqaAPIError)
    assert restored.status_code == 503
    assert restored.code == "idempotency_contention"
