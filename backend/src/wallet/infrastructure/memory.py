from __future__ import annotations

from wallet.domain.accounts import Account


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
