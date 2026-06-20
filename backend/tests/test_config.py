from __future__ import annotations

from wallet.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.app_name == "Wallet API"
    assert settings.environment == "local"
    assert settings.debug is False
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.frontend_host == "http://localhost:5173"
    assert settings.all_cors_origins == ["http://localhost:5173"]


def test_get_settings_respects_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("WALLET_APP_NAME", "Wallet Override")
    monkeypatch.setenv("WALLET_ENVIRONMENT", "test")
    monkeypatch.setenv("WALLET_DEBUG", "true")
    monkeypatch.setenv("WALLET_API_V1_PREFIX", "/api/custom/")
    monkeypatch.setenv("WALLET_FRONTEND_HOST", "http://localhost:4173/")
    monkeypatch.setenv(
        "WALLET_BACKEND_CORS_ORIGINS",
        "http://localhost:3000/,https://wallet.example.com",
    )
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "Wallet Override"
    assert settings.environment == "test"
    assert settings.debug is True
    assert settings.api_v1_prefix == "/api/custom"
    assert settings.frontend_host == "http://localhost:4173/"
    assert settings.all_cors_origins == [
        "http://localhost:3000",
        "https://wallet.example.com",
        "http://localhost:4173",
    ]
    get_settings.cache_clear()


def test_settings_accept_list_based_cors_origins() -> None:
    settings = Settings(
        frontend_host="http://localhost:5173/",
        backend_cors_origins=[
            "http://localhost:3000/",
            "https://wallet.example.com/",
        ],
    )

    assert settings.all_cors_origins == [
        "http://localhost:3000",
        "https://wallet.example.com",
        "http://localhost:5173",
    ]
