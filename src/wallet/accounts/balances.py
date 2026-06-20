from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

BalanceSnapshotReason = Literal[
    "opening_balance",
    "manual_check",
    "statement_balance",
    "sync",
    "correction",
]


class BalanceSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    account_id: str
    balance_minor: int
    checked_at: date
    reason: BalanceSnapshotReason = "opening_balance"

    @field_validator("balance_minor")
    @classmethod
    def validate_balance_minor(cls, value: int) -> int:
        if value < 0:
            raise ValueError("balance must not be negative")
        return value
