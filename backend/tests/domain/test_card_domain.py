from __future__ import annotations

from datetime import date

import pytest

from wallet.domain.cards import Card, CurrencyMismatchError, InsufficientFundsError
from wallet.domain.money import Money


def test_issue_card_given_valid_inputs_yields_zero_balance() -> None:
    card = Card.issue(
        id="card_test",
        name="Daily card",
        currency=" usd ",
        created_on=date(2026, 6, 18),
    )

    assert card.id == "card_test"
    assert card.name == "Daily card"
    assert card.currency == "USD"
    assert card.balance == Money.zero("USD")


def test_card_deposit_given_currency_mismatch_rejects_operation() -> None:
    card = Card.issue(
        id="card_test",
        name="Daily card",
        currency="USD",
        created_on=date(2026, 6, 18),
    )

    with pytest.raises(CurrencyMismatchError):
        card.deposit(Money(amount_minor=100, currency="ARS"))


def test_card_withdraw_given_insufficient_funds_rejects_operation() -> None:
    card = Card.issue(
        id="card_test",
        name="Daily card",
        currency="USD",
        created_on=date(2026, 6, 18),
    )

    with pytest.raises(InsufficientFundsError):
        card.withdraw(Money(amount_minor=100, currency="USD"))


def test_card_rejects_negative_balance_state() -> None:
    with pytest.raises(ValueError, match="card balance must not be negative"):
        Card(
            id="card_test",
            name="Daily card",
            currency="USD",
            balance=Money(amount_minor=-1, currency="USD"),
            created_on=date(2026, 6, 18),
        )
