from __future__ import annotations

from collections.abc import Callable
from datetime import date
from itertools import count

import pytest

from wallet.ai.transaction_capture.domain import CandidateField, TransactionCandidate
from wallet.ai.transaction_capture.ports import CaptureReference
from wallet.ai.transaction_capture.wallet_adapter import WalletCaptureAdapter
from wallet.application.transactions import TransactionService
from wallet.domain.accounts import Account, AccountType
from wallet.domain.income_categories import IncomeCategory
from wallet.domain.spending_categories import SpendingCategory
from wallet.domain.transactions import TransactionType
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)

TODAY = date(2026, 8, 5)


@pytest.mark.parametrize(
    ("candidate", "expected_postings"),
    [
        (
            TransactionCandidate(
                type=TransactionType.EXPENSE,
                amount_minor=4000,
                occurred_on=TODAY,
                account_id="checking",
                spending_category_id="groceries",
                description="Groceries",
                merchant_name="Market",
                notes="Weekly",
            ),
            (
                ("checking", None, -4000, "ARS"),
                (None, "groceries", 4000, "ARS"),
            ),
        ),
        (
            TransactionCandidate(
                type=TransactionType.INCOME,
                amount_minor=250000,
                occurred_on=TODAY,
                account_id="checking",
                income_category_id="payroll",
            ),
            (
                ("checking", None, 250000, "ARS"),
                (None, "payroll", -250000, "ARS"),
            ),
        ),
        (
            TransactionCandidate(
                type=TransactionType.TRANSFER,
                amount_minor=10000,
                occurred_on=TODAY,
                source_account_id="checking",
                destination_account_id="wallet",
            ),
            (
                ("checking", None, -10000, "ARS"),
                ("wallet", None, 10000, "ARS"),
            ),
        ),
        (
            TransactionCandidate(
                type=TransactionType.ADJUSTMENT,
                occurred_on=TODAY,
                account_id="cash_usd",
                balance_change_minor=5000,
            ),
            (
                ("cash_usd", None, 5000, "USD"),
                ("system_equity_usd", None, -5000, "USD"),
            ),
        ),
    ],
    ids=("expense", "income", "transfer", "adjustment"),
)
def test_adapter_creates_type_specific_wallet_transaction(
    candidate: TransactionCandidate,
    expected_postings: tuple[tuple[str | None, str | None, int, str], ...],
) -> None:
    adapter, transactions, _ = _adapter()

    transaction_id = adapter.execute(candidate)

    transaction = transactions.get(transaction_id)
    assert transaction is not None
    assert transaction.type is candidate.type
    assert transaction.occurred_on == candidate.occurred_on
    assert transaction.description == candidate.description
    assert transaction.merchant_name == candidate.merchant_name
    assert transaction.notes == candidate.notes
    assert (
        tuple(
            (
                posting.account_id,
                posting.category_id,
                posting.amount_minor,
                posting.currency,
            )
            for posting in transaction.postings
        )
        == expected_postings
    )


@pytest.mark.parametrize(
    ("candidate", "invalid_field"),
    [
        (
            TransactionCandidate(
                type=TransactionType.EXPENSE,
                amount_minor=100,
                occurred_on=TODAY,
                account_id="archived",
                spending_category_id="groceries",
            ),
            CandidateField.ACCOUNT_ID,
        ),
        (
            TransactionCandidate(
                type=TransactionType.EXPENSE,
                amount_minor=100,
                occurred_on=TODAY,
                account_id="checking",
                spending_category_id="payroll",
            ),
            CandidateField.SPENDING_CATEGORY_ID,
        ),
        (
            TransactionCandidate(
                type=TransactionType.INCOME,
                amount_minor=100,
                occurred_on=TODAY,
                account_id="checking",
                income_category_id="groceries",
            ),
            CandidateField.INCOME_CATEGORY_ID,
        ),
        (
            TransactionCandidate(
                type=TransactionType.TRANSFER,
                amount_minor=100,
                occurred_on=TODAY,
                source_account_id="missing",
                destination_account_id="wallet",
            ),
            CandidateField.SOURCE_ACCOUNT_ID,
        ),
        (
            TransactionCandidate(
                type=TransactionType.TRANSFER,
                amount_minor=100,
                occurred_on=TODAY,
                source_account_id="checking",
                destination_account_id="cash_usd",
            ),
            CandidateField.DESTINATION_ACCOUNT_ID,
        ),
    ],
    ids=(
        "archived-account",
        "wrong-spending-category",
        "wrong-income-category",
        "missing-source",
        "cross-currency-destination",
    ),
)
def test_adapter_reports_first_contextually_invalid_field(
    candidate: TransactionCandidate,
    invalid_field: CandidateField,
) -> None:
    adapter, _, _ = _adapter()

    assert adapter.invalid_field(candidate) is invalid_field


def test_adapter_exposes_only_unambiguous_selectable_reference_labels() -> None:
    accounts = InMemoryAccountRepository()
    accounts.add(_account("checking", "Daily checking", currency="ARS"))
    accounts.add(_account("duplicate_1", "Duplicate", currency="ARS"))
    accounts.add(_account("duplicate_2", " duplicate ", currency="ARS"))
    archived = _account("archived", "Archived", currency="ARS")
    archived.archive(archived_on=TODAY)
    accounts.add(archived)
    accounts.add(_account("system", "System", currency="ARS", is_system=True))

    spending = InMemorySpendingCategoryRepository()
    spending.add(_spending_category("food", "Food"))
    spending.add(_spending_category("groceries", "Groceries", parent_id="food"))
    spending.add(_spending_category("duplicate_category_1", "Duplicate"))
    spending.add(_spending_category("duplicate_category_2", " duplicate "))
    income = InMemoryIncomeCategoryRepository()
    income.add(_income_category("salary", "Salary"))
    income.add(_income_category("payroll", "Payroll", parent_id="salary"))

    catalog = _wallet_adapter(accounts, spending, income).capture_references()

    assert catalog.accounts == (CaptureReference("checking", "Daily checking"),)
    assert catalog.spending_categories == (
        CaptureReference("food", "Food"),
        CaptureReference("groceries", "Food > Groceries"),
    )
    assert catalog.income_categories == (
        CaptureReference("salary", "Salary"),
        CaptureReference("payroll", "Salary > Payroll"),
    )


def _adapter() -> tuple[
    WalletCaptureAdapter,
    InMemoryTransactionRepository,
    InMemoryAccountRepository,
]:
    accounts = InMemoryAccountRepository()
    accounts.add(_account("checking", "Checking", currency="ARS"))
    accounts.add(_account("wallet", "Wallet", currency="ARS"))
    accounts.add(_account("cash_usd", "USD cash", currency="USD"))
    archived = _account("archived", "Archived", currency="ARS")
    archived.archive(archived_on=TODAY)
    accounts.add(archived)

    spending = InMemorySpendingCategoryRepository()
    spending.add(
        SpendingCategory.create(
            id="groceries",
            name="Groceries",
            parent_id=None,
            icon=None,
            color=None,
            sort_order=0,
        )
    )
    income = InMemoryIncomeCategoryRepository()
    income.add(
        IncomeCategory.create(
            id="payroll",
            name="Payroll",
            parent_id=None,
            icon=None,
            color=None,
            sort_order=0,
        )
    )
    transactions = InMemoryTransactionRepository()
    return (
        _wallet_adapter(accounts, spending, income, transactions=transactions),
        transactions,
        accounts,
    )


def _wallet_adapter(
    accounts: InMemoryAccountRepository,
    spending: InMemorySpendingCategoryRepository,
    income: InMemoryIncomeCategoryRepository,
    *,
    transactions: InMemoryTransactionRepository | None = None,
) -> WalletCaptureAdapter:
    transaction_repository = transactions or InMemoryTransactionRepository()
    service = TransactionService(
        accounts=accounts,
        spending_categories=spending,
        income_categories=income,
        transactions=transaction_repository,
        today=lambda: TODAY,
        generate_transaction_id=lambda: "transaction_1",
        generate_posting_id=_id_generator("posting"),
    )
    return WalletCaptureAdapter(
        accounts=accounts,
        spending_categories=spending,
        income_categories=income,
        transactions=service,
    )


def _account(
    account_id: str,
    name: str,
    *,
    currency: str,
    is_system: bool = False,
) -> Account:
    return Account.open(
        id=account_id,
        name=name,
        type=AccountType.SYSTEM if is_system else AccountType.BANK_ACCOUNT,
        currency=currency,
        color_key=None,
        opened_on=TODAY,
        created_on=TODAY,
        is_system=is_system,
    )


def _spending_category(
    category_id: str,
    name: str,
    *,
    parent_id: str | None = None,
) -> SpendingCategory:
    return SpendingCategory.create(
        id=category_id,
        name=name,
        parent_id=parent_id,
        icon=None,
        color=None,
        sort_order=0,
    )


def _income_category(
    category_id: str,
    name: str,
    *,
    parent_id: str | None = None,
) -> IncomeCategory:
    return IncomeCategory.create(
        id=category_id,
        name=name,
        parent_id=parent_id,
        icon=None,
        color=None,
        sort_order=0,
    )


def _id_generator(prefix: str) -> Callable[[], str]:
    sequence = count(1)
    return lambda: f"{prefix}_{next(sequence)}"
