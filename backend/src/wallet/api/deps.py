from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from wallet.application.cards import CardService
from wallet.config import Settings, get_settings
from wallet.infrastructure.memory import InMemoryCardRepository
from wallet.ports.cards import CardRepository


@dataclass(frozen=True, slots=True)
class AppContainer:
    settings: Settings
    cards: InMemoryCardRepository


def build_container(settings: Settings | None = None) -> AppContainer:
    return AppContainer(
        settings=settings or get_settings(),
        cards=InMemoryCardRepository(),
    )


def get_container(request: Request) -> AppContainer:
    return cast(AppContainer, request.app.state.container)


ContainerDep = Annotated[AppContainer, Depends(get_container)]


def get_app_settings(container: ContainerDep) -> Settings:
    return container.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_card_repository(container: ContainerDep) -> CardRepository:
    return container.cards


CardRepositoryDep = Annotated[CardRepository, Depends(get_card_repository)]


def get_card_service(cards: CardRepositoryDep) -> CardService:
    return CardService(cards=cards)


CardServiceDep = Annotated[CardService, Depends(get_card_service)]
