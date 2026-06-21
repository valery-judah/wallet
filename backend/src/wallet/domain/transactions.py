from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ._validation import normalize_currency, normalize_nonblank


class TransactionNotFoundError(LookupError):
    pass


class TransactionType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    POSTED = "posted"
    VOID = "void"


@dataclass(frozen=True, slots=True)
class Posting:
    id: str
    transaction_id: str
    account_id: str | None
    category_id: str | None
    amount_minor: int
    currency: str
    memo: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalize_nonblank(self.id, field_name="posting id"),
        )
        object.__setattr__(
            self,
            "transaction_id",
            normalize_nonblank(self.transaction_id, field_name="transaction id"),
        )
        object.__setattr__(
            self,
            "account_id",
            _normalize_optional_token(self.account_id, field_name="account id"),
        )
        object.__setattr__(
            self,
            "category_id",
            _normalize_optional_token(self.category_id, field_name="category id"),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_currency(self.currency, field_name="posting currency"),
        )
        object.__setattr__(
            self,
            "memo",
            _normalize_optional_token(self.memo, field_name="posting memo"),
        )
        if self.amount_minor == 0:
            raise ValueError("posting amount must not be zero")
        if (self.account_id is None) == (self.category_id is None):
            raise ValueError("posting must target exactly one account or category")


@dataclass(frozen=True, slots=True)
class Transaction:
    id: str
    occurred_on: date
    posted_on: date | None
    description: str | None
    merchant_name: str | None
    notes: str | None
    status: TransactionStatus
    type: TransactionType
    postings: tuple[Posting, ...]
    created_on: date
    updated_on: date

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalize_nonblank(self.id, field_name="transaction id"),
        )
        object.__setattr__(self, "status", TransactionStatus(self.status))
        object.__setattr__(self, "type", TransactionType(self.type))
        object.__setattr__(
            self,
            "description",
            _normalize_optional_token(self.description, field_name="transaction description"),
        )
        object.__setattr__(
            self,
            "merchant_name",
            _normalize_optional_token(self.merchant_name, field_name="merchant name"),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_optional_token(self.notes, field_name="transaction notes"),
        )
        if len(self.postings) < 2:
            raise ValueError("transaction must include at least two postings")
        total_minor = sum(posting.amount_minor for posting in self.postings)
        if total_minor != 0:
            raise ValueError("transaction postings must balance to zero")
        currencies = {posting.currency for posting in self.postings}
        if len(currencies) != 1:
            raise ValueError("transaction postings must use one currency")

        account_postings = [posting for posting in self.postings if posting.account_id is not None]
        category_postings = [
            posting for posting in self.postings if posting.category_id is not None
        ]
        if self.type is TransactionType.TRANSFER:
            if category_postings:
                raise ValueError("transfer transactions must use only account postings")
            if len(account_postings) != 2:
                raise ValueError("transfer transactions must use exactly two account postings")
            negative_postings = [
                posting for posting in account_postings if posting.amount_minor < 0
            ]
            positive_postings = [
                posting for posting in account_postings if posting.amount_minor > 0
            ]
            if len(negative_postings) != 1 or len(positive_postings) != 1:
                raise ValueError(
                    "transfer transactions must use one negative and one positive account posting"
                )
        if self.type is TransactionType.EXPENSE:
            if len(account_postings) != 1 or len(category_postings) < 1:
                raise ValueError(
                    "expense transactions must use one account and at least one category posting"
                )
            if any(posting.amount_minor >= 0 for posting in account_postings):
                raise ValueError("expense account postings must be negative")
            if any(posting.amount_minor <= 0 for posting in category_postings):
                raise ValueError("expense category postings must be positive")
        if self.type is TransactionType.INCOME:
            if len(account_postings) != 1 or len(category_postings) != 1:
                raise ValueError(
                    "income transactions must use one account and one category posting"
                )
            if any(posting.amount_minor <= 0 for posting in account_postings):
                raise ValueError("income account postings must be positive")
            if any(posting.amount_minor >= 0 for posting in category_postings):
                raise ValueError("income category postings must be negative")
        if self.type is TransactionType.ADJUSTMENT:
            if category_postings:
                raise ValueError("adjustment transactions must use only account postings")
            if len(account_postings) != 2:
                raise ValueError("adjustment transactions must use two account postings")


def _normalize_optional_token(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)
