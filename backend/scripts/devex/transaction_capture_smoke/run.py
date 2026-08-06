"""Run transaction-capture smoke scenarios through the public HTTP API."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, TextIO
from urllib.parse import urlsplit

from scripts.devex.smoke.common import HttpClient, SmokeFailure
from scripts.devex.smoke.run import ManagedBackend, managed_backend
from scripts.devex.transaction_capture_smoke.scenarios import (
    HttpRequester,
    Scenario,
    build_scenarios,
    run_scenario,
    select_scenarios,
)
from wallet.config import Settings, get_settings

DEFAULT_API_BASE_URL = "http://127.0.0.1:8011"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60.0


class ManagedBackendFactory(Protocol):
    def __call__(
        self,
        base_url: str,
        *,
        environment: dict[str, str] | None = None,
    ) -> AbstractContextManager[ManagedBackend]: ...


@dataclass(frozen=True, slots=True)
class CaptureSmokeConfig:
    settings: Settings
    api_base_url: str = DEFAULT_API_BASE_URL
    use_existing_backend: bool = False
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    selected_scenario: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    total: int
    passed: int
    failed: int

    @property
    def exit_code(self) -> int:
        return 0 if self.failed == 0 else 1


class Console:
    def __init__(self, output: TextIO | None = None) -> None:
        self.output = output or sys.stdout

    def write(self, message: str) -> None:
        self.output.write(f"{message}\n")


def load_config(
    argv: Sequence[str] | None = None,
    *,
    configured: Settings | None = None,
) -> CaptureSmokeConfig:
    """Resolve API and managed-backend settings from CLI overrides."""

    args = _parse_args(argv)
    base_settings = configured or get_settings()
    updates: dict[str, Any] = {"seed_sample_data": True}
    if args.ollama_base_url is not None:
        updates["ollama_base_url"] = args.ollama_base_url
    if args.model is not None:
        updates["ollama_model"] = args.model
    if args.ollama_timeout is not None:
        updates["ollama_timeout_seconds"] = args.ollama_timeout
    settings = Settings.model_validate(base_settings.model_dump() | updates)

    request_timeout = (
        DEFAULT_REQUEST_TIMEOUT_SECONDS if args.request_timeout is None else args.request_timeout
    )
    if request_timeout <= 0:
        raise ValueError("request timeout must be greater than zero")
    return CaptureSmokeConfig(
        settings=settings,
        api_base_url=_normalize_api_base_url(args.api_base_url),
        use_existing_backend=args.existing_backend,
        request_timeout_seconds=request_timeout,
        selected_scenario=args.scenario,
    )


def run_capture_smoke(
    config: CaptureSmokeConfig,
    *,
    console: Console,
    current_date: date | None = None,
    client_factory: Callable[[str, float], HttpRequester] = HttpClient,
    backend_factory: ManagedBackendFactory = managed_backend,
) -> ScenarioSummary:
    """Run selected scenarios against a managed or existing public API."""

    scenarios = select_scenarios(
        build_scenarios(current_date or date.today()),
        config.selected_scenario,
    )
    console.write(f"Running {len(scenarios)} scenario(s) against {config.api_base_url}")
    if config.use_existing_backend:
        client = client_factory(config.api_base_url, config.request_timeout_seconds)
        return _run_scenarios(client, scenarios, console=console)

    with backend_factory(
        config.api_base_url,
        environment=_backend_environment(config.settings),
    ) as backend:
        client = client_factory(backend.base_url, config.request_timeout_seconds)
        return _run_scenarios(client, scenarios, console=console)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command and translate command-level failures into an exit code."""

    console = Console()
    try:
        config = load_config(argv)
        summary = run_capture_smoke(config, console=console)
    except (RuntimeError, ValueError) as exc:
        console.write(f"FAIL {exc}")
        return 1
    return summary.exit_code


def _run_scenarios(
    client: HttpRequester,
    scenarios: Sequence[Scenario],
    *,
    console: Console,
) -> ScenarioSummary:
    total = 0
    passed = 0
    for scenario in scenarios:
        total += 1
        try:
            run_scenario(client, scenario, write=console.write)
        except Exception as exc:
            console.write(f"FAIL {scenario.name}: {_format_error(exc)}")
        else:
            passed += 1

    summary = ScenarioSummary(total=total, passed=passed, failed=total - passed)
    console.write(
        f"{'PASS' if summary.failed == 0 else 'FAIL'} scenarios: {summary.passed}/{summary.total}"
    )
    return summary


def _backend_environment(settings: Settings) -> dict[str, str]:
    return {
        "WALLET_ENVIRONMENT": settings.environment,
        "WALLET_SEED_SAMPLE_DATA": "true",
        "WALLET_OLLAMA_BASE_URL": settings.ollama_base_url,
        "WALLET_OLLAMA_MODEL": settings.ollama_model,
        "WALLET_OLLAMA_TIMEOUT_SECONDS": str(settings.ollama_timeout_seconds),
    }


def _format_error(exc: Exception) -> str:
    if not isinstance(exc, SmokeFailure) or exc.response is None:
        return str(exc) or exc.__class__.__name__
    return (
        f"{exc}; url={exc.response.url}; status={exc.response.status_code}; "
        f"body={exc.response.body!r}"
    )


def _normalize_api_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("API base URL must be a full HTTP URL")
    if parsed.port is None:
        raise ValueError("API base URL must include an explicit port")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("API base URL must not include a path, query, or fragment")
    return normalized


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test transaction capture through the public HTTP API.",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help="Backend API base URL.",
    )
    parser.add_argument(
        "--existing-backend",
        action="store_true",
        help="Use an already-running seeded backend instead of managing one.",
    )
    parser.add_argument(
        "--ollama-base-url",
        help="Override the Ollama base URL passed to a managed backend.",
    )
    parser.add_argument("--model", help="Override the Ollama model for a managed backend.")
    parser.add_argument(
        "--ollama-timeout",
        type=float,
        help="Override the managed backend's Ollama timeout in seconds.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        help="HTTP timeout for each smoke request in seconds.",
    )
    parser.add_argument("--scenario", help="Run one scenario by name.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
