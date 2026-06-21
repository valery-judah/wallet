from __future__ import annotations

from scripts.devex.smoke.common import (
    HttpClient,
    assert_json_object,
    assert_status,
    unique_account_name,
)

name = "adjustment_balance"


def run(client: HttpClient) -> None:
    create_response = client.request(
        "POST",
        "/api/v1/accounts",
        payload={
            "name": unique_account_name("Adjustment account"),
            "type": "bank_account",
            "currency": "USD",
            "opening_balance_minor": 1_000,
        },
    )
    assert_status(create_response, 201)
    created_account = assert_json_object(create_response)
    account_id = created_account["id"]

    adjustment_response = client.request(
        "POST",
        "/api/v1/transactions",
        payload={
            "type": "adjustment",
            "description": "Smoke adjustment",
            "postings": [
                {
                    "account_id": account_id,
                    "amount_minor": 500,
                    "currency": "USD",
                }
            ],
        },
    )
    assert_status(adjustment_response, 201)
    adjustment = assert_json_object(adjustment_response)
    if adjustment.get("status") != "posted":
        raise AssertionError(f"unexpected adjustment status: {adjustment!r}")
    if len(adjustment.get("postings", [])) != 2:
        raise AssertionError(f"unexpected synthesized postings: {adjustment!r}")
    account_posting_ids = {
        posting.get("account_id") for posting in adjustment["postings"] if posting.get("account_id")
    }
    if account_id not in account_posting_ids or "system_equity_usd" not in account_posting_ids:
        raise AssertionError(f"unexpected adjustment account targets: {adjustment!r}")

    get_response = client.request("GET", f"/api/v1/accounts/{account_id}")
    assert_status(get_response, 200)
    fetched_account = assert_json_object(get_response)
    if fetched_account.get("current_balance") != {
        "amount_minor": 1_500,
        "currency": "USD",
    }:
        raise AssertionError(f"unexpected post-adjustment balance: {fetched_account!r}")
