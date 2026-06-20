from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

AccountKind = Literal["cash"]
AccountStatus = Literal["active", "closed", "archived"]
AccountAction = Literal["rename", "close", "archive", "record_balance_snapshot"]

ALLOWED_ACCOUNT_TRANSITIONS: dict[tuple[AccountStatus, AccountAction], AccountStatus] = {
    ("active", "rename"): "active",
    ("active", "record_balance_snapshot"): "active",
    ("active", "close"): "closed",
    ("closed", "rename"): "closed",
    ("closed", "archive"): "archived",
}


class InvalidAccountStateTransition(ValueError):
    pass


class Account(BaseModel):
    model_config = ConfigDict(frozen=False, validate_assignment=True)

    id: str
    name: str
    currency: str = "ARS"
    created_on: date
    kind: AccountKind = "cash"
    status: AccountStatus = "active"

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("account name must not be blank")
        return stripped

    @classmethod
    def open_cash(
        cls,
        *,
        id: str,
        name: str,
        currency: str,
        opened_on: date,
    ) -> Account:
        return cls(
            id=id,
            name=name,
            currency=currency,
            created_on=opened_on,
            kind="cash",
            status="active",
        )

    def rename(self, *, name: str) -> None:
        self._require_transition("rename")
        self.name = name

    def close(self) -> None:
        self._require_transition("close")
        self.status = "closed"

    def archive(self) -> None:
        self._require_transition("archive")
        self.status = "archived"

    def ensure_can_record_balance_snapshot(self) -> None:
        self._require_transition("record_balance_snapshot")

    def _require_transition(self, action: AccountAction) -> AccountStatus:
        next_status = ALLOWED_ACCOUNT_TRANSITIONS.get((self.status, action))
        if next_status is None:
            raise InvalidAccountStateTransition(
                f"cannot {action} account while status is {self.status}"
            )
        return next_status


CashAccount = Account
