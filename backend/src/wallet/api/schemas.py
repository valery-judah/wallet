from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from wallet.domain.accounts import Account, AccountStatus, AccountType
from wallet.domain.money import Money

if TYPE_CHECKING:
    from wallet.application.spending_categories import SpendingCategoryTreeNode

NonBlankStr = Annotated[str, StringConstraints(min_length=1)]


class ApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class HealthResponse(ApiModel):
    status: str
    app_name: str
    environment: str


class MoneyRequest(ApiModel):
    amount_minor: Annotated[int, Field(gt=0)]
    currency: NonBlankStr


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
    type: AccountType = AccountType.CARD
    currency: NonBlankStr = "ARS"
    current_balance_minor: Annotated[int, Field(ge=0)] = 0
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
    status: AccountStatus
    color_key: str | None = None
    opened_on: date
    closed_on: date | None = None
    created_on: date
    updated_on: date

    @classmethod
    def from_domain(cls, account: Account) -> AccountResponse:
        return cls(
            id=account.id,
            name=account.name,
            type=account.type,
            currency=account.currency,
            current_balance=MoneyResponse.from_domain(account.current_balance),
            status=account.status,
            color_key=account.color_key,
            opened_on=account.opened_on,
            closed_on=account.closed_on,
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


SpendingCategoryResponse.model_rebuild()
