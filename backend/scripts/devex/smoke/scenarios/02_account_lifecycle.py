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
            "current_balance_minor": 2_500,
            "color_key": "blue",
            "icon_key": "cash",
            "opened_on": opened_on,
        },
    )
    assert_status(create_response, 201)
    created_account = assert_json_object(create_response)
    account_id = created_account["id"]
    if created_account.get("status") != "active" or created_account.get("closed_on") is not None:
        raise AssertionError(f"unexpected created account status: {created_account!r}")
    if created_account.get("current_balance") != {
        "amount_minor": 2_500,
        "currency": "ARS",
    }:
        raise AssertionError(f"unexpected opening balance: {created_account!r}")
    if created_account.get("color_key") != "blue" or created_account.get("icon_key") != "cash":
        raise AssertionError(f"unexpected created account metadata: {created_account!r}")

    list_response = client.request("GET", "/api/v1/accounts")
    assert_status(list_response, 200)
    listed_accounts = list_response.body
    if not isinstance(listed_accounts, list) or not any(
        account.get("id") == account_id for account in listed_accounts
    ):
        raise AssertionError(f"created account missing from list response: {listed_accounts!r}")

    update_response = client.request(
        "PATCH",
        f"/api/v1/accounts/{account_id}",
        payload={
            "name": unique_account_name("Smoke wallet"),
            "type": "wallet",
            "color_key": "amber",
            "icon_key": "globe",
        },
    )
    assert_status(update_response, 200)
    updated_account = assert_json_object(update_response)
    if updated_account.get("type") != "wallet":
        raise AssertionError(f"unexpected updated account type: {updated_account!r}")
    if updated_account.get("color_key") != "amber" or updated_account.get("icon_key") != "globe":
        raise AssertionError(f"unexpected updated account metadata: {updated_account!r}")
    if updated_account.get("current_balance") != {
        "amount_minor": 2_500,
        "currency": "ARS",
    }:
        raise AssertionError(f"unexpected updated account balance: {updated_account!r}")
    if updated_account.get("status") != "active" or updated_account.get("closed_on") is not None:
        raise AssertionError(f"unexpected updated account lifecycle state: {updated_account!r}")

    deposit_response = client.request(
        "POST",
        f"/api/v1/accounts/{account_id}/deposits",
        payload={"amount_minor": 5_000, "currency": "ARS"},
    )
    assert_status(deposit_response, 200)
    deposited_account = assert_json_object(deposit_response)
    if deposited_account.get("current_balance") != {
        "amount_minor": 7_500,
        "currency": "ARS",
    }:
        raise AssertionError(f"unexpected deposit balance: {deposited_account!r}")

    withdraw_response = client.request(
        "POST",
        f"/api/v1/accounts/{account_id}/withdrawals",
        payload={"amount_minor": 1_250, "currency": "ARS"},
    )
    assert_status(withdraw_response, 200)
    withdrawn_account = assert_json_object(withdraw_response)
    if withdrawn_account.get("current_balance") != {
        "amount_minor": 6_250,
        "currency": "ARS",
    }:
        raise AssertionError(f"unexpected withdrawal balance: {withdrawn_account!r}")

    get_response = client.request("GET", f"/api/v1/accounts/{account_id}")
    assert_status(get_response, 200)
    fetched_account = assert_json_object(get_response)
    if fetched_account != withdrawn_account:
        raise AssertionError(f"fetched account does not match latest state: {fetched_account!r}")

    close_response = client.request("POST", f"/api/v1/accounts/{account_id}/close")
    assert_status(close_response, 200)
    closed_account = assert_json_object(close_response)
    if closed_account.get("status") != "closed":
        raise AssertionError(f"unexpected closed account status: {closed_account!r}")
    if not closed_account.get("closed_on"):
        raise AssertionError(f"closed account missing closed_on: {closed_account!r}")
    if closed_account.get("current_balance") != withdrawn_account.get("current_balance"):
        raise AssertionError(f"close changed balance unexpectedly: {closed_account!r}")

    get_closed_response = client.request("GET", f"/api/v1/accounts/{account_id}")
    assert_status(get_closed_response, 200)
    fetched_closed_account = assert_json_object(get_closed_response)
    if fetched_closed_account != closed_account:
        raise AssertionError(
            f"fetched closed account does not match latest state: {fetched_closed_account!r}"
        )

    deposit_after_close = client.request(
        "POST",
        f"/api/v1/accounts/{account_id}/deposits",
        payload={"amount_minor": 100, "currency": "ARS"},
    )
    assert_status(deposit_after_close, 409)
    deposit_after_close_body = assert_json_object(deposit_after_close)
    if deposit_after_close_body.get("detail") != "account is closed":
        raise AssertionError(
            f"unexpected post-close deposit rejection payload: {deposit_after_close_body!r}"
        )

    withdraw_after_close = client.request(
        "POST",
        f"/api/v1/accounts/{account_id}/withdrawals",
        payload={"amount_minor": 100, "currency": "ARS"},
    )
    assert_status(withdraw_after_close, 409)
    withdraw_after_close_body = assert_json_object(withdraw_after_close)
    if withdraw_after_close_body.get("detail") != "account is closed":
        raise AssertionError(
            f"unexpected post-close withdrawal rejection payload: {withdraw_after_close_body!r}"
        )
