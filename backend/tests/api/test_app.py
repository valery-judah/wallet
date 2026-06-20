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
        "/api/v1/accounts",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in response.headers


def test_cors_preflight_allows_loopback_twin_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/accounts",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert "access-control-allow-credentials" not in response.headers


def test_cors_preflight_rejects_unconfigured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/accounts",
        headers={
            "Origin": "http://192.168.1.10:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_create_account_normalizes_values_and_returns_created_account(client: TestClient) -> None:
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": "  Daily account  ",
            "type": "cash",
            "currency": "usd",
            "current_balance_minor": 500,
            "color_key": "emerald",
            "icon_key": "wallet",
            "opened_on": "2026-06-18",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("account_")
    assert body["name"] == "Daily account"
    assert body["type"] == "cash"
    assert body["currency"] == "USD"
    assert body["current_balance"] == {"amount_minor": 500, "currency": "USD"}
    assert body["status"] == "active"
    assert body["color_key"] == "emerald"
    assert body["icon_key"] == "wallet"
    assert body["opened_on"] == "2026-06-18"
    assert body["closed_on"] is None
    assert body["created_on"] == "2026-06-18"
    assert body["updated_on"] == "2026-06-18"


def test_list_and_get_accounts_persist_across_requests(client: TestClient) -> None:
    first = _open_account(client, name="Daily account", type="card", currency="USD")
    second = _open_account(client, name="Travel cash", type="cash", currency="EUR")

    list_response = client.get("/api/v1/accounts")
    get_response = client.get(f"/api/v1/accounts/{first['id']}")

    assert list_response.status_code == 200
    assert [account["id"] for account in list_response.json()] == [first["id"], second["id"]]
    assert get_response.status_code == 200
    assert get_response.json() == first


def test_deposit_and_withdraw_update_account_balance(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank", currency="USD")

    deposit_response = client.post(
        f"/api/v1/accounts/{account['id']}/deposits",
        json={"amount_minor": 50_000, "currency": "USD"},
    )
    withdraw_response = client.post(
        f"/api/v1/accounts/{account['id']}/withdrawals",
        json={"amount_minor": 24_500, "currency": "USD"},
    )

    assert deposit_response.status_code == 200
    assert deposit_response.json()["current_balance"] == {
        "amount_minor": 50_000,
        "currency": "USD",
    }
    assert withdraw_response.status_code == 200
    assert withdraw_response.json()["current_balance"] == {
        "amount_minor": 25_500,
        "currency": "USD",
    }


def test_update_account_profile_persists_new_type_and_display_metadata(
    client: TestClient,
) -> None:
    account = _open_account(client, name="Main account", type="card", currency="USD")

    response = client.patch(
        f"/api/v1/accounts/{account['id']}",
        json={
            "name": "Travel wallet",
            "type": "wallet",
            "color_key": "cyan",
            "icon_key": "wallet",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Travel wallet"
    assert response.json()["type"] == "wallet"
    assert response.json()["color_key"] == "cyan"
    assert response.json()["icon_key"] == "wallet"


def test_close_account_marks_account_closed(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank", currency="USD")

    response = client.post(f"/api/v1/accounts/{account['id']}/close")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "closed"
    assert body["closed_on"] is not None


def test_closed_account_rejects_future_balance_updates(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="card", currency="USD")
    close_response = client.post(f"/api/v1/accounts/{account['id']}/close")

    assert close_response.status_code == 200

    response = client.post(
        f"/api/v1/accounts/{account['id']}/deposits",
        json={"amount_minor": 100, "currency": "USD"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "account is closed"}


def test_missing_account_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/accounts/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "account not found: missing"}


def test_insufficient_funds_returns_conflict(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="card", currency="USD")

    response = client.post(
        f"/api/v1/accounts/{account['id']}/withdrawals",
        json={"amount_minor": 100, "currency": "USD"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "insufficient funds"}


def test_currency_mismatch_returns_conflict(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="card", currency="USD")

    response = client.post(
        f"/api/v1/accounts/{account['id']}/deposits",
        json={"amount_minor": 100, "currency": "ARS"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "currency mismatch"}


def test_invalid_payload_returns_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/accounts",
        json={"name": "   ", "currency": "USD"},
    )

    assert response.status_code == 422


def test_openapi_schema_exposes_tagged_routes_and_stable_operation_ids(
    client: TestClient,
) -> None:
    schema = client.app.openapi()

    assert schema["paths"]["/api/v1/health"]["get"]["tags"] == ["system"]
    assert schema["paths"]["/api/v1/health"]["get"]["operationId"] == "system-get_health"
    assert schema["paths"]["/api/v1/accounts"]["get"]["tags"] == ["accounts"]
    assert schema["paths"]["/api/v1/accounts"]["get"]["operationId"] == "accounts-list_accounts"
    assert schema["paths"]["/api/v1/accounts"]["post"]["operationId"] == "accounts-create_account"
    assert schema["paths"]["/api/v1/accounts/{account_id}"]["patch"]["operationId"] == (
        "accounts-update_account_profile"
    )
    assert (
        schema["paths"]["/api/v1/accounts/{account_id}/deposits"]["post"]["operationId"]
        == "accounts-deposit_to_account"
    )


def _open_account(
    client: TestClient,
    *,
    name: str,
    type: str,
    currency: str,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/accounts",
        json={"name": name, "type": type, "currency": currency},
    )

    assert response.status_code == 201
    return response.json()
