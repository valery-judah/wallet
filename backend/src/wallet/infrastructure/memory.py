from __future__ import annotations

from wallet.domain.accounts import Account
from wallet.domain.income_categories import IncomeCategory
from wallet.domain.spending_categories import SpendingCategory
from wallet.domain.transactions import Transaction


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


class InMemoryIncomeCategoryRepository:
    def __init__(self) -> None:
        self._categories_by_id: dict[str, IncomeCategory] = {}

    def add(self, category: IncomeCategory) -> None:
        self._categories_by_id[category.id] = category

    def get(self, category_id: str) -> IncomeCategory | None:
        return self._categories_by_id.get(category_id)

    def save(self, category: IncomeCategory) -> None:
        self._categories_by_id[category.id] = category

    def list(self) -> list[IncomeCategory]:
        return list(self._categories_by_id.values())


class InMemoryTransactionRepository:
    def __init__(self) -> None:
        self._transactions_by_id: dict[str, Transaction] = {}

    def add(self, transaction: Transaction) -> None:
        self._transactions_by_id[transaction.id] = transaction

    def get(self, transaction_id: str) -> Transaction | None:
        return self._transactions_by_id.get(transaction_id)

    def list(self) -> list[Transaction]:
        return list(self._transactions_by_id.values())
