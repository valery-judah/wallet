from __future__ import annotations

from datetime import date

from wallet.domain.accounts import Account, AccountType
from wallet.domain.money import Money
from wallet.domain.spending_categories import SpendingCategory
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemorySpendingCategoryRepository,
)


def test_in_memory_account_repository_stores_and_lists_accounts() -> None:
    repo = InMemoryAccountRepository()
    first = Account.open(
        id="account_1",
        name="Daily account",
        type=AccountType.CARD,
        currency="USD",
        current_balance=Money.zero("USD"),
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )
    second = Account.open(
        id="account_2",
        name="Travel cash",
        type=AccountType.CASH,
        currency="EUR",
        current_balance=Money.zero("EUR"),
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
