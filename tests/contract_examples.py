"""Response payloads copied from the V1 contract examples.

Source: `openapi/nbq-v1.openapi.yaml` in nbq-engine, `components/examples`
(`SessionNeuve`, `DecisionNormale`, `DecisionApresMaxTurns`, `ArretSansQuestion`)
and the `202` example of `POST /v1/sessions/{session_id}/feedback`.

The fake client validates them through the SDK response models, so a divergence
between these fixtures and the models fails the suite instead of passing
silently.
"""

from __future__ import annotations

from typing import Any

SESSION_NEUVE: dict[str, Any] = {
    "request_id": "req_1001",
    "session_id": "ses_01J8Z",
    "client_reference": "crm-lead-8842",
    "status": "active",
    "turn_count": 0,
    "max_turns": 10,
    "turns_remaining": 10,
    "question_state": {"outcomes": []},
    "targets": {},
    "progress": {
        "objective": {
            "computed_status": "not_started",
            "progress": 0,
            "client_override": None,
            "effective_status": "not_started",
        },
        "sub_objectives": [
            {
                "id": "so_besoin",
                "order_position": 0,
                "completion_role": "blocking",
                "computed_status": "not_started",
                "progress": 0,
                "client_override": None,
                "effective_status": "not_started",
            },
            {
                "id": "so_budget",
                "order_position": 1,
                "completion_role": "blocking",
                "computed_status": "not_started",
                "progress": 0,
                "client_override": None,
                "effective_status": "not_started",
            },
            {
                "id": "so_livraison",
                "order_position": 2,
                "completion_role": "contributing",
                "computed_status": "not_started",
                "progress": 0,
                "client_override": None,
                "effective_status": "not_started",
            },
        ],
    },
    "pending_decision": None,
    "degraded": False,
    "versions": {"state_version": 0, "engine_version": "1.0.0", "api_version": "1.0"},
}

DECISION_NORMALE: dict[str, Any] = {
    "request_id": "req_1002",
    "session_id": "ses_01J8Z",
    "decision_id": "dec_7f2a",
    "action": "ask",
    "stop_reason": None,
    "candidates": [
        {
            "rank": 1,
            "question_id": "q_budget",
            "text": "Quel budget souhaitez-vous consacrer au canapé ?",
            "type": "open",
            "choices": [],
            "target_ids": ["annual_budget"],
        },
        {
            "rank": 2,
            "question_id": "q_delai",
            "text": "À quelle période souhaitez-vous être livré ?",
            "type": "single_choice",
            "choices": [
                {"choice_id": "choice_1m", "label": "Dans le mois"},
                {"choice_id": "choice_3m", "label": "Dans les trois mois"},
                {"choice_id": "choice_later", "label": "Plus tard"},
            ],
            "target_ids": ["delivery_window"],
        },
    ],
    "progress": {
        "objective": {
            "computed_status": "in_progress",
            "progress": 0.34,
            "client_override": None,
            "effective_status": "in_progress",
        },
        "sub_objectives": [
            {
                "id": "so_besoin",
                "order_position": 0,
                "completion_role": "blocking",
                "computed_status": "covered",
                "progress": 1,
                "client_override": None,
                "effective_status": "covered",
            },
            {
                "id": "so_budget",
                "order_position": 1,
                "completion_role": "blocking",
                "computed_status": "in_progress",
                "progress": 0.15,
                "client_override": None,
                "effective_status": "in_progress",
            },
            {
                "id": "so_livraison",
                "order_position": 2,
                "completion_role": "contributing",
                "computed_status": "not_started",
                "progress": 0,
                "client_override": None,
                "effective_status": "not_started",
            },
        ],
    },
    "turn_count": 2,
    "turns_remaining": 8,
    "warnings": [],
    "degraded": False,
    "degraded_reasons": [],
    "versions": {"state_version": 4, "engine_version": "1.0.0", "api_version": "1.0"},
}

DECISION_APRES_MAX_TURNS: dict[str, Any] = {
    "request_id": "req_1003",
    "session_id": "ses_01J8Z",
    "decision_id": "dec_8c11",
    "action": "ask",
    "stop_reason": None,
    "candidates": [
        {
            "rank": 1,
            "question_id": "q_delai",
            "text": "À quelle période souhaitez-vous être livré ?",
            "type": "single_choice",
            "choices": [
                {"choice_id": "choice_1m", "label": "Dans le mois"},
                {"choice_id": "choice_3m", "label": "Dans les trois mois"},
                {"choice_id": "choice_later", "label": "Plus tard"},
            ],
            "target_ids": ["delivery_window"],
        }
    ],
    "progress": {
        "objective": {
            "computed_status": "in_progress",
            "progress": 0.86,
            "client_override": None,
            "effective_status": "in_progress",
        },
        "sub_objectives": [
            {
                "id": "so_besoin",
                "order_position": 0,
                "completion_role": "blocking",
                "computed_status": "covered",
                "progress": 1,
                "client_override": None,
                "effective_status": "covered",
            },
            {
                "id": "so_budget",
                "order_position": 1,
                "completion_role": "blocking",
                "computed_status": "covered",
                "progress": 1,
                "client_override": None,
                "effective_status": "covered",
            },
            {
                "id": "so_livraison",
                "order_position": 2,
                "completion_role": "contributing",
                "computed_status": "in_progress",
                "progress": 0.4,
                "client_override": None,
                "effective_status": "in_progress",
            },
        ],
    },
    "turn_count": 10,
    "turns_remaining": 0,
    "warnings": ["max_turns_reached"],
    "degraded": True,
    "degraded_reasons": ["missing_user_text"],
    "versions": {"state_version": 21, "engine_version": "1.0.0", "api_version": "1.0"},
}

ARRET_SANS_QUESTION: dict[str, Any] = {
    "request_id": "req_1004",
    "session_id": "ses_01J8Z",
    "decision_id": None,
    "action": "stop",
    "stop_reason": "no_question_available",
    "candidates": [],
    "progress": {
        "objective": {
            "computed_status": "covered",
            "progress": 1,
            "client_override": None,
            "effective_status": "covered",
        },
        "sub_objectives": [
            {
                "id": "so_besoin",
                "order_position": 0,
                "completion_role": "blocking",
                "computed_status": "covered",
                "progress": 1,
                "client_override": None,
                "effective_status": "covered",
            },
            {
                "id": "so_budget",
                "order_position": 1,
                "completion_role": "blocking",
                "computed_status": "covered",
                "progress": 1,
                "client_override": None,
                "effective_status": "covered",
            },
            {
                "id": "so_livraison",
                "order_position": 2,
                "completion_role": "contributing",
                "computed_status": "not_started",
                "progress": 0,
                "client_override": {
                    "status": "excluded",
                    "updated_at": "2026-09-01T09:31:00Z",
                },
                "effective_status": "excluded",
            },
        ],
    },
    "turn_count": 12,
    "turns_remaining": 0,
    "warnings": ["objective_achieved", "max_turns_reached"],
    "degraded": False,
    "degraded_reasons": [],
    "versions": {"state_version": 25, "engine_version": "1.0.0", "api_version": "1.0"},
}

FEEDBACK_ENREGISTRE: dict[str, Any] = {
    "request_id": "req_5f31",
    "session_id": "ses_01J8Z",
    "feedback_id": "fbk_02K1",
    "recorded_at": "2026-09-01T09:14:22Z",
}


def session_state(**overrides: Any) -> dict[str, Any]:
    """A copy of `SessionNeuve` with contract fields overridden."""

    payload = {**SESSION_NEUVE, **overrides}
    return payload
