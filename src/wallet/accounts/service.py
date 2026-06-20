from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, field_validator

from .account import Account, AccountKind, AccountStatus
from .balances import BalanceSnapshot, BalanceSnapshotReason
from .repositories import (
    InMemoryAccountRepository,
    InMemoryBalanceSnapshotRepository,
)


class AccountNotFoundError(LookupError):
    pass


class OpenCashAccountRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["cash"] = "cash"
    name: str
    currency: str = "ARS"
    opening_balance_minor: int
    opened_on: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("account name must not be blank")
        return stripped

    @field_validator("opening_balance_minor")
    @classmethod
    def validate_opening_balance_minor(cls, value: int) -> int:
        if value < 0:
            raise ValueError("balance must not be negative")
        return value


OpenAccountRequest = OpenCashAccountRequest


class AccountSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    account: Account
    current_balance: BalanceSnapshot | None


class AccountService:
    def __init__(
        self,
        accounts: InMemoryAccountRepository | None = None,
        balances: InMemoryBalanceSnapshotRepository | None = None,
    ) -> None:
        self.accounts = accounts or InMemoryAccountRepository()
        self.balances = balances or InMemoryBalanceSnapshotRepository()

    def open_account(self, request: OpenAccountRequest) -> AccountSummary:
        opened_on = request.opened_on or date.today()
        account = Account.open_cash(
            id=_new_id("acct"),
            name=request.name,
            currency=request.currency,
            opened_on=opened_on,
        )
        opening_balance = BalanceSnapshot(
            id=_new_id("bal"),
            account_id=account.id,
            balance_minor=request.opening_balance_minor,
            checked_at=opened_on,
            reason="opening_balance",
        )
        self.accounts.add(account)
        self.balances.add(opening_balance)
        return AccountSummary(account=account, current_balance=opening_balance)

    def get_account_record(self, account_id: str) -> Account | None:
        return self.accounts.get(account_id)

    def get_account(self, account_id: str) -> AccountSummary | None:
        account = self.accounts.get(account_id)
        if account is None:
            return None
        return AccountSummary(
            account=account,
            current_balance=self.balances.get_latest_for_account(account_id),
        )

    def list_accounts(
        self,
        *,
        kind: AccountKind | None = None,
        status: AccountStatus | None = "active",
        currency: str | None = None,
    ) -> list[AccountSummary]:
        accounts = self.accounts.list()
        return [
            AccountSummary(
                account=account,
                current_balance=self.balances.get_latest_for_account(account.id),
            )
            for account in accounts
            if (kind is None or account.kind == kind)
            and (status is None or account.status == status)
            and (currency is None or account.currency == currency)
        ]

    def rename_account(self, account_id: str, name: str) -> AccountSummary:
        account = self._require_account(account_id)
        account.rename(name=name)
        self.accounts.save(account)
        return self._build_summary(account)

    def close_account(
        self,
        account_id: str,
    ) -> AccountSummary:
        account = self._require_account(account_id)
        account.close()
        self.accounts.save(account)
        return self._build_summary(account)

    def archive_account(self, account_id: str) -> AccountSummary:
        account = self._require_account(account_id)
        account.archive()
        self.accounts.save(account)
        return self._build_summary(account)

    def record_balance_snapshot(
        self,
        account_id: str,
        balance_minor: int,
        *,
        checked_at: date | None = None,
        reason: BalanceSnapshotReason = "manual_check",
    ) -> AccountSummary:
        account = self._require_account(account_id)
        account.ensure_can_record_balance_snapshot()
        snapshot = BalanceSnapshot(
            id=_new_id("bal"),
            account_id=account.id,
            balance_minor=balance_minor,
            checked_at=checked_at or date.today(),
            reason=reason,
        )
        self.balances.add(snapshot)
        return AccountSummary(account=account, current_balance=snapshot)

    def get_current_balance(self, account_id: str) -> BalanceSnapshot | None:
        self._require_account(account_id)
        return self.balances.get_latest_for_account(account_id)

    def list_balance_snapshots(self, account_id: str) -> list[BalanceSnapshot]:
        self._require_account(account_id)
        return self.balances.list_for_account(account_id)

    def _require_account(self, account_id: str) -> Account:
        account = self.accounts.get(account_id)
        if account is None:
            raise AccountNotFoundError(account_id)
        return account

    def _build_summary(self, account: Account) -> AccountSummary:
        return AccountSummary(
            account=account,
            current_balance=self.balances.get_latest_for_account(account.id),
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
