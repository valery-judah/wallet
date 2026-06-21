from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ._validation import normalize_currency, normalize_nonblank


class AccountNotFoundError(LookupError):
    pass


class AccountClosedError(ValueError):
    pass


class AccountType(StrEnum):
    CASH = "cash"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    WALLET = "wallet"
    SYSTEM = "system"


@dataclass(slots=True)
class Account:
    id: str
    name: str
    type: AccountType
    currency: str
    color_key: str | None
    opened_on: date
    archived_at: date | None
    created_on: date
    updated_on: date
    is_system: bool = False

    def __post_init__(self) -> None:
        self.id = normalize_nonblank(self.id, field_name="account id")
        self.name = normalize_nonblank(self.name, field_name="account name")
        self.type = AccountType(self.type)
        self.currency = normalize_currency(
            self.currency,
            field_name="account currency",
        )
        self.color_key = _normalize_optional_token(
            self.color_key,
            field_name="account color key",
        )
        if self.is_system and self.type is not AccountType.SYSTEM:
            raise ValueError("system account type must be system")
        if not self.is_system and self.type is AccountType.SYSTEM:
            raise ValueError("user account type must not be system")

    @classmethod
    def open(
        cls,
        *,
        id: str,
        name: str,
        type: AccountType,
        currency: str,
        color_key: str | None,
        opened_on: date,
        created_on: date,
        is_system: bool = False,
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
            color_key=color_key,
            opened_on=opened_on,
            archived_at=None,
            created_on=created_on,
            updated_on=created_on,
            is_system=is_system,
        )

    def update_profile(
        self,
        *,
        name: str,
        type: AccountType,
        color_key: str | None,
        updated_on: date,
    ) -> None:
        if self.is_system:
            raise ValueError("system account profile cannot be updated")
        if type is AccountType.SYSTEM:
            raise ValueError("account type must not be system")
        self.name = normalize_nonblank(name, field_name="account name")
        self.type = AccountType(type)
        self.color_key = _normalize_optional_token(
            color_key,
            field_name="account color key",
        )
        self.updated_on = updated_on

    def archive(self, *, archived_on: date) -> None:
        if self.archived_at is not None:
            return
        self.archived_at = archived_on
        self.updated_on = archived_on

    def assert_allows_transactions(self) -> None:
        if self.archived_at is not None:
            raise AccountClosedError("account is archived")


def _normalize_optional_token(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)
