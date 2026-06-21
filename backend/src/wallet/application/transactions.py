from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from wallet.domain._validation import normalize_currency, normalize_nonblank
from wallet.domain.accounts import Account, AccountNotFoundError, AccountType
from wallet.domain.income_categories import IncomeCategoryNotFoundError
from wallet.domain.spending_categories import SpendingCategoryNotFoundError
from wallet.domain.transactions import (
    Posting,
    Transaction,
    TransactionNotFoundError,
    TransactionStatus,
    TransactionType,
)
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository
from wallet.ports.system import DateProvider, PostingIdGenerator, TransactionIdGenerator
from wallet.ports.transactions import TransactionRepository


class CreateTransactionRejectedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CreatePosting:
    account_id: str | None = None
    category_id: str | None = None
    amount_minor: int = 0
    currency: str = "ARS"
    memo: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_id",
            _normalize_optional_value(self.account_id, field_name="account id"),
        )
        object.__setattr__(
            self,
            "category_id",
            _normalize_optional_value(self.category_id, field_name="category id"),
        )
        object.__setattr__(
            self,
            "currency",
            normalize_currency(self.currency, field_name="posting currency"),
        )
        object.__setattr__(
            self,
            "memo",
            _normalize_optional_value(self.memo, field_name="posting memo"),
        )


@dataclass(frozen=True, slots=True)
class CreateTransaction:
    type: TransactionType
    postings: tuple[CreatePosting, ...]
    occurred_on: date | None = None
    description: str | None = None
    merchant_name: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", TransactionType(self.type))
        object.__setattr__(
            self,
            "postings",
            tuple(self.postings),
        )
        object.__setattr__(
            self,
            "description",
            _normalize_optional_value(self.description, field_name="transaction description"),
        )
        object.__setattr__(
            self,
            "merchant_name",
            _normalize_optional_value(self.merchant_name, field_name="merchant name"),
        )
        object.__setattr__(
            self,
            "notes",
            _normalize_optional_value(self.notes, field_name="transaction notes"),
        )
        if not self.postings:
            raise ValueError("transaction must include postings")


class TransactionService:
    def __init__(
        self,
        *,
        accounts: AccountRepository | None = None,
        spending_categories: SpendingCategoryRepository | None = None,
        income_categories: IncomeCategoryRepository | None = None,
        transactions: TransactionRepository | None = None,
        today: DateProvider | None = None,
        generate_transaction_id: TransactionIdGenerator | None = None,
        generate_posting_id: PostingIdGenerator | None = None,
    ) -> None:
        self.accounts = accounts or InMemoryAccountRepository()
        self.spending_categories = spending_categories or InMemorySpendingCategoryRepository()
        self.income_categories = income_categories or InMemoryIncomeCategoryRepository()
        self.transactions = transactions or InMemoryTransactionRepository()
        self._today = today or date.today
        self._generate_transaction_id = generate_transaction_id or _new_transaction_id
        self._generate_posting_id = generate_posting_id or _new_posting_id

    def create_transaction(self, command: CreateTransaction) -> Transaction:
        occurred_on = command.occurred_on or self._today()
        transaction_id = self._generate_transaction_id()
        postings = list(command.postings)
        if command.type is TransactionType.ADJUSTMENT and len(postings) == 1:
            first = postings[0]
            if first.account_id is None or first.category_id is not None:
                raise CreateTransactionRejectedError(
                    "adjustment transactions must target an account",
                )
            system_account = self._ensure_system_account(first.currency, occurred_on=occurred_on)
            postings.append(
                CreatePosting(
                    account_id=system_account.id,
                    amount_minor=-first.amount_minor,
                    currency=first.currency,
                    memo=first.memo,
                )
            )
        try:
            resolved_postings = tuple(
                self._build_posting(
                    transaction_id=transaction_id, posting=posting, tx_type=command.type
                )
                for posting in postings
            )
            transaction = Transaction(
                id=transaction_id,
                occurred_on=occurred_on,
                posted_on=occurred_on,
                description=command.description,
                merchant_name=command.merchant_name,
                notes=command.notes,
                status=TransactionStatus.POSTED,
                type=command.type,
                postings=resolved_postings,
                created_on=occurred_on,
                updated_on=occurred_on,
            )
        except ValueError as exc:
            raise CreateTransactionRejectedError(str(exc)) from exc
        self._validate_transaction_references(transaction)
        self.transactions.add(transaction)
        return transaction

    def get_transaction(self, transaction_id: str) -> Transaction:
        transaction = self.transactions.get(transaction_id)
        if transaction is None:
            raise TransactionNotFoundError(transaction_id)
        return transaction

    def list_transactions(self, *, account_id: str | None = None) -> list[Transaction]:
        transactions = self.transactions.list()
        if account_id is None:
            return transactions
        self._require_visible_account(account_id)
        return [
            transaction
            for transaction in transactions
            if any(posting.account_id == account_id for posting in transaction.postings)
        ]

    def _build_posting(
        self,
        *,
        transaction_id: str,
        posting: CreatePosting,
        tx_type: TransactionType,
    ) -> Posting:
        if posting.account_id is not None:
            account = self.accounts.get(posting.account_id)
            if account is None:
                raise AccountNotFoundError(posting.account_id)
            if account.currency != posting.currency:
                raise ValueError("currency mismatch")
            if not account.is_system:
                account.assert_allows_transactions()
            if tx_type is not TransactionType.ADJUSTMENT and account.is_system:
                raise ValueError("system account postings are only allowed for adjustments")
        if posting.category_id is not None:
            self._require_category_exists(posting.category_id, tx_type)
        return Posting(
            id=self._generate_posting_id(),
            transaction_id=transaction_id,
            account_id=posting.account_id,
            category_id=posting.category_id,
            amount_minor=posting.amount_minor,
            currency=posting.currency,
            memo=posting.memo,
        )

    def _validate_transaction_references(self, transaction: Transaction) -> None:
        accounts = [
            self.accounts.get(posting.account_id)
            for posting in transaction.postings
            if posting.account_id is not None
        ]
        if any(account is None for account in accounts):
            raise CreateTransactionRejectedError("account not found")

        if transaction.type is TransactionType.EXPENSE:
            self._assert_only_spending_categories(transaction)
        if transaction.type is TransactionType.INCOME:
            self._assert_only_income_categories(transaction)
        if transaction.type is TransactionType.TRANSFER and self._has_category_postings(
            transaction
        ):
            raise CreateTransactionRejectedError(
                "transfer transactions must not use categories",
            )
        if transaction.type is TransactionType.ADJUSTMENT:
            if self._has_category_postings(transaction):
                raise CreateTransactionRejectedError(
                    "adjustment transactions must not use categories",
                )
            system_accounts = [
                account for account in accounts if account is not None and account.is_system
            ]
            user_accounts = [
                account for account in accounts if account is not None and not account.is_system
            ]
            if len(system_accounts) != 1 or len(user_accounts) != 1:
                raise CreateTransactionRejectedError(
                    "adjustment transactions must use one user account and one system account",
                )

    def _ensure_system_account(self, currency: str, *, occurred_on: date) -> Account:
        system_account_id = _system_account_id(currency)
        existing = self.accounts.get(system_account_id)
        if existing is not None:
            return existing

        system_account = Account.open(
            id=system_account_id,
            name=f"{currency} system equity",
            type=AccountType.SYSTEM,
            currency=currency,
            color_key=None,
            opened_on=occurred_on,
            created_on=occurred_on,
            is_system=True,
        )
        self.accounts.add(system_account)
        return system_account

    def _require_visible_account(self, account_id: str) -> None:
        account = self.accounts.get(account_id)
        if account is None or account.is_system:
            raise AccountNotFoundError(account_id)

    def _require_category_exists(self, category_id: str, tx_type: TransactionType) -> None:
        if tx_type is TransactionType.EXPENSE:
            if self.income_categories.get(category_id) is not None:
                raise ValueError("expense transactions must use spending categories")
            if self.spending_categories.get(category_id) is None:
                raise SpendingCategoryNotFoundError(category_id)
            return
        if tx_type is TransactionType.INCOME:
            if self.spending_categories.get(category_id) is not None:
                raise ValueError("income transactions must use income categories")
            if self.income_categories.get(category_id) is None:
                raise IncomeCategoryNotFoundError(category_id)
            return
        raise CreateTransactionRejectedError(
            f"{tx_type.value} transactions must not use categories",
        )

    def _assert_only_spending_categories(self, transaction: Transaction) -> None:
        for posting in transaction.postings:
            if posting.category_id is None:
                continue
            if self.spending_categories.get(posting.category_id) is None:
                raise CreateTransactionRejectedError(
                    "expense transactions must use spending categories",
                )

    def _assert_only_income_categories(self, transaction: Transaction) -> None:
        for posting in transaction.postings:
            if posting.category_id is None:
                continue
            if self.income_categories.get(posting.category_id) is None:
                raise CreateTransactionRejectedError(
                    "income transactions must use income categories",
                )

    def _has_category_postings(self, transaction: Transaction) -> bool:
        return any(posting.category_id is not None for posting in transaction.postings)


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
