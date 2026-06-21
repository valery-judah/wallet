from __future__ import annotations

from typing import Protocol

from wallet.domain.income_categories import IncomeCategory


class IncomeCategoryRepository(Protocol):
    def add(self, category: IncomeCategory) -> None: ...

    def get(self, category_id: str) -> IncomeCategory | None: ...

    def save(self, category: IncomeCategory) -> None: ...

    def list(self) -> list[IncomeCategory]: ...
