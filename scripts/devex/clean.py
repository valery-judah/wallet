from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_TOP_LEVEL_NAMES = {
    ".git",
    ".venv",
}
DIRECTORY_NAMES = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    "htmlcov",
}
FILE_NAMES = {
    ".coverage",
}
GLOB_PATTERNS = ("*.egg-info",)


def _iter_cleanup_paths() -> list[Path]:
    candidates: set[Path] = set()

    for path in ROOT.rglob("*"):
        if any(part in EXCLUDED_TOP_LEVEL_NAMES for part in path.relative_to(ROOT).parts):
            continue

        if path.name in DIRECTORY_NAMES | FILE_NAMES:
            candidates.add(path)

    for pattern in GLOB_PATTERNS:
        for path in ROOT.glob(pattern):
            if path.name not in EXCLUDED_TOP_LEVEL_NAMES:
                candidates.add(path)
        for path in ROOT.rglob(pattern):
            if any(part in EXCLUDED_TOP_LEVEL_NAMES for part in path.relative_to(ROOT).parts):
                continue
            candidates.add(path)

    return sorted(candidates, key=lambda path: (len(path.parts), str(path)), reverse=True)


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return

    path.unlink()


def main() -> int:
    removed_any = False

    for path in _iter_cleanup_paths():
        if not path.exists():
            continue

        _remove_path(path)
        removed_any = True
        print(path.relative_to(ROOT))

    if not removed_any:
        print("Nothing to clean.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
