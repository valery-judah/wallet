from __future__ import annotations

from fastapi import APIRouter, Query, status

from wallet.application.accounts import ArchiveAccount, OpenAccount, UpdateAccountProfile
from wallet.application.income_categories import (
    CreateIncomeCategory,
    IncomeCategoryTreeNode,
    UpdateIncomeCategory,
)
from wallet.application.spending_categories import (
    CreateSpendingCategory,
    SpendingCategoryTreeNode,
    UpdateSpendingCategory,
)
from wallet.application.transactions import CreatePosting, CreateTransaction
from wallet.domain.accounts import AccountNotFoundError
from wallet.domain.income_categories import IncomeCategory
from wallet.domain.spending_categories import SpendingCategory
from wallet.domain.transactions import TransactionNotFoundError

from .deps import (
    AccountServiceDep,
    IncomeCategoryServiceDep,
    SettingsDep,
    SpendingCategoryServiceDep,
    TransactionServiceDep,
)
from .schemas import (
    AccountResponse,
    CreateAccountRequest,
    CreateIncomeCategoryRequest,
    CreateSpendingCategoryRequest,
    CreateTransactionRequest,
    HealthResponse,
    IncomeCategoryResponse,
    SpendingCategoryResponse,
    TransactionResponse,
    UpdateAccountProfileRequest,
    UpdateIncomeCategoryRequest,
    UpdateSpendingCategoryRequest,
)

api_router = APIRouter()
system_router = APIRouter(tags=["system"])
accounts_router = APIRouter(prefix="/accounts", tags=["accounts"])
spending_categories_router = APIRouter(
    prefix="/spending-categories",
    tags=["spending-categories"],
)
income_categories_router = APIRouter(
    prefix="/income-categories",
    tags=["income-categories"],
)
transactions_router = APIRouter(prefix="/transactions", tags=["transactions"])


@system_router.get("/health", response_model=HealthResponse)
def get_health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
    )


@accounts_router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    payload: CreateAccountRequest,
    service: AccountServiceDep,
) -> AccountResponse:
    account = service.open_account(
        OpenAccount(
            name=payload.name,
            type=payload.type,
            currency=payload.currency,
            opening_balance_minor=payload.opening_balance_minor,
            opened_on=payload.opened_on,
            color_key=payload.color_key,
        )
    )
    return AccountResponse.from_snapshot(account)


@accounts_router.get("", response_model=list[AccountResponse])
def list_accounts(service: AccountServiceDep) -> list[AccountResponse]:
    return [AccountResponse.from_snapshot(account) for account in service.list_accounts()]


@accounts_router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: str, service: AccountServiceDep) -> AccountResponse:
    account = service.get_account(account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return AccountResponse.from_snapshot(account)


@accounts_router.patch("/{account_id}", response_model=AccountResponse)
def update_account_profile(
    account_id: str,
    payload: UpdateAccountProfileRequest,
    service: AccountServiceDep,
) -> AccountResponse:
    account = service.update_account_profile(
        UpdateAccountProfile(
            account_id=account_id,
            name=payload.name,
            type=payload.type,
            color_key=payload.color_key,
        )
    )
    return AccountResponse.from_snapshot(account)


@accounts_router.post("/{account_id}/archive", response_model=AccountResponse)
def archive_account(
    account_id: str,
    service: AccountServiceDep,
) -> AccountResponse:
    account = service.archive_account(ArchiveAccount(account_id=account_id))
    return AccountResponse.from_snapshot(account)


@spending_categories_router.get("", response_model=list[SpendingCategoryResponse])
def list_spending_categories(service: SpendingCategoryServiceDep) -> list[SpendingCategoryResponse]:
    return [
        SpendingCategoryResponse.from_tree_node(node) for node in service.list_spending_categories()
    ]


@spending_categories_router.post(
    "",
    response_model=SpendingCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_spending_category(
    payload: CreateSpendingCategoryRequest,
    service: SpendingCategoryServiceDep,
) -> SpendingCategoryResponse:
    category = service.create_spending_category(
        CreateSpendingCategory(
            name=payload.name,
            parent_id=payload.parent_id,
            icon=payload.icon,
            color=payload.color,
            sort_order=payload.sort_order,
        )
    )
    return SpendingCategoryResponse.from_tree_node(_to_tree_node(category))


@spending_categories_router.patch(
    "/{category_id}",
    response_model=SpendingCategoryResponse,
)
def update_spending_category(
    category_id: str,
    payload: UpdateSpendingCategoryRequest,
    service: SpendingCategoryServiceDep,
) -> SpendingCategoryResponse:
    fields_set = payload.model_fields_set
    category = service.update_spending_category(
        UpdateSpendingCategory(
            category_id=category_id,
            name=payload.name,
            name_provided="name" in fields_set,
            parent_id=payload.parent_id,
            parent_id_provided="parent_id" in fields_set,
            icon=payload.icon,
            icon_provided="icon" in fields_set,
            color=payload.color,
            color_provided="color" in fields_set,
            sort_order=payload.sort_order,
            sort_order_provided="sort_order" in fields_set,
        )
    )
    return SpendingCategoryResponse.from_tree_node(_to_tree_node(category))


@income_categories_router.get("", response_model=list[IncomeCategoryResponse])
def list_income_categories(service: IncomeCategoryServiceDep) -> list[IncomeCategoryResponse]:
    return [
        IncomeCategoryResponse.from_tree_node(node) for node in service.list_income_categories()
    ]


@income_categories_router.post(
    "",
    response_model=IncomeCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_income_category(
    payload: CreateIncomeCategoryRequest,
    service: IncomeCategoryServiceDep,
) -> IncomeCategoryResponse:
    category = service.create_income_category(
        CreateIncomeCategory(
            name=payload.name,
            parent_id=payload.parent_id,
            icon=payload.icon,
            color=payload.color,
            sort_order=payload.sort_order,
        )
    )
    return IncomeCategoryResponse.from_tree_node(_to_income_tree_node(category))


@income_categories_router.patch(
    "/{category_id}",
    response_model=IncomeCategoryResponse,
)
def update_income_category(
    category_id: str,
    payload: UpdateIncomeCategoryRequest,
    service: IncomeCategoryServiceDep,
) -> IncomeCategoryResponse:
    fields_set = payload.model_fields_set
    category = service.update_income_category(
        UpdateIncomeCategory(
            category_id=category_id,
            name=payload.name,
            name_provided="name" in fields_set,
            parent_id=payload.parent_id,
            parent_id_provided="parent_id" in fields_set,
            icon=payload.icon,
            icon_provided="icon" in fields_set,
            color=payload.color,
            color_provided="color" in fields_set,
            sort_order=payload.sort_order,
            sort_order_provided="sort_order" in fields_set,
        )
    )
    return IncomeCategoryResponse.from_tree_node(_to_income_tree_node(category))


@transactions_router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: CreateTransactionRequest,
    service: TransactionServiceDep,
) -> TransactionResponse:
    transaction = service.create_transaction(
        CreateTransaction(
            type=payload.type,
            occurred_on=payload.occurred_on,
            description=payload.description,
            merchant_name=payload.merchant_name,
            notes=payload.notes,
            postings=tuple(
                CreatePosting(
                    account_id=posting.account_id,
                    category_id=posting.category_id,
                    amount_minor=posting.amount_minor,
                    currency=posting.currency,
                    memo=posting.memo,
                )
                for posting in payload.postings
            ),
        )
    )
    return TransactionResponse.from_domain(transaction)


@transactions_router.get("", response_model=list[TransactionResponse])
def list_transactions(
    service: TransactionServiceDep,
    account_id: str | None = Query(default=None),
) -> list[TransactionResponse]:
    return [
        TransactionResponse.from_domain(transaction)
        for transaction in service.list_transactions(account_id=account_id)
    ]


@transactions_router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: str,
    service: TransactionServiceDep,
) -> TransactionResponse:
    transaction = service.get_transaction(transaction_id)
    if transaction is None:
        raise TransactionNotFoundError(transaction_id)
    return TransactionResponse.from_domain(transaction)


api_router.include_router(system_router)
api_router.include_router(accounts_router)
api_router.include_router(spending_categories_router)
api_router.include_router(income_categories_router)
api_router.include_router(transactions_router)


def _to_tree_node(category: SpendingCategory) -> SpendingCategoryTreeNode:
    return SpendingCategoryTreeNode(category=category, children=())


def _to_income_tree_node(category: IncomeCategory) -> IncomeCategoryTreeNode:
    return IncomeCategoryTreeNode(category=category, children=())
