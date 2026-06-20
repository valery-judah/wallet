from __future__ import annotations

from typing import Protocol

from wallet.domain.spending_categories import SpendingCategory


class SpendingCategoryRepository(Protocol):
    def add(self, category: SpendingCategory) -> None: ...

    def get(self, category_id: str) -> SpendingCategory | None: ...

    def save(self, category: SpendingCategory) -> None: ...

    def list(self) -> list[SpendingCategory]: ...
