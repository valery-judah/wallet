from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from itertools import count

from wallet.application.accounts import AccountService, ArchiveAccount, OpenAccount
from wallet.application.transactions import CreatePosting, CreateTransaction, TransactionService
from wallet.domain.accounts import AccountType
from wallet.domain.transactions import TransactionType
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository
from wallet.ports.transactions import TransactionRepository


@dataclass(frozen=True, slots=True)
class SampleAccountSeed:
    id: str
    name: str
    type: AccountType
    currency: str
    opened_on: date
    opening_balance_minor: int = 0
    color_key: str | None = None
    archived_on: date | None = None


@dataclass(frozen=True, slots=True)
class SamplePostingSeed:
    amount_minor: int
    currency: str
    account_id: str | None = None
    category_id: str | None = None
    memo: str | None = None


@dataclass(frozen=True, slots=True)
class SampleTransactionSeed:
    type: TransactionType
    occurred_on: date
    description: str
    postings: tuple[SamplePostingSeed, ...]
    merchant_name: str | None = None
    notes: str | None = None


SAMPLE_ACCOUNT_SEEDS: tuple[SampleAccountSeed, ...] = (
    SampleAccountSeed(
        id="sample_account_checking_ars",
        name="Daily checking",
        type=AccountType.BANK_ACCOUNT,
        currency="ARS",
        opened_on=date(2026, 5, 1),
        opening_balance_minor=180_000,
        color_key="emerald",
    ),
    SampleAccountSeed(
        id="sample_account_wallet_ars",
        name="Pocket wallet",
        type=AccountType.WALLET,
        currency="ARS",
        opened_on=date(2026, 5, 3),
        opening_balance_minor=25_000,
        color_key="amber",
    ),
    SampleAccountSeed(
        id="sample_account_cash_usd",
        name="USD cash",
        type=AccountType.CASH,
        currency="USD",
        opened_on=date(2026, 5, 8),
        opening_balance_minor=65_000,
        color_key="cyan",
    ),
    SampleAccountSeed(
        id="sample_account_archived_card",
        name="Old travel card",
        type=AccountType.CREDIT_CARD,
        currency="ARS",
        opened_on=date(2026, 4, 15),
        opening_balance_minor=-12_000,
        color_key="slate",
        archived_on=date(2026, 5, 28),
    ),
)

SAMPLE_TRANSACTION_SEEDS: tuple[SampleTransactionSeed, ...] = (
    SampleTransactionSeed(
        type=TransactionType.INCOME,
        occurred_on=date(2026, 6, 1),
        description="June payroll",
        merchant_name="Employer Inc.",
        notes="Monthly salary payment",
        postings=(
            SamplePostingSeed(
                account_id="sample_account_checking_ars",
                amount_minor=250_000,
                currency="ARS",
            ),
            SamplePostingSeed(
                category_id="income_salary_payroll",
                amount_minor=-250_000,
                currency="ARS",
            ),
        ),
    ),
    SampleTransactionSeed(
        type=TransactionType.EXPENSE,
        occurred_on=date(2026, 6, 2),
        description="Market and coffee",
        merchant_name="Corner Market",
        notes="Split across groceries and coffee",
        postings=(
            SamplePostingSeed(
                account_id="sample_account_checking_ars",
                amount_minor=-18_500,
                currency="ARS",
            ),
            SamplePostingSeed(
                category_id="category_food_groceries",
                amount_minor=15_000,
                currency="ARS",
            ),
            SamplePostingSeed(
                category_id="category_food_coffee",
                amount_minor=3_500,
                currency="ARS",
            ),
        ),
    ),
    SampleTransactionSeed(
        type=TransactionType.TRANSFER,
        occurred_on=date(2026, 6, 4),
        description="Cash top-up",
        notes="Move spending money into the wallet",
        postings=(
            SamplePostingSeed(
                account_id="sample_account_checking_ars",
                amount_minor=-40_000,
                currency="ARS",
            ),
            SamplePostingSeed(
                account_id="sample_account_wallet_ars",
                amount_minor=40_000,
                currency="ARS",
            ),
        ),
    ),
    SampleTransactionSeed(
        type=TransactionType.ADJUSTMENT,
        occurred_on=date(2026, 6, 6),
        description="Cash count correction",
        notes="Reflect the physical USD cash on hand",
        postings=(
            SamplePostingSeed(
                account_id="sample_account_cash_usd",
                amount_minor=5_000,
                currency="USD",
            ),
        ),
    ),
)


def seed_sample_data(
    accounts: AccountRepository,
    spending_categories: SpendingCategoryRepository,
    income_categories: IncomeCategoryRepository,
    transactions: TransactionRepository,
) -> None:
    if _has_user_accounts(accounts):
        return

    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        generate_account_id=_sequence_generator([seed.id for seed in SAMPLE_ACCOUNT_SEEDS]),
        generate_transaction_id=_counter_generator("sample_opening_transaction"),
        generate_posting_id=_counter_generator("sample_opening_posting"),
    )
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
        generate_transaction_id=_counter_generator("sample_transaction"),
        generate_posting_id=_counter_generator("sample_posting"),
    )

    for account_seed in SAMPLE_ACCOUNT_SEEDS:
        account_service.open_account(
            OpenAccount(
                name=account_seed.name,
                type=account_seed.type,
                currency=account_seed.currency,
                opening_balance_minor=account_seed.opening_balance_minor,
                opened_on=account_seed.opened_on,
                color_key=account_seed.color_key,
            )
        )
        if account_seed.archived_on is not None:
            account_service.archive_account(
                ArchiveAccount(
                    account_id=account_seed.id,
                    archived_on=account_seed.archived_on,
                )
            )

    for transaction_seed in SAMPLE_TRANSACTION_SEEDS:
        transaction_service.create_transaction(
            CreateTransaction(
                type=transaction_seed.type,
                occurred_on=transaction_seed.occurred_on,
                description=transaction_seed.description,
                merchant_name=transaction_seed.merchant_name,
                notes=transaction_seed.notes,
                postings=tuple(
                    CreatePosting(
                        account_id=posting.account_id,
                        category_id=posting.category_id,
                        amount_minor=posting.amount_minor,
                        currency=posting.currency,
                        memo=posting.memo,
                    )
                    for posting in transaction_seed.postings
                ),
            )
        )


def _has_user_accounts(accounts: AccountRepository) -> bool:
    return any(not account.is_system for account in accounts.list())


def _sequence_generator(values: list[str]) -> Callable[[], str]:
    iterator = iter(values)

    def next_value() -> str:
        try:
            return next(iterator)
        except StopIteration as exc:  # pragma: no cover - defensive only
            raise RuntimeError("sample seed id generator exhausted") from exc

    return next_value


def _counter_generator(prefix: str) -> Callable[[], str]:
    sequence = count(1)

    def next_value() -> str:
        return f"{prefix}_{next(sequence):03d}"

    return next_value


def list_sample_account_ids() -> list[str]:
    return [seed.id for seed in SAMPLE_ACCOUNT_SEEDS]


def get_sample_archived_account_id() -> str:
    archived_seed = next(seed for seed in SAMPLE_ACCOUNT_SEEDS if seed.archived_on is not None)
    return archived_seed.id


def get_sample_transfer_account_ids() -> tuple[str, str]:
    transfer = next(
        seed for seed in SAMPLE_TRANSACTION_SEEDS if seed.type is TransactionType.TRANSFER
    )
    account_ids = tuple(
        posting.account_id for posting in transfer.postings if posting.account_id is not None
    )
    if len(account_ids) != 2:  # pragma: no cover - fixture integrity guard
        raise RuntimeError("transfer seed must include exactly two account ids")
    return account_ids


def list_sample_transaction_types() -> list[TransactionType]:
    return [seed.type for seed in SAMPLE_TRANSACTION_SEEDS]
