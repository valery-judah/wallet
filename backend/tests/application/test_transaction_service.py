from __future__ import annotations

import logging
from datetime import date

import pytest

from wallet.application.accounts import AccountService, ArchiveAccount, OpenAccount
from wallet.application.income_categories import CreateIncomeCategory, IncomeCategoryService
from wallet.application.spending_categories import CreateSpendingCategory, SpendingCategoryService
from wallet.application.transactions import (
    CreatePosting,
    CreateTransaction,
    CreateTransactionRejectedError,
    TransactionService,
)
from wallet.domain.accounts import AccountType
from wallet.domain.transactions import TransactionType
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)


def test_create_expense_transaction_updates_derived_balance() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        today=lambda: date(2026, 6, 20),
        generate_account_id=lambda: "account_main",
    )
    category_service = SpendingCategoryService(categories=spending_categories)
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
        today=lambda: date(2026, 6, 20),
        generate_transaction_id=lambda: "transaction_lunch",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2"]),
    )
    opened = account_service.open_account(
        OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )
    groceries = category_service.create_spending_category(
        CreateSpendingCategory(
            category_id="category_groceries",
            name="Groceries",
        )
    )

    transaction = transaction_service.create_transaction(
        CreateTransaction(
            type=TransactionType.EXPENSE,
            postings=(
                CreatePosting(
                    account_id=opened.account.id,
                    amount_minor=-1_200,
                    currency="USD",
                ),
                CreatePosting(
                    category_id=groceries.id,
                    amount_minor=1_200,
                    currency="USD",
                ),
            ),
            description="Lunch",
        )
    )

    updated = account_service.get_account(opened.account.id)
    assert transaction.id == "transaction_lunch"
    assert updated is not None
    assert updated.current_balance.amount_minor == -1_200


def test_create_transaction_operation_id_replays_same_command_and_rejects_change(
    caplog: pytest.LogCaptureFixture,
) -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account = AccountService(
        accounts=accounts,
        transactions=transactions,
        generate_account_id=lambda: "account_main",
    ).open_account(OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD"))
    category = SpendingCategoryService(categories=spending_categories).create_spending_category(
        CreateSpendingCategory(category_id="category_food", name="Food")
    )
    service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
        generate_transaction_id=lambda: "transaction_once",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2"]),
    )
    command = CreateTransaction(
        type=TransactionType.EXPENSE,
        postings=(
            CreatePosting(account_id=account.account.id, amount_minor=-500, currency="USD"),
            CreatePosting(category_id=category.id, amount_minor=500, currency="USD"),
        ),
    )
    caplog.set_level(logging.INFO, logger="wallet.application.transactions")

    first = service.create_transaction(command, operation_id="conversation:one:turn:two")
    replay = service.create_transaction(command, operation_id="conversation:one:turn:two")

    assert replay is first
    assert transactions.list() == [first]
    recorded_events = [
        record
        for record in caplog.records
        if getattr(record, "event", None) in {"transaction.recorded", "transaction.replayed"}
    ]
    assert [record.event for record in recorded_events] == [
        "transaction.recorded",
        "transaction.replayed",
    ]
    assert recorded_events[0].event_data["transaction_id"] == "transaction_once"
    assert recorded_events[1].event_data["operation_id"] == "conversation:one:turn:two"
    with pytest.raises(CreateTransactionRejectedError, match="already used"):
        service.create_transaction(
            CreateTransaction(
                type=TransactionType.EXPENSE,
                postings=(
                    CreatePosting(
                        account_id=account.account.id,
                        amount_minor=-600,
                        currency="USD",
                    ),
                    CreatePosting(category_id=category.id, amount_minor=600, currency="USD"),
                ),
            ),
            operation_id="conversation:one:turn:two",
        )
    assert any(
        getattr(record, "event", None) == "transaction.operation_conflict"
        for record in caplog.records
    )


def test_create_split_expense_transaction_accepts_multiple_spending_categories() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        today=lambda: date(2026, 6, 20),
        generate_account_id=lambda: "account_main",
    )
    category_service = SpendingCategoryService(categories=spending_categories)
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
        today=lambda: date(2026, 6, 20),
        generate_transaction_id=lambda: "transaction_split_expense",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2", "posting_3", "posting_4"]),
    )
    opened = account_service.open_account(
        OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )
    groceries = category_service.create_spending_category(
        CreateSpendingCategory(category_id="category_groceries", name="Groceries")
    )
    household = category_service.create_spending_category(
        CreateSpendingCategory(category_id="category_household", name="Household")
    )
    transport = category_service.create_spending_category(
        CreateSpendingCategory(category_id="category_transport", name="Transport")
    )

    transaction = transaction_service.create_transaction(
        CreateTransaction(
            type=TransactionType.EXPENSE,
            postings=(
                CreatePosting(
                    account_id=opened.account.id,
                    amount_minor=-1_200,
                    currency="USD",
                ),
                CreatePosting(
                    category_id=groceries.id,
                    amount_minor=600,
                    currency="USD",
                ),
                CreatePosting(
                    category_id=household.id,
                    amount_minor=400,
                    currency="USD",
                ),
                CreatePosting(
                    category_id=transport.id,
                    amount_minor=200,
                    currency="USD",
                ),
            ),
            description="Split expense",
        )
    )

    updated = account_service.get_account(opened.account.id)
    assert transaction.id == "transaction_split_expense"
    assert len(transaction.postings) == 4
    assert updated is not None
    assert updated.current_balance.amount_minor == -1_200


def test_create_transaction_rejects_spending_category_for_income() -> None:
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
    )
    opened = account_service.open_account(
        OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )
    expense_category = category_service.create_spending_category(
        CreateSpendingCategory(
            category_id="category_groceries",
            name="Groceries",
        )
    )

    with pytest.raises(
        CreateTransactionRejectedError,
        match="income transactions must use income categories",
    ):
        transaction_service.create_transaction(
            CreateTransaction(
                type=TransactionType.INCOME,
                postings=(
                    CreatePosting(
                        account_id=opened.account.id,
                        amount_minor=3_000,
                        currency="USD",
                    ),
                    CreatePosting(
                        category_id=expense_category.id,
                        amount_minor=-3_000,
                        currency="USD",
                    ),
                ),
            )
        )


def test_create_transaction_rejects_income_category_for_expense() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        generate_account_id=lambda: "account_main",
    )
    category_service = IncomeCategoryService(categories=income_categories)
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
    )
    opened = account_service.open_account(
        OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )
    income_category = category_service.create_income_category(
        CreateIncomeCategory(
            category_id="income_salary",
            name="Salary",
        )
    )

    with pytest.raises(
        CreateTransactionRejectedError,
        match="expense transactions must use spending categories",
    ):
        transaction_service.create_transaction(
            CreateTransaction(
                type=TransactionType.EXPENSE,
                postings=(
                    CreatePosting(
                        account_id=opened.account.id,
                        amount_minor=-3_000,
                        currency="USD",
                    ),
                    CreatePosting(
                        category_id=income_category.id,
                        amount_minor=3_000,
                        currency="USD",
                    ),
                ),
            )
        )


def test_create_adjustment_transaction_auto_adds_system_counterparty() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        generate_account_id=lambda: "account_main",
    )
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
        generate_transaction_id=lambda: "transaction_adjustment",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2"]),
    )
    opened = account_service.open_account(
        OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )

    transaction = transaction_service.create_transaction(
        CreateTransaction(
            type=TransactionType.ADJUSTMENT,
            postings=(
                CreatePosting(
                    account_id=opened.account.id,
                    amount_minor=500,
                    currency="USD",
                ),
            ),
            notes="Manual correction",
        )
    )

    assert len(transaction.postings) == 2
    assert any(posting.account_id == opened.account.id for posting in transaction.postings)
    assert any(posting.account_id == "system_equity_usd" for posting in transaction.postings)


def test_create_transaction_rejects_system_account_for_non_adjustments() -> None:
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
        generate_transaction_id=lambda: "transaction_adjustment",
        generate_posting_id=_sequential_ids(["posting_1", "posting_2", "posting_3", "posting_4"]),
    )
    opened = account_service.open_account(
        OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )
    category = category_service.create_spending_category(
        CreateSpendingCategory(category_id="category_food", name="Food")
    )
    transaction_service.create_transaction(
        CreateTransaction(
            type=TransactionType.ADJUSTMENT,
            postings=(
                CreatePosting(
                    account_id=opened.account.id,
                    amount_minor=500,
                    currency="USD",
                ),
            ),
        )
    )

    with pytest.raises(
        CreateTransactionRejectedError,
        match="system account postings are only allowed for adjustments",
    ):
        transaction_service.create_transaction(
            CreateTransaction(
                type=TransactionType.EXPENSE,
                postings=(
                    CreatePosting(
                        account_id="system_equity_usd",
                        amount_minor=-100,
                        currency="USD",
                    ),
                    CreatePosting(
                        category_id=category.id,
                        amount_minor=100,
                        currency="USD",
                    ),
                ),
            )
        )


def test_create_transfer_rejects_cross_currency_accounts() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        generate_account_id=_sequential_ids(["account_usd", "account_ars"]),
    )
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
    )
    usd_account = account_service.open_account(
        OpenAccount(name="USD account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )
    ars_account = account_service.open_account(
        OpenAccount(name="ARS account", type=AccountType.BANK_ACCOUNT, currency="ARS")
    )

    with pytest.raises(
        CreateTransactionRejectedError, match="transaction postings must use one currency"
    ):
        transaction_service.create_transaction(
            CreateTransaction(
                type=TransactionType.TRANSFER,
                postings=(
                    CreatePosting(
                        account_id=usd_account.account.id,
                        amount_minor=-100,
                        currency="USD",
                    ),
                    CreatePosting(
                        account_id=ars_account.account.id,
                        amount_minor=100,
                        currency="ARS",
                    ),
                ),
            )
        )


def test_archived_accounts_reject_new_transactions() -> None:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        today=lambda: date(2026, 6, 20),
        generate_account_id=lambda: "account_main",
    )
    category_service = SpendingCategoryService(categories=spending_categories)
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
        today=lambda: date(2026, 6, 20),
    )
    opened = account_service.open_account(
        OpenAccount(name="Main account", type=AccountType.BANK_ACCOUNT, currency="USD")
    )
    category = category_service.create_spending_category(
        CreateSpendingCategory(
            category_id="category_groceries",
            name="Groceries",
        )
    )
    account_service.archive_account(ArchiveAccount(account_id=opened.account.id))

    with pytest.raises(CreateTransactionRejectedError, match="account is archived"):
        transaction_service.create_transaction(
            CreateTransaction(
                type=TransactionType.EXPENSE,
                postings=(
                    CreatePosting(
                        account_id=opened.account.id,
                        amount_minor=-200,
                        currency="USD",
                    ),
                    CreatePosting(
                        category_id=category.id,
                        amount_minor=200,
                        currency="USD",
                    ),
                ),
            )
        )


def _sequential_ids(ids: list[str]):
    def factory() -> str:
        return ids.pop(0)

    return factory
