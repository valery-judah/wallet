from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from wallet.domain._validation import normalize_currency, normalize_nonblank, require_positive
from wallet.domain.cards import Card, CardNotFoundError
from wallet.domain.money import Money
from wallet.infrastructure.memory import InMemoryCardRepository
from wallet.ports.cards import CardRepository
from wallet.ports.system import CardIdGenerator, DateProvider


class CreateCardRejectedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class IssueCard:
    name: str
    currency: str = "ARS"
    opened_on: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            normalize_nonblank(self.name, field_name="card name"),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_currency(self.currency, field_name="card currency"),
        )


@dataclass(frozen=True, slots=True)
class DepositToCard:
    card_id: str
    amount: Money

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "card_id",
            normalize_nonblank(self.card_id, field_name="card id"),
        )
        require_positive(self.amount.amount_minor, field_name="amount")


@dataclass(frozen=True, slots=True)
class WithdrawFromCard:
    card_id: str
    amount: Money

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "card_id",
            normalize_nonblank(self.card_id, field_name="card id"),
        )
        require_positive(self.amount.amount_minor, field_name="amount")


class CardService:
    def __init__(
        self,
        *,
        cards: CardRepository | None = None,
        today: DateProvider | None = None,
        generate_card_id: CardIdGenerator | None = None,
    ) -> None:
        self.cards = cards or InMemoryCardRepository()
        self._today = today or date.today
        self._generate_card_id = generate_card_id or _new_card_id

    def issue_card(self, command: IssueCard) -> Card:
        opened_on = command.opened_on or self._today()
        try:
            card = Card.issue(
                id=self._generate_card_id(),
                name=command.name,
                currency=command.currency,
                created_on=opened_on,
            )
        except ValueError as exc:
            raise CreateCardRejectedError(str(exc)) from exc
        self.cards.add(card)
        return card

    def deposit_to_card(self, command: DepositToCard) -> Card:
        card = self._require_card(command.card_id)
        card.deposit(command.amount)
        self.cards.save(card)
        return card

    def withdraw_from_card(self, command: WithdrawFromCard) -> Card:
        card = self._require_card(command.card_id)
        card.withdraw(command.amount)
        self.cards.save(card)
        return card

    def get_card(self, card_id: str) -> Card | None:
        return self.cards.get(card_id)

    def list_cards(self) -> list[Card]:
        return self.cards.list()

    def _require_card(self, card_id: str) -> Card:
        card = self.cards.get(card_id)
        if card is None:
            raise CardNotFoundError(card_id)
        return card


def _new_card_id() -> str:
    return f"card_{uuid4().hex}"
