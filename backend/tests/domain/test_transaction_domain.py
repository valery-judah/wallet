from __future__ import annotations

from datetime import date

import pytest

from wallet.domain.transactions import Posting, Transaction, TransactionStatus, TransactionType


def test_transaction_requires_balanced_postings() -> None:
    with pytest.raises(ValueError, match="balance to zero"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Lunch",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.EXPENSE,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=-1200,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id=None,
                    category_id="category_food",
                    amount_minor=1100,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_posting_requires_exactly_one_target() -> None:
    with pytest.raises(ValueError, match="exactly one account or category"):
        Posting(
            id="posting_1",
            transaction_id="transaction_1",
            account_id="account_1",
            category_id="category_food",
            amount_minor=100,
            currency="USD",
        )


def test_transfer_rejects_category_postings() -> None:
    with pytest.raises(ValueError, match="only account postings"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Bad transfer",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.TRANSFER,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=-100,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id=None,
                    category_id="category_food",
                    amount_minor=100,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_transfer_requires_exactly_two_account_postings() -> None:
    with pytest.raises(ValueError, match="exactly two account postings"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Three-way transfer",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.TRANSFER,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=-200,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id="account_2",
                    category_id=None,
                    amount_minor=100,
                    currency="USD",
                ),
                Posting(
                    id="posting_3",
                    transaction_id="transaction_1",
                    account_id="account_3",
                    category_id=None,
                    amount_minor=100,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_transaction_requires_at_least_two_postings() -> None:
    with pytest.raises(ValueError, match="at least two postings"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Opening balance",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.ADJUSTMENT,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=100,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_transaction_requires_one_currency() -> None:
    with pytest.raises(ValueError, match="one currency"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Cross currency",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.TRANSFER,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=-100,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id="account_2",
                    category_id=None,
                    amount_minor=100,
                    currency="EUR",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_expense_requires_negative_account_and_positive_category_amounts() -> None:
    with pytest.raises(ValueError, match="expense account postings must be negative"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Backward lunch",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.EXPENSE,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=1200,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id=None,
                    category_id="category_food",
                    amount_minor=-1200,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_expense_allows_multiple_category_postings() -> None:
    transaction = Transaction(
        id="transaction_1",
        occurred_on=date(2026, 6, 20),
        posted_on=date(2026, 6, 20),
        description="Split groceries run",
        merchant_name=None,
        notes=None,
        status=TransactionStatus.POSTED,
        type=TransactionType.EXPENSE,
        postings=(
            Posting(
                id="posting_1",
                transaction_id="transaction_1",
                account_id="account_1",
                category_id=None,
                amount_minor=-1200,
                currency="USD",
            ),
            Posting(
                id="posting_2",
                transaction_id="transaction_1",
                account_id=None,
                category_id="category_food",
                amount_minor=600,
                currency="USD",
            ),
            Posting(
                id="posting_3",
                transaction_id="transaction_1",
                account_id=None,
                category_id="category_household",
                amount_minor=400,
                currency="USD",
            ),
            Posting(
                id="posting_4",
                transaction_id="transaction_1",
                account_id=None,
                category_id="category_transport",
                amount_minor=200,
                currency="USD",
            ),
        ),
        created_on=date(2026, 6, 20),
        updated_on=date(2026, 6, 20),
    )

    assert len(transaction.postings) == 4


def test_expense_requires_at_least_one_category_posting() -> None:
    with pytest.raises(ValueError, match="at least one category posting"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Bad expense",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.EXPENSE,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=-1200,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id="account_2",
                    category_id=None,
                    amount_minor=1200,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_income_requires_positive_account_and_negative_category_amounts() -> None:
    with pytest.raises(ValueError, match="income account postings must be positive"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Backward salary",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.INCOME,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=-3000,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id=None,
                    category_id="income_salary",
                    amount_minor=3000,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )


def test_adjustment_rejects_category_postings() -> None:
    with pytest.raises(ValueError, match="only account postings"):
        Transaction(
            id="transaction_1",
            occurred_on=date(2026, 6, 20),
            posted_on=date(2026, 6, 20),
            description="Bad adjustment",
            merchant_name=None,
            notes=None,
            status=TransactionStatus.POSTED,
            type=TransactionType.ADJUSTMENT,
            postings=(
                Posting(
                    id="posting_1",
                    transaction_id="transaction_1",
                    account_id="account_1",
                    category_id=None,
                    amount_minor=500,
                    currency="USD",
                ),
                Posting(
                    id="posting_2",
                    transaction_id="transaction_1",
                    account_id=None,
                    category_id="category_food",
                    amount_minor=-500,
                    currency="USD",
                ),
            ),
            created_on=date(2026, 6, 20),
            updated_on=date(2026, 6, 20),
        )
