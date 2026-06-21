from __future__ import annotations

from scripts.devex.smoke.common import (
    HttpClient,
    assert_json_object,
    assert_status,
    unique_account_name,
)

name = "invalid_transaction"


def run(client: HttpClient) -> None:
    create_response = client.request(
        "POST",
        "/api/v1/accounts",
        payload={
            "name": unique_account_name("Invalid transaction"),
            "type": "debit_card",
            "currency": "ARS",
        },
    )
    assert_status(create_response, 201)
    created_account = assert_json_object(create_response)

    invalid_response = client.request(
        "POST",
        "/api/v1/transactions",
        payload={
            "type": "transfer",
            "postings": [
                {
                    "account_id": created_account["id"],
                    "amount_minor": -100,
                    "currency": "ARS",
                },
                {
                    "category_id": "category_food",
                    "amount_minor": 100,
                    "currency": "ARS",
                },
            ],
        },
    )
    assert_status(invalid_response, 400)
    response_body = assert_json_object(invalid_response)
    if response_body.get("detail") != "transfer transactions must not use categories":
        raise AssertionError(f"unexpected invalid transaction payload: {response_body!r}")
