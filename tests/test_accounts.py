from __future__ import annotations

from collections.abc import Callable

import pytest

from wallet.accounts import (
    Account,
    AccountNotFoundError,
    AccountService,
    AccountSummary,
    BalanceSnapshot,
)

# Account query scenarios


def test_get_account_record_given_existing_account_returns_raw_account(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account(name="Peso cash", opening_balance_minor=100)

    # When
    account = service.get_account_record(opened.account.id)

    # Then
    assert account is not None
    assert account.id == opened.account.id
    assert account.name == "Peso cash"


def test_list_accounts_given_closed_and_active_accounts_returns_only_active_by_default(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    active = open_cash_account(name="Peso cash", opening_balance_minor=100)
    closed = open_cash_account(name="Travel cash", opening_balance_minor=200)
    service.close_account(closed.account.id)

    # When
    listed = service.list_accounts()

    # Then
    assert [summary.account.id for summary in listed] == [active.account.id]


# Balance snapshot scenarios


def test_list_balance_snapshots_given_opening_and_manual_check_returns_snapshot_history(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()
    service.record_balance_snapshot(opened.account.id, 250, reason="manual_check")

    # When
    snapshots = service.list_balance_snapshots(opened.account.id)

    # Then
    assert [snapshot.balance_minor for snapshot in snapshots] == [100, 250]
    assert [snapshot.reason for snapshot in snapshots] == [
        "opening_balance",
        "manual_check",
    ]


# Missing-account scenarios


def test_get_account_queries_given_missing_account_return_none(
    service: AccountService,
) -> None:
    # Given / When
    summary = service.get_account("missing")
    account = service.get_account_record("missing")

    # Then
    assert summary is None
    assert account is None


def test_account_commands_given_missing_account_raise_not_found(
    service: AccountService,
) -> None:
    # Given / When / Then
    with pytest.raises(AccountNotFoundError):
        service.rename_account("missing", "Renamed")

    with pytest.raises(AccountNotFoundError):
        service.get_current_balance("missing")

    with pytest.raises(AccountNotFoundError):
        service.list_balance_snapshots("missing")


def test_wallet_accounts_facade_re_exports_representative_types() -> None:
    assert Account.__name__ == "Account"
    assert BalanceSnapshot.__name__ == "BalanceSnapshot"
    assert AccountService.__name__ == "AccountService"
