from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ._validation import normalize_currency, normalize_nonblank, require_positive
from .money import CurrencyMismatchError, Money


class CardNotFoundError(LookupError):
    pass


class InsufficientFundsError(ValueError):
    pass


@dataclass(slots=True)
class Card:
    id: str
    name: str
    currency: str
    balance: Money
    created_on: date

    def __post_init__(self) -> None:
        self.id = normalize_nonblank(self.id, field_name="card id")
        self.name = normalize_nonblank(self.name, field_name="card name")
        self.currency = normalize_currency(self.currency, field_name="card currency")
        if self.balance.currency != self.currency:
            raise CurrencyMismatchError("currency mismatch")
        if self.balance.amount_minor < 0:
            raise ValueError("card balance must not be negative")

    @classmethod
    def issue(
        cls,
        *,
        id: str,
        name: str,
        currency: str,
        created_on: date,
    ) -> Card:
        normalized_currency = normalize_currency(currency, field_name="card currency")
        return cls(
            id=id,
            name=name,
            currency=normalized_currency,
            balance=Money.zero(normalized_currency),
            created_on=created_on,
        )

    def deposit(self, amount: Money) -> None:
        self._assert_operation_amount(amount)
        self.balance = self.balance.add(amount)

    def withdraw(self, amount: Money) -> None:
        self._assert_operation_amount(amount)
        if amount.amount_minor > self.balance.amount_minor:
            raise InsufficientFundsError("insufficient funds")
        self.balance = self.balance.subtract(amount)

    def _assert_operation_amount(self, amount: Money) -> None:
        require_positive(amount.amount_minor, field_name="amount")
        if amount.currency != self.currency:
            raise CurrencyMismatchError("currency mismatch")
