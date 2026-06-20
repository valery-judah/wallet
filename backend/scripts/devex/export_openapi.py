from __future__ import annotations

import argparse
import json
from pathlib import Path

from wallet.api.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]


def default_output_path() -> Path:
    frontend_dir = REPO_ROOT / "frontend"
    if frontend_dir.is_dir():
        return frontend_dir / "openapi.json"
    return REPO_ROOT / "openapi.json"


def resolve_output_path(value: str) -> Path:
    requested_path = Path(value)
    if requested_path.is_absolute():
        return requested_path.resolve()
    return (REPO_ROOT / requested_path).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the FastAPI OpenAPI schema for UI integration.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=str(default_output_path()),
        help="Output path for the generated OpenAPI JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = resolve_output_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    schema = create_app().openapi()
    output_path.write_text(f"{json.dumps(schema, indent=2)}\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
