from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_documented_product_paths_exist() -> None:
    assert (REPO_ROOT / "docs/product/spec.md").is_file()
    assert (REPO_ROOT / "docs/product/concepts.md").is_file()
    assert (REPO_ROOT / "docs/product/archive/README.md").is_file()
