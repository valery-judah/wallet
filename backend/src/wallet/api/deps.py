from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from wallet.application.accounts import AccountService
from wallet.application.spending_categories import SpendingCategoryService
from wallet.bootstrap import seed_default_spending_categories
from wallet.config import Settings, get_settings
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemorySpendingCategoryRepository,
)
from wallet.ports.accounts import AccountRepository
from wallet.ports.spending_categories import SpendingCategoryRepository


@dataclass(frozen=True, slots=True)
class AppContainer:
    settings: Settings
    accounts: InMemoryAccountRepository
    spending_categories: InMemorySpendingCategoryRepository


def build_container(settings: Settings | None = None) -> AppContainer:
    accounts = InMemoryAccountRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    seed_default_spending_categories(spending_categories)
    return AppContainer(
        settings=settings or get_settings(),
        accounts=accounts,
        spending_categories=spending_categories,
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


def get_account_service(accounts: AccountRepositoryDep) -> AccountService:
    return AccountService(accounts=accounts)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


def get_spending_category_repository(container: ContainerDep) -> SpendingCategoryRepository:
    return container.spending_categories


SpendingCategoryRepositoryDep = Annotated[
    SpendingCategoryRepository,
    Depends(get_spending_category_repository),
]


def get_spending_category_service(
    categories: SpendingCategoryRepositoryDep,
) -> SpendingCategoryService:
    return SpendingCategoryService(categories=categories)


SpendingCategoryServiceDep = Annotated[
    SpendingCategoryService,
    Depends(get_spending_category_service),
]
