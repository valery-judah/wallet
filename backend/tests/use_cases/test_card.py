from __future__ import annotations

from wallet.application.cards import CardService, DepositToCard, IssueCard, WithdrawFromCard
from wallet.domain.money import Money


def test_run_card_use_case_posts_expected_balance() -> None:
    service = CardService(generate_card_id=lambda: "card_main")
    card = service.issue_card(
        IssueCard(
            name="Main card",
            currency="USD",
        )
    )

    service.deposit_to_card(
        DepositToCard(
            card_id=card.id,
            amount=Money(amount_minor=50_000, currency="USD"),
        )
    )
    service.withdraw_from_card(
        WithdrawFromCard(
            card_id=card.id,
            amount=Money(amount_minor=4_500, currency="USD"),
        )
    )
    updated = service.withdraw_from_card(
        WithdrawFromCard(
            card_id=card.id,
            amount=Money(amount_minor=20_000, currency="USD"),
        )
    )

    assert updated.name == "Main card"
    assert updated.currency == "USD"
    assert updated.balance == Money(amount_minor=25_500, currency="USD")
