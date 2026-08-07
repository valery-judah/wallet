from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from wallet.ai.control.engine import (
    ConversationProcessingError,
    InvalidTurnRequestError,
    TurnGuardConflictError,
)
from wallet.ai.control.registry import ConversationNotFoundError, RequestIdConflictError
from wallet.ai.llm import StructuredChatError
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
from wallet.observability import bind_log_context, configure_logging, error_details, log_event

from .deps import build_app_container
from .routes import api_router

logger = logging.getLogger(__name__)


def generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(
        resolved_settings.log_level,
        environment=resolved_settings.environment,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.container = build_app_container(resolved_settings)
        log_event(
            logger,
            logging.INFO,
            "application.started",
            data={"sample_data": resolved_settings.seed_sample_data},
        )
        try:
            yield
        finally:
            log_event(logger, logging.INFO, "application.stopped")

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
            expose_headers=["X-Trace-ID"],
        )
    _register_request_logging(app, api_prefix=resolved_settings.api_v1_prefix)
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    _register_exception_handlers(app)
    return app


def _register_request_logging(app: FastAPI, *, api_prefix: str) -> None:
    @app.middleware("http")
    async def log_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = uuid4().hex
        with bind_log_context(trace_id=trace_id, origin="api"):
            started_at = perf_counter()
            try:
                response = await call_next(request)
            except Exception as exc:
                log_event(
                    logger,
                    logging.ERROR,
                    "http.request.failed",
                    data={
                        "method": request.method,
                        "route": _route_template(request.scope, api_prefix=api_prefix),
                        "duration_ms": round(_duration_ms(started_at), 2),
                    },
                    error=error_details(exc, code="unexpected_error", retryable=False),
                    exc_info=exc,
                )
                raise

            response.headers["X-Trace-ID"] = trace_id
            if response.status_code >= 400:
                log_event(
                    logger,
                    logging.WARNING,
                    "http.request.rejected",
                    data={
                        "method": request.method,
                        "route": _route_template(request.scope, api_prefix=api_prefix),
                        "status_code": response.status_code,
                    },
                    error={
                        "type": "HttpResponseError",
                        "code": f"http_{response.status_code}",
                        "retryable": response.status_code >= 500,
                    },
                )
            log_event(
                logger,
                logging.WARNING if response.status_code >= 500 else logging.INFO,
                "http.request.completed",
                data={
                    "method": request.method,
                    "route": _route_template(request.scope, api_prefix=api_prefix),
                    "status_code": response.status_code,
                    "duration_ms": round(_duration_ms(started_at), 2),
                },
            )
            return response


def _route_template(scope: Mapping[str, Any], *, api_prefix: str) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    if not isinstance(path, str):
        return "<unmatched>"
    if path == api_prefix or path.startswith(f"{api_prefix}/"):
        return path
    return f"{api_prefix.rstrip('/')}/{path.lstrip('/')}"


def _duration_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1_000


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

    @app.exception_handler(ConversationNotFoundError)
    async def handle_conversation_not_found(
        request: Request,
        exc: ConversationNotFoundError,
    ) -> JSONResponse:
        conversation_id = exc.args[0] if exc.args else "unknown"
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"conversation not found: {conversation_id}",
        )

    @app.exception_handler(RequestIdConflictError)
    @app.exception_handler(TurnGuardConflictError)
    async def handle_turn_conflict(
        request: Request,
        exc: RequestIdConflictError | TurnGuardConflictError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    @app.exception_handler(InvalidTurnRequestError)
    async def handle_invalid_turn_request(
        request: Request,
        exc: InvalidTurnRequestError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    @app.exception_handler(ConversationProcessingError)
    async def handle_conversation_processing_error(
        request: Request,
        exc: ConversationProcessingError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Conversation processing is temporarily unavailable.",
        )

    @app.exception_handler(StructuredChatError)
    async def handle_structured_chat_error(
        request: Request,
        exc: StructuredChatError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Conversation processing is temporarily unavailable.",
        )


def _error_response(*, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})
