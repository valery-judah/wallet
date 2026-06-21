from __future__ import annotations

from datetime import date

from wallet.domain.accounts import Account, AccountType
from wallet.domain.income_categories import IncomeCategory
from wallet.domain.spending_categories import SpendingCategory
from wallet.domain.transactions import Posting, Transaction, TransactionStatus, TransactionType
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)


def test_in_memory_account_repository_stores_and_lists_accounts() -> None:
    repo = InMemoryAccountRepository()
    first = Account.open(
        id="account_1",
        name="Daily account",
        type=AccountType.DEBIT_CARD,
        currency="USD",
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )
    second = Account.open(
        id="account_2",
        name="Travel cash",
        type=AccountType.CASH,
        currency="EUR",
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    repo.add(first)
    repo.add(second)

    assert repo.get("account_1") == first
    assert repo.list() == [first, second]


def test_in_memory_spending_category_repository_stores_and_lists_categories() -> None:
    repo = InMemorySpendingCategoryRepository()
    first = SpendingCategory.create(
        id="category_1",
        name="Food",
        parent_id=None,
        icon=None,
        color=None,
        sort_order=10,
    )
    second = SpendingCategory.create(
        id="category_2",
        name="Groceries",
        parent_id="category_1",
        icon=None,
        color=None,
        sort_order=10,
    )

    repo.add(first)
    repo.add(second)

    assert repo.get("category_1") == first
    assert repo.list() == [first, second]


def test_in_memory_income_category_repository_stores_and_lists_categories() -> None:
    repo = InMemoryIncomeCategoryRepository()
    first = IncomeCategory.create(
        id="income_1",
        name="Salary",
        parent_id=None,
        icon=None,
        color=None,
        sort_order=10,
    )
    second = IncomeCategory.create(
        id="income_2",
        name="Payroll",
        parent_id="income_1",
        icon=None,
        color=None,
        sort_order=10,
    )

    repo.add(first)
    repo.add(second)

    assert repo.get("income_1") == first
    assert repo.list() == [first, second]


def test_in_memory_transaction_repository_stores_and_lists_transactions() -> None:
    repo = InMemoryTransactionRepository()
    transaction = Transaction(
        id="transaction_1",
        occurred_on=date(2026, 6, 18),
        posted_on=date(2026, 6, 18),
        description="Lunch",
        merchant_name=None,
        notes=None,
        status=TransactionStatus.POSTED,
        type=TransactionType.EXPENSE,
        postings=(
            Posting(
                id="posting_1",
                transaction_id="transaction_1",
                account_id="account_1",
                category_id=None,
                amount_minor=-100,
                currency="USD",
            ),
            Posting(
                id="posting_2",
                transaction_id="transaction_1",
                account_id=None,
                category_id="category_1",
                amount_minor=100,
                currency="USD",
            ),
        ),
        created_on=date(2026, 6, 18),
        updated_on=date(2026, 6, 18),
    )

    repo.add(transaction)

    assert repo.get("transaction_1") == transaction
    assert repo.list() == [transaction]
