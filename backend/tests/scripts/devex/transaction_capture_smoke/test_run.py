from __future__ import annotations

import io
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from typing import Any, cast

import pytest

import scripts.devex.transaction_capture_smoke.run as run_module
from scripts.devex.smoke.common import HttpResponse, SmokeFailure
from scripts.devex.smoke.run import ManagedBackend
from scripts.devex.transaction_capture_smoke.run import (
    DEFAULT_API_BASE_URL,
    CaptureSmokeConfig,
    Console,
    ScenarioSummary,
    load_config,
    main,
    run_capture_smoke,
)
from scripts.devex.transaction_capture_smoke.scenarios import Scenario
from wallet.config import Settings


class FakeRequester:
    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> HttpResponse:
        raise AssertionError("scenario execution is replaced by a test double")


def test_load_config_defaults_to_managed_seeded_backend() -> None:
    configured = Settings(
        environment="test",
        seed_sample_data=False,
        ollama_base_url="http://localhost:11434",
        ollama_model="configured-model",
        ollama_timeout_seconds=18,
    )

    config = load_config([], configured=configured)

    assert config.api_base_url == DEFAULT_API_BASE_URL
    assert config.use_existing_backend is False
    assert config.request_timeout_seconds == 60
    assert config.settings.environment == "test"
    assert config.settings.seed_sample_data is True
    assert config.settings.ollama_base_url == "http://localhost:11434"
    assert config.settings.ollama_model == "configured-model"
    assert config.settings.ollama_timeout_seconds == 18
    assert config.selected_scenario is None


def test_load_config_applies_api_and_ollama_overrides() -> None:
    config = load_config(
        [
            "--api-base-url",
            "http://localhost:8022/",
            "--existing-backend",
            "--ollama-base-url",
            "http://localhost:22468/",
            "--model",
            "qwen3.5:4b",
            "--ollama-timeout",
            "12",
            "--request-timeout",
            "20",
            "--scenario",
            "progressive_expense",
        ],
        configured=Settings(environment="test"),
    )

    assert config.api_base_url == "http://localhost:8022"
    assert config.use_existing_backend is True
    assert config.request_timeout_seconds == 20
    assert config.settings.ollama_base_url == "http://localhost:22468"
    assert config.settings.ollama_model == "qwen3.5:4b"
    assert config.settings.ollama_timeout_seconds == 12
    assert config.settings.seed_sample_data is True
    assert config.selected_scenario == "progressive_expense"


@pytest.mark.parametrize(
    "arguments",
    [
        ["--api-base-url", "localhost:8011"],
        ["--api-base-url", "http://localhost"],
        ["--ollama-base-url", "localhost:11434"],
        ["--ollama-timeout", "0"],
        ["--request-timeout", "0"],
    ],
)
def test_load_config_rejects_invalid_overrides(arguments: list[str]) -> None:
    with pytest.raises(ValueError):
        load_config(arguments, configured=Settings(environment="test"))


def test_managed_run_passes_settings_to_one_backend_and_uses_selected_scenario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        environment="test",
        seed_sample_data=True,
        ollama_base_url="http://localhost:22468",
        ollama_model="test-model",
        ollama_timeout_seconds=17,
    )
    config = CaptureSmokeConfig(
        settings=settings,
        selected_scenario="progressive_expense",
    )
    requester = FakeRequester()
    backend_calls: list[tuple[str, dict[str, str] | None]] = []
    client_calls: list[tuple[str, float]] = []
    received_scenarios: list[Scenario] = []

    @contextmanager
    def build_backend(
        base_url: str,
        *,
        environment: dict[str, str] | None = None,
    ) -> Iterator[ManagedBackend]:
        backend_calls.append((base_url, environment))
        yield ManagedBackend(base_url, process=cast(Any, object()))

    def build_client(base_url: str, timeout: float) -> FakeRequester:
        client_calls.append((base_url, timeout))
        return requester

    def run_test_scenario(
        received_client: object,
        scenario: Scenario,
        *,
        write: object,
    ) -> None:
        assert received_client is requester
        received_scenarios.append(scenario)

    monkeypatch.setattr(run_module, "run_scenario", run_test_scenario)

    summary = run_capture_smoke(
        config,
        console=Console(io.StringIO()),
        current_date=date(2026, 8, 5),
        client_factory=build_client,
        backend_factory=build_backend,
    )

    assert [scenario.name for scenario in received_scenarios] == ["progressive_expense"]
    assert client_calls == [(DEFAULT_API_BASE_URL, 60)]
    assert backend_calls == [
        (
            DEFAULT_API_BASE_URL,
            {
                "WALLET_ENVIRONMENT": "test",
                "WALLET_SEED_SAMPLE_DATA": "true",
                "WALLET_OLLAMA_BASE_URL": "http://localhost:22468",
                "WALLET_OLLAMA_MODEL": "test-model",
                "WALLET_OLLAMA_TIMEOUT_SECONDS": "17.0",
            },
        )
    ]
    assert summary == ScenarioSummary(total=1, passed=1, failed=0)


def test_existing_backend_mode_does_not_start_a_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = FakeRequester()
    config = CaptureSmokeConfig(
        settings=Settings(environment="test", seed_sample_data=True),
        api_base_url="http://127.0.0.1:8000",
        use_existing_backend=True,
        selected_scenario="complete_expense",
    )

    def forbidden_backend(
        base_url: str,
        *,
        environment: dict[str, str] | None = None,
    ) -> object:
        raise AssertionError("existing-backend mode must not start a process")

    monkeypatch.setattr(run_module, "run_scenario", lambda *args, **kwargs: None)

    summary = run_capture_smoke(
        config,
        console=Console(io.StringIO()),
        client_factory=lambda base_url, timeout: requester,
        backend_factory=forbidden_backend,  # type: ignore[arg-type]
    )

    assert summary == ScenarioSummary(total=1, passed=1, failed=0)


def test_runner_reuses_one_api_client_and_continues_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requester = FakeRequester()
    received: list[tuple[object, str]] = []
    output = io.StringIO()

    def run_test_scenario(
        client: object,
        scenario: Scenario,
        *,
        write: object,
    ) -> None:
        received.append((client, scenario.name))
        if scenario.name == "complete_expense":
            raise AssertionError("candidate mismatch")

    @contextmanager
    def build_backend(
        base_url: str,
        *,
        environment: dict[str, str] | None = None,
    ) -> Iterator[ManagedBackend]:
        yield ManagedBackend(base_url, process=cast(Any, object()))

    monkeypatch.setattr(run_module, "run_scenario", run_test_scenario)

    summary = run_capture_smoke(
        CaptureSmokeConfig(settings=Settings(environment="test")),
        console=Console(output),
        client_factory=lambda base_url, timeout: requester,
        backend_factory=build_backend,
        current_date=date(2026, 8, 5),
    )

    assert all(client is requester for client, _ in received)
    assert [name for _, name in received] == [
        "complete_expense",
        "progressive_expense",
        "complete_income",
        "complete_transfer",
        "positive_adjustment",
        "ambiguous_category",
    ]
    assert summary == ScenarioSummary(total=6, passed=5, failed=1)
    assert output.getvalue() == (
        f"Running 6 scenario(s) against {DEFAULT_API_BASE_URL}\n"
        "FAIL complete_expense: candidate mismatch\n"
        "FAIL scenarios: 5/6\n"
    )


def test_runner_reports_safe_api_failure_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = io.StringIO()

    def fail_scenario(*args: object, **kwargs: object) -> None:
        raise SmokeFailure(
            "expected HTTP 201, got 502",
            response=HttpResponse(
                status_code=502,
                body={"detail": "Transaction capture is temporarily unavailable."},
                url="http://127.0.0.1:8000/api/v1/transaction-captures",
            ),
        )

    monkeypatch.setattr(run_module, "run_scenario", fail_scenario)
    summary = run_capture_smoke(
        CaptureSmokeConfig(
            settings=Settings(environment="test"),
            api_base_url="http://127.0.0.1:8000",
            use_existing_backend=True,
            selected_scenario="complete_expense",
        ),
        console=Console(output),
        client_factory=lambda base_url, timeout: FakeRequester(),
    )

    assert summary.failed == 1
    assert "Transaction capture is temporarily unavailable." in output.getvalue()
    assert "model" not in output.getvalue().lower()


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("backend unavailable"),
        ValueError("unknown scenario: missing"),
    ],
)
def test_main_reports_command_level_failures(
    error: Exception,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        run_module,
        "load_config",
        lambda argv: (_ for _ in ()).throw(error),
    )

    exit_code = main([])

    assert exit_code == 1
    assert capsys.readouterr().out == f"FAIL {error}\n"
