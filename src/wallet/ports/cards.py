from __future__ import annotations

from typing import Protocol

from wallet.domain.cards import Card


class CardRepository(Protocol):
    def add(self, card: Card) -> None: ...

    def get(self, card_id: str) -> Card | None: ...

    def save(self, card: Card) -> None: ...

    def list(self) -> list[Card]: ...
