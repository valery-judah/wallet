from __future__ import annotations

from datetime import date

import pytest

from wallet.domain.accounts import (
    Account,
    AccountClosedError,
    AccountStatus,
    AccountType,
    CurrencyMismatchError,
    InsufficientFundsError,
)
from wallet.domain.money import Money


def test_open_account_given_valid_inputs_yields_requested_starting_balance() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.CARD,
        currency=" usd ",
        current_balance=Money(amount_minor=500, currency="USD"),
        color_key="violet",
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    assert account.id == "account_test"
    assert account.name == "Daily account"
    assert account.type is AccountType.CARD
    assert account.currency == "USD"
    assert account.current_balance == Money(amount_minor=500, currency="USD")
    assert account.status is AccountStatus.ACTIVE
    assert account.color_key == "violet"


def test_account_credit_given_currency_mismatch_rejects_operation() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.CARD,
        currency="USD",
        current_balance=Money.zero("USD"),
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    with pytest.raises(CurrencyMismatchError):
        account.credit(
            Money(amount_minor=100, currency="ARS"),
            updated_on=date(2026, 6, 19),
        )


def test_account_debit_given_insufficient_funds_rejects_operation() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.CARD,
        currency="USD",
        current_balance=Money.zero("USD"),
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    with pytest.raises(InsufficientFundsError):
        account.debit(
            Money(amount_minor=100, currency="USD"),
            updated_on=date(2026, 6, 19),
        )


def test_account_rejects_negative_balance_state() -> None:
    with pytest.raises(ValueError, match="account balance must not be negative"):
        Account(
            id="account_test",
            name="Daily account",
            type=AccountType.CARD,
            currency="USD",
            current_balance=Money(amount_minor=-1, currency="USD"),
            status=AccountStatus.ACTIVE,
            color_key=None,
            opened_on=date(2026, 6, 18),
            closed_on=None,
            created_on=date(2026, 6, 18),
            updated_on=date(2026, 6, 18),
        )


def test_account_update_profile_changes_type_and_metadata() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.CARD,
        currency="USD",
        current_balance=Money.zero("USD"),
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    account.update_profile(
        name="Reserve fund",
        type=AccountType.SAVINGS,
        color_key="emerald",
        updated_on=date(2026, 6, 19),
    )

    assert account.name == "Reserve fund"
    assert account.type is AccountType.SAVINGS
    assert account.color_key == "emerald"
    assert account.updated_on == date(2026, 6, 19)


def test_closed_account_rejects_balance_movements() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.CARD,
        currency="USD",
        current_balance=Money(amount_minor=500, currency="USD"),
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )
    account.close(closed_on=date(2026, 6, 19))

    with pytest.raises(AccountClosedError, match="account is closed"):
        account.credit(
            Money(amount_minor=100, currency="USD"),
            updated_on=date(2026, 6, 20),
        )
