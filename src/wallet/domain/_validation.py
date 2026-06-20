from __future__ import annotations


def normalize_nonblank(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def normalize_currency(value: str, *, field_name: str) -> str:
    return normalize_nonblank(value, field_name=field_name).upper()


def require_positive(amount_minor: int, *, field_name: str) -> None:
    if amount_minor <= 0:
        raise ValueError(f"{field_name} must be positive")
