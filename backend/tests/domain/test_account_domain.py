from __future__ import annotations

from datetime import date

import pytest

from wallet.domain.accounts import (
    Account,
    AccountClosedError,
    AccountType,
)


def test_open_account_given_valid_inputs_tracks_archive_state() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.DEBIT_CARD,
        currency=" usd ",
        color_key="violet",
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    assert account.id == "account_test"
    assert account.name == "Daily account"
    assert account.type is AccountType.DEBIT_CARD
    assert account.currency == "USD"
    assert account.archived_at is None
    assert account.color_key == "violet"


def test_account_update_profile_changes_type_and_metadata() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.DEBIT_CARD,
        currency="USD",
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    account.update_profile(
        name="Reserve fund",
        type=AccountType.BANK_ACCOUNT,
        color_key="emerald",
        updated_on=date(2026, 6, 19),
    )

    assert account.name == "Reserve fund"
    assert account.type is AccountType.BANK_ACCOUNT
    assert account.color_key == "emerald"
    assert account.updated_on == date(2026, 6, 19)


def test_archived_account_rejects_transactions() -> None:
    account = Account.open(
        id="account_test",
        name="Daily account",
        type=AccountType.DEBIT_CARD,
        currency="USD",
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )
    account.archive(archived_on=date(2026, 6, 19))

    assert account.archived_at == date(2026, 6, 19)

    with pytest.raises(AccountClosedError, match="account is archived"):
        account.assert_allows_transactions()
