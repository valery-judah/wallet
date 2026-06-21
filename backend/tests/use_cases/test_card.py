from __future__ import annotations

from wallet.application.accounts import AccountService, OpenAccount
from wallet.application.spending_categories import CreateSpendingCategory, SpendingCategoryService
from wallet.application.transactions import CreatePosting, CreateTransaction, TransactionService
from wallet.domain.accounts import AccountType
from wallet.domain.transactions import TransactionType
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)


def test_run_account_use_case_posts_expected_balance() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        generate_account_id=lambda: "account_main",
    )
    category_service = SpendingCategoryService(categories=spending_categories)
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
        generate_transaction_id=lambda: "transaction_groceries",
        generate_posting_id=lambda: "posting_fixed",
    )

    opened = account_service.open_account(
        OpenAccount(
            name="Main account",
            type=AccountType.DEBIT_CARD,
            currency="USD",
        )
    )
    groceries = category_service.create_spending_category(
        CreateSpendingCategory(
            category_id="category_food",
            name="Food",
        )
    )

    transaction_service.create_transaction(
        CreateTransaction(
            type=TransactionType.EXPENSE,
            postings=(
                CreatePosting(
                    account_id=opened.account.id,
                    amount_minor=-25_500,
                    currency="USD",
                ),
                CreatePosting(
                    category_id=groceries.id,
                    amount_minor=25_500,
                    currency="USD",
                ),
            ),
        )
    )

    updated = account_service.get_account(opened.account.id)

    assert updated is not None
    assert updated.account.name == "Main account"
    assert updated.account.currency == "USD"
    assert updated.current_balance.amount_minor == -25_500
