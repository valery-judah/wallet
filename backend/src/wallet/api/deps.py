from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from wallet.application.accounts import AccountService
from wallet.config import Settings, get_settings
from wallet.infrastructure.memory import InMemoryAccountRepository
from wallet.ports.accounts import AccountRepository


@dataclass(frozen=True, slots=True)
class AppContainer:
    settings: Settings
    accounts: InMemoryAccountRepository


def build_container(settings: Settings | None = None) -> AppContainer:
    return AppContainer(
        settings=settings or get_settings(),
        accounts=InMemoryAccountRepository(),
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
