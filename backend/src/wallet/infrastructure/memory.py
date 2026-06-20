from __future__ import annotations

from wallet.domain.cards import Card


class InMemoryCardRepository:
    def __init__(self) -> None:
        self._cards_by_id: dict[str, Card] = {}

    def add(self, card: Card) -> None:
        self._cards_by_id[card.id] = card

    def get(self, card_id: str) -> Card | None:
        return self._cards_by_id.get(card_id)

    def save(self, card: Card) -> None:
        self._cards_by_id[card.id] = card

    def list(self) -> list[Card]:
        return list(self._cards_by_id.values())
