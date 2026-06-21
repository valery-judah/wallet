from __future__ import annotations

from datetime import date

import pytest

from wallet.application.accounts import (
    AccountService,
    ArchiveAccount,
    OpenAccount,
    UpdateAccountProfile,
)
from wallet.domain.accounts import AccountClosedError, AccountNotFoundError, AccountType
from wallet.infrastructure.memory import InMemoryAccountRepository, InMemoryTransactionRepository


def test_open_account_uses_injected_clock_and_id_generator() -> None:
    repo = InMemoryAccountRepository()
    transactions = InMemoryTransactionRepository()
    service = AccountService(
        accounts=repo,
        transactions=transactions,
        today=lambda: date(2026, 6, 18),
        generate_account_id=lambda: "account_fixed",
        generate_transaction_id=lambda: "transaction_fixed",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2"]),
    )

    snapshot = service.open_account(
        OpenAccount(name="Daily account", type=AccountType.DEBIT_CARD, currency="usd"),
    )

    assert snapshot.account.id == "account_fixed"
    assert snapshot.account.created_on == date(2026, 6, 18)
    assert snapshot.account.opened_on == date(2026, 6, 18)
    assert snapshot.current_balance.amount_minor == 0
    assert repo.get("account_fixed") == snapshot.account


def test_open_account_supports_opening_balance_and_creates_synthetic_adjustment() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 18),
        generate_account_id=lambda: "account_cash",
        generate_transaction_id=lambda: "transaction_opening",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2"]),
    )

    snapshot = service.open_account(
        OpenAccount(
            name="Cash wallet",
            type=AccountType.CASH,
            currency="USD",
            opening_balance_minor=12_500,
            color_key="amber",
        ),
    )

    assert snapshot.account.type is AccountType.CASH
    assert snapshot.current_balance.amount_minor == 12_500
    assert snapshot.current_balance.currency == "USD"
    transactions = service.transactions.list()
    assert len(transactions) == 1
    assert transactions[0].type.value == "adjustment"


def test_open_account_supports_negative_opening_balance_for_credit_cards() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 18),
        generate_account_id=lambda: "account_card",
        generate_transaction_id=lambda: "transaction_opening",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2"]),
    )

    snapshot = service.open_account(
        OpenAccount(
            name="Visa",
            type=AccountType.CREDIT_CARD,
            currency="USD",
            opening_balance_minor=-4_200,
        ),
    )

    assert snapshot.current_balance.amount_minor == -4_200


def test_update_account_profile_changes_name_type_and_display_metadata() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 19),
        generate_account_id=lambda: "account_daily",
    )
    opened = service.open_account(OpenAccount(name="Daily account", currency="USD"))

    updated = service.update_account_profile(
        UpdateAccountProfile(
            account_id=opened.account.id,
            name="Travel wallet",
            type=AccountType.WALLET,
            color_key="cyan",
        )
    )

    assert updated.account.name == "Travel wallet"
    assert updated.account.type is AccountType.WALLET
    assert updated.account.color_key == "cyan"
    assert updated.account.updated_on == date(2026, 6, 19)


def test_archive_account_marks_account_archived_and_preserves_balance() -> None:
    service = AccountService(
        today=lambda: date(2026, 6, 19),
        generate_account_id=lambda: "account_daily",
        generate_transaction_id=lambda: "transaction_opening",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2"]),
    )
    opened = service.open_account(
        OpenAccount(name="Daily account", currency="USD", opening_balance_minor=100)
    )

    closed = service.archive_account(ArchiveAccount(account_id=opened.account.id))

    assert closed.account.archived_at == date(2026, 6, 19)
    assert closed.current_balance.amount_minor == 100

    with pytest.raises(AccountClosedError, match="account is archived"):
        closed.account.assert_allows_transactions()


def test_get_account_given_missing_account_returns_none() -> None:
    service = AccountService()

    assert service.get_account("missing") is None


def test_account_commands_given_missing_account_raise_not_found() -> None:
    service = AccountService()

    with pytest.raises(AccountNotFoundError):
        service.archive_account(ArchiveAccount(account_id="missing"))


def test_list_accounts_returns_only_user_accounts() -> None:
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
