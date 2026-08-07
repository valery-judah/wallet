"""Tests for the focused real-model routing smoke harness."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pytest

from scripts.devex.message_router_smoke import (
    Console,
    RouterSmokeCase,
    RouterSmokeSummary,
    build_cases,
    load_settings,
    run_router_smoke,
)
from wallet.ai.capabilities.contract import CapabilityDefinition
from wallet.ai.control.routing import (
    MessageRoutingContext,
    RouteDecision,
    UnsupportedRouteDecision,
)
from wallet.config import Settings


@dataclass
class StubRouter:
    decisions: list[RouteDecision | Exception]
    calls: list[tuple[str, MessageRoutingContext, tuple[CapabilityDefinition, ...]]]

    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        self.calls.append((message, context, definitions))
        decision = self.decisions.pop(0)
        if isinstance(decision, Exception):
            raise decision
        return decision


def test_router_smoke_corpus_covers_idle_routing_boundaries() -> None:
    cases = build_cases()

    assert [case.name for case in cases] == [
        "idle_wallet_state",
        "idle_repeat_wallet_state",
        "idle_balance_adjustment",
        "idle_expense",
        "idle_ambiguity",
        "idle_false_control",
        "idle_compound_control",
    ]
    assert {case.recent_capability_id for case in cases} == {None, "wallet.current_state"}


def test_router_smoke_reports_all_cases_and_continues_after_failures() -> None:
    cases = (
        RouterSmokeCase("pass", "one", UnsupportedRouteDecision()),
        RouterSmokeCase("wrong", "two", UnsupportedRouteDecision()),
        RouterSmokeCase("error", "three", UnsupportedRouteDecision()),
    )
    router = StubRouter(
        [UnsupportedRouteDecision(), build_cases()[0].expected, RuntimeError("offline")],
        [],
    )
    output = io.StringIO()

    summary = run_router_smoke(router, console=Console(output), cases=cases)

    assert summary == RouterSmokeSummary(total=3, passed=1)
    assert summary.exit_code == 1
    assert len(router.calls) == 3
    assert "PASS pass" in output.getvalue()
    assert "FAIL wrong" in output.getvalue()
    assert "FAIL error: RuntimeError: offline" in output.getvalue()
    assert "FAIL router cases: 1/3" in output.getvalue()


def test_load_settings_applies_model_overrides() -> None:
    settings = load_settings(
        [
            "--ollama-base-url",
            "http://localhost:22468/",
            "--model",
            "test-model",
            "--ollama-timeout",
            "12",
        ],
        configured=Settings(environment="test"),
    )

    assert settings.ollama_base_url == "http://localhost:22468"
    assert settings.ollama_model == "test-model"
    assert settings.ollama_timeout_seconds == 12


def test_load_settings_rejects_nonpositive_timeout() -> None:
    with pytest.raises(ValueError):
        load_settings(["--ollama-timeout", "0"], configured=Settings(environment="test"))
