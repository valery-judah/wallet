from __future__ import annotations

from pathlib import Path


def test_documented_product_paths_exist() -> None:
    assert Path("docs/product/spec.md").is_file()
    assert Path("docs/product/concepts.md").is_file()
    assert Path("docs/product/archive/README.md").is_file()
