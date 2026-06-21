from __future__ import annotations

from datetime import date

from scripts.devex.smoke.common import (
    HttpClient,
    assert_json_object,
    assert_status,
    unique_account_name,
)

name = "account_lifecycle"


def run(client: HttpClient) -> None:
    opened_on = date.today().isoformat()
    create_response = client.request(
        "POST",
        "/api/v1/accounts",
        payload={
            "name": unique_account_name("Smoke account"),
            "type": "cash",
            "currency": "ARS",
            "opening_balance_minor": 2_500,
            "color_key": "blue",
            "opened_on": opened_on,
        },
    )
    assert_status(create_response, 201)
    created_account = assert_json_object(create_response)
    account_id = created_account["id"]
    if created_account.get("archived_at") is not None:
        raise AssertionError(f"unexpected created account archive state: {created_account!r}")
    if created_account.get("current_balance") != {
        "amount_minor": 2_500,
        "currency": "ARS",
    }:
        raise AssertionError(f"unexpected opening balance: {created_account!r}")
    if created_account.get("color_key") != "blue":
        raise AssertionError(f"unexpected created account metadata: {created_account!r}")

    update_response = client.request(
        "PATCH",
        f"/api/v1/accounts/{account_id}",
        payload={
            "name": unique_account_name("Smoke wallet"),
            "type": "wallet",
            "color_key": "amber",
        },
    )
    assert_status(update_response, 200)
    updated_account = assert_json_object(update_response)
    if updated_account.get("type") != "wallet":
        raise AssertionError(f"unexpected updated account type: {updated_account!r}")

    category_response = client.request(
        "POST",
        "/api/v1/spending-categories",
        payload={
            "name": unique_account_name("Smoke food"),
        },
    )
    assert_status(category_response, 201)
    category = assert_json_object(category_response)

    expense_response = client.request(
        "POST",
        "/api/v1/transactions",
        payload={
            "type": "expense",
            "description": "Smoke expense",
            "postings": [
                {
                    "account_id": account_id,
                    "amount_minor": -1_250,
                    "currency": "ARS",
                },
                {
                    "category_id": category["id"],
                    "amount_minor": 1_250,
                    "currency": "ARS",
                },
            ],
        },
    )
    assert_status(expense_response, 201)

    get_response = client.request("GET", f"/api/v1/accounts/{account_id}")
    assert_status(get_response, 200)
    fetched_account = assert_json_object(get_response)
    if fetched_account.get("current_balance") != {
        "amount_minor": 1_250,
        "currency": "ARS",
    }:
        raise AssertionError(f"unexpected post-expense balance: {fetched_account!r}")

    transactions_response = client.request("GET", "/api/v1/transactions?account_id=" + account_id)
    assert_status(transactions_response, 200)
    if not isinstance(transactions_response.body, list) or len(transactions_response.body) != 2:
        raise AssertionError(
            f"unexpected account transaction history: {transactions_response.body!r}"
        )

    close_response = client.request("POST", f"/api/v1/accounts/{account_id}/archive")
    assert_status(close_response, 200)
    closed_account = assert_json_object(close_response)
    if closed_account.get("archived_at") is None:
        raise AssertionError(f"unexpected archived account payload: {closed_account!r}")

    expense_after_close = client.request(
        "POST",
        "/api/v1/transactions",
        payload={
            "type": "expense",
            "postings": [
                {
                    "account_id": account_id,
                    "amount_minor": -100,
                    "currency": "ARS",
                },
                {
                    "category_id": category["id"],
                    "amount_minor": 100,
                    "currency": "ARS",
                },
            ],
        },
    )
    assert_status(expense_after_close, 400)
    rejection_body = assert_json_object(expense_after_close)
    if rejection_body.get("detail") != "account is archived":
        raise AssertionError(f"unexpected post-archive rejection payload: {rejection_body!r}")
