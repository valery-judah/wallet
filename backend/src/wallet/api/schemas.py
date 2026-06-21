from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from wallet.application.accounts import AccountSnapshot
from wallet.domain.accounts import AccountType
from wallet.domain.money import Money
from wallet.domain.transactions import Posting, Transaction, TransactionStatus, TransactionType

if TYPE_CHECKING:
    from wallet.application.income_categories import IncomeCategoryTreeNode
    from wallet.application.spending_categories import SpendingCategoryTreeNode

NonBlankStr = Annotated[str, StringConstraints(min_length=1)]


class ApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


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


SpendingCategoryResponse.model_rebuild()
IncomeCategoryResponse.model_rebuild()
