from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol, TypeVar

from wallet.ai.transaction_capture.domain import CandidateField, TransactionCandidate
from wallet.ai.transaction_capture.ports import (
    CaptureAccountReference,
    CaptureCategoryReference,
    CaptureReferenceCatalog,
)
from wallet.application.transactions import CreatePosting, CreateTransaction, TransactionService
from wallet.domain.accounts import Account
from wallet.domain.transactions import Transaction, TransactionType
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository

_T = TypeVar("_T")


class _Category(Protocol):
    id: str
    name: str
    parent_id: str | None


class WalletCaptureAdapter:
    """Expose safe wallet reads, validation, and transaction creation to capture."""

    def __init__(
        self,
        *,
        accounts: AccountRepository,
        spending_categories: SpendingCategoryRepository,
        income_categories: IncomeCategoryRepository,
        transactions: TransactionService,
    ) -> None:
        self._accounts = accounts
        self._spending_categories = spending_categories
        self._income_categories = income_categories
        self._transactions = transactions

    def capture_references(self) -> CaptureReferenceCatalog:
        """Return unambiguous references that the capture workflow may select."""

        accounts = _unique_account_references(
            (account.name, account.id, account.currency)
            for account in self._accounts.list()
            if not account.is_system and account.archived_at is None
        )
        return CaptureReferenceCatalog(
            accounts=accounts,
            spending_categories=_category_references(self._spending_categories.list()),
            income_categories=_category_references(self._income_categories.list()),
        )

    def invalid_field(self, candidate: TransactionCandidate) -> CandidateField | None:
        match candidate.type:
            case TransactionType.EXPENSE:
                account = self._available_account(candidate.account_id)
                if account is None or _currency_conflicts(
                    candidate.currency_code, account.currency
                ):
                    return CandidateField.ACCOUNT_ID
                if (
                    candidate.spending_category_id is None
                    or self._spending_categories.get(candidate.spending_category_id) is None
                ):
                    return CandidateField.SPENDING_CATEGORY_ID
            case TransactionType.INCOME:
                account = self._available_account(candidate.account_id)
                if account is None or _currency_conflicts(
                    candidate.currency_code, account.currency
                ):
                    return CandidateField.ACCOUNT_ID
                if (
                    candidate.income_category_id is None
                    or self._income_categories.get(candidate.income_category_id) is None
                ):
                    return CandidateField.INCOME_CATEGORY_ID
            case TransactionType.TRANSFER:
                source = self._available_account(candidate.source_account_id)
                if source is None:
                    return CandidateField.SOURCE_ACCOUNT_ID
                if _currency_conflicts(candidate.currency_code, source.currency):
                    return CandidateField.SOURCE_ACCOUNT_ID
                destination = self._available_account(candidate.destination_account_id)
                if destination is None:
                    return CandidateField.DESTINATION_ACCOUNT_ID
                if source.currency != destination.currency or _currency_conflicts(
                    candidate.currency_code, destination.currency
                ):
                    return CandidateField.DESTINATION_ACCOUNT_ID
            case TransactionType.ADJUSTMENT:
                account = self._available_account(candidate.account_id)
                if account is None or _currency_conflicts(
                    candidate.currency_code, account.currency
                ):
                    return CandidateField.ACCOUNT_ID
            case None:
                return CandidateField.TYPE

        if candidate.occurred_on is None:
            return CandidateField.OCCURRED_ON
        return None

    def execute(
        self,
        candidate: TransactionCandidate,
        *,
        operation_id: str,
    ) -> Transaction:
        occurred_on = _require(candidate.occurred_on, field_name="occurred_on")
        postings: tuple[CreatePosting, ...]
        match candidate.type:
            case TransactionType.EXPENSE:
                amount = _require(candidate.amount_minor, field_name="amount_minor")
                account = self._require_available_account(candidate.account_id)
                category_id = _require(
                    candidate.spending_category_id,
                    field_name="spending_category_id",
                )
                postings = (
                    CreatePosting(
                        account_id=account.id,
                        amount_minor=-amount,
                        currency=account.currency,
                    ),
                    CreatePosting(
                        category_id=category_id,
                        amount_minor=amount,
                        currency=account.currency,
                    ),
                )
            case TransactionType.INCOME:
                amount = _require(candidate.amount_minor, field_name="amount_minor")
                account = self._require_available_account(candidate.account_id)
                category_id = _require(
                    candidate.income_category_id,
                    field_name="income_category_id",
                )
                postings = (
                    CreatePosting(
                        account_id=account.id,
                        amount_minor=amount,
                        currency=account.currency,
                    ),
                    CreatePosting(
                        category_id=category_id,
                        amount_minor=-amount,
                        currency=account.currency,
                    ),
                )
            case TransactionType.TRANSFER:
                amount = _require(candidate.amount_minor, field_name="amount_minor")
                source = self._require_available_account(candidate.source_account_id)
                destination = self._require_available_account(candidate.destination_account_id)
                postings = (
                    CreatePosting(
                        account_id=source.id,
                        amount_minor=-amount,
                        currency=source.currency,
                    ),
                    CreatePosting(
                        account_id=destination.id,
                        amount_minor=amount,
                        currency=destination.currency,
                    ),
                )
            case TransactionType.ADJUSTMENT:
                account = self._require_available_account(candidate.account_id)
                balance_change = _require(
                    candidate.balance_change_minor,
                    field_name="balance_change_minor",
                )
                postings = (
                    CreatePosting(
                        account_id=account.id,
                        amount_minor=balance_change,
                        currency=account.currency,
                    ),
                )
            case None:
                raise ValueError("transaction candidate type is required")

        return self._transactions.create_transaction(
            CreateTransaction(
                type=_require(candidate.type, field_name="type"),
                postings=postings,
                occurred_on=occurred_on,
                description=candidate.description,
                merchant_name=candidate.merchant_name,
                notes=candidate.notes,
            ),
            operation_id=operation_id,
        )

    def _available_account(self, account_id: str | None) -> Account | None:
        if account_id is None:
            return None
        account = self._accounts.get(account_id)
        if account is None or account.is_system or account.archived_at is not None:
            return None
        return account

    def _require_available_account(self, account_id: str | None) -> Account:
        account = self._available_account(account_id)
        if account is None:
            raise ValueError("transaction candidate references an unavailable account")
        return account


def _require(value: _T | None, *, field_name: str) -> _T:
    if value is None:
        raise ValueError(f"transaction candidate {field_name} is required")
    return value


def _category_references(
    categories: Sequence[_Category],
) -> tuple[CaptureCategoryReference, ...]:
    categories_by_id = {category.id: category for category in categories}
    return _unique_references(
        (
            _category_path(category, categories_by_id=categories_by_id),
            category.id,
        )
        for category in categories
    )


def _category_path(
    category: _Category,
    *,
    categories_by_id: dict[str, _Category],
) -> str:
    names = [category.name]
    parent_id = category.parent_id
    visited = {category.id}
    while parent_id is not None and parent_id not in visited:
        visited.add(parent_id)
        parent = categories_by_id.get(parent_id)
        if parent is None:
            break
        names.append(parent.name)
        parent_id = parent.parent_id
    return " > ".join(reversed(names))


def _unique_references(
    entries: Iterable[tuple[str, str]],
) -> tuple[CaptureCategoryReference, ...]:
    grouped: dict[str, list[CaptureCategoryReference]] = {}
    for label, entity_id in entries:
        reference = CaptureCategoryReference(id=entity_id, label=label)
        grouped.setdefault(_normalize_label(label), []).append(reference)
    unique = [matches[0] for matches in grouped.values() if len(matches) == 1]
    return tuple(
        sorted(
            unique,
            key=lambda reference: (_normalize_label(reference.label), reference.id),
        )
    )


def _unique_account_references(
    entries: Iterable[tuple[str, str, str]],
) -> tuple[CaptureAccountReference, ...]:
    grouped: dict[str, list[CaptureAccountReference]] = {}
    for label, entity_id, currency in entries:
        reference = CaptureAccountReference(id=entity_id, label=label, currency=currency)
        grouped.setdefault(_normalize_label(label), []).append(reference)
    unique = [matches[0] for matches in grouped.values() if len(matches) == 1]
    return tuple(
        sorted(
            unique,
            key=lambda reference: (_normalize_label(reference.label), reference.id),
        )
    )


def _currency_conflicts(expected: str | None, actual: str) -> bool:
    return expected is not None and expected != actual


def _normalize_label(value: str) -> str:
    return " ".join(value.split()).casefold()
