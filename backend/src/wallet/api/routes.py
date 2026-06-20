from __future__ import annotations

from fastapi import APIRouter, status

from wallet.application.accounts import (
    CloseAccount,
    CreditAccount,
    DebitAccount,
    OpenAccount,
    UpdateAccountProfile,
)
from wallet.application.spending_categories import (
    CreateSpendingCategory,
    SpendingCategoryTreeNode,
    UpdateSpendingCategory,
)
from wallet.domain.accounts import AccountNotFoundError
from wallet.domain.money import Money
from wallet.domain.spending_categories import SpendingCategory

from .deps import AccountServiceDep, SettingsDep, SpendingCategoryServiceDep
from .schemas import (
    AccountResponse,
    CreateAccountRequest,
    CreateSpendingCategoryRequest,
    HealthResponse,
    MoneyRequest,
    SpendingCategoryResponse,
    UpdateAccountProfileRequest,
    UpdateSpendingCategoryRequest,
)

api_router = APIRouter()
system_router = APIRouter(tags=["system"])
accounts_router = APIRouter(prefix="/accounts", tags=["accounts"])
spending_categories_router = APIRouter(
    prefix="/spending-categories",
    tags=["spending-categories"],
)


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
            current_balance_minor=payload.current_balance_minor,
            opened_on=payload.opened_on,
            color_key=payload.color_key,
        )
    )
    return AccountResponse.from_domain(account)


@accounts_router.get("", response_model=list[AccountResponse])
def list_accounts(service: AccountServiceDep) -> list[AccountResponse]:
    return [AccountResponse.from_domain(account) for account in service.list_accounts()]


@accounts_router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: str, service: AccountServiceDep) -> AccountResponse:
    account = service.get_account(account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return AccountResponse.from_domain(account)


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
    return AccountResponse.from_domain(account)


@accounts_router.post("/{account_id}/deposits", response_model=AccountResponse)
def deposit_to_account(
    account_id: str,
    payload: MoneyRequest,
    service: AccountServiceDep,
) -> AccountResponse:
    account = service.credit_account(
        CreditAccount(
            account_id=account_id,
            amount=Money(
                amount_minor=payload.amount_minor,
                currency=payload.currency,
            ),
        )
    )
    return AccountResponse.from_domain(account)


@accounts_router.post("/{account_id}/withdrawals", response_model=AccountResponse)
def withdraw_from_account(
    account_id: str,
    payload: MoneyRequest,
    service: AccountServiceDep,
) -> AccountResponse:
    account = service.debit_account(
        DebitAccount(
            account_id=account_id,
            amount=Money(
                amount_minor=payload.amount_minor,
                currency=payload.currency,
            ),
        )
    )
    return AccountResponse.from_domain(account)


@accounts_router.post("/{account_id}/close", response_model=AccountResponse)
def close_account(
    account_id: str,
    service: AccountServiceDep,
) -> AccountResponse:
    account = service.close_account(CloseAccount(account_id=account_id))
    return AccountResponse.from_domain(account)


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


api_router.include_router(system_router)
api_router.include_router(accounts_router)
api_router.include_router(spending_categories_router)


def _to_tree_node(category: SpendingCategory) -> SpendingCategoryTreeNode:
    return SpendingCategoryTreeNode(category=category, children=())
