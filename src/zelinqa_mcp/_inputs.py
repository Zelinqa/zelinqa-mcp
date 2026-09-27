"""Typed tool arguments mirroring the V1 request schemas.

Field names are the contract names in snake_case, so a host that read the public
API documentation can call these tools without a translation table.

Two request schemas of the contract are ``oneOf`` unions discriminated by a
literal (``ContextUpdate`` on ``mode``, ``SubObjectiveOverrideUpdate`` and
``DataClientUpdate`` on ``operation``). They are exposed here as one flat object
per family with the discriminator plus the fields of each branch, validated by a
model validator: nested ``oneOf`` schemas are poorly supported by MCP hosts,
while the rejection message stays just as precise. The payload sent to the SDK
is exactly the contract shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MessageRole = Literal["user", "assistant"]
QuestionOutcome = Literal["asked_answered", "asked_no_answer", "refused"]
QuestionType = Literal["open", "single_choice", "multiple_choice", "semi_open"]
FeedbackResult = Literal["success", "partial", "failure"]

ScalarValue = bool | int | float | str
DataValue = ScalarValue | list[ScalarValue]
MetadataValue = str | float | bool | None


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def wire(self) -> dict[str, Any]:
        """Return the contract-shaped JSON body for this object."""

        return self.model_dump(mode="json", exclude_none=True)


class StructuredAnswerInput(_Input):
    """Answer to a choice question. Mapped deterministically, no LLM call."""

    choice_ids: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=50,
            description="choice_id values taken from the candidate's `choices`, never invented.",
        ),
    ]
    free_text: Annotated[
        str | None,
        Field(
            default=None,
            max_length=4000,
            description="Free complement, allowed only for a `semi_open` question.",
        ),
    ] = None


class ConversationMessageInput(_Input):
    """One new message of a context delta, in conversational order."""

    role: MessageRole
    message_id: Annotated[str | None, Field(default=None, max_length=128)] = None
    question_id: Annotated[
        str | None,
        Field(
            default=None,
            max_length=128,
            description=(
                "Required when this message carries a structured_answer, "
                "otherwise the call is rejected with invalid_previous_turn."
            ),
        ),
    ] = None
    text: Annotated[str | None, Field(default=None, max_length=8000)] = None
    structured_answer: StructuredAnswerInput | None = None
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def _require_content(self) -> Self:
        if self.text is None and self.structured_answer is None:
            raise ValueError("a message needs text or structured_answer")
        if self.structured_answer is not None and self.question_id is None:
            raise ValueError("a message carrying structured_answer also needs question_id")
        return self


class PreviousTurnInput(_Input):
    """What the host actually asked and what the user actually answered.

    `decision_id`, `question_id` and `outcome` are optional helpers, never
    identifiers the host should fabricate: when they are absent NBQ resolves the
    candidate that was used from the pending decision, `assistant_text`, the
    structured answer and the context. Reformulating a question is supported.
    """

    decision_id: Annotated[str | None, Field(default=None, max_length=128)] = None
    question_id: Annotated[str | None, Field(default=None, max_length=128)] = None
    outcome: Annotated[
        QuestionOutcome | None,
        Field(
            default=None,
            description=(
                "asked_answered, asked_no_answer or refused. Omit it and NBQ infers it; "
                "a question that was never asked simply has no outcome."
            ),
        ),
    ] = None
    assistant_text: Annotated[
        str | None,
        Field(
            default=None,
            max_length=8000,
            description="The question or message the host really sent, reformulation included.",
        ),
    ] = None
    user_text: Annotated[
        str | None,
        Field(
            default=None,
            max_length=8000,
            description=(
                "The user's verbatim answer. Optional when structured_answer or "
                "client_updates already carry the information: the turn is then "
                "understood in reduced mode and flagged in degraded_reasons."
            ),
        ),
    ] = None
    structured_answer: StructuredAnswerInput | None = None
    message_id: Annotated[str | None, Field(default=None, max_length=128)] = None

    @model_validator(mode="after")
    def _require_one_field(self) -> Self:
        if not self.model_dump(exclude_none=True):
            raise ValueError("previous_turn must carry at least one field")
        return self


class ContextUpdateInput(_Input):
    """Context that appeared since the last NBQ call.

    Either a compact summary (`mode="summary"` with `text`) or the ordered delta
    of new messages (`mode="messages"` with `messages`). Never resend history
    NBQ has already processed.
    """

    mode: Literal["summary", "messages"]
    text: Annotated[
        str | None,
        Field(default=None, max_length=16000, description="Required when mode is summary."),
    ] = None
    messages: Annotated[
        list[ConversationMessageInput] | None,
        Field(
            default=None,
            max_length=100,
            description="Required when mode is messages. New messages only, in order.",
        ),
    ] = None

    @model_validator(mode="after")
    def _check_branch(self) -> Self:
        if self.mode == "summary":
            if not self.text:
                raise ValueError('context_update with mode="summary" needs text')
            if self.messages is not None:
                raise ValueError('context_update with mode="summary" must not carry messages')
        else:
            if not self.messages:
                raise ValueError('context_update with mode="messages" needs messages')
            if self.text is not None:
                raise ValueError('context_update with mode="messages" must not carry text')
        return self


class DataUpdateInput(_Input):
    """An explicit value the calling system already knows.

    `set` stores a confirmed value with the highest evidence priority, `unset`
    removes the current value, `not_applicable` satisfies a success information
    without giving it a value.
    """

    id: Annotated[str, Field(max_length=128, description="Success information id.")]
    operation: Literal["set", "unset", "not_applicable"] = "set"
    value: Annotated[
        DataValue | None,
        Field(
            default=None,
            description=(
                "Required for set, forbidden otherwise. A string, number, boolean, "
                "or a list of those; never an object."
            ),
        ),
    ] = None

    @model_validator(mode="after")
    def _check_branch(self) -> Self:
        if self.operation == "set" and self.value is None:
            raise ValueError('a data update with operation="set" needs a value')
        if self.operation != "set" and self.value is not None:
            raise ValueError(f'a data update with operation="{self.operation}" takes no value')
        return self


class SubObjectiveUpdateInput(_Input):
    """Client control over one sub-objective."""

    id: Annotated[str, Field(max_length=128)]
    operation: Annotated[
        Literal["set", "exclude", "clear"],
        Field(
            description=(
                "set applies `status`; exclude removes the sub-objective from selection "
                "and from the objective's denominators; clear drops the override."
            )
        ),
    ]
    status: Annotated[
        Literal["achieved", "not_achieved"] | None,
        Field(default=None, description='Required for operation="set".'),
    ] = None

    @model_validator(mode="after")
    def _check_branch(self) -> Self:
        if self.operation == "set" and self.status is None:
            raise ValueError('a sub-objective update with operation="set" needs a status')
        if self.operation != "set" and self.status is not None:
            raise ValueError(
                f'a sub-objective update with operation="{self.operation}" takes no status'
            )
        return self


class ObjectiveUpdateInput(_Input):
    """Client control over the objective itself."""

    operation: Literal["set", "clear"]
    status: Annotated[
        Literal["achieved", "not_achieved"] | None,
        Field(default=None, description='Required for operation="set".'),
    ] = None

    @model_validator(mode="after")
    def _check_branch(self) -> Self:
        if self.operation == "set" and self.status is None:
            raise ValueError('an objective update with operation="set" needs a status')
        if self.operation == "clear" and self.status is not None:
            raise ValueError('an objective update with operation="clear" takes no status')
        return self


class ClientUpdatesInput(_Input):
    """Explicit updates from the calling system. They win over inference."""

    data: Annotated[list[DataUpdateInput] | None, Field(default=None, max_length=100)] = None
    sub_objectives: Annotated[
        list[SubObjectiveUpdateInput] | None, Field(default=None, max_length=100)
    ] = None
    objective: ObjectiveUpdateInput | None = None

    @model_validator(mode="after")
    def _require_one_field(self) -> Self:
        if self.data is None and self.sub_objectives is None and self.objective is None:
            raise ValueError("client_updates must carry data, sub_objectives or objective")
        return self


class SubObjectiveSelectionInput(_Input):
    """Restrict or prefer some sub-objectives for this call only."""

    ids: Annotated[list[str], Field(min_length=1, max_length=100)]
    mode: Annotated[
        Literal["restrict", "prefer"],
        Field(
            description=(
                "restrict strictly forbids questions outside these sub-objectives; "
                "prefer favours them but allows a fallback, reported as "
                "constraints_relaxed in warnings."
            )
        ),
    ]


class SelectionInput(_Input):
    """Constraints valid for this call only, applied before the ranking."""

    candidate_count: Annotated[
        int | None,
        Field(default=None, ge=1, le=10, description="Overrides the configured number."),
    ] = None
    sub_objectives: SubObjectiveSelectionInput | None = None
    allowed_question_types: Annotated[
        list[QuestionType] | None, Field(default=None, min_length=1)
    ] = None
    required_target_ids: Annotated[
        list[str] | None,
        Field(
            default=None,
            min_length=1,
            max_length=100,
            description="Only accept questions covering at least one of these targets.",
        ),
    ] = None
    excluded_question_ids: Annotated[list[str] | None, Field(default=None, max_length=500)] = None


class InitialHistoryItemInput(_Input):
    """One message of a conversation that started outside NBQ.

    Consumed once in memory to build the initial state: never persisted, never
    returned.
    """

    role: MessageRole
    message_id: Annotated[str | None, Field(default=None, max_length=128)] = None
    question_id: Annotated[
        str | None,
        Field(default=None, max_length=128, description="Only if it maps to a known question."),
    ] = None
    text: Annotated[str | None, Field(default=None, max_length=8000)] = None
    structured_answer: StructuredAnswerInput | None = None
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def _require_content(self) -> Self:
        if self.text is None and self.structured_answer is None:
            raise ValueError("an initial history item needs text or structured_answer")
        return self
