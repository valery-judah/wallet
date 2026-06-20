from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AnyUrl, BeforeValidator, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def parse_cors(value: Any) -> list[str] | str:
    if isinstance(value, str) and not value.startswith("["):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list | str):
        return value
    raise ValueError(value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WALLET_",
        env_file=str(_ENV_FILE),
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "Wallet API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    frontend_host: str = "http://localhost:5173"
    backend_cors_origins: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_api_v1_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/") or "/"
        if not normalized.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        return normalized

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        configured = [str(origin).rstrip("/") for origin in self.backend_cors_origins]
        frontend = self.frontend_host.rstrip("/")
        if frontend in configured:
            return configured
        return [*configured, frontend]


@lru_cache
def get_settings() -> Settings:
    return Settings()
