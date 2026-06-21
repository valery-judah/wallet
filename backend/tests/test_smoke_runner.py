from __future__ import annotations

import importlib
import io
import socket
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

smoke_common = importlib.import_module("scripts.devex.smoke.common")
smoke_run = importlib.import_module("scripts.devex.smoke.run")

HttpClient = smoke_common.HttpClient
HttpResponse = smoke_common.HttpResponse
SmokeFailure = smoke_common.SmokeFailure
Console = smoke_run.Console
Scenario = smoke_run.Scenario
discover_scenarios = smoke_run.discover_scenarios
managed_backend = smoke_run.managed_backend
run_scenarios = smoke_run.run_scenarios
select_scenarios = smoke_run.select_scenarios


def test_discover_scenarios_sorts_by_filename(tmp_path: Path) -> None:
    first = tmp_path / "10_first.py"
    second = tmp_path / "20_second.py"
    second.write_text("name = 'second'\n\ndef run(client):\n    return None\n", encoding="utf-8")
    first.write_text("name = 'first'\n\ndef run(client):\n    return None\n", encoding="utf-8")

    scenarios = discover_scenarios(tmp_path)

    assert [scenario.name for scenario in scenarios] == ["first", "second"]


def test_select_scenarios_filters_by_name() -> None:
    scenarios = [
        Scenario(name="health", run=lambda client: None, path=Path("health.py")),
        Scenario(name="account_lifecycle", run=lambda client: None, path=Path("account.py")),
    ]

    selected = select_scenarios(scenarios, "account_lifecycle")

    assert [scenario.name for scenario in selected] == ["account_lifecycle"]


def test_select_scenarios_raises_for_unknown_name() -> None:
    scenarios = [Scenario(name="health", run=lambda client: None, path=Path("health.py"))]

    with pytest.raises(RuntimeError, match="unknown scenario: missing"):
        select_scenarios(scenarios, "missing")


def test_run_scenarios_reports_failure_summary() -> None:
    output = io.StringIO()
    console = Console(output=output, color=False)
    client = HttpClient("http://127.0.0.1:8000")

    def pass_scenario(_: HttpClient) -> None:
        return None

    def fail_scenario(_: HttpClient) -> None:
        raise SmokeFailure(
            "expected HTTP 409, got 200",
            response=HttpResponse(
                status_code=200,
                body={"detail": "wrong"},
                url="http://127.0.0.1:8000/api/v1/transactions",
            ),
        )

    summary = run_scenarios(
        client,
        [
            Scenario(name="health", run=pass_scenario, path=Path("health.py")),
            Scenario(name="insufficient_funds", run=fail_scenario, path=Path("insufficient.py")),
        ],
        console,
    )

    assert summary.total == 2
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.exit_code == 1
    assert output.getvalue() == (
        "PASS health\n"
        "FAIL insufficient_funds expected HTTP 409, got 200; "
        "url=http://127.0.0.1:8000/api/v1/transactions; "
        "status=200; body={'detail': 'wrong'}\n"
        "FAIL scenarios: 1/2 passed, 1 failed\n"
    )


def test_managed_backend_serves_health_and_stops() -> None:
    port = _reserve_local_port()
    base_url = f"http://127.0.0.1:{port}"

    with managed_backend(base_url) as backend:
        response = HttpClient(backend.base_url).request("GET", "/api/v1/health")

        assert response.status_code == 200
        assert backend.process.poll() is None

    assert backend.process.poll() is not None


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
