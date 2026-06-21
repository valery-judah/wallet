from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from wallet.application.accounts import CreateAccountRejectedError, UpdateAccountRejectedError
from wallet.application.income_categories import (
    CreateIncomeCategoryRejectedError,
    UpdateIncomeCategoryRejectedError,
)
from wallet.application.spending_categories import (
    CreateSpendingCategoryRejectedError,
    UpdateSpendingCategoryRejectedError,
)
from wallet.application.transactions import CreateTransactionRejectedError
from wallet.config import Settings, get_settings
from wallet.domain.accounts import AccountClosedError, AccountNotFoundError
from wallet.domain.income_categories import IncomeCategoryNotFoundError
from wallet.domain.money import CurrencyMismatchError
from wallet.domain.spending_categories import SpendingCategoryNotFoundError
from wallet.domain.transactions import TransactionNotFoundError

from .deps import build_container
from .routes import api_router


def generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.container = build_container(resolved_settings)
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        openapi_url=f"{resolved_settings.api_v1_prefix}/openapi.json",
        generate_unique_id_function=generate_unique_id,
        lifespan=lifespan,
    )
    if resolved_settings.all_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.all_cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CreateAccountRejectedError)
    async def handle_create_account_rejected(
        request: Request,
        exc: CreateAccountRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(UpdateAccountRejectedError)
    async def handle_update_account_rejected(
        request: Request,
        exc: UpdateAccountRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(CreateSpendingCategoryRejectedError)
    async def handle_create_spending_category_rejected(
        request: Request,
        exc: CreateSpendingCategoryRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(UpdateSpendingCategoryRejectedError)
    async def handle_update_spending_category_rejected(
        request: Request,
        exc: UpdateSpendingCategoryRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(CreateIncomeCategoryRejectedError)
    async def handle_create_income_category_rejected(
        request: Request,
        exc: CreateIncomeCategoryRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(UpdateIncomeCategoryRejectedError)
    async def handle_update_income_category_rejected(
        request: Request,
        exc: UpdateIncomeCategoryRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(CreateTransactionRejectedError)
    async def handle_create_transaction_rejected(
        request: Request,
        exc: CreateTransactionRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(AccountNotFoundError)
    async def handle_account_not_found(
        request: Request,
        exc: AccountNotFoundError,
    ) -> JSONResponse:
        account_id = exc.args[0] if exc.args else "unknown"
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"account not found: {account_id}",
        )

    @app.exception_handler(SpendingCategoryNotFoundError)
    async def handle_spending_category_not_found(
        request: Request,
        exc: SpendingCategoryNotFoundError,
    ) -> JSONResponse:
        category_id = exc.args[0] if exc.args else "unknown"
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"spending category not found: {category_id}",
        )

    @app.exception_handler(IncomeCategoryNotFoundError)
    async def handle_income_category_not_found(
        request: Request,
        exc: IncomeCategoryNotFoundError,
    ) -> JSONResponse:
        category_id = exc.args[0] if exc.args else "unknown"
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"income category not found: {category_id}",
        )

    @app.exception_handler(TransactionNotFoundError)
    async def handle_transaction_not_found(
        request: Request,
        exc: TransactionNotFoundError,
    ) -> JSONResponse:
        transaction_id = exc.args[0] if exc.args else "unknown"
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"transaction not found: {transaction_id}",
        )

    @app.exception_handler(AccountClosedError)
    async def handle_account_closed(
        request: Request,
        exc: AccountClosedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    @app.exception_handler(CurrencyMismatchError)
    async def handle_currency_mismatch(
        request: Request,
        exc: CurrencyMismatchError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


def _error_response(*, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})
