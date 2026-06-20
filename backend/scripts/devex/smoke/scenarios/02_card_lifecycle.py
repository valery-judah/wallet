from __future__ import annotations

from datetime import date

from scripts.devex.smoke.common import (
    HttpClient,
    assert_json_object,
    assert_status,
    unique_card_name,
)

name = "card_lifecycle"


def run(client: HttpClient) -> None:
    opened_on = date.today().isoformat()
    create_response = client.request(
        "POST",
        "/api/v1/cards",
        payload={
            "name": unique_card_name("Smoke card"),
            "currency": "ARS",
            "opened_on": opened_on,
        },
    )
    assert_status(create_response, 201)
    created_card = assert_json_object(create_response)
    card_id = created_card["id"]

    list_response = client.request("GET", "/api/v1/cards")
    assert_status(list_response, 200)
    listed_cards = list_response.body
    if not isinstance(listed_cards, list) or not any(
        card.get("id") == card_id for card in listed_cards
    ):
        raise AssertionError(f"created card missing from list response: {listed_cards!r}")

    deposit_response = client.request(
        "POST",
        f"/api/v1/cards/{card_id}/deposits",
        payload={"amount_minor": 5_000, "currency": "ARS"},
    )
    assert_status(deposit_response, 200)
    deposited_card = assert_json_object(deposit_response)
    if deposited_card.get("balance") != {"amount_minor": 5_000, "currency": "ARS"}:
        raise AssertionError(f"unexpected deposit balance: {deposited_card!r}")

    withdraw_response = client.request(
        "POST",
        f"/api/v1/cards/{card_id}/withdrawals",
        payload={"amount_minor": 1_250, "currency": "ARS"},
    )
    assert_status(withdraw_response, 200)
    withdrawn_card = assert_json_object(withdraw_response)
    if withdrawn_card.get("balance") != {"amount_minor": 3_750, "currency": "ARS"}:
        raise AssertionError(f"unexpected withdrawal balance: {withdrawn_card!r}")

    get_response = client.request("GET", f"/api/v1/cards/{card_id}")
    assert_status(get_response, 200)
    fetched_card = assert_json_object(get_response)
    if fetched_card != withdrawn_card:
        raise AssertionError(f"fetched card does not match latest state: {fetched_card!r}")
