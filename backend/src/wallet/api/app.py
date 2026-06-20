from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from wallet.application.cards import CreateCardRejectedError
from wallet.config import Settings, get_settings
from wallet.domain.cards import CardNotFoundError, InsufficientFundsError
from wallet.domain.money import CurrencyMismatchError

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
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CreateCardRejectedError)
    async def handle_create_card_rejected(
        request: Request,
        exc: CreateCardRejectedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(CardNotFoundError)
    async def handle_card_not_found(
        request: Request,
        exc: CardNotFoundError,
    ) -> JSONResponse:
        card_id = exc.args[0] if exc.args else "unknown"
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"card not found: {card_id}",
        )

    @app.exception_handler(InsufficientFundsError)
    async def handle_insufficient_funds(
        request: Request,
        exc: InsufficientFundsError,
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
