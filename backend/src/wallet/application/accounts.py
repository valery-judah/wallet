from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from wallet.domain._validation import normalize_currency, normalize_nonblank
from wallet.domain.accounts import Account, AccountNotFoundError, AccountType
from wallet.domain.money import Money
from wallet.domain.transactions import Posting, Transaction, TransactionStatus, TransactionType
from wallet.infrastructure.memory import InMemoryAccountRepository, InMemoryTransactionRepository
from wallet.ports.accounts import AccountRepository
from wallet.ports.system import (
    AccountIdGenerator,
    DateProvider,
    PostingIdGenerator,
    TransactionIdGenerator,
)
from wallet.ports.transactions import TransactionRepository


class CreateAccountRejectedError(ValueError):
    pass


class UpdateAccountRejectedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OpenAccount:
    name: str
    type: AccountType = AccountType.DEBIT_CARD
    currency: str = "ARS"
    opening_balance_minor: int = 0
    opened_on: date | None = None
    color_key: str | None = None

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
        if self.type is AccountType.SYSTEM:
            raise ValueError("account type must not be system")
        object.__setattr__(
            self,
            "currency",
            normalize_currency(self.currency, field_name="account currency"),
        )
        object.__setattr__(
            self,
            "color_key",
            _normalize_optional_value(
                self.color_key,
                field_name="account color key",
            ),
        )


@dataclass(frozen=True, slots=True)
class UpdateAccountProfile:
    account_id: str
    name: str
    type: AccountType
    color_key: str | None = None

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
        if self.type is AccountType.SYSTEM:
            raise ValueError("account type must not be system")
        object.__setattr__(
            self,
            "color_key",
            _normalize_optional_value(
                self.color_key,
                field_name="account color key",
            ),
        )


@dataclass(frozen=True, slots=True)
class ArchiveAccount:
    account_id: str
    archived_on: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_id",
            normalize_nonblank(self.account_id, field_name="account id"),
        )


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    account: Account
    current_balance: Money


class AccountService:
    def __init__(
        self,
        *,
        accounts: AccountRepository | None = None,
        transactions: TransactionRepository | None = None,
        today: DateProvider | None = None,
        generate_account_id: AccountIdGenerator | None = None,
        generate_transaction_id: TransactionIdGenerator | None = None,
        generate_posting_id: PostingIdGenerator | None = None,
    ) -> None:
        self.accounts = accounts or InMemoryAccountRepository()
        self.transactions = transactions or InMemoryTransactionRepository()
        self._today = today or date.today
        self._generate_account_id = generate_account_id or _new_account_id
        self._generate_transaction_id = generate_transaction_id or _new_transaction_id
        self._generate_posting_id = generate_posting_id or _new_posting_id

    def open_account(self, command: OpenAccount) -> AccountSnapshot:
        opened_on = command.opened_on or self._today()
        created_on = opened_on
        try:
            account = Account.open(
                id=self._generate_account_id(),
                name=command.name,
                type=command.type,
                currency=command.currency,
                color_key=command.color_key,
                opened_on=opened_on,
                created_on=created_on,
            )
        except ValueError as exc:
            raise CreateAccountRejectedError(str(exc)) from exc
        self.accounts.add(account)
        if command.opening_balance_minor != 0:
            self._record_opening_balance(
                account=account,
                amount_minor=command.opening_balance_minor,
                occurred_on=opened_on,
            )
        return self._snapshot(account)

    def update_account_profile(self, command: UpdateAccountProfile) -> AccountSnapshot:
        account = self._require_user_account(command.account_id)
        try:
            account.update_profile(
                name=command.name,
                type=command.type,
                color_key=command.color_key,
                updated_on=self._today(),
            )
        except ValueError as exc:
            raise UpdateAccountRejectedError(str(exc)) from exc
        self.accounts.save(account)
        return self._snapshot(account)

    def get_account(self, account_id: str) -> AccountSnapshot | None:
        account = self.accounts.get(account_id)
        if account is None or account.is_system:
            return None
        return self._snapshot(account)

    def list_accounts(self) -> list[AccountSnapshot]:
        return [
            self._snapshot(account) for account in self.accounts.list() if not account.is_system
        ]

    def archive_account(self, command: ArchiveAccount) -> AccountSnapshot:
        account = self._require_user_account(command.account_id)
        account.archive(archived_on=command.archived_on or self._today())
        self.accounts.save(account)
        return self._snapshot(account)

    def _snapshot(self, account: Account) -> AccountSnapshot:
        balance = Money.zero(account.currency)
        for transaction in self.transactions.list():
            for posting in transaction.postings:
                if posting.account_id == account.id:
                    balance = balance.add(
                        Money(amount_minor=posting.amount_minor, currency=posting.currency)
                    )
        return AccountSnapshot(account=account, current_balance=balance)

    def _record_opening_balance(
        self,
        *,
        account: Account,
        amount_minor: int,
        occurred_on: date,
    ) -> None:
        system_account = self._ensure_system_account(account.currency, occurred_on=occurred_on)
        transaction_id = self._generate_transaction_id()
        transaction = Transaction(
            id=transaction_id,
            occurred_on=occurred_on,
            posted_on=occurred_on,
            description="Opening balance",
            merchant_name=None,
            notes="Synthetic opening balance transaction",
            status=TransactionStatus.POSTED,
            type=TransactionType.ADJUSTMENT,
            postings=(
                Posting(
                    id=self._generate_posting_id(),
                    transaction_id=transaction_id,
                    account_id=account.id,
                    category_id=None,
                    amount_minor=amount_minor,
                    currency=account.currency,
                ),
                Posting(
                    id=self._generate_posting_id(),
                    transaction_id=transaction_id,
                    account_id=system_account.id,
                    category_id=None,
                    amount_minor=-amount_minor,
                    currency=account.currency,
                ),
            ),
            created_on=occurred_on,
            updated_on=occurred_on,
        )
        self.transactions.add(transaction)

    def _ensure_system_account(self, currency: str, *, occurred_on: date) -> Account:
        system_account_id = _system_account_id(currency)
        existing = self.accounts.get(system_account_id)
        if existing is not None:
            return existing
        account = Account.open(
            id=system_account_id,
            name=f"{currency} system equity",
            type=AccountType.SYSTEM,
            currency=currency,
            color_key=None,
            opened_on=occurred_on,
            created_on=occurred_on,
            is_system=True,
        )
        self.accounts.add(account)
        return account

    def _require_user_account(self, account_id: str) -> Account:
        account = self.accounts.get(account_id)
        if account is None or account.is_system:
            raise AccountNotFoundError(account_id)
        return account


def _new_account_id() -> str:
    return f"account_{uuid4().hex}"


def _new_transaction_id() -> str:
    return f"transaction_{uuid4().hex}"


def _new_posting_id() -> str:
    return f"posting_{uuid4().hex}"


def _system_account_id(currency: str) -> str:
    return f"system_equity_{currency.lower()}"


def _normalize_optional_value(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)
