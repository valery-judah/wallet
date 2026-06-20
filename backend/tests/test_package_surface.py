from __future__ import annotations

import wallet


def test_wallet_package_exposes_metadata_only() -> None:
    assert wallet.__all__ == ["__version__"]
    assert wallet.__version__ == "0.1.0"
    assert not hasattr(wallet, "CardService")
