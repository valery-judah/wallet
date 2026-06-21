from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from wallet.api.app import create_app
from wallet.bootstrap.sample_data import (
    get_sample_archived_account_id,
    get_sample_transfer_account_ids,
    list_sample_account_ids,
    list_sample_transaction_types,
)
from wallet.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(_test_settings())

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_client() -> Iterator[TestClient]:
    app = create_app(_test_settings(seed_sample_data=True))

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
            "opening_balance_minor": 500,
            "color_key": "emerald",
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
    assert body["color_key"] == "emerald"
    assert body["opened_on"] == "2026-06-18"
    assert body["archived_at"] is None
    assert body["created_on"] == "2026-06-18"
    assert body["updated_on"] == "2026-06-18"


def test_list_and_get_accounts_persist_across_requests(client: TestClient) -> None:
    first = _open_account(client, name="Daily account", type="debit_card", currency="USD")
    second = _open_account(client, name="Travel cash", type="cash", currency="EUR")

    list_response = client.get("/api/v1/accounts")
    get_response = client.get(f"/api/v1/accounts/{first['id']}")

    assert list_response.status_code == 200
    assert [account["id"] for account in list_response.json()] == [first["id"], second["id"]]
    assert get_response.status_code == 200
    assert get_response.json() == first


def test_update_account_profile_persists_new_type_and_display_metadata(
    client: TestClient,
) -> None:
    account = _open_account(client, name="Main account", type="debit_card", currency="USD")

    response = client.patch(
        f"/api/v1/accounts/{account['id']}",
        json={
            "name": "Travel wallet",
            "type": "wallet",
            "color_key": "cyan",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Travel wallet"
    assert response.json()["type"] == "wallet"
    assert response.json()["color_key"] == "cyan"


def test_archive_account_marks_account_archived(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank_account", currency="USD")

    response = client.post(f"/api/v1/accounts/{account['id']}/archive")

    assert response.status_code == 200
    body = response.json()
    assert body["archived_at"] is not None


def test_missing_account_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/accounts/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "account not found: missing"}


def test_create_transaction_updates_account_balance(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank_account", currency="USD")
    category = client.post(
        "/api/v1/spending-categories",
        json={"name": "Lunch"},
    ).json()

    response = client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "description": "Lunch",
            "postings": [
                {"account_id": account["id"], "amount_minor": -1200, "currency": "USD"},
                {"category_id": category["id"], "amount_minor": 1200, "currency": "USD"},
            ],
        },
    )
    updated_account = client.get(f"/api/v1/accounts/{account['id']}")

    assert response.status_code == 201
    assert response.json()["type"] == "expense"
    assert updated_account.status_code == 200
    assert updated_account.json()["current_balance"] == {
        "amount_minor": -1200,
        "currency": "USD",
    }


def test_create_split_expense_transaction_updates_account_balance(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank_account", currency="USD")
    food = client.post("/api/v1/spending-categories", json={"name": "Split Food"}).json()
    home = client.post("/api/v1/spending-categories", json={"name": "Split Home"}).json()
    transit = client.post("/api/v1/spending-categories", json={"name": "Split Transit"}).json()

    response = client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "description": "Split receipt",
            "postings": [
                {"account_id": account["id"], "amount_minor": -1500, "currency": "USD"},
                {"category_id": food["id"], "amount_minor": 700, "currency": "USD"},
                {"category_id": home["id"], "amount_minor": 500, "currency": "USD"},
                {"category_id": transit["id"], "amount_minor": 300, "currency": "USD"},
            ],
        },
    )
    updated_account = client.get(f"/api/v1/accounts/{account['id']}")

    assert response.status_code == 201
    assert response.json()["type"] == "expense"
    assert len(response.json()["postings"]) == 4
    assert updated_account.status_code == 200
    assert updated_account.json()["current_balance"] == {
        "amount_minor": -1500,
        "currency": "USD",
    }


def test_list_and_get_transactions_support_account_filter(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank_account", currency="USD")
    category = client.post(
        "/api/v1/income-categories",
        json={"name": "Freelance"},
    ).json()
    created = client.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "description": "Payroll",
            "postings": [
                {"account_id": account["id"], "amount_minor": 5000, "currency": "USD"},
                {"category_id": category["id"], "amount_minor": -5000, "currency": "USD"},
            ],
        },
    ).json()

    list_response = client.get("/api/v1/transactions", params={"account_id": account["id"]})
    get_response = client.get(f"/api/v1/transactions/{created['id']}")

    assert list_response.status_code == 200
    assert [transaction["id"] for transaction in list_response.json()] == [created["id"]]
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_create_adjustment_auto_balances_and_returns_posted_transaction(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank_account", currency="USD")

    response = client.post(
        "/api/v1/transactions",
        json={
            "type": "adjustment",
            "description": "Opening correction",
            "postings": [
                {"account_id": account["id"], "amount_minor": 500, "currency": "USD"},
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "posted"
    assert body["type"] == "adjustment"
    assert len(body["postings"]) == 2
    assert (
        body["postings"][0]["account_id"] == account["id"]
        or body["postings"][1]["account_id"] == account["id"]
    )
    assert any(posting["account_id"] == "system_equity_usd" for posting in body["postings"])


def test_archived_accounts_reject_new_transactions(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="debit_card", currency="USD")
    category = client.post(
        "/api/v1/spending-categories",
        json={"name": "Lunch"},
    ).json()
    close_response = client.post(f"/api/v1/accounts/{account['id']}/archive")

    assert close_response.status_code == 200

    response = client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "postings": [
                {"account_id": account["id"], "amount_minor": -100, "currency": "USD"},
                {"category_id": category["id"], "amount_minor": 100, "currency": "USD"},
            ],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "account is archived"}


def test_transaction_rejects_invalid_sign_direction(client: TestClient) -> None:
    account = _open_account(client, name="Main account", type="bank_account", currency="USD")
    category = client.post(
        "/api/v1/spending-categories",
        json={"name": "Lunch"},
    ).json()

    response = client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "postings": [
                {"account_id": account["id"], "amount_minor": 100, "currency": "USD"},
                {"category_id": category["id"], "amount_minor": -100, "currency": "USD"},
            ],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "expense account postings must be negative"}


def test_transaction_rejects_cross_currency_transfer(client: TestClient) -> None:
    usd_account = _open_account(client, name="USD account", type="bank_account", currency="USD")
    ars_account = _open_account(client, name="ARS account", type="bank_account", currency="ARS")

    response = client.post(
        "/api/v1/transactions",
        json={
            "type": "transfer",
            "postings": [
                {"account_id": usd_account["id"], "amount_minor": -100, "currency": "USD"},
                {"account_id": ars_account["id"], "amount_minor": 100, "currency": "ARS"},
            ],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "transaction postings must use one currency"}


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
    assert "/api/v1/accounts/{account_id}/deposits" not in schema["paths"]
    assert "/api/v1/accounts/{account_id}/withdrawals" not in schema["paths"]
    assert "/api/v1/accounts/{account_id}/close" not in schema["paths"]
    assert schema["paths"]["/api/v1/accounts/{account_id}/archive"]["post"]["operationId"] == (
        "accounts-archive_account"
    )
    assert schema["paths"]["/api/v1/transactions"]["post"]["operationId"] == (
        "transactions-create_transaction"
    )


def test_seeded_app_exposes_sample_accounts_and_transaction_types(
    seeded_client: TestClient,
) -> None:
    accounts_response = seeded_client.get("/api/v1/accounts")
    transactions_response = seeded_client.get("/api/v1/transactions")

    assert accounts_response.status_code == 200
    assert transactions_response.status_code == 200
    assert [account["id"] for account in accounts_response.json()] == list_sample_account_ids()
    assert {transaction["type"] for transaction in transactions_response.json()} >= {
        transaction_type.value for transaction_type in list_sample_transaction_types()
    }


def test_seeded_app_archived_account_rejects_new_transactions(
    seeded_client: TestClient,
) -> None:
    archived_account_id = get_sample_archived_account_id()

    response = seeded_client.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "postings": [
                {"account_id": archived_account_id, "amount_minor": -100, "currency": "ARS"},
                {
                    "category_id": "category_food_groceries",
                    "amount_minor": 100,
                    "currency": "ARS",
                },
            ],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "account is archived"}


def test_seeded_app_includes_transfer_ready_same_currency_accounts(
    seeded_client: TestClient,
) -> None:
    from_account_id, to_account_id = get_sample_transfer_account_ids()

    accounts_response = seeded_client.get("/api/v1/accounts")
    transactions_response = seeded_client.get("/api/v1/transactions")

    assert accounts_response.status_code == 200
    assert transactions_response.status_code == 200

    accounts_by_id = {account["id"]: account for account in accounts_response.json()}
    assert accounts_by_id[from_account_id]["currency"] == "ARS"
    assert accounts_by_id[to_account_id]["currency"] == "ARS"
    assert accounts_by_id[from_account_id]["archived_at"] is None
    assert accounts_by_id[to_account_id]["archived_at"] is None
    assert any(
        transaction["type"] == "transfer"
        and {posting["account_id"] for posting in transaction["postings"] if posting["account_id"]}
        == {from_account_id, to_account_id}
        for transaction in transactions_response.json()
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


def _test_settings(*, seed_sample_data: bool = False) -> Settings:
    return Settings(
        app_name="Wallet Test API",
        environment="test",
        debug=False,
        api_v1_prefix="/api/v1",
        frontend_host="http://localhost:5173",
        seed_sample_data=seed_sample_data,
    )
