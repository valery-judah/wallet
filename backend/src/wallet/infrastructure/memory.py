from __future__ import annotations

from wallet.domain.accounts import Account
from wallet.domain.spending_categories import SpendingCategory


class InMemoryAccountRepository:
    def __init__(self) -> None:
        self._accounts_by_id: dict[str, Account] = {}

    def add(self, account: Account) -> None:
        self._accounts_by_id[account.id] = account

    def get(self, account_id: str) -> Account | None:
        return self._accounts_by_id.get(account_id)

    def save(self, account: Account) -> None:
        self._accounts_by_id[account.id] = account

    def list(self) -> list[Account]:
        return list(self._accounts_by_id.values())


class InMemorySpendingCategoryRepository:
    def __init__(self) -> None:
        self._categories_by_id: dict[str, SpendingCategory] = {}

    def add(self, category: SpendingCategory) -> None:
        self._categories_by_id[category.id] = category

    def get(self, category_id: str) -> SpendingCategory | None:
        return self._categories_by_id.get(category_id)

    def save(self, category: SpendingCategory) -> None:
        self._categories_by_id[category.id] = category

    def list(self) -> list[SpendingCategory]:
        return list(self._categories_by_id.values())
