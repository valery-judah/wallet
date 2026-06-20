from __future__ import annotations

from collections.abc import Callable
from datetime import date

import pytest

from wallet.accounts import AccountService, AccountSummary, OpenCashAccountRequest

OpenCashAccountRequestFactory = Callable[..., OpenCashAccountRequest]
OpenCashAccountFactory = Callable[..., AccountSummary]


@pytest.fixture
def service() -> AccountService:
    return AccountService()


@pytest.fixture
def make_open_cash_account_request() -> OpenCashAccountRequestFactory:
    def factory(
        *,
        name: str = "Wallet",
        opening_balance_minor: int = 100,
        currency: str = "ARS",
        opened_on: date | None = None,
    ) -> OpenCashAccountRequest:
        return OpenCashAccountRequest(
            name=name,
            opening_balance_minor=opening_balance_minor,
            currency=currency,
            opened_on=opened_on,
        )

    return factory


@pytest.fixture
def open_cash_account(
    service: AccountService,
    make_open_cash_account_request: OpenCashAccountRequestFactory,
) -> OpenCashAccountFactory:
    def factory(
        *,
        name: str = "Wallet",
        opening_balance_minor: int = 100,
        currency: str = "ARS",
        opened_on: date | None = None,
    ) -> AccountSummary:
        request = make_open_cash_account_request(
            name=name,
            opening_balance_minor=opening_balance_minor,
            currency=currency,
            opened_on=opened_on,
        )
        return service.open_account(request)

    return factory
