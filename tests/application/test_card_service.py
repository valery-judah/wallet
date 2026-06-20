from __future__ import annotations

from datetime import date

import pytest

from wallet.application.cards import CardService, DepositToCard, IssueCard, WithdrawFromCard
from wallet.domain.cards import CardNotFoundError, CurrencyMismatchError, InsufficientFundsError
from wallet.domain.money import Money
from wallet.infrastructure.memory import InMemoryCardRepository


def test_issue_card_uses_injected_clock_and_id_generator() -> None:
    repo = InMemoryCardRepository()
    service = CardService(
        cards=repo,
        today=lambda: date(2026, 6, 18),
        generate_card_id=lambda: "card_fixed",
    )

    card = service.issue_card(IssueCard(name="Daily card", currency="usd"))

    assert card.id == "card_fixed"
    assert card.created_on == date(2026, 6, 18)
    assert repo.get("card_fixed") == card


def test_deposit_to_card_increases_balance() -> None:
    service = CardService(
        today=lambda: date(2026, 6, 18),
        generate_card_id=lambda: "card_daily",
    )
    card = service.issue_card(IssueCard(name="Daily card", currency="USD"))

    updated = service.deposit_to_card(
        DepositToCard(
            card_id=card.id,
            amount=Money(amount_minor=50_000, currency="USD"),
        )
    )

    assert updated.balance == Money(amount_minor=50_000, currency="USD")


def test_withdraw_from_card_given_multiple_operations_decreases_balance() -> None:
    service = CardService(generate_card_id=lambda: "card_daily")
    card = service.issue_card(IssueCard(name="Daily card", currency="USD"))
    service.deposit_to_card(
        DepositToCard(
            card_id=card.id,
            amount=Money(amount_minor=50_000, currency="USD"),
        )
    )
    service.withdraw_from_card(
        WithdrawFromCard(
            card_id=card.id,
            amount=Money(amount_minor=4_500, currency="USD"),
        )
    )

    updated = service.withdraw_from_card(
        WithdrawFromCard(
            card_id=card.id,
            amount=Money(amount_minor=20_000, currency="USD"),
        )
    )

    assert updated.balance == Money(amount_minor=25_500, currency="USD")


def test_withdraw_from_card_given_insufficient_funds_rejects_operation() -> None:
    service = CardService(generate_card_id=lambda: "card_daily")
    card = service.issue_card(IssueCard(name="Daily card", currency="USD"))

    with pytest.raises(InsufficientFundsError):
        service.withdraw_from_card(
            WithdrawFromCard(
                card_id=card.id,
                amount=Money(amount_minor=100, currency="USD"),
            )
        )


def test_deposit_to_card_given_currency_mismatch_rejects_operation() -> None:
    service = CardService(generate_card_id=lambda: "card_daily")
    card = service.issue_card(IssueCard(name="Daily card", currency="USD"))

    with pytest.raises(CurrencyMismatchError):
        service.deposit_to_card(
            DepositToCard(
                card_id=card.id,
                amount=Money(amount_minor=100, currency="ARS"),
            )
        )


def test_get_card_given_missing_card_returns_none() -> None:
    service = CardService()

    assert service.get_card("missing") is None


def test_card_commands_given_missing_card_raise_not_found() -> None:
    service = CardService()

    with pytest.raises(CardNotFoundError):
        service.deposit_to_card(
            DepositToCard(
                card_id="missing",
                amount=Money(amount_minor=100, currency="USD"),
            )
        )


def test_list_cards_returns_issued_cards() -> None:
    service = CardService(generate_card_id=_sequential_ids(["card_1", "card_2"]))
    first = service.issue_card(IssueCard(name="Daily card", currency="USD"))
    second = service.issue_card(IssueCard(name="Travel card", currency="EUR"))

    assert service.list_cards() == [first, second]


def _sequential_ids(ids: list[str]):
    def factory() -> str:
        return ids.pop(0)

    return factory
