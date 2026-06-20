from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TextIO
from urllib.parse import urlparse

from scripts.devex.smoke.common import HttpClient, SmokeFailure

BACKEND_ROOT = Path(__file__).resolve().parents[3]
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_MANAGED_BASE_URL = "http://127.0.0.1:8010"
READINESS_TIMEOUT_SECONDS = 10.0
SHUTDOWN_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class Scenario:
    name: str
    run: Callable[[HttpClient], None]
    path: Path


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    passed: bool
    detail: str | None = None


@dataclass(frozen=True)
class ScenarioSummary:
    total: int
    passed: int
    failed: int

    @property
    def exit_code(self) -> int:
        return 0 if self.failed == 0 else 1


@dataclass(frozen=True)
class ManagedBackend:
    base_url: str
    process: subprocess.Popen[str]


class Console:
    def __init__(self, output: TextIO | None = None, *, color: bool | None = None) -> None:
        self.output = output or sys.stdout
        self.color = self.output.isatty() if color is None else color

    def info(self, message: str) -> None:
        self._write(message)

    def scenario(self, result: ScenarioResult) -> None:
        label = "PASS" if result.passed else "FAIL"
        colored_label = self._colorize(label, "32" if result.passed else "31")
        detail = f" {result.detail}" if result.detail else ""
        self._write(f"{colored_label} {result.name}{detail}")

    def summary(self, summary: ScenarioSummary) -> None:
        label = "PASS" if summary.failed == 0 else "FAIL"
        colored_label = self._colorize(label, "32" if summary.failed == 0 else "31")
        self._write(
            f"{colored_label} scenarios: {summary.passed}/{summary.total} passed, "
            f"{summary.failed} failed"
        )

    def _colorize(self, text: str, code: str) -> str:
        if not self.color:
            return text
        return f"\033[{code}m{text}\033[0m"

    def _write(self, message: str) -> None:
        self.output.write(f"{message}\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run manual API smoke scenarios.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Backend base URL for smoke requests.",
    )
    parser.add_argument(
        "--managed",
        action="store_true",
        help="Start and stop a temporary backend for the run.",
    )
    parser.add_argument(
        "--scenario",
        help="Run a single scenario by name.",
    )
    return parser.parse_args(argv)


def discover_scenarios(scenarios_dir: Path = SCENARIOS_DIR) -> list[Scenario]:
    scenarios: list[Scenario] = []

    for path in sorted(scenarios_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue

        module = _load_module(path)
        name = getattr(module, "name", None)
        run = getattr(module, "run", None)
        if not isinstance(name, str) or not callable(run):
            raise RuntimeError(f"invalid scenario module: {path}")
        scenarios.append(Scenario(name=name, run=run, path=path))

    return scenarios


def select_scenarios(scenarios: Sequence[Scenario], selected_name: str | None) -> list[Scenario]:
    if selected_name is None:
        return list(scenarios)

    selected = [scenario for scenario in scenarios if scenario.name == selected_name]
    if not selected:
        raise RuntimeError(f"unknown scenario: {selected_name}")
    return selected


def run_scenarios(
    client: HttpClient,
    scenarios: Iterable[Scenario],
    console: Console,
) -> ScenarioSummary:
    total = 0
    passed = 0

    for scenario in scenarios:
        total += 1
        try:
            scenario.run(client)
        except Exception as exc:
            console.scenario(
                ScenarioResult(name=scenario.name, passed=False, detail=_format_error(exc))
            )
            continue

        passed += 1
        console.scenario(ScenarioResult(name=scenario.name, passed=True))

    summary = ScenarioSummary(total=total, passed=passed, failed=total - passed)
    console.summary(summary)
    return summary


@contextmanager
def managed_backend(base_url: str) -> Iterator[ManagedBackend]:
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or parsed_url.hostname is None:
        raise RuntimeError(f"managed mode requires a full HTTP base URL: {base_url}")
    if parsed_url.port is None:
        raise RuntimeError(f"managed mode requires an explicit port in base URL: {base_url}")
    if parsed_url.path not in {"", "/"}:
        raise RuntimeError("managed mode base URL must not include a path")

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--factory",
            "wallet.api.app:create_app",
            "--host",
            parsed_url.hostname,
            "--port",
            str(parsed_url.port),
        ],
        cwd=BACKEND_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    backend = ManagedBackend(base_url=base_url.rstrip("/"), process=process)

    try:
        wait_for_backend_ready(backend)
        yield backend
    finally:
        _stop_process(process)


def wait_for_backend_ready(backend: ManagedBackend) -> None:
    client = HttpClient(backend.base_url, timeout_seconds=1.0)
    deadline = time.monotonic() + READINESS_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if backend.process.poll() is not None:
            raise RuntimeError(
                "managed backend exited before readiness\n"
                + _collect_process_output(backend.process)
            )

        try:
            response = client.request("GET", "/api/v1/health")
        except SmokeFailure:
            time.sleep(0.1)
            continue

        if response.status_code == 200:
            return
        time.sleep(0.1)

    raise RuntimeError(
        "managed backend did not become ready in time\n" + _collect_process_output(backend.process)
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.managed and args.base_url == DEFAULT_BASE_URL:
        base_url = DEFAULT_MANAGED_BASE_URL
    else:
        base_url = args.base_url

    scenarios = select_scenarios(discover_scenarios(), args.scenario)
    console = Console()
    console.info(f"Running {len(scenarios)} scenario(s) against {base_url}")

    if args.managed:
        with managed_backend(base_url) as backend:
            summary = run_scenarios(HttpClient(backend.base_url), scenarios, console)
    else:
        summary = run_scenarios(HttpClient(base_url), scenarios, console)

    return summary.exit_code


def _load_module(path: Path) -> ModuleType:
    module_name = f"wallet_smoke_{path.stem}_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load scenario module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _format_error(exc: Exception) -> str:
    if isinstance(exc, SmokeFailure):
        detail = str(exc)
        if exc.response is None:
            return detail
        return (
            f"{detail}; url={exc.response.url}; status={exc.response.status_code}; "
            f"body={exc.response.body!r}"
        )

    return str(exc) or exc.__class__.__name__


def _collect_process_output(process: subprocess.Popen[str]) -> str:
    if process.stdout is None:
        return ""

    if process.poll() is None:
        return ""

    output = process.stdout.read()
    return output.strip()


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
