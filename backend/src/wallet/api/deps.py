from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from wallet.application.accounts import AccountService
from wallet.application.income_categories import IncomeCategoryService
from wallet.application.spending_categories import SpendingCategoryService
from wallet.application.transactions import TransactionService
from wallet.bootstrap import seed_default_categories
from wallet.config import Settings, get_settings
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository
from wallet.ports.transactions import TransactionRepository


@dataclass(frozen=True, slots=True)
class AppContainer:
    settings: Settings
    accounts: InMemoryAccountRepository
    income_categories: InMemoryIncomeCategoryRepository
    spending_categories: InMemorySpendingCategoryRepository
    transactions: InMemoryTransactionRepository


def build_container(settings: Settings | None = None) -> AppContainer:
    accounts = InMemoryAccountRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    transactions = InMemoryTransactionRepository()
    seed_default_categories(spending_categories, income_categories)
    return AppContainer(
        settings=settings or get_settings(),
        accounts=accounts,
        income_categories=income_categories,
        spending_categories=spending_categories,
        transactions=transactions,
    )


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


ContainerDep = Annotated[AppContainer, Depends(get_container)]


def get_app_settings(container: ContainerDep) -> Settings:
    return container.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_account_repository(container: ContainerDep) -> AccountRepository:
    return container.accounts


AccountRepositoryDep = Annotated[AccountRepository, Depends(get_account_repository)]


def get_spending_category_repository(container: ContainerDep) -> SpendingCategoryRepository:
    return container.spending_categories


def get_income_category_repository(container: ContainerDep) -> IncomeCategoryRepository:
    return container.income_categories


SpendingCategoryRepositoryDep = Annotated[
    SpendingCategoryRepository,
    Depends(get_spending_category_repository),
]

IncomeCategoryRepositoryDep = Annotated[
    IncomeCategoryRepository,
    Depends(get_income_category_repository),
]


def get_transaction_repository(container: ContainerDep) -> TransactionRepository:
    return container.transactions


TransactionRepositoryDep = Annotated[
    TransactionRepository,
    Depends(get_transaction_repository),
]


def get_account_service(
    accounts: AccountRepositoryDep,
    transactions: TransactionRepositoryDep,
) -> AccountService:
    return AccountService(accounts=accounts, transactions=transactions)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


def get_spending_category_service(
    categories: SpendingCategoryRepositoryDep,
) -> SpendingCategoryService:
    return SpendingCategoryService(categories=categories)


SpendingCategoryServiceDep = Annotated[
    SpendingCategoryService,
    Depends(get_spending_category_service),
]


def get_income_category_service(
    categories: IncomeCategoryRepositoryDep,
) -> IncomeCategoryService:
    return IncomeCategoryService(categories=categories)


IncomeCategoryServiceDep = Annotated[
    IncomeCategoryService,
    Depends(get_income_category_service),
]


def get_transaction_service(
    accounts: AccountRepositoryDep,
    spending_categories: SpendingCategoryRepositoryDep,
    income_categories: IncomeCategoryRepositoryDep,
    transactions: TransactionRepositoryDep,
) -> TransactionService:
    return TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
    )


TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
