from __future__ import annotations

from collections.abc import Iterator
from importlib import import_module

import pytest
from fastapi.testclient import TestClient

from wallet.ai.capabilities.contract import CapabilityDefinition
from wallet.ai.control.routing import (
    ClarifyRouteDecision,
    MessageRoutingContext,
    RouteDecision,
    StartRouteDecision,
)
from wallet.api.app import create_app
from wallet.api.deps import AppContainer, build_app_container
from wallet.config import Settings

app_module = import_module("wallet.api.app")


class WalletStateRouter:
    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        if message == "Summary expense":
            return ClarifyRouteDecision(("transactions.capture", "wallet.current_state"))
        if message == "one more time":
            assert context.recent_capability_id == "wallet.current_state"
        return StartRouteDecision("wallet.current_state")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    def build_test_container(settings: Settings) -> AppContainer:
        return build_app_container(settings, message_router=WalletStateRouter())

    monkeypatch.setattr(app_module, "build_app_container", build_test_container)
    app = create_app(
        Settings(
            app_name="Wallet Test API",
            environment="test",
            seed_sample_data=False,
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def test_current_state_reads_explicitly_seeded_balances_without_mutating_wallet(
    client: TestClient,
) -> None:
    cash = _open_account(
        client,
        name="Cash",
        account_type="cash",
        currency="USD",
        opening_balance_minor=10_000,
    )
    savings = _open_account(
        client,
        name="Savings",
        account_type="bank_account",
        currency="USD",
        opening_balance_minor=25_000,
    )
    pesos = _open_account(
        client,
        name="Pesos",
        account_type="wallet",
        currency="ARS",
        opening_balance_minor=7_000,
    )
    archived = _open_account(
        client,
        name="Old card",
        account_type="credit_card",
        currency="ARS",
        opening_balance_minor=-3_000,
    )
    assert client.post(f"/api/v1/accounts/{archived['id']}/archive").status_code == 200
    groceries = client.post(
        "/api/v1/spending-categories",
        json={"name": "State test groceries"},
    ).json()
    expense = client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "occurred_on": "2026-08-05",
            "description": "Seeded groceries",
            "postings": [
                {
                    "account_id": cash["id"],
                    "amount_minor": -1_250,
                    "currency": "USD",
                },
                {
                    "category_id": groceries["id"],
                    "amount_minor": 1_250,
                    "currency": "USD",
                },
            ],
        },
    )
    assert expense.status_code == 201, expense.text
    transactions_before = client.get("/api/v1/transactions").json()

    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": "state-request-1",
            "input": {"kind": "message", "content": "Show my current balances"},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    expected_state = {
        "accounts": [
            {
                "id": cash["id"],
                "name": "Cash",
                "type": "cash",
                "currency": "USD",
                "balance_minor": 8_750,
            },
            {
                "id": pesos["id"],
                "name": "Pesos",
                "type": "wallet",
                "currency": "ARS",
                "balance_minor": 7_000,
            },
            {
                "id": savings["id"],
                "name": "Savings",
                "type": "bank_account",
                "currency": "USD",
                "balance_minor": 25_000,
            },
        ],
        "totals_by_currency": [
            {"currency": "ARS", "balance_minor": 7_000},
            {"currency": "USD", "balance_minor": 33_750},
        ],
    }
    assert payload["outcome"] == {
        "kind": "state_shown",
        "message": ("Current balances — Cash: USD 87.50; Pesos: ARS 70.00; Savings: USD 250.00."),
        "view": {
            "kind": "wallet_state",
            "data": expected_state,
            "available_actions": [],
        },
        "result": None,
    }
    assert payload["conversation"]["active_task"] is None
    assert payload["conversation"]["last_outcome"] == payload["outcome"]
    assert (
        client.get(f"/api/v1/conversations/{payload['conversation']['id']}").json()
        == payload["conversation"]
    )
    assert client.get("/api/v1/transactions").json() == transactions_before


def test_current_state_handles_a_wallet_with_no_active_accounts(client: TestClient) -> None:
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": "state-request-1",
            "input": {"kind": "message", "content": "Give me a wallet overview"},
        },
    )

    assert response.status_code == 200
    outcome = response.json()["outcome"]
    assert outcome["kind"] == "state_shown"
    assert outcome["message"] == "You have no active accounts."
    assert outcome["result"] is None
    assert outcome["view"]["data"] == {"accounts": [], "totals_by_currency": []}


def test_singular_show_balance_routes_to_current_state_without_starting_capture(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": "singular-balance-request",
            "input": {"kind": "message", "content": "show balance"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"]["kind"] == "state_shown"
    assert payload["outcome"]["view"]["kind"] == "wallet_state"
    assert payload["conversation"]["active_task"] is None


def test_reference_only_followup_repeats_the_recent_wallet_state_capability(
    client: TestClient,
) -> None:
    first = client.post(
        "/api/v1/turns",
        json={
            "request_id": "repeat-state-request-1",
            "input": {"kind": "message", "content": "show balance"},
        },
    )

    repeated = client.post(
        "/api/v1/turns",
        json={
            "request_id": "repeat-state-request-2",
            "conversation_id": first.json()["conversation"]["id"],
            "input": {"kind": "message", "content": "one more time"},
        },
    )

    assert repeated.status_code == 200
    assert repeated.json()["outcome"]["kind"] == "state_shown"
    assert repeated.json()["conversation"]["version"] == 2
    assert repeated.json()["conversation"]["active_task"] is None


def test_ambiguous_state_and_capture_request_stays_idle_until_clear_followup(
    client: TestClient,
) -> None:
    ambiguous = client.post(
        "/api/v1/turns",
        json={
            "request_id": "state-request-1",
            "input": {"kind": "message", "content": "Summary expense"},
        },
    )

    assert ambiguous.status_code == 200
    assert ambiguous.json()["outcome"]["kind"] == "clarify_idle_route"
    assert ambiguous.json()["conversation"]["active_task"] is None

    explicit = client.post(
        "/api/v1/turns",
        json={
            "request_id": "state-request-2",
            "conversation_id": ambiguous.json()["conversation"]["id"],
            "input": {"kind": "message", "content": "Show my current balances"},
        },
    )

    assert explicit.status_code == 200
    assert explicit.json()["outcome"]["kind"] == "state_shown"
    assert explicit.json()["conversation"]["active_task"] is None


def test_state_turn_replay_returns_original_snapshot_and_new_turn_reads_new_balance(
    client: TestClient,
) -> None:
    cash = _open_account(
        client,
        name="Cash",
        account_type="cash",
        currency="USD",
        opening_balance_minor=10_000,
    )
    request = {
        "request_id": "state-request-1",
        "input": {"kind": "message", "content": "Show my current balances"},
    }
    first = client.post(
        "/api/v1/turns",
        json=request,
    )
    adjustment = client.post(
        "/api/v1/transactions",
        json={
            "type": "adjustment",
            "occurred_on": "2026-08-06",
            "description": "External correction",
            "postings": [
                {
                    "account_id": cash["id"],
                    "amount_minor": 500,
                    "currency": "USD",
                }
            ],
        },
    )
    assert adjustment.status_code == 201, adjustment.text

    replay = client.post(
        "/api/v1/turns",
        json=request,
    )
    refreshed = client.post(
        "/api/v1/turns",
        json={
            "request_id": "state-request-2",
            "conversation_id": first.json()["conversation"]["id"],
            "input": {"kind": "message", "content": "Give me a wallet overview"},
        },
    )

    assert replay.json() == first.json()
    assert first.json()["outcome"]["view"]["data"]["accounts"][0]["balance_minor"] == 10_000
    assert refreshed.json()["outcome"]["view"]["data"]["accounts"][0]["balance_minor"] == 10_500
    assert refreshed.json()["conversation"]["version"] == 2


def _open_account(
    client: TestClient,
    *,
    name: str,
    account_type: str,
    currency: str,
    opening_balance_minor: int,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "type": account_type,
            "currency": currency,
            "opening_balance_minor": opening_balance_minor,
            "opened_on": "2026-08-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
