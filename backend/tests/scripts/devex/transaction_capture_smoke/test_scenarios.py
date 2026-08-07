from __future__ import annotations

import json
from datetime import date
from importlib import import_module
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.devex.smoke.common import HttpResponse
from scripts.devex.transaction_capture_smoke.scenarios import (
    build_scenarios,
    run_scenario,
    select_scenarios,
)
from wallet.ai.capabilities.contract import CapabilityDefinition
from wallet.ai.control.routing import (
    MessageRoutingContext,
    RouteDecision,
    StartRouteDecision,
)
from wallet.ai.transaction_capture import ModelDrivenContributionProcessorFactory
from wallet.api.app import create_app
from wallet.api.deps import AppContainer, build_app_container
from wallet.config import Settings

app_module = import_module("wallet.api.app")


class CaptureMessageRouter:
    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        return StartRouteDecision("transactions.capture")


class ProgressiveExpenseModel:
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        updates: dict[str, object]
        if user_prompt == "Record an expense today.":
            updates = {"type": "expense"}
        elif user_prompt == "35":
            updates = {"amount_minor": 3500}
        elif user_prompt == "Pocket wallet":
            updates = {"account_key": _reference_key(system_prompt, "accounts", "Pocket wallet")}
        else:
            updates = {
                "spending_category_key": _reference_key(
                    system_prompt,
                    "spending_categories",
                    "Food > Coffee",
                )
            }
        return _interpretation_response(updates=updates)


class AmbiguousCategoryModel:
    def __init__(self) -> None:
        self.calls = 0

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        self.calls += 1
        if user_prompt == "Food > Coffee":
            return _interpretation_response(
                updates={
                    "spending_category_key": _reference_key(
                        system_prompt,
                        "spending_categories",
                        "Food > Coffee",
                    )
                }
            )
        coffee_keys = [
            item["key"]
            for item in _context(system_prompt)["spending_categories"]
            if item["label"].endswith(" > Coffee")
        ]
        return _interpretation_response(
            updates={
                "type": "expense",
                "amount_minor": 3500,
                "account_key": _reference_key(system_prompt, "accounts", "Pocket wallet"),
                "currency_code": "ARS",
            },
            ambiguities=[
                {
                    "field": "spending_category_id",
                    "candidate_keys": coffee_keys,
                }
            ],
        )


class TestClientRequester:
    __test__ = False

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> HttpResponse:
        response = self.client.request(method, path, json=payload)
        return HttpResponse(
            status_code=response.status_code,
            body=response.json(),
            url=str(response.url),
        )


def test_select_progressive_discovery_scenario() -> None:
    scenarios = build_scenarios(date(2026, 8, 5))

    selected = select_scenarios(scenarios, "progressive_expense")

    assert [scenario.name for scenario in selected] == ["progressive_expense"]
    assert tuple(step.contribution for step in selected[0].steps) == (
        "Record an expense today.",
        "35",
        "Pocket wallet",
        "Food > Coffee",
    )
    assert [step.status for step in selected[0].steps] == [
        "active",
        "active",
        "active",
        "awaiting_confirmation",
    ]
    assert [
        None if step.interaction is None else step.interaction.field for step in selected[0].steps
    ] == ["amount_minor", "account_id", "spending_category_id", None]
    assert selected[0].steps[1].expected_fields == {
        "type": "expense",
        "amount_minor": 3500,
        "occurred_on": "2026-08-05",
    }


def test_select_scenarios_returns_all_when_name_is_omitted() -> None:
    scenarios = build_scenarios(date(2026, 8, 5))

    assert select_scenarios(scenarios, None) == list(scenarios)


def test_select_scenarios_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown scenario: missing"):
        select_scenarios(build_scenarios(date(2026, 8, 5)), "missing")


def test_progressive_scenario_uses_api_and_verifies_persisted_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = ProgressiveExpenseModel()
    app = _build_test_app(monkeypatch, model)
    scenario = select_scenarios(
        build_scenarios(date.today()),
        "progressive_expense",
    )[0]
    messages: list[str] = []

    with TestClient(app) as client:
        run_scenario(TestClientRequester(client), scenario, write=messages.append)

    assert any('"status": "awaiting_confirmation"' in line for line in messages)
    assert all('"trace"' not in line for line in messages)
    assert messages[-1] == "PASS progressive_expense"


def test_ambiguous_scenario_prepares_categories_through_api_and_records_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = AmbiguousCategoryModel()
    app = _build_test_app(monkeypatch, model)
    scenario = select_scenarios(
        build_scenarios(date.today()),
        "ambiguous_category",
    )[0]
    messages: list[str] = []

    with TestClient(app) as client:
        requester = TestClientRequester(client)
        run_scenario(requester, scenario, write=messages.append)
        categories = client.get("/api/v1/spending-categories").json()

    assert model.calls == 2
    smoke_root = next(category for category in categories if category["name"] == "Capture smoke")
    assert [child["name"] for child in smoke_root["children"]] == ["Coffee"]
    assert any("Capture smoke > Coffee" in line for line in messages)
    assert messages[-1] == "PASS ambiguous_category"


def _build_test_app(
    monkeypatch: pytest.MonkeyPatch,
    model: ProgressiveExpenseModel | AmbiguousCategoryModel,
) -> FastAPI:
    processor_factory = ModelDrivenContributionProcessorFactory(model=model)

    def build_test_container(settings: Settings) -> AppContainer:
        return build_app_container(
            settings,
            capture_processor_factory=processor_factory,
            message_router=CaptureMessageRouter(),
        )

    monkeypatch.setattr(app_module, "build_app_container", build_test_container)
    return create_app(Settings(environment="test", seed_sample_data=True))


def _context(system_prompt: str) -> dict[str, Any]:
    serialized = system_prompt.split("\nCONTEXT=", maxsplit=1)[1].splitlines()[0]
    value = json.loads(serialized)
    assert isinstance(value, dict)
    return value


def _reference_key(system_prompt: str, family: str, label: str) -> str:
    references = _context(system_prompt)[family]
    return next(item["key"] for item in references if item["label"] == label)


def _interpretation_response(
    *,
    updates: dict[str, object],
    ambiguities: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps(
        {
            "updates": updates,
            "clear_fields": [],
            "ambiguities": ambiguities or [],
            "unresolved_fields": [],
            "clarification_needed": False,
            "evidence": [],
        }
    )
