from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from wallet.domain._validation import normalize_currency, normalize_nonblank, require_positive
from wallet.domain.accounts import Account, AccountNotFoundError, AccountType
from wallet.domain.money import Money
from wallet.infrastructure.memory import InMemoryAccountRepository
from wallet.ports.accounts import AccountRepository
from wallet.ports.system import AccountIdGenerator, DateProvider


class CreateAccountRejectedError(ValueError):
    pass


class UpdateAccountRejectedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OpenAccount:
    name: str
    type: AccountType = AccountType.CARD
    currency: str = "ARS"
    current_balance_minor: int = 0
    opened_on: date | None = None
    color_key: str | None = None
    icon_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "name",
            normalize_nonblank(self.name, field_name="account name"),
        )
        object.__setattr__(
            self,
            "type",
            AccountType(self.type),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_currency(self.currency, field_name="account currency"),
        )
        if self.current_balance_minor < 0:
            raise ValueError("account balance must not be negative")
        object.__setattr__(
            self,
            "color_key",
            _normalize_optional_value(
                self.color_key,
                field_name="account color key",
            ),
        )
        object.__setattr__(
            self,
            "icon_key",
            _normalize_optional_value(
                self.icon_key,
                field_name="account icon key",
            ),
        )


@dataclass(frozen=True, slots=True)
class UpdateAccountProfile:
    account_id: str
    name: str
    type: AccountType
    color_key: str | None = None
    icon_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_id",
            normalize_nonblank(self.account_id, field_name="account id"),
        )
        object.__setattr__(
            self,
            "name",
            normalize_nonblank(self.name, field_name="account name"),
        )
        object.__setattr__(
            self,
            "type",
            AccountType(self.type),
        )
        object.__setattr__(
            self,
            "color_key",
            _normalize_optional_value(
                self.color_key,
                field_name="account color key",
            ),
        )
        object.__setattr__(
            self,
            "icon_key",
            _normalize_optional_value(
                self.icon_key,
                field_name="account icon key",
            ),
        )


@dataclass(frozen=True, slots=True)
class CreditAccount:
    account_id: str
    amount: Money

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_id",
            normalize_nonblank(self.account_id, field_name="account id"),
        )
        require_positive(self.amount.amount_minor, field_name="amount")


@dataclass(frozen=True, slots=True)
class DebitAccount:
    account_id: str
    amount: Money

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_id",
            normalize_nonblank(self.account_id, field_name="account id"),
        )
        require_positive(self.amount.amount_minor, field_name="amount")


@dataclass(frozen=True, slots=True)
class CloseAccount:
    account_id: str
    closed_on: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_id",
            normalize_nonblank(self.account_id, field_name="account id"),
        )


class AccountService:
    def __init__(
        self,
        *,
        accounts: AccountRepository | None = None,
        today: DateProvider | None = None,
        generate_account_id: AccountIdGenerator | None = None,
    ) -> None:
        self.accounts = accounts or InMemoryAccountRepository()
        self._today = today or date.today
        self._generate_account_id = generate_account_id or _new_account_id

    def open_account(self, command: OpenAccount) -> Account:
        opened_on = command.opened_on or self._today()
        created_on = opened_on
        try:
            account = Account.open(
                id=self._generate_account_id(),
                name=command.name,
                type=command.type,
                currency=command.currency,
                current_balance=Money(
                    amount_minor=command.current_balance_minor,
                    currency=command.currency,
                ),
                color_key=command.color_key,
                icon_key=command.icon_key,
                opened_on=opened_on,
                created_on=created_on,
            )
        except ValueError as exc:
            raise CreateAccountRejectedError(str(exc)) from exc
        self.accounts.add(account)
        return account

    def update_account_profile(self, command: UpdateAccountProfile) -> Account:
        account = self._require_account(command.account_id)
        try:
            account.update_profile(
                name=command.name,
                type=command.type,
                color_key=command.color_key,
                icon_key=command.icon_key,
                updated_on=self._today(),
            )
        except ValueError as exc:
            raise UpdateAccountRejectedError(str(exc)) from exc
        self.accounts.save(account)
        return account

    def credit_account(self, command: CreditAccount) -> Account:
        account = self._require_account(command.account_id)
        account.credit(command.amount, updated_on=self._today())
        self.accounts.save(account)
        return account

    def debit_account(self, command: DebitAccount) -> Account:
        account = self._require_account(command.account_id)
        account.debit(command.amount, updated_on=self._today())
        self.accounts.save(account)
        return account

    def get_account(self, account_id: str) -> Account | None:
        return self.accounts.get(account_id)

    def list_accounts(self) -> list[Account]:
        return self.accounts.list()

    def close_account(self, command: CloseAccount) -> Account:
        account = self._require_account(command.account_id)
        account.close(closed_on=command.closed_on or self._today())
        self.accounts.save(account)
        return account

    def _require_account(self, account_id: str) -> Account:
        account = self.accounts.get(account_id)
        if account is None:
            raise AccountNotFoundError(account_id)
        return account


def _new_account_id() -> str:
    return f"account_{uuid4().hex}"


def _normalize_optional_value(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)
