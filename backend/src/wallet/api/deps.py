from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from wallet.ai.transaction_capture.composition import (
    build_capture_workflow,
    build_default_contribution_processor_factory,
)
from wallet.ai.transaction_capture.ports import ContributionProcessorFactory
from wallet.ai.transaction_capture.workflow import CaptureWorkflow
from wallet.application.accounts import AccountService
from wallet.application.income_categories import IncomeCategoryService
from wallet.application.spending_categories import SpendingCategoryService
from wallet.application.transactions import TransactionService
from wallet.bootstrap import seed_default_categories, seed_sample_data
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

from .capture_presenter import CapturePresenter


@dataclass(frozen=True, slots=True)
class AppContainer:
    """Process-local dependency graph shared by the API and in-process tools."""

    settings: Settings
    accounts: InMemoryAccountRepository
    income_categories: InMemoryIncomeCategoryRepository
    spending_categories: InMemorySpendingCategoryRepository
    transactions: InMemoryTransactionRepository
    account_service: AccountService
    transaction_service: TransactionService
    capture_workflow: CaptureWorkflow


def build_app_container(
    settings: Settings | None = None,
    *,
    capture_processor_factory: ContributionProcessorFactory | None = None,
) -> AppContainer:
    """Assemble and initialize the process-local application dependency graph.

    Construction creates fresh in-memory repositories and always seeds the default
    spending and income categories. When ``settings.seed_sample_data`` is enabled,
    it also seeds the sample accounts and historical transactions before wiring the
    shared application services and workflows. It starts no server and makes no
    Ollama request.
    """
    resolved_settings = settings or get_settings()
    accounts = InMemoryAccountRepository()
    income_categories = InMemoryIncomeCategoryRepository()
    spending_categories = InMemorySpendingCategoryRepository()
    transactions = InMemoryTransactionRepository()
    seed_default_categories(spending_categories, income_categories)
    if resolved_settings.seed_sample_data:
        seed_sample_data(
            accounts,
            spending_categories,
            income_categories,
            transactions,
        )
    account_service = AccountService(accounts=accounts, transactions=transactions)
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
    )
    resolved_capture_processor_factory = (
        capture_processor_factory or build_default_contribution_processor_factory(resolved_settings)
    )
    capture_workflow = build_capture_workflow(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transaction_service,
        processor_factory=resolved_capture_processor_factory,
    )
    return AppContainer(
        settings=resolved_settings,
        accounts=accounts,
        income_categories=income_categories,
        spending_categories=spending_categories,
        transactions=transactions,
        account_service=account_service,
        transaction_service=transaction_service,
        capture_workflow=capture_workflow,
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


def get_account_service(container: ContainerDep) -> AccountService:
    return container.account_service


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


def get_transaction_service(container: ContainerDep) -> TransactionService:
    return container.transaction_service


TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]


def get_capture_workflow(container: ContainerDep) -> CaptureWorkflow:
    return container.capture_workflow


CaptureWorkflowDep = Annotated[CaptureWorkflow, Depends(get_capture_workflow)]


def get_capture_presenter(container: ContainerDep) -> CapturePresenter:
    return CapturePresenter(
        accounts=container.accounts,
        spending_categories=container.spending_categories,
        income_categories=container.income_categories,
        transactions=container.transaction_service,
    )


CapturePresenterDep = Annotated[CapturePresenter, Depends(get_capture_presenter)]
