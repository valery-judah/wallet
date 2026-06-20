from __future__ import annotations

from typing import Protocol

from wallet.domain.accounts import Account


class AccountRepository(Protocol):
    def add(self, account: Account) -> None: ...

    def get(self, account_id: str) -> Account | None: ...

    def save(self, account: Account) -> None: ...

    def list(self) -> list[Account]: ...
