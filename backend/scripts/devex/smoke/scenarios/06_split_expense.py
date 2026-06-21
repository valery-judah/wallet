from __future__ import annotations

from scripts.devex.smoke.common import (
    HttpClient,
    assert_json_object,
    assert_status,
    unique_account_name,
)

name = "split_expense"


def run(client: HttpClient) -> None:
    create_response = client.request(
        "POST",
        "/api/v1/accounts",
        payload={
            "name": unique_account_name("Split expense"),
            "type": "bank_account",
            "currency": "USD",
            "opening_balance_minor": 5_000,
        },
    )
    assert_status(create_response, 201)
    created_account = assert_json_object(create_response)
    account_id = created_account["id"]

    food_response = client.request(
        "POST",
        "/api/v1/spending-categories",
        payload={"name": unique_account_name("Smoke food")},
    )
    home_response = client.request(
        "POST",
        "/api/v1/spending-categories",
        payload={"name": unique_account_name("Smoke home")},
    )
    transport_response = client.request(
        "POST",
        "/api/v1/spending-categories",
        payload={"name": unique_account_name("Smoke transport")},
    )
    assert_status(food_response, 201)
    assert_status(home_response, 201)
    assert_status(transport_response, 201)
    food = assert_json_object(food_response)
    home = assert_json_object(home_response)
    transport = assert_json_object(transport_response)

    expense_response = client.request(
        "POST",
        "/api/v1/transactions",
        payload={
            "type": "expense",
            "description": "Smoke split expense",
            "postings": [
                {
                    "account_id": account_id,
                    "amount_minor": -1_200,
                    "currency": "USD",
                },
                {
                    "category_id": food["id"],
                    "amount_minor": 500,
                    "currency": "USD",
                },
                {
                    "category_id": home["id"],
                    "amount_minor": 400,
                    "currency": "USD",
                },
                {
                    "category_id": transport["id"],
                    "amount_minor": 300,
                    "currency": "USD",
                },
            ],
        },
    )
    assert_status(expense_response, 201)
    expense = assert_json_object(expense_response)
    if len(expense.get("postings", [])) != 4:
        raise AssertionError(f"unexpected split expense postings: {expense!r}")

    get_response = client.request("GET", f"/api/v1/accounts/{account_id}")
    assert_status(get_response, 200)
    fetched_account = assert_json_object(get_response)
    if fetched_account.get("current_balance") != {
        "amount_minor": 3_800,
        "currency": "USD",
    }:
        raise AssertionError(f"unexpected post-split balance: {fetched_account!r}")
