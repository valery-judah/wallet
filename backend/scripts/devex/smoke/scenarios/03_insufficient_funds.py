from __future__ import annotations

from scripts.devex.smoke.common import (
    HttpClient,
    assert_json_object,
    assert_status,
    unique_card_name,
)

name = "insufficient_funds"


def run(client: HttpClient) -> None:
    create_response = client.request(
        "POST",
        "/api/v1/cards",
        payload={"name": unique_card_name("Insufficient funds"), "currency": "ARS"},
    )
    assert_status(create_response, 201)
    created_card = assert_json_object(create_response)

    withdraw_response = client.request(
        "POST",
        f"/api/v1/cards/{created_card['id']}/withdrawals",
        payload={"amount_minor": 100, "currency": "ARS"},
    )
    assert_status(withdraw_response, 409)
    response_body = assert_json_object(withdraw_response)
    if response_body.get("detail") != "insufficient funds":
        raise AssertionError(f"unexpected insufficient funds payload: {response_body!r}")
