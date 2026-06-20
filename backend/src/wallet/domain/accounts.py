from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ._validation import normalize_currency, normalize_nonblank, require_positive
from .money import CurrencyMismatchError, Money


class AccountNotFoundError(LookupError):
    pass


class InsufficientFundsError(ValueError):
    pass


class AccountClosedError(ValueError):
    pass


class AccountType(StrEnum):
    CARD = "card"
    CASH = "cash"
    BANK = "bank"
    WALLET = "wallet"
    PLATFORM = "platform"
    SAVINGS = "savings"
    OTHER = "other"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass(slots=True)
class Account:
    id: str
    name: str
    type: AccountType
    currency: str
    current_balance: Money
    status: AccountStatus
    color_key: str | None
    icon_key: str | None
    opened_on: date
    closed_on: date | None
    created_on: date
    updated_on: date

    def __post_init__(self) -> None:
        self.id = normalize_nonblank(self.id, field_name="account id")
        self.name = normalize_nonblank(self.name, field_name="account name")
        self.type = AccountType(self.type)
        self.currency = normalize_currency(
            self.currency,
            field_name="account currency",
        )
        self.status = AccountStatus(self.status)
        self.color_key = _normalize_optional_token(
            self.color_key,
            field_name="account color key",
        )
        self.icon_key = _normalize_optional_token(
            self.icon_key,
            field_name="account icon key",
        )
        if self.current_balance.currency != self.currency:
            raise CurrencyMismatchError("currency mismatch")
        if self.current_balance.amount_minor < 0:
            raise ValueError("account balance must not be negative")
        if self.status is AccountStatus.ACTIVE and self.closed_on is not None:
            raise ValueError("active account must not have a closed date")
        if self.status is AccountStatus.CLOSED and self.closed_on is None:
            raise ValueError("closed account must have a closed date")

    @classmethod
    def open(
        cls,
        *,
        id: str,
        name: str,
        type: AccountType,
        currency: str,
        current_balance: Money,
        color_key: str | None,
        icon_key: str | None,
        opened_on: date,
        created_on: date,
    ) -> Account:
        normalized_currency = normalize_currency(
            currency,
            field_name="account currency",
        )
        return cls(
            id=id,
            name=name,
            type=type,
            currency=normalized_currency,
            current_balance=current_balance,
            status=AccountStatus.ACTIVE,
            color_key=color_key,
            icon_key=icon_key,
            opened_on=opened_on,
            closed_on=None,
            created_on=created_on,
            updated_on=created_on,
        )

    def credit(self, amount: Money, *, updated_on: date) -> None:
        self._assert_active()
        self._assert_operation_amount(amount)
        self.current_balance = self.current_balance.add(amount)
        self.updated_on = updated_on

    def debit(self, amount: Money, *, updated_on: date) -> None:
        self._assert_active()
        self._assert_operation_amount(amount)
        if amount.amount_minor > self.current_balance.amount_minor:
            raise InsufficientFundsError("insufficient funds")
        self.current_balance = self.current_balance.subtract(amount)
        self.updated_on = updated_on

    def update_profile(
        self,
        *,
        name: str,
        type: AccountType,
        color_key: str | None,
        icon_key: str | None,
        updated_on: date,
    ) -> None:
        self.name = normalize_nonblank(name, field_name="account name")
        self.type = AccountType(type)
        self.color_key = _normalize_optional_token(
            color_key,
            field_name="account color key",
        )
        self.icon_key = _normalize_optional_token(
            icon_key,
            field_name="account icon key",
        )
        self.updated_on = updated_on

    def close(self, *, closed_on: date) -> None:
        if self.status is AccountStatus.CLOSED:
            return
        self.status = AccountStatus.CLOSED
        self.closed_on = closed_on
        self.updated_on = closed_on

    def _assert_operation_amount(self, amount: Money) -> None:
        require_positive(amount.amount_minor, field_name="amount")
        if amount.currency != self.currency:
            raise CurrencyMismatchError("currency mismatch")

    def _assert_active(self) -> None:
        if self.status is AccountStatus.CLOSED:
            raise AccountClosedError("account is closed")


def _normalize_optional_token(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)
