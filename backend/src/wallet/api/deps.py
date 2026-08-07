from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from wallet.ai.control.composition import (
    build_conversation_controller,
    build_default_message_router,
)
from wallet.ai.control.controller import ConversationController
from wallet.ai.control.routing import MessageRouter
from wallet.ai.transaction_capture.composition import (
    build_default_contribution_processor_factory,
    build_transaction_capture_capability,
)
from wallet.ai.transaction_capture.ports import ContributionProcessorFactory
from wallet.ai.wallet_state import CurrentWalletStateCapability
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
from wallet.observability import (
    bind_log_context,
    error_details,
    log_event,
    suppress_domain_success_events,
)
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository
from wallet.ports.transactions import TransactionRepository

logger = logging.getLogger(__name__)


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
    conversation_controller: ConversationController


def build_app_container(
    settings: Settings | None = None,
    *,
    capture_processor_factory: ContributionProcessorFactory | None = None,
    message_router: MessageRouter | None = None,
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
    with bind_log_context(origin="bootstrap"), suppress_domain_success_events():
        try:
            seed_default_categories(spending_categories, income_categories)
            if resolved_settings.seed_sample_data:
                seed_sample_data(
                    accounts,
                    spending_categories,
                    income_categories,
                    transactions,
                )
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "bootstrap.failed",
                data={"sample_data": resolved_settings.seed_sample_data},
                error=error_details(exc, code="bootstrap_failed", retryable=False),
                exc_info=exc,
            )
            raise
        log_event(
            logger,
            logging.INFO,
            "bootstrap.completed",
            data={
                "spending_category_count": len(spending_categories.list()),
                "income_category_count": len(income_categories.list()),
                "sample_account_count": len(
                    [account for account in accounts.list() if not account.is_system]
                ),
                "sample_transaction_count": len(transactions.list()),
                "sample_data": resolved_settings.seed_sample_data,
            },
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
    resolved_message_router = message_router or build_default_message_router(resolved_settings)
    transaction_capture = build_transaction_capture_capability(
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
        conversation_controller=build_conversation_controller(
            transaction_capture,
            CurrentWalletStateCapability(accounts=account_service),
            resolved_message_router,
        ),
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


def get_conversation_controller(container: ContainerDep) -> ConversationController:
    return container.conversation_controller


ConversationControllerDep = Annotated[
    ConversationController,
    Depends(get_conversation_controller),
]
