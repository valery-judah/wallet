"""Exercise the authoritative message router against the configured real model."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TextIO

from wallet.ai.capabilities.contract import CapabilityDefinition
from wallet.ai.control.composition import build_default_message_router
from wallet.ai.control.routing import (
    ClarifyRouteDecision,
    CompoundControlRouteDecision,
    MessageRoutingContext,
    RouteDecision,
    StartRouteDecision,
    UnsupportedRouteDecision,
)
from wallet.ai.transaction_capture.capability import TransactionCaptureCapability
from wallet.ai.wallet_state.capability import CurrentWalletStateCapability
from wallet.config import Settings, get_settings


class Router(Protocol):
    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision: ...


@dataclass(frozen=True, slots=True)
class RouterSmokeCase:
    name: str
    message: str
    expected: RouteDecision
    recent_capability_id: str | None = None


@dataclass(frozen=True, slots=True)
class RouterSmokeSummary:
    total: int
    passed: int

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def exit_code(self) -> int:
        return 0 if self.failed == 0 else 1


class Console:
    def __init__(self, output: TextIO | None = None) -> None:
        self.output = output or sys.stdout

    def write(self, message: str) -> None:
        self.output.write(f"{message}\n")


def build_cases() -> tuple[RouterSmokeCase, ...]:
    capture = "transactions.capture"
    state = "wallet.current_state"
    return (
        RouterSmokeCase("idle_wallet_state", "show balance", StartRouteDecision(state)),
        RouterSmokeCase(
            "idle_repeat_wallet_state",
            "one more time",
            StartRouteDecision(state),
            recent_capability_id=state,
        ),
        RouterSmokeCase(
            "idle_balance_adjustment",
            "set Pocket wallet balance to 250",
            StartRouteDecision(capture),
        ),
        RouterSmokeCase(
            "idle_expense",
            "spent 20 pesos on Food",
            StartRouteDecision(capture),
        ),
        RouterSmokeCase(
            "idle_ambiguity",
            "I need to do something with my balance",
            ClarifyRouteDecision((capture, state)),
        ),
        RouterSmokeCase(
            "idle_false_control",
            "cancel my gym membership",
            UnsupportedRouteDecision(),
        ),
        RouterSmokeCase(
            "idle_compound_control",
            "cancel and show my balance",
            CompoundControlRouteDecision(),
        ),
    )


def run_router_smoke(
    router: Router,
    *,
    console: Console,
    cases: Sequence[RouterSmokeCase] | None = None,
    definitions: tuple[CapabilityDefinition, ...] | None = None,
) -> RouterSmokeSummary:
    selected_cases = tuple(cases or build_cases())
    registered = definitions or (
        TransactionCaptureCapability.definition,
        CurrentWalletStateCapability.definition,
    )
    passed = 0
    for case in selected_cases:
        try:
            actual = router.route(
                case.message,
                MessageRoutingContext(
                    recent_capability_id=case.recent_capability_id,
                ),
                registered,
            )
        except Exception as exc:
            console.write(f"FAIL {case.name}: {type(exc).__name__}: {exc}")
            continue
        if actual != case.expected:
            console.write(f"FAIL {case.name}: expected {case.expected!r}; got {actual!r}")
            continue
        passed += 1
        console.write(f"PASS {case.name}")

    summary = RouterSmokeSummary(total=len(selected_cases), passed=passed)
    console.write(
        f"{'PASS' if summary.failed == 0 else 'FAIL'} router cases: "
        f"{summary.passed}/{summary.total}"
    )
    return summary


def load_settings(
    argv: Sequence[str] | None = None,
    *,
    configured: Settings | None = None,
) -> Settings:
    parser = argparse.ArgumentParser(description="Smoke-test the real LLM message router.")
    parser.add_argument("--ollama-base-url")
    parser.add_argument("--model")
    parser.add_argument("--ollama-timeout", type=float)
    args = parser.parse_args(argv)
    base = configured or get_settings()
    updates: dict[str, object] = {}
    if args.ollama_base_url is not None:
        updates["ollama_base_url"] = args.ollama_base_url
    if args.model is not None:
        updates["ollama_model"] = args.model
    if args.ollama_timeout is not None:
        updates["ollama_timeout_seconds"] = args.ollama_timeout
    return Settings.model_validate(base.model_dump() | updates)


def main(argv: Sequence[str] | None = None) -> int:
    console = Console()
    try:
        settings = load_settings(argv)
    except ValueError as exc:
        console.write(f"FAIL {exc}")
        return 1
    summary = run_router_smoke(build_default_message_router(settings), console=console)
    return summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
