from __future__ import annotations

from datetime import date

from wallet.domain.accounts import Account, AccountType
from wallet.domain.money import Money
from wallet.infrastructure.memory import InMemoryAccountRepository


def test_in_memory_account_repository_stores_and_lists_accounts() -> None:
    repo = InMemoryAccountRepository()
    first = Account.open(
        id="account_1",
        name="Daily account",
        type=AccountType.CARD,
        currency="USD",
        current_balance=Money.zero("USD"),
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )
    second = Account.open(
        id="account_2",
        name="Travel cash",
        type=AccountType.CASH,
        currency="EUR",
        current_balance=Money.zero("EUR"),
        color_key=None,
        opened_on=date(2026, 6, 18),
        created_on=date(2026, 6, 18),
    )

    repo.add(first)
    repo.add(second)

    assert repo.get("account_1") == first
    assert repo.list() == [first, second]
