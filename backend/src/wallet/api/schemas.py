from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from wallet.ai.capabilities.contract import CapabilityView
from wallet.ai.control.domain import (
    ControlAction,
    ControlActionSubmission,
    ConversationView,
    MessageSubmission,
    PublicCapabilityView,
    TaskActionSubmission,
    TurnOutcome,
    TurnRequest,
    TurnResponse,
)
from wallet.application.accounts import AccountSnapshot
from wallet.domain.accounts import AccountType
from wallet.domain.money import Money
from wallet.domain.transactions import Posting, Transaction, TransactionStatus, TransactionType

if TYPE_CHECKING:
    from wallet.application.income_categories import IncomeCategoryTreeNode
    from wallet.application.spending_categories import SpendingCategoryTreeNode

NonBlankStr = Annotated[str, StringConstraints(min_length=1)]
TurnContent = Annotated[str, StringConstraints(min_length=1, max_length=4_000)]


class ApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class HealthResponse(ApiModel):
    status: str
    app_name: str
    environment: str


class MoneyResponse(ApiModel):
    amount_minor: int
    currency: NonBlankStr

    @classmethod
    def from_domain(cls, money: Money) -> MoneyResponse:
        return cls(
            amount_minor=money.amount_minor,
            currency=money.currency,
        )


class CreateAccountRequest(ApiModel):
    name: NonBlankStr
    type: AccountType = AccountType.DEBIT_CARD
    currency: NonBlankStr = "ARS"
    opening_balance_minor: int = 0
    opened_on: date | None = None
    color_key: str | None = None


class UpdateAccountProfileRequest(ApiModel):
    name: NonBlankStr
    type: AccountType
    color_key: str | None = None


class AccountResponse(ApiModel):
    id: str
    name: str
    type: AccountType
    currency: str
    current_balance: MoneyResponse
    color_key: str | None = None
    opened_on: date
    archived_at: date | None = None
    created_on: date
    updated_on: date

    @classmethod
    def from_snapshot(cls, snapshot: AccountSnapshot) -> AccountResponse:
        account = snapshot.account
        return cls(
            id=account.id,
            name=account.name,
            type=account.type,
            currency=account.currency,
            current_balance=MoneyResponse.from_domain(snapshot.current_balance),
            color_key=account.color_key,
            opened_on=account.opened_on,
            archived_at=account.archived_at,
            created_on=account.created_on,
            updated_on=account.updated_on,
        )


class CreateSpendingCategoryRequest(ApiModel):
    name: NonBlankStr
    parent_id: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0


class UpdateSpendingCategoryRequest(ApiModel):
    name: NonBlankStr | None = None
    parent_id: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None


class SpendingCategoryResponse(ApiModel):
    id: str
    name: str
    parent_id: str | None
    icon: str | None = None
    color: str | None = None
    sort_order: int
    children: list[SpendingCategoryResponse] = Field(default_factory=list)

    @classmethod
    def from_tree_node(cls, node: SpendingCategoryTreeNode) -> SpendingCategoryResponse:
        category = node.category
        return cls(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            icon=category.icon,
            color=category.color,
            sort_order=category.sort_order,
            children=[cls.from_tree_node(child) for child in node.children],
        )


class CreateIncomeCategoryRequest(ApiModel):
    name: NonBlankStr
    parent_id: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0


class UpdateIncomeCategoryRequest(ApiModel):
    name: NonBlankStr | None = None
    parent_id: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None


class IncomeCategoryResponse(ApiModel):
    id: str
    name: str
    parent_id: str | None
    icon: str | None = None
    color: str | None = None
    sort_order: int
    children: list[IncomeCategoryResponse] = Field(default_factory=list)

    @classmethod
    def from_tree_node(cls, node: IncomeCategoryTreeNode) -> IncomeCategoryResponse:
        category = node.category
        return cls(
            id=category.id,
            name=category.name,
            parent_id=category.parent_id,
            icon=category.icon,
            color=category.color,
            sort_order=category.sort_order,
            children=[cls.from_tree_node(child) for child in node.children],
        )


class CreateTransactionPostingRequest(ApiModel):
    account_id: str | None = None
    category_id: str | None = None
    amount_minor: int
    currency: NonBlankStr
    memo: str | None = None


class CreateTransactionRequest(ApiModel):
    type: TransactionType
    postings: list[CreateTransactionPostingRequest] = Field(min_length=1)
    occurred_on: date | None = None
    description: str | None = None
    merchant_name: str | None = None
    notes: str | None = None


class PostingResponse(ApiModel):
    id: str
    account_id: str | None = None
    category_id: str | None = None
    amount_minor: int
    currency: NonBlankStr
    memo: str | None = None

    @classmethod
    def from_domain(cls, posting: Posting) -> PostingResponse:
        return cls(
            id=posting.id,
            account_id=posting.account_id,
            category_id=posting.category_id,
            amount_minor=posting.amount_minor,
            currency=posting.currency,
            memo=posting.memo,
        )


class TransactionResponse(ApiModel):
    id: str
    occurred_on: date
    posted_on: date | None = None
    description: str | None = None
    merchant_name: str | None = None
    notes: str | None = None
    status: TransactionStatus
    type: TransactionType
    postings: list[PostingResponse]
    created_on: date
    updated_on: date

    @classmethod
    def from_domain(cls, transaction: Transaction) -> TransactionResponse:
        return cls(
            id=transaction.id,
            occurred_on=transaction.occurred_on,
            posted_on=transaction.posted_on,
            description=transaction.description,
            merchant_name=transaction.merchant_name,
            notes=transaction.notes,
            status=transaction.status,
            type=transaction.type,
            postings=[PostingResponse.from_domain(posting) for posting in transaction.postings],
            created_on=transaction.created_on,
            updated_on=transaction.updated_on,
        )


RequestId = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
]
EntityId = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"),
]
TaskActionName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$"),
]


class MessageTurnInput(ApiModel):
    kind: Literal["message"]
    content: TurnContent

    def to_domain(self) -> MessageSubmission:
        return MessageSubmission(self.content)


class ControlActionTurnInput(ApiModel):
    kind: Literal["control_action"]
    action: ControlAction
    expected_task_id: EntityId | None = None
    expected_conversation_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_guard(self) -> ControlActionTurnInput:
        if self.action is ControlAction.HELP:
            if (
                "expected_task_id" in self.model_fields_set
                or "expected_conversation_version" in self.model_fields_set
            ):
                raise ValueError("help cannot contain target or version fields")
        elif self.expected_task_id is None or self.expected_conversation_version is None:
            raise ValueError("cancel and restart require target and version fields")
        return self

    def to_domain(self) -> ControlActionSubmission:
        return ControlActionSubmission(
            action=self.action,
            expected_task_id=self.expected_task_id,
            expected_conversation_version=self.expected_conversation_version,
        )


class TaskActionTurnInput(ApiModel):
    kind: Literal["task_action"]
    expected_task_id: EntityId
    expected_conversation_version: int = Field(ge=1)
    action: TaskActionName
    payload: dict[str, object] = Field(default_factory=dict)

    def to_domain(self) -> TaskActionSubmission:
        return TaskActionSubmission(
            expected_task_id=self.expected_task_id,
            expected_conversation_version=self.expected_conversation_version,
            action=self.action,
            payload=self.payload,
        )


TurnInput = Annotated[
    MessageTurnInput | ControlActionTurnInput | TaskActionTurnInput,
    Field(discriminator="kind"),
]


class SubmitTurnRequest(ApiModel):
    request_id: RequestId
    conversation_id: EntityId | None = None
    input: TurnInput

    def to_domain(self) -> TurnRequest:
        return TurnRequest(
            request_id=self.request_id,
            conversation_id=self.conversation_id,
            input=self.input.to_domain(),
        )


class TaskActionOfferResponse(ApiModel):
    action: str
    label: str
    payload: dict[str, object] | None = None
    expected_task_id: str
    expected_conversation_version: int


class TaskViewResponse(ApiModel):
    kind: str
    data: dict[str, object]
    available_actions: list[TaskActionOfferResponse]

    @classmethod
    def from_domain(cls, view: PublicCapabilityView) -> TaskViewResponse:
        return cls(
            kind=view.kind,
            data=view.data,
            available_actions=[
                TaskActionOfferResponse(
                    action=offer.action,
                    label=offer.label,
                    payload=offer.payload,
                    expected_task_id=offer.expected_task_id,
                    expected_conversation_version=offer.expected_conversation_version,
                )
                for offer in view.available_actions
            ],
        )


class ActiveTaskResponse(ApiModel):
    id: str
    version: int
    view: TaskViewResponse


class TurnOutcomeResponse(ApiModel):
    kind: str
    message: str
    view: TaskViewResponse | None = None
    result: dict[str, object] | None = None

    @classmethod
    def from_domain(cls, outcome: TurnOutcome) -> TurnOutcomeResponse:
        if isinstance(outcome.view, CapabilityView):
            raise ValueError("public outcome contains an unbound capability view")
        return cls(
            kind=outcome.kind,
            message=outcome.message,
            view=(None if outcome.view is None else TaskViewResponse.from_domain(outcome.view)),
            result=outcome.result,
        )


class ConversationResponse(ApiModel):
    id: str
    version: int
    active_task: ActiveTaskResponse | None
    last_outcome: TurnOutcomeResponse | None

    @classmethod
    def from_domain(cls, conversation: ConversationView) -> ConversationResponse:
        current = conversation.active_task
        return cls(
            id=conversation.id,
            version=conversation.version,
            active_task=(
                None
                if current is None
                else ActiveTaskResponse(
                    id=current.id,
                    version=current.version,
                    view=TaskViewResponse.from_domain(current.view),
                )
            ),
            last_outcome=(
                None
                if conversation.last_outcome is None
                else TurnOutcomeResponse.from_domain(conversation.last_outcome)
            ),
        )


class SubmitTurnResponse(ApiModel):
    request_id: str
    conversation: ConversationResponse
    outcome: TurnOutcomeResponse

    @classmethod
    def from_domain(cls, response: TurnResponse) -> SubmitTurnResponse:
        return cls(
            request_id=response.request_id,
            conversation=ConversationResponse.from_domain(response.conversation),
            outcome=TurnOutcomeResponse.from_domain(response.outcome),
        )


SpendingCategoryResponse.model_rebuild()
IncomeCategoryResponse.model_rebuild()
