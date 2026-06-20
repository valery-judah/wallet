from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from wallet.domain.cards import Card
from wallet.domain.money import Money

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


class CardCreateRequest(ApiModel):
    name: NonBlankStr
    currency: NonBlankStr = "ARS"
    opened_on: date | None = None


class CardResponse(ApiModel):
    id: str
    name: str
    currency: str
    balance: MoneyResponse
    created_on: date

    @classmethod
    def from_domain(cls, card: Card) -> CardResponse:
        return cls(
            id=card.id,
            name=card.name,
            currency=card.currency,
            balance=MoneyResponse.from_domain(card.balance),
            created_on=card.created_on,
        )
