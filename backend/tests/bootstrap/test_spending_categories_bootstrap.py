from __future__ import annotations

from wallet.api.deps import build_container
from wallet.application.accounts import AccountService, OpenAccount
from wallet.bootstrap.sample_data import seed_sample_data
from wallet.bootstrap.spending_categories import (
    seed_default_categories,
    seed_default_income_categories,
    seed_default_spending_categories,
)
from wallet.config import Settings
from wallet.domain.transactions import TransactionType
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)


def test_seed_default_spending_categories_populates_empty_repository() -> None:
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()

    seed_default_categories(spending_categories, income_categories)

    expense_roots = [
        category.name for category in spending_categories.list() if category.parent_id is None
    ]
    income_roots = [
        category.name for category in income_categories.list() if category.parent_id is None
    ]
    assert expense_roots == [
        "Food",
        "Housing",
        "Transport",
        "Shopping",
        "Health",
        "Entertainment",
        "Travel",
        "Education",
        "Personal",
        "Pets",
        "Fees",
        "Gifts & Donations",
        "Taxes",
        "Other",
    ]
    assert income_roots == [
        "Salary",
        "Business",
        "Investments",
        "Other income",
    ]
    assert spending_categories.get("category_food") is not None
    assert spending_categories.get("category_food_groceries") is not None
    assert income_categories.get("income_salary") is not None


def test_seed_default_spending_categories_is_noop_for_non_empty_repository() -> None:
    categories = InMemorySpendingCategoryRepository()
    seed_default_spending_categories(categories)
    original_ids = [category.id for category in categories.list()]

    seed_default_spending_categories(categories)

    assert [category.id for category in categories.list()] == original_ids


def test_seed_default_income_categories_is_noop_for_non_empty_repository() -> None:
    categories = InMemoryIncomeCategoryRepository()
    seed_default_income_categories(categories)
    original_ids = [category.id for category in categories.list()]

    seed_default_income_categories(categories)

    assert [category.id for category in categories.list()] == original_ids


def test_build_container_seeds_categories_during_container_creation() -> None:
    container = build_container(
        Settings(
            app_name="Wallet Test API",
            environment="test",
            debug=False,
            api_v1_prefix="/api/v1",
            frontend_host="http://localhost:5173",
        )
    )

    assert container.spending_categories.get("category_food") is not None
    assert container.spending_categories.get("category_food_groceries") is not None
    assert container.income_categories.get("income_salary") is not None


def test_seed_sample_data_populates_accounts_and_transactions() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()

    seed_default_categories(spending_categories, income_categories)
    seed_sample_data(accounts, spending_categories, income_categories, transactions)

    user_accounts = [account for account in accounts.list() if not account.is_system]
    archived_accounts = [account for account in user_accounts if account.archived_at is not None]

    assert [account.id for account in user_accounts] == [
        "sample_account_checking_ars",
        "sample_account_wallet_ars",
        "sample_account_cash_usd",
        "sample_account_archived_card",
    ]
    assert [account.id for account in archived_accounts] == ["sample_account_archived_card"]
    assert [transaction.type for transaction in transactions.list()] == [
        TransactionType.ADJUSTMENT,
        TransactionType.ADJUSTMENT,
        TransactionType.ADJUSTMENT,
        TransactionType.ADJUSTMENT,
        TransactionType.INCOME,
        TransactionType.EXPENSE,
        TransactionType.TRANSFER,
        TransactionType.ADJUSTMENT,
    ]


def test_seed_sample_data_is_noop_when_user_accounts_already_exist() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()

    seed_default_categories(spending_categories, income_categories)
    AccountService(accounts=accounts, transactions=transactions).open_account(
        OpenAccount(name="Existing account", type="cash", currency="ARS")
    )

    seed_sample_data(accounts, spending_categories, income_categories, transactions)

    user_accounts = [account for account in accounts.list() if not account.is_system]
    assert [account.name for account in user_accounts] == ["Existing account"]
    assert transactions.list() == []


def test_build_container_seeds_categories_before_sample_data() -> None:
    container = build_container(
        Settings(
            app_name="Wallet Test API",
            environment="test",
            debug=False,
            api_v1_prefix="/api/v1",
            frontend_host="http://localhost:5173",
            seed_sample_data=True,
        )
    )

    assert container.spending_categories.get("category_food_groceries") is not None
    assert container.income_categories.get("income_salary_payroll") is not None
    assert container.transactions.list()
