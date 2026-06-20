from __future__ import annotations

import pytest

from wallet.domain.money import CurrencyMismatchError, Money


def test_money_normalizes_currency() -> None:
    amount = Money(amount_minor=100, currency=" usd ")

    assert amount.currency == "USD"


def test_money_add_requires_matching_currency() -> None:
    with pytest.raises(CurrencyMismatchError):
        Money(amount_minor=100, currency="USD").add(Money(amount_minor=50, currency="ARS"))


def test_money_subtract_returns_new_amount() -> None:
    result = Money(amount_minor=500, currency="USD").subtract(
        Money(amount_minor=125, currency="USD")
    )

    assert result == Money(amount_minor=375, currency="USD")
