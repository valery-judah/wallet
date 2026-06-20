from __future__ import annotations

from .account import Account
from .balances import BalanceSnapshot


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


class InMemoryBalanceSnapshotRepository:
    def __init__(self) -> None:
        self._snapshots_by_account_id: dict[str, list[BalanceSnapshot]] = {}

    def add(self, snapshot: BalanceSnapshot) -> None:
        snapshots = self._snapshots_by_account_id.setdefault(snapshot.account_id, [])
        snapshots.append(snapshot)

    def get_latest_for_account(self, account_id: str) -> BalanceSnapshot | None:
        snapshots = self._snapshots_by_account_id.get(account_id)
        if not snapshots:
            return None
        return snapshots[-1]

    def list_for_account(self, account_id: str) -> list[BalanceSnapshot]:
        return list(self._snapshots_by_account_id.get(account_id, []))
