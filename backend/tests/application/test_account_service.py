from __future__ import annotations

from datetime import date

import pytest

from wallet.application.accounts import (
    AccountService,
    CloseAccount,
    CreditAccount,
    DebitAccount,
    OpenAccount,
    UpdateAccountProfile,
)
from wallet.domain.accounts import (
    AccountClosedError,
    AccountNotFoundError,
    AccountType,
    CurrencyMismatchError,
    InsufficientFundsError,
)
from wallet.domain.money import Money
from wallet.infrastructure.memory import InMemoryAccountRepository


def test_open_account_uses_injected_clock_and_id_generator() -> None:
    repo = InMemoryAccountRepository()
    service = AccountService(
        accounts=repo,
        today=lambda: date(2026, 6, 18),
        generate_account_id=lambda: "account_fixed",
    )

    account = service.open_account(
        OpenAccount(name="Daily account", type=AccountType.CARD, currency="usd"),
    )

    assert account.id == "account_fixed"
    assert account.created_on == date(2026, 6, 18)
    assert account.opened_on == date(2026, 6, 18)
    assert repo.get("account_fixed") == account


def test_open_account_supports_starting_balance_and_type() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 18),
        generate_account_id=lambda: "account_cash",
    )

    account = service.open_account(
        OpenAccount(
            name="Cash wallet",
            type=AccountType.CASH,
            currency="USD",
            current_balance_minor=12_500,
            color_key="amber",
        ),
    )

    assert account.type is AccountType.CASH
    assert account.current_balance == Money(amount_minor=12_500, currency="USD")
    assert account.color_key == "amber"


def test_open_account_given_negative_starting_balance_is_rejected() -> None:
    with pytest.raises(ValueError, match="account balance must not be negative"):
        OpenAccount(
            name="Broken account",
            current_balance_minor=-1,
        )


def test_credit_account_increases_balance() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 18),
        generate_account_id=lambda: "account_daily",
    )
    account = service.open_account(OpenAccount(name="Daily account", currency="USD"))

    updated = service.credit_account(
        CreditAccount(
            account_id=account.id,
            amount=Money(amount_minor=50_000, currency="USD"),
        ),
    )

    assert updated.current_balance == Money(amount_minor=50_000, currency="USD")


def test_update_account_profile_changes_name_type_and_display_metadata() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 19),
        generate_account_id=lambda: "account_daily",
    )
    account = service.open_account(OpenAccount(name="Daily account", currency="USD"))

    updated = service.update_account_profile(
        UpdateAccountProfile(
            account_id=account.id,
            name="Travel wallet",
            type=AccountType.WALLET,
            color_key="cyan",
            icon_key="wallet",
        )
    )

    assert updated.name == "Travel wallet"
    assert updated.type is AccountType.WALLET
    assert updated.color_key == "cyan"
    assert updated.icon_key == "wallet"
    assert updated.updated_on == date(2026, 6, 19)


def test_debit_account_given_multiple_operations_decreases_balance() -> None:
    service = AccountService(generate_account_id=lambda: "account_daily")
    account = service.open_account(OpenAccount(name="Daily account", currency="USD"))
    service.credit_account(
        CreditAccount(
            account_id=account.id,
            amount=Money(amount_minor=50_000, currency="USD"),
        ),
    )
    service.debit_account(
        DebitAccount(
            account_id=account.id,
            amount=Money(amount_minor=4_500, currency="USD"),
        ),
    )

    updated = service.debit_account(
        DebitAccount(
            account_id=account.id,
            amount=Money(amount_minor=20_000, currency="USD"),
        ),
    )

    assert updated.current_balance == Money(amount_minor=25_500, currency="USD")


def test_debit_account_given_insufficient_funds_rejects_operation() -> None:
    service = AccountService(generate_account_id=lambda: "account_daily")
    account = service.open_account(OpenAccount(name="Daily account", currency="USD"))

    with pytest.raises(InsufficientFundsError):
        service.debit_account(
            DebitAccount(
                account_id=account.id,
                amount=Money(amount_minor=100, currency="USD"),
            )
        )


def test_credit_account_given_currency_mismatch_rejects_operation() -> None:
    service = AccountService(generate_account_id=lambda: "account_daily")
    account = service.open_account(OpenAccount(name="Daily account", currency="USD"))

    with pytest.raises(CurrencyMismatchError):
        service.credit_account(
            CreditAccount(
                account_id=account.id,
                amount=Money(amount_minor=100, currency="ARS"),
            )
        )


def test_close_account_marks_account_closed_and_blocks_future_balance_changes() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 19),
        generate_account_id=lambda: "account_daily",
    )
    account = service.open_account(OpenAccount(name="Daily account", currency="USD"))

    closed = service.close_account(CloseAccount(account_id=account.id))

    assert closed.status.value == "closed"
    assert closed.closed_on == date(2026, 6, 19)

    with pytest.raises(AccountClosedError, match="account is closed"):
        service.credit_account(
            CreditAccount(
                account_id=account.id,
                amount=Money(amount_minor=100, currency="USD"),
            )
        )


def test_get_account_given_missing_account_returns_none() -> None:
    service = AccountService()

    assert service.get_account("missing") is None


def test_account_commands_given_missing_account_raise_not_found() -> None:
    service = AccountService()

    with pytest.raises(AccountNotFoundError):
        service.credit_account(
            CreditAccount(
                account_id="missing",
                amount=Money(amount_minor=100, currency="USD"),
            )
        )


def test_list_accounts_returns_opened_accounts() -> None:
    service = AccountService(generate_account_id=_sequential_ids(["account_1", "account_2"]))
    first = service.open_account(OpenAccount(name="Daily account", currency="USD"))
    second = service.open_account(
        OpenAccount(name="Travel cash", type=AccountType.CASH, currency="EUR"),
    )

    assert service.list_accounts() == [first, second]


def _sequential_ids(ids: list[str]):
    def factory() -> str:
        return ids.pop(0)

    return factory
