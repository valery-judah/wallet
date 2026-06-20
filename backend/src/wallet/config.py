from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import AnyUrl, BeforeValidator, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def parse_cors(value: Any) -> list[str] | str:
    if isinstance(value, str) and not value.startswith("["):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list | str):
        return value
    raise ValueError(value)


def normalize_origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return value.rstrip("/")


def get_loopback_twin(origin: str) -> str | None:
    parsed = urlsplit(origin)
    hostname = parsed.hostname
    if hostname not in {"localhost", "127.0.0.1"}:
        return None

    twin_host = "127.0.0.1" if hostname == "localhost" else "localhost"
    netloc = twin_host
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    return f"{parsed.scheme}://{netloc}"


def unique_origins(origins: list[str]) -> list[str]:
    return list(dict.fromkeys(origins))


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
        frontend = normalize_origin(self.frontend_host)
        twin = get_loopback_twin(frontend)
        configured = [normalize_origin(str(origin)) for origin in self.backend_cors_origins]

        origins = [frontend]
        if twin:
            origins.append(twin)
        origins.extend(configured)
        return unique_origins(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
