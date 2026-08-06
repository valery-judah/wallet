"""Define capture scenarios and assert their public HTTP representations."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from scripts.devex.smoke.common import (
    HttpResponse,
    SmokeFailure,
    assert_json_object,
    assert_status,
)

API_PREFIX = "/api/v1"
CAPTURE_RESPONSE_FIELDS = {
    "id",
    "status",
    "candidate",
    "interaction",
    "message",
    "transaction",
}
CANDIDATE_FIELDS = {
    "type",
    "amount_minor",
    "occurred_on",
    "account_id",
    "spending_category_id",
    "income_category_id",
    "source_account_id",
    "destination_account_id",
    "balance_change_minor",
    "description",
    "merchant_name",
    "notes",
}


class HttpRequester(Protocol):
    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> HttpResponse: ...


class CaptureSmokeApi:
    """Small wire-level client for the endpoints used by capture smoke scenarios."""

    def __init__(self, client: HttpRequester) -> None:
        self._client = client

    def create_capture(self, content: str) -> dict[str, Any]:
        return self._object(
            "POST",
            f"{API_PREFIX}/transaction-captures",
            expected_status=201,
            payload={"content": content},
        )

    def get_capture(self, capture_id: str) -> dict[str, Any]:
        return self._object(
            "GET",
            f"{API_PREFIX}/transaction-captures/{capture_id}",
            expected_status=200,
        )

    def contribute(self, capture_id: str, content: str) -> dict[str, Any]:
        return self._object(
            "POST",
            f"{API_PREFIX}/transaction-captures/{capture_id}/contributions",
            expected_status=200,
            payload={"content": content},
        )

    def confirm(self, capture_id: str) -> dict[str, Any]:
        return self._object(
            "POST",
            f"{API_PREFIX}/transaction-captures/{capture_id}/confirm",
            expected_status=200,
        )

    def list_accounts(self) -> list[dict[str, Any]]:
        return self._objects("GET", f"{API_PREFIX}/accounts")

    def list_spending_categories(self) -> list[dict[str, Any]]:
        return self._objects("GET", f"{API_PREFIX}/spending-categories")

    def list_income_categories(self) -> list[dict[str, Any]]:
        return self._objects("GET", f"{API_PREFIX}/income-categories")

    def create_spending_category(
        self,
        *,
        name: str,
        parent_id: str | None,
    ) -> dict[str, Any]:
        return self._object(
            "POST",
            f"{API_PREFIX}/spending-categories",
            expected_status=201,
            payload={"name": name, "parent_id": parent_id},
        )

    def list_transactions(self) -> list[dict[str, Any]]:
        return self._objects("GET", f"{API_PREFIX}/transactions")

    def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        return self._object(
            "GET",
            f"{API_PREFIX}/transactions/{transaction_id}",
            expected_status=200,
        )

    def _objects(self, method: str, path: str) -> list[dict[str, Any]]:
        response = self._client.request(method, path)
        assert_status(response, 200)
        if not isinstance(response.body, list) or not all(
            isinstance(item, dict) for item in response.body
        ):
            raise SmokeFailure("expected JSON object array", response=response)
        return response.body

    def _object(
        self,
        method: str,
        path: str,
        *,
        expected_status: int,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._client.request(method, path, payload)
        assert_status(response, expected_status)
        return assert_json_object(response)


@dataclass(frozen=True, slots=True)
class ExpectedPosting:
    account_id: str | None
    category_id: str | None
    amount_minor: int
    currency: str


@dataclass(frozen=True, slots=True)
class ExpectedOption:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class ExpectedInteraction:
    kind: str
    field: str | None
    options: tuple[ExpectedOption, ...] = ()
    allow_additional_options: bool = False


@dataclass(frozen=True, slots=True)
class ExpectedStep:
    contribution: str
    status: str
    expected_fields: dict[str, object]
    interaction: ExpectedInteraction | None
    message: str


@dataclass(frozen=True, slots=True)
class AdditionalSpendingCategory:
    reference: str
    name: str
    parent_reference: str | None = None


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    steps: tuple[ExpectedStep, ...]
    expected_postings: tuple[ExpectedPosting, ...]
    additional_spending_categories: tuple[AdditionalSpendingCategory, ...] = ()


def build_scenarios(today: date) -> tuple[Scenario, ...]:
    """Build deterministic public API expectations for the supplied date."""

    yesterday = (today - timedelta(days=1)).isoformat()
    today_text = today.isoformat()
    return (
        _complete_scenario(
            name="complete_expense",
            contribution="Spent 40 pesos from Daily checking on Groceries yesterday.",
            expected_fields={
                "type": "expense",
                "amount_minor": 4000,
                "account_id": "sample_account_checking_ars",
                "spending_category_id": "category_food_groceries",
                "occurred_on": yesterday,
            },
            preview=(f"ARS 40.00 expense from Daily checking for Food > Groceries on {yesterday}"),
            expected_postings=(
                ExpectedPosting("sample_account_checking_ars", None, -4000, "ARS"),
                ExpectedPosting(None, "category_food_groceries", 4000, "ARS"),
            ),
        ),
        Scenario(
            name="progressive_expense",
            steps=(
                _awaiting_step(
                    "Record an expense today.",
                    expected_fields={"type": "expense", "occurred_on": today_text},
                    field="amount_minor",
                    message="How much?",
                ),
                _awaiting_step(
                    "35",
                    expected_fields={
                        "type": "expense",
                        "amount_minor": 3500,
                        "occurred_on": today_text,
                    },
                    field="account_id",
                    message="Which account did you use?",
                ),
                _awaiting_step(
                    "Pocket wallet",
                    expected_fields={
                        "type": "expense",
                        "amount_minor": 3500,
                        "account_id": "sample_account_wallet_ars",
                        "occurred_on": today_text,
                    },
                    field="spending_category_id",
                    message="Which spending category should I use?",
                ),
                _confirmation_step(
                    "Coffee",
                    expected_fields={
                        "type": "expense",
                        "amount_minor": 3500,
                        "account_id": "sample_account_wallet_ars",
                        "spending_category_id": "category_food_coffee",
                        "occurred_on": today_text,
                    },
                    preview=(
                        f"ARS 35.00 expense from Pocket wallet for Food > Coffee on {today_text}"
                    ),
                ),
            ),
            expected_postings=(
                ExpectedPosting("sample_account_wallet_ars", None, -3500, "ARS"),
                ExpectedPosting(None, "category_food_coffee", 3500, "ARS"),
            ),
        ),
        _complete_scenario(
            name="complete_income",
            contribution="Received 2500 pesos as Payroll into Daily checking today.",
            expected_fields={
                "type": "income",
                "amount_minor": 250000,
                "account_id": "sample_account_checking_ars",
                "income_category_id": "income_salary_payroll",
                "occurred_on": today_text,
            },
            preview=(
                f"ARS 2,500.00 income to Daily checking from Salary > Payroll on {today_text}"
            ),
            expected_postings=(
                ExpectedPosting("sample_account_checking_ars", None, 250000, "ARS"),
                ExpectedPosting(None, "income_salary_payroll", -250000, "ARS"),
            ),
        ),
        _complete_scenario(
            name="complete_transfer",
            contribution="Transfer 100 pesos from Daily checking to Pocket wallet today.",
            expected_fields={
                "type": "transfer",
                "amount_minor": 10000,
                "source_account_id": "sample_account_checking_ars",
                "destination_account_id": "sample_account_wallet_ars",
                "occurred_on": today_text,
            },
            preview=(f"ARS 100.00 transfer from Daily checking to Pocket wallet on {today_text}"),
            expected_postings=(
                ExpectedPosting("sample_account_checking_ars", None, -10000, "ARS"),
                ExpectedPosting("sample_account_wallet_ars", None, 10000, "ARS"),
            ),
        ),
        _complete_scenario(
            name="positive_adjustment",
            contribution="Increase USD cash by 50 dollars today.",
            expected_fields={
                "type": "adjustment",
                "account_id": "sample_account_cash_usd",
                "balance_change_minor": 5000,
                "occurred_on": today_text,
            },
            preview=f"USD cash balance increase of USD 50.00 on {today_text}",
            expected_postings=(
                ExpectedPosting("sample_account_cash_usd", None, 5000, "USD"),
                ExpectedPosting("system_equity_usd", None, -5000, "USD"),
            ),
        ),
        Scenario(
            name="ambiguous_category",
            steps=(
                ExpectedStep(
                    contribution="Spent 35 pesos from Pocket wallet on Coffee today.",
                    status="active",
                    expected_fields={
                        "type": "expense",
                        "amount_minor": 3500,
                        "account_id": "sample_account_wallet_ars",
                        "spending_category_id": None,
                        "occurred_on": today_text,
                    },
                    interaction=ExpectedInteraction(
                        kind="disambiguate",
                        field="spending_category_id",
                        options=(
                            ExpectedOption("category_food_coffee", "Food > Coffee"),
                            ExpectedOption("$smoke_category_coffee", "Capture smoke > Coffee"),
                        ),
                        allow_additional_options=True,
                    ),
                    message="Which spending category did you mean?",
                ),
                _confirmation_step(
                    "Food > Coffee",
                    expected_fields={
                        "type": "expense",
                        "amount_minor": 3500,
                        "account_id": "sample_account_wallet_ars",
                        "spending_category_id": "category_food_coffee",
                        "occurred_on": today_text,
                    },
                    preview=(
                        f"ARS 35.00 expense from Pocket wallet for Food > Coffee on {today_text}"
                    ),
                ),
            ),
            expected_postings=(
                ExpectedPosting("sample_account_wallet_ars", None, -3500, "ARS"),
                ExpectedPosting(None, "category_food_coffee", 3500, "ARS"),
            ),
            additional_spending_categories=(
                AdditionalSpendingCategory("smoke_category_root", "Capture smoke"),
                AdditionalSpendingCategory(
                    "smoke_category_coffee",
                    "Coffee",
                    parent_reference="smoke_category_root",
                ),
            ),
        ),
    )


def _complete_scenario(
    *,
    name: str,
    contribution: str,
    expected_fields: dict[str, object],
    preview: str,
    expected_postings: tuple[ExpectedPosting, ...],
) -> Scenario:
    return Scenario(
        name=name,
        steps=(_confirmation_step(contribution, expected_fields, preview=preview),),
        expected_postings=expected_postings,
    )


def _confirmation_step(
    contribution: str,
    expected_fields: dict[str, object],
    *,
    preview: str,
) -> ExpectedStep:
    return ExpectedStep(
        contribution=contribution,
        status="awaiting_confirmation",
        expected_fields=expected_fields,
        interaction=None,
        message=f"Ready to record: {preview}. Confirm or cancel.",
    )


def _awaiting_step(
    contribution: str,
    *,
    expected_fields: dict[str, object],
    field: str,
    message: str,
) -> ExpectedStep:
    return ExpectedStep(
        contribution=contribution,
        status="active",
        expected_fields=expected_fields,
        interaction=ExpectedInteraction(kind="request_value", field=field),
        message=message,
    )


def select_scenarios(
    scenarios: Sequence[Scenario],
    selected_name: str | None,
) -> list[Scenario]:
    if selected_name is None:
        return list(scenarios)
    selected = [scenario for scenario in scenarios if scenario.name == selected_name]
    if not selected:
        raise ValueError(f"unknown scenario: {selected_name}")
    return selected


def run_scenario(
    client: HttpRequester,
    scenario: Scenario,
    *,
    write: Callable[[str], None],
) -> None:
    """Run one capture through HTTP and assert its public and persisted state."""

    api = CaptureSmokeApi(client)
    _assert_seeded_wallet(api)
    references = _prepare_scenario(api, scenario)
    transactions_before = api.list_transactions()
    transaction_ids_before = {transaction["id"] for transaction in transactions_before}
    balances_before = _account_balances(api, scenario.expected_postings)
    capture_id: str | None = None
    result: dict[str, Any] | None = None

    write(f"SCENARIO {scenario.name}")
    for step in scenario.steps:
        started = time.monotonic()
        if capture_id is None:
            result = api.create_capture(step.contribution)
            capture_id = _required_string(result, "id")
        else:
            result = api.contribute(capture_id, step.contribution)
        elapsed = time.monotonic() - started
        write(f"  USER {step.contribution}")
        write(
            "  RESULT "
            + json.dumps(
                {
                    "elapsed_seconds": round(elapsed, 3),
                    "status": result.get("status"),
                    "candidate": result.get("candidate"),
                    "interaction": result.get("interaction"),
                    "message": result.get("message"),
                },
                sort_keys=True,
            )
        )
        _assert_step(
            api,
            scenario=scenario,
            step=step,
            result=result,
            references=references,
            transaction_ids_before=transaction_ids_before,
        )
        if api.get_capture(capture_id) != result:
            raise AssertionError(f"{scenario.name}: capture GET did not match latest response")

    if result is None or result.get("status") != "awaiting_confirmation":
        raise AssertionError(f"scenario was not ready for confirmation: {scenario.name}")
    preview_message = _required_string(result, "message")

    started = time.monotonic()
    completed = api.confirm(_required_string(result, "id"))
    elapsed = time.monotonic() - started
    transaction = completed.get("transaction")
    write(
        "  CONFIRM "
        + json.dumps(
            {
                "elapsed_seconds": round(elapsed, 3),
                "status": completed.get("status"),
                "transaction_id": (
                    transaction.get("id") if isinstance(transaction, dict) else None
                ),
            },
            sort_keys=True,
        )
    )
    _assert_completed_capture(
        api,
        scenario=scenario,
        completed=completed,
        preview_message=preview_message,
        transaction_ids_before=transaction_ids_before,
        balances_before=balances_before,
    )
    write(f"PASS {scenario.name}")


def _prepare_scenario(api: CaptureSmokeApi, scenario: Scenario) -> dict[str, str]:
    references: dict[str, str] = {}
    for expected in scenario.additional_spending_categories:
        parent_id = (
            None if expected.parent_reference is None else references[expected.parent_reference]
        )
        categories = _flatten_categories(api.list_spending_categories())
        matches = [
            category
            for category in categories
            if category.get("name") == expected.name and category.get("parent_id") == parent_id
        ]
        if len(matches) > 1:
            raise AssertionError(
                f"multiple spending categories match {expected.name!r} under {parent_id!r}"
            )
        category = (
            matches[0]
            if matches
            else api.create_spending_category(name=expected.name, parent_id=parent_id)
        )
        references[expected.reference] = _required_string(category, "id")
    return references


def _assert_step(
    api: CaptureSmokeApi,
    *,
    scenario: Scenario,
    step: ExpectedStep,
    result: dict[str, Any],
    references: dict[str, str],
    transaction_ids_before: set[str],
) -> None:
    if set(result) != CAPTURE_RESPONSE_FIELDS:
        raise AssertionError(f"{scenario.name}: unexpected capture response fields")
    if result.get("status") != step.status:
        raise AssertionError(
            f"{scenario.name}: expected {step.status}, got {result.get('status')!r}"
        )
    if result.get("message") != step.message:
        raise AssertionError(f"{scenario.name}: unexpected message: {result.get('message')!r}")
    if result.get("transaction") is not None:
        raise AssertionError(f"{scenario.name}: transaction appeared before confirmation")

    candidate = result.get("candidate")
    if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_FIELDS:
        raise AssertionError(f"{scenario.name}: incomplete candidate response")
    for field, expected in step.expected_fields.items():
        resolved = _resolve_reference(expected, references)
        if candidate.get(field) != resolved:
            raise AssertionError(
                f"{scenario.name}: expected {field}={resolved!r}, got {candidate.get(field)!r}"
            )

    _assert_interaction(
        scenario.name,
        actual=result.get("interaction"),
        expected=step.interaction,
        references=references,
    )
    if {transaction["id"] for transaction in api.list_transactions()} != (transaction_ids_before):
        raise AssertionError(f"{scenario.name}: transaction list changed before confirmation")


def _assert_interaction(
    scenario_name: str,
    *,
    actual: object,
    expected: ExpectedInteraction | None,
    references: dict[str, str],
) -> None:
    if expected is None:
        if actual is not None:
            raise AssertionError(f"{scenario_name}: unexpected interaction: {actual!r}")
        return
    if not isinstance(actual, dict):
        raise AssertionError(f"{scenario_name}: expected an interaction")
    if actual.get("kind") != expected.kind or actual.get("field") != expected.field:
        raise AssertionError(f"{scenario_name}: unexpected interaction: {actual!r}")
    options = actual.get("options")
    if not isinstance(options, list):
        raise AssertionError(f"{scenario_name}: interaction options are not an array")
    expected_options = [
        {
            "value": _resolve_reference(option.value, references),
            "label": option.label,
        }
        for option in expected.options
    ]
    if expected.allow_additional_options:
        if any(option not in options for option in expected_options):
            raise AssertionError(f"{scenario_name}: missing expected options: {options!r}")
    elif options != expected_options:
        raise AssertionError(f"{scenario_name}: unexpected options: {options!r}")


def _assert_completed_capture(
    api: CaptureSmokeApi,
    *,
    scenario: Scenario,
    completed: dict[str, Any],
    preview_message: str,
    transaction_ids_before: set[str],
    balances_before: dict[str, int],
) -> None:
    if set(completed) != CAPTURE_RESPONSE_FIELDS:
        raise AssertionError(f"{scenario.name}: unexpected completed response fields")
    if completed.get("status") != "completed" or completed.get("interaction") is not None:
        raise AssertionError(f"{scenario.name}: confirmation did not complete capture")
    expected_message = preview_message.removeprefix("Ready to record: ").removesuffix(
        " Confirm or cancel."
    )
    if completed.get("message") != f"Recorded: {expected_message}":
        raise AssertionError(f"{scenario.name}: unexpected recorded message")

    transaction = completed.get("transaction")
    if not isinstance(transaction, dict):
        raise AssertionError(f"{scenario.name}: completed capture has no transaction")
    transaction_id = _required_string(transaction, "id")
    if api.get_transaction(transaction_id) != transaction:
        raise AssertionError(f"{scenario.name}: transaction GET did not match capture response")
    if api.get_capture(_required_string(completed, "id")) != completed:
        raise AssertionError(f"{scenario.name}: completed capture was not retained")
    transaction_ids_after = {persisted["id"] for persisted in api.list_transactions()}
    if transaction_ids_after != transaction_ids_before | {transaction_id}:
        raise AssertionError(f"{scenario.name}: expected exactly one new transaction")
    if transaction.get("status") != "posted":
        raise AssertionError(f"{scenario.name}: transaction is not posted")

    candidate = completed.get("candidate")
    if not isinstance(candidate, dict):
        raise AssertionError(f"{scenario.name}: completed candidate is missing")
    if (
        transaction.get("type"),
        transaction.get("occurred_on"),
        transaction.get("description"),
        transaction.get("merchant_name"),
        transaction.get("notes"),
    ) != (
        candidate.get("type"),
        candidate.get("occurred_on"),
        candidate.get("description"),
        candidate.get("merchant_name"),
        candidate.get("notes"),
    ):
        raise AssertionError(f"{scenario.name}: transaction does not match candidate")

    postings = transaction.get("postings")
    if not isinstance(postings, list):
        raise AssertionError(f"{scenario.name}: transaction postings are missing")
    actual_postings = tuple(
        _posting_snapshot(posting) for posting in postings if isinstance(posting, dict)
    )
    if len(actual_postings) != len(postings) or actual_postings != scenario.expected_postings:
        raise AssertionError(f"{scenario.name}: unexpected postings: {actual_postings!r}")
    _assert_balanced(postings, scenario_name=scenario.name)
    _assert_balance_changes(
        api,
        scenario=scenario,
        balances_before=balances_before,
    )


def _assert_seeded_wallet(api: CaptureSmokeApi) -> None:
    expected_accounts = {
        "sample_account_checking_ars": ("Daily checking", "ARS", False),
        "sample_account_wallet_ars": ("Pocket wallet", "ARS", False),
        "sample_account_cash_usd": ("USD cash", "USD", False),
        "sample_account_archived_card": ("Old travel card", "ARS", True),
    }
    accounts = {account.get("id"): account for account in api.list_accounts()}
    for account_id, (name, currency, archived) in expected_accounts.items():
        account = accounts.get(account_id)
        if account is None:
            raise AssertionError(f"seeded wallet is missing account {account_id}")
        if (
            account.get("name"),
            account.get("current_balance", {}).get("currency"),
            account.get("archived_at") is not None,
        ) != (name, currency, archived):
            raise AssertionError(f"seeded wallet account is misconfigured: {account_id}")

    categories = {
        category.get("id") for category in _flatten_categories(api.list_spending_categories())
    }
    if not {"category_food_groceries", "category_food_coffee"}.issubset(categories):
        raise AssertionError("seeded wallet is missing spending categories")
    income_categories = {
        category.get("id") for category in _flatten_categories(api.list_income_categories())
    }
    if "income_salary_payroll" not in income_categories:
        raise AssertionError("seeded wallet is missing income categories")


def _account_balances(
    api: CaptureSmokeApi,
    postings: tuple[ExpectedPosting, ...],
) -> dict[str, int]:
    accounts = {account.get("id"): account for account in api.list_accounts()}
    balances: dict[str, int] = {}
    for posting in postings:
        if posting.account_id is None or posting.account_id.startswith("system_"):
            continue
        account = accounts.get(posting.account_id)
        if account is None:
            raise AssertionError(f"wallet account is not visible: {posting.account_id}")
        balance = account.get("current_balance")
        if not isinstance(balance, dict) or not isinstance(balance.get("amount_minor"), int):
            raise AssertionError(f"wallet account has no balance: {posting.account_id}")
        balances[posting.account_id] = balance["amount_minor"]
    return balances


def _assert_balance_changes(
    api: CaptureSmokeApi,
    *,
    scenario: Scenario,
    balances_before: dict[str, int],
) -> None:
    expected_changes: dict[str, int] = {}
    for posting in scenario.expected_postings:
        if posting.account_id in balances_before:
            expected_changes[posting.account_id] = (
                expected_changes.get(posting.account_id, 0) + posting.amount_minor
            )
    accounts = {account.get("id"): account for account in api.list_accounts()}
    for account_id, before in balances_before.items():
        balance = accounts.get(account_id, {}).get("current_balance", {}).get("amount_minor")
        expected = before + expected_changes.get(account_id, 0)
        if balance != expected:
            raise AssertionError(
                f"{scenario.name}: expected {account_id} balance {expected}, got {balance}"
            )


def _assert_balanced(postings: list[Any], *, scenario_name: str) -> None:
    totals: dict[str, int] = {}
    for posting in postings:
        if not isinstance(posting, dict):
            raise AssertionError(f"{scenario_name}: invalid posting response")
        currency = posting.get("currency")
        amount = posting.get("amount_minor")
        if not isinstance(currency, str) or not isinstance(amount, int):
            raise AssertionError(f"{scenario_name}: invalid posting amount")
        totals[currency] = totals.get(currency, 0) + amount
    if any(total != 0 for total in totals.values()):
        raise AssertionError(f"{scenario_name}: transaction is not balanced: {totals!r}")


def _posting_snapshot(posting: dict[str, Any]) -> ExpectedPosting:
    account_id = posting.get("account_id")
    category_id = posting.get("category_id")
    amount = posting.get("amount_minor")
    currency = posting.get("currency")
    if account_id is not None and not isinstance(account_id, str):
        raise AssertionError("posting account_id is invalid")
    if category_id is not None and not isinstance(category_id, str):
        raise AssertionError("posting category_id is invalid")
    if not isinstance(amount, int) or not isinstance(currency, str):
        raise AssertionError("posting amount is invalid")
    return ExpectedPosting(account_id, category_id, amount, currency)


def _flatten_categories(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    remaining = list(categories)
    while remaining:
        category = remaining.pop(0)
        flattened.append(category)
        children = category.get("children", [])
        if isinstance(children, list):
            remaining.extend(child for child in children if isinstance(child, dict))
    return flattened


def _resolve_reference(value: object, references: dict[str, str]) -> object:
    if isinstance(value, str) and value.startswith("$"):
        return references[value[1:]]
    return value


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise AssertionError(f"expected non-empty string field {field!r}")
    return value
