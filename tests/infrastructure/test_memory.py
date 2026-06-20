from __future__ import annotations

from datetime import date

from wallet.domain.cards import Card
from wallet.domain.money import Money
from wallet.infrastructure.memory import InMemoryCardRepository


def test_in_memory_card_repository_stores_and_lists_cards() -> None:
    repo = InMemoryCardRepository()
    first = Card(
        id="card_1",
        name="Daily card",
        currency="USD",
        balance=Money.zero("USD"),
        created_on=date(2026, 6, 18),
    )
    second = Card(
        id="card_2",
        name="Travel card",
        currency="EUR",
        balance=Money.zero("EUR"),
        created_on=date(2026, 6, 18),
    )

    repo.add(first)
    repo.add(second)

    assert repo.get("card_1") == first
    assert repo.list() == [first, second]
