from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from wallet.api.app import create_app
from wallet.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(
        Settings(
            app_name="Wallet Test API",
            environment="test",
            debug=False,
            api_v1_prefix="/api/v1",
            frontend_host="http://localhost:5173",
        )
    )

    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_returns_status_payload(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "Wallet Test API",
        "environment": "test",
    }


def test_cors_preflight_allows_configured_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/cards",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_create_card_normalizes_values_and_returns_created_card(client: TestClient) -> None:
    response = client.post(
        "/api/v1/cards",
        json={
            "name": "  Daily card  ",
            "currency": "usd",
            "opened_on": "2026-06-18",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("card_")
    assert body["name"] == "Daily card"
    assert body["currency"] == "USD"
    assert body["balance"] == {"amount_minor": 0, "currency": "USD"}
    assert body["created_on"] == "2026-06-18"


def test_list_and_get_cards_persist_across_requests(client: TestClient) -> None:
    first = _issue_card(client, name="Daily card", currency="USD")
    second = _issue_card(client, name="Travel card", currency="EUR")

    list_response = client.get("/api/v1/cards")
    get_response = client.get(f"/api/v1/cards/{first['id']}")

    assert list_response.status_code == 200
    assert [card["id"] for card in list_response.json()] == [first["id"], second["id"]]
    assert get_response.status_code == 200
    assert get_response.json() == first


def test_deposit_and_withdraw_update_card_balance(client: TestClient) -> None:
    card = _issue_card(client, name="Main card", currency="USD")

    deposit_response = client.post(
        f"/api/v1/cards/{card['id']}/deposits",
        json={"amount_minor": 50_000, "currency": "USD"},
    )
    withdraw_response = client.post(
        f"/api/v1/cards/{card['id']}/withdrawals",
        json={"amount_minor": 24_500, "currency": "USD"},
    )

    assert deposit_response.status_code == 200
    assert deposit_response.json()["balance"] == {
        "amount_minor": 50_000,
        "currency": "USD",
    }
    assert withdraw_response.status_code == 200
    assert withdraw_response.json()["balance"] == {
        "amount_minor": 25_500,
        "currency": "USD",
    }


def test_missing_card_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/cards/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "card not found: missing"}


def test_insufficient_funds_returns_conflict(client: TestClient) -> None:
    card = _issue_card(client, name="Main card", currency="USD")

    response = client.post(
        f"/api/v1/cards/{card['id']}/withdrawals",
        json={"amount_minor": 100, "currency": "USD"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "insufficient funds"}


def test_currency_mismatch_returns_conflict(client: TestClient) -> None:
    card = _issue_card(client, name="Main card", currency="USD")

    response = client.post(
        f"/api/v1/cards/{card['id']}/deposits",
        json={"amount_minor": 100, "currency": "ARS"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "currency mismatch"}


def test_invalid_payload_returns_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/cards",
        json={"name": "   ", "currency": "USD"},
    )

    assert response.status_code == 422


def test_openapi_schema_exposes_tagged_routes_and_stable_operation_ids(
    client: TestClient,
) -> None:
    schema = client.app.openapi()

    assert schema["paths"]["/api/v1/health"]["get"]["tags"] == ["system"]
    assert schema["paths"]["/api/v1/health"]["get"]["operationId"] == "system-get_health"
    assert schema["paths"]["/api/v1/cards"]["get"]["tags"] == ["cards"]
    assert schema["paths"]["/api/v1/cards"]["get"]["operationId"] == "cards-list_cards"
    assert schema["paths"]["/api/v1/cards"]["post"]["operationId"] == "cards-create_card"
    assert (
        schema["paths"]["/api/v1/cards/{card_id}/deposits"]["post"]["operationId"]
        == "cards-deposit_to_card"
    )


def _issue_card(client: TestClient, *, name: str, currency: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/cards",
        json={"name": name, "currency": currency},
    )

    assert response.status_code == 201
    return response.json()
