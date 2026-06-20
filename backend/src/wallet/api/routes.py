from __future__ import annotations

from fastapi import APIRouter, status

from wallet.application.cards import DepositToCard, IssueCard, WithdrawFromCard
from wallet.domain.cards import CardNotFoundError
from wallet.domain.money import Money

from .deps import CardServiceDep, SettingsDep
from .schemas import CardCreateRequest, CardResponse, HealthResponse, MoneyRequest

api_router = APIRouter()
system_router = APIRouter(tags=["system"])
cards_router = APIRouter(prefix="/cards", tags=["cards"])


@system_router.get("/health", response_model=HealthResponse)
def get_health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
    )


@cards_router.post(
    "",
    response_model=CardResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_card(payload: CardCreateRequest, service: CardServiceDep) -> CardResponse:
    card = service.issue_card(
        IssueCard(
            name=payload.name,
            currency=payload.currency,
            opened_on=payload.opened_on,
        )
    )
    return CardResponse.from_domain(card)


@cards_router.get("", response_model=list[CardResponse])
def list_cards(service: CardServiceDep) -> list[CardResponse]:
    return [CardResponse.from_domain(card) for card in service.list_cards()]


@cards_router.get("/{card_id}", response_model=CardResponse)
def get_card(card_id: str, service: CardServiceDep) -> CardResponse:
    card = service.get_card(card_id)
    if card is None:
        raise CardNotFoundError(card_id)
    return CardResponse.from_domain(card)


@cards_router.post("/{card_id}/deposits", response_model=CardResponse)
def deposit_to_card(
    card_id: str,
    payload: MoneyRequest,
    service: CardServiceDep,
) -> CardResponse:
    card = service.deposit_to_card(
        DepositToCard(
            card_id=card_id,
            amount=Money(
                amount_minor=payload.amount_minor,
                currency=payload.currency,
            ),
        )
    )
    return CardResponse.from_domain(card)


@cards_router.post("/{card_id}/withdrawals", response_model=CardResponse)
def withdraw_from_card(
    card_id: str,
    payload: MoneyRequest,
    service: CardServiceDep,
) -> CardResponse:
    card = service.withdraw_from_card(
        WithdrawFromCard(
            card_id=card_id,
            amount=Money(
                amount_minor=payload.amount_minor,
                currency=payload.currency,
            ),
        )
    )
    return CardResponse.from_domain(card)


api_router.include_router(system_router)
api_router.include_router(cards_router)
