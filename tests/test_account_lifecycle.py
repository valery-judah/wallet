from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest
from pydantic import ValidationError

from wallet.accounts import (
    ALLOWED_ACCOUNT_TRANSITIONS,
    Account,
    AccountAction,
    AccountService,
    AccountSummary,
    InvalidAccountStateTransition,
    OpenCashAccountRequest,
)


def test_open_cash_given_valid_inputs_returns_active_cash_account() -> None:
    # Given / When
    account = Account.open_cash(
        id="acct_123",
        name="Peso cash",
        currency="ARS",
        opened_on=date(2026, 6, 16),
    )

    # Then
    assert account.id == "acct_123"
    assert account.name == "Peso cash"
    assert account.currency == "ARS"
    assert account.kind == "cash"
    assert account.status == "active"
    assert account.created_on == date(2026, 6, 16)


def test_account_state_graph_defines_expected_allowed_transitions() -> None:
    # Given / Then
    assert ALLOWED_ACCOUNT_TRANSITIONS == {
        ("active", "rename"): "active",
        ("active", "record_balance_snapshot"): "active",
        ("active", "close"): "closed",
        ("closed", "rename"): "closed",
        ("closed", "archive"): "archived",
    }


def test_open_account_given_valid_cash_request_returns_active_account_with_opening_balance(
    service: AccountService,
    make_open_cash_account_request: Callable[..., OpenCashAccountRequest],
) -> None:
    # Given
    request = make_open_cash_account_request(
        name="Peso cash",
        opening_balance_minor=6_100_000,
        opened_on=date(2026, 6, 16),
    )

    # When
    summary = service.open_account(request)

    # Then
    assert summary.account.name == "Peso cash"
    assert summary.account.kind == "cash"
    assert summary.account.status == "active"
    assert summary.account.created_on == date(2026, 6, 16)
    assert summary.current_balance is not None
    assert summary.current_balance.account_id == summary.account.id
    assert summary.current_balance.balance_minor == 6_100_000
    assert summary.current_balance.checked_at == date(2026, 6, 16)
    assert summary.current_balance.reason == "opening_balance"


def test_open_account_given_no_currency_uses_ars_by_default(
    service: AccountService,
    make_open_cash_account_request: Callable[..., OpenCashAccountRequest],
) -> None:
    # Given
    request = make_open_cash_account_request(name="Peso cash", opening_balance_minor=0)

    # When
    summary = service.open_account(request)

    # Then
    assert summary.account.currency == "ARS"


def test_open_account_given_blank_name_rejects_request_during_validation(
    make_open_cash_account_request: Callable[..., OpenCashAccountRequest],
) -> None:
    # Given / When / Then
    with pytest.raises(ValidationError, match="account name must not be blank"):
        make_open_cash_account_request(name="  ", opening_balance_minor=0)


def test_open_account_given_negative_opening_balance_rejects_request_during_validation(
    make_open_cash_account_request: Callable[..., OpenCashAccountRequest],
) -> None:
    # Given / When / Then
    with pytest.raises(ValidationError, match="balance must not be negative"):
        make_open_cash_account_request(name="Peso cash", opening_balance_minor=-1)


def test_rename_account_given_existing_account_updates_name_in_summary_and_storage(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()

    # When
    renamed = service.rename_account(opened.account.id, "Peso cash")
    fetched = service.get_account(opened.account.id)

    # Then
    assert renamed.account.name == "Peso cash"
    assert fetched is not None
    assert fetched.account.name == "Peso cash"


def test_rename_account_given_blank_name_raises_validation_error(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()

    # When / Then
    with pytest.raises(ValidationError, match="account name must not be blank"):
        service.rename_account(opened.account.id, "  ")


def test_close_account_given_existing_account_marks_it_closed(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()

    # When
    closed = service.close_account(opened.account.id)

    # Then
    assert closed.account.status == "closed"


def test_archive_account_given_closed_account_marks_it_archived(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()
    service.close_account(opened.account.id)

    # When
    archived = service.archive_account(opened.account.id)

    # Then
    assert archived.account.status == "archived"


@pytest.mark.parametrize(
    ("action", "prepare"),
    [
        ("close", lambda svc, account_id: svc.close_account(account_id)),
        (
            "archive",
            lambda svc, account_id: (
                svc.close_account(account_id),
                svc.archive_account(account_id),
            ),
        ),
    ],
)
def test_lifecycle_commands_given_invalid_repeated_transition_raise_error(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
    action: AccountAction,
    prepare,
) -> None:
    # Given
    opened = open_cash_account()
    prepare(service, opened.account.id)

    # When / Then
    with pytest.raises(
        InvalidAccountStateTransition,
        match=f"cannot {action} account",
    ):
        if action == "close":
            service.close_account(opened.account.id)
        else:
            service.archive_account(opened.account.id)


def test_archive_account_given_active_account_raises_invalid_transition(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()

    # When / Then
    with pytest.raises(
        InvalidAccountStateTransition,
        match="cannot archive account while status is active",
    ):
        service.archive_account(opened.account.id)


def test_rename_account_given_archived_account_raises_invalid_transition(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()
    service.close_account(opened.account.id)
    service.archive_account(opened.account.id)

    # When / Then
    with pytest.raises(
        InvalidAccountStateTransition,
        match="cannot rename account while status is archived",
    ):
        service.rename_account(opened.account.id, "Archived wallet")


def test_record_balance_snapshot_given_existing_account_updates_current_balance(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()

    # When
    updated = service.record_balance_snapshot(
        opened.account.id,
        250,
        checked_at=date(2026, 6, 19),
        reason="manual_check",
    )

    # Then
    assert updated.current_balance is not None
    assert updated.current_balance.balance_minor == 250
    assert updated.current_balance.reason == "manual_check"
    assert service.get_current_balance(opened.account.id) == updated.current_balance


def test_record_balance_snapshot_given_closed_account_raises_invalid_transition(
    service: AccountService,
    open_cash_account: Callable[..., AccountSummary],
) -> None:
    # Given
    opened = open_cash_account()
    service.close_account(opened.account.id)

    # When / Then
    with pytest.raises(
        InvalidAccountStateTransition,
        match="cannot record_balance_snapshot account while status is closed",
    ):
        service.record_balance_snapshot(opened.account.id, 250, reason="manual_check")
