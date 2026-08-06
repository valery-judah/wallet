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
from wallet.ai.transaction_capture import PhasedContributionProcessorFactory
from wallet.api.app import create_app
from wallet.api.deps import AppContainer, build_app_container
from wallet.config import Settings

app_module = import_module("wallet.api.app")


class ProgressiveExpenseModel:
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        if "mentions" in output_schema.get("properties", {}):
            return json.dumps({"mentions": [{"kind": "action", "source_text": "expense"}]})
        return json.dumps(
            {
                "hypotheses": [
                    {
                        "field": "type",
                        "mention_id": "m0",
                        "origin": "explicit",
                        "semantic_value": "expense",
                    }
                ],
                "clears": [],
            }
        )


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
        if "mentions" in output_schema.get("properties", {}):
            return json.dumps(
                {
                    "mentions": [
                        {"kind": "action", "source_text": "Spent"},
                        {"kind": "money", "source_text": "35 pesos"},
                        {"kind": "reference", "source_text": "Pocket wallet"},
                        {"kind": "reference", "source_text": "Coffee"},
                        {"kind": "date_time", "source_text": "today"},
                    ]
                }
            )
        return json.dumps(
            {
                "hypotheses": [
                    {
                        "field": "type",
                        "mention_id": "m0",
                        "origin": "inferred",
                        "semantic_value": "expense",
                    },
                    {
                        "field": "amount_minor",
                        "mention_id": "m1",
                        "origin": "explicit",
                        "semantic_value": None,
                    },
                    {
                        "field": "account_id",
                        "mention_id": "m2",
                        "origin": "explicit",
                        "semantic_value": None,
                    },
                    {
                        "field": "spending_category_id",
                        "mention_id": "m3",
                        "origin": "explicit",
                        "semantic_value": None,
                    },
                    {
                        "field": "occurred_on",
                        "mention_id": "m4",
                        "origin": "explicit",
                        "semantic_value": None,
                    },
                ],
                "clears": [],
            }
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
        "Coffee",
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
    processor_factory = PhasedContributionProcessorFactory(
        extraction_model=model,
        semantic_model=model,
    )

    def build_test_container(settings: Settings) -> AppContainer:
        return build_app_container(
            settings,
            capture_processor_factory=processor_factory,
        )

    monkeypatch.setattr(app_module, "build_app_container", build_test_container)
    return create_app(Settings(environment="test", seed_sample_data=True))
