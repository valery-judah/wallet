from __future__ import annotations

from wallet.application.accounts import AccountService, CreditAccount, DebitAccount, OpenAccount
from wallet.domain.money import Money


def test_run_account_use_case_posts_expected_balance() -> None:
    service = AccountService(generate_account_id=lambda: "account_main")
    account = service.open_account(
        OpenAccount(
            name="Main account",
            currency="USD",
        )
    )

    service.credit_account(
        CreditAccount(
            account_id=account.id,
            amount=Money(amount_minor=50_000, currency="USD"),
        )
    )
    service.debit_account(
        DebitAccount(
            account_id=account.id,
            amount=Money(amount_minor=4_500, currency="USD"),
        )
    )
    updated = service.debit_account(
        DebitAccount(
            account_id=account.id,
            amount=Money(amount_minor=20_000, currency="USD"),
        )
    )

    assert updated.name == "Main account"
    assert updated.currency == "USD"
    assert updated.current_balance == Money(amount_minor=25_500, currency="USD")
