"""Release-critical behavior required from the pinned Python SDK."""

from __future__ import annotations

import pickle

from zelinqa.errors import ZelinqaAPIError
from zelinqa.models import NextResponse

from .contract_examples import ARRET_SANS_QUESTION, DECISION_APRES_MAX_TURNS


def test_sdk_errors_survive_serialization() -> None:
    original = ZelinqaAPIError("temporary failure", status_code=503, code="idempotency_contention")

    restored = pickle.loads(pickle.dumps(original))

    assert isinstance(restored, ZelinqaAPIError)
    assert restored.status_code == 503
    assert restored.code == "idempotency_contention"


def test_sdk_parses_the_max_turns_stop() -> None:
    decision = NextResponse.model_validate(DECISION_APRES_MAX_TURNS)

    assert decision.action == "stop"
    assert decision.stop_reason == "max_turns_reached"
    assert decision.decision_id is None
    assert decision.candidates == []


def test_sdk_accepts_stop_reasons_and_warnings_from_a_later_release() -> None:
    payload = {
        **ARRET_SANS_QUESTION,
        "stop_reason": "a_future_stop_reason",
        "warnings": ["a_future_warning"],
    }

    decision = NextResponse.model_validate(payload)

    assert decision.stop_reason == "a_future_stop_reason"
    assert decision.warnings == ["a_future_warning"]
