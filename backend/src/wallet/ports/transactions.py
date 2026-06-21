from __future__ import annotations

from typing import Protocol

from wallet.domain.transactions import Transaction


class TransactionRepository(Protocol):
    def add(self, transaction: Transaction) -> None: ...

    def get(self, transaction_id: str) -> Transaction | None: ...

    def list(self) -> list[Transaction]: ...
