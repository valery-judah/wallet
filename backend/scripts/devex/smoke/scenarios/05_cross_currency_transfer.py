from __future__ import annotations

from scripts.devex.smoke.common import (
    HttpClient,
    assert_json_object,
    assert_status,
    unique_account_name,
)

name = "cross_currency_transfer"


def run(client: HttpClient) -> None:
    usd_response = client.request(
        "POST",
        "/api/v1/accounts",
        payload={
            "name": unique_account_name("USD transfer"),
            "type": "bank_account",
            "currency": "USD",
        },
    )
    assert_status(usd_response, 201)
    usd_account = assert_json_object(usd_response)

    ars_response = client.request(
        "POST",
        "/api/v1/accounts",
        payload={
            "name": unique_account_name("ARS transfer"),
            "type": "bank_account",
            "currency": "ARS",
        },
    )
    assert_status(ars_response, 201)
    ars_account = assert_json_object(ars_response)

    transfer_response = client.request(
        "POST",
        "/api/v1/transactions",
        payload={
            "type": "transfer",
            "postings": [
                {
                    "account_id": usd_account["id"],
                    "amount_minor": -100,
                    "currency": "USD",
                },
                {
                    "account_id": ars_account["id"],
                    "amount_minor": 100,
                    "currency": "ARS",
                },
            ],
        },
    )
    assert_status(transfer_response, 400)
    rejection = assert_json_object(transfer_response)
    if rejection.get("detail") != "transaction postings must use one currency":
        raise AssertionError(f"unexpected cross-currency rejection payload: {rejection!r}")
