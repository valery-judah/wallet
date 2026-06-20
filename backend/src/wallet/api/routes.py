from __future__ import annotations

from fastapi import APIRouter, status

from wallet.application.accounts import (
    CloseAccount,
    CreditAccount,
    DebitAccount,
    OpenAccount,
    UpdateAccountProfile,
)
from wallet.domain.accounts import AccountNotFoundError
from wallet.domain.money import Money

from .deps import AccountServiceDep, SettingsDep
from .schemas import (
    AccountResponse,
    CreateAccountRequest,
    HealthResponse,
    MoneyRequest,
    UpdateAccountProfileRequest,
)

api_router = APIRouter()
system_router = APIRouter(tags=["system"])
accounts_router = APIRouter(prefix="/accounts", tags=["accounts"])


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


api_router.include_router(system_router)
api_router.include_router(accounts_router)
