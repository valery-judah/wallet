from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_export_openapi_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "devex" / "export_openapi.py"
    spec = importlib.util.spec_from_file_location("wallet_export_openapi", script_path)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load export_openapi.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_output_path_prefers_frontend_directory() -> None:
    export_openapi = _load_export_openapi_module()

    assert export_openapi.default_output_path() == (
        Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
    )


def test_resolve_output_path_uses_repo_root_for_relative_paths() -> None:
    export_openapi = _load_export_openapi_module()

    assert export_openapi.resolve_output_path("frontend/openapi.json") == (
        Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
    )
