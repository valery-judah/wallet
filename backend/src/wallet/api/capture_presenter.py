from __future__ import annotations

from typing import Protocol, TypeVar

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CaptureSession,
    CaptureStatus,
    PendingInteraction,
    PendingInteractionKind,
    TransactionCandidate,
)
from wallet.ai.transaction_capture.workflow import CaptureResult
from wallet.application.transactions import TransactionService
from wallet.domain.accounts import Account
from wallet.domain.transactions import TransactionType
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository

from .schemas import (
    CaptureCandidateResponse,
    CaptureInteractionResponse,
    CaptureResponse,
    TransactionResponse,
)


class _Category(Protocol):
    id: str
    name: str
    parent_id: str | None


_CategoryT = TypeVar("_CategoryT", bound=_Category)
_T = TypeVar("_T")


_REQUEST_MESSAGES: dict[CandidateField, str] = {
    CandidateField.TYPE: (
        "What kind of transaction is this: expense, income, transfer, or adjustment?"
    ),
    CandidateField.AMOUNT_MINOR: "How much?",
    CandidateField.OCCURRED_ON: "When did this happen?",
    CandidateField.ACCOUNT_ID: "Which account did you use?",
    CandidateField.SPENDING_CATEGORY_ID: "Which spending category should I use?",
    CandidateField.INCOME_CATEGORY_ID: "Which income category should I use?",
    CandidateField.SOURCE_ACCOUNT_ID: "Which account did the money come from?",
    CandidateField.DESTINATION_ACCOUNT_ID: "Which account did the money go to?",
    CandidateField.BALANCE_CHANGE_MINOR: "How much should the balance change?",
    CandidateField.DESCRIPTION: "What description should I use?",
    CandidateField.MERCHANT_NAME: "Which merchant should I use?",
    CandidateField.NOTES: "What notes should I use?",
}

_FIELD_LABELS: dict[CandidateField, str] = {
    CandidateField.TYPE: "transaction type",
    CandidateField.AMOUNT_MINOR: "amount",
    CandidateField.OCCURRED_ON: "date",
    CandidateField.ACCOUNT_ID: "account",
    CandidateField.SPENDING_CATEGORY_ID: "spending category",
    CandidateField.INCOME_CATEGORY_ID: "income category",
    CandidateField.SOURCE_ACCOUNT_ID: "source account",
    CandidateField.DESTINATION_ACCOUNT_ID: "destination account",
    CandidateField.BALANCE_CHANGE_MINOR: "balance change",
    CandidateField.DESCRIPTION: "description",
    CandidateField.MERCHANT_NAME: "merchant",
    CandidateField.NOTES: "notes",
}


class CapturePresenter:
    """Translate capture domain state into the stable public API representation."""

    def __init__(
        self,
        *,
        accounts: AccountRepository,
        spending_categories: SpendingCategoryRepository,
        income_categories: IncomeCategoryRepository,
        transactions: TransactionService,
    ) -> None:
        self._accounts = accounts
        self._spending_categories = spending_categories
        self._income_categories = income_categories
        self._transactions = transactions

    def present(self, result: CaptureResult) -> CaptureResponse:
        session = result.session
        transaction = self._transaction_response(session)
        return CaptureResponse(
            id=session.id,
            status=session.status,
            candidate=CaptureCandidateResponse.from_domain(session.candidate),
            interaction=(
                None
                if session.pending_interaction is None
                else CaptureInteractionResponse.from_domain(session.pending_interaction)
            ),
            message=self._message(session),
            transaction=transaction,
        )

    def _message(self, session: CaptureSession) -> str:
        match session.status:
            case CaptureStatus.ACTIVE:
                return self._interaction_message(session.pending_interaction)
            case CaptureStatus.AWAITING_CONFIRMATION:
                return f"Ready to record: {self._summary(session.candidate)}. Confirm or cancel."
            case CaptureStatus.COMPLETED:
                return f"Recorded: {self._summary(session.candidate)}."
            case CaptureStatus.CANCELLED:
                return "Capture cancelled."

    def _interaction_message(self, interaction: PendingInteraction | None) -> str:
        if interaction is None:
            return "Tell me about the transaction you want to record."
        if interaction.kind is PendingInteractionKind.CLARIFY:
            return "I couldn't confidently interpret that. Please rephrase it."
        field = interaction.field
        if field is None:
            return "Please provide the missing transaction information."
        if interaction.kind is PendingInteractionKind.DISAMBIGUATE:
            return f"Which {_FIELD_LABELS[field]} did you mean?"
        question = _REQUEST_MESSAGES[field]
        if interaction.kind is PendingInteractionKind.CORRECT:
            return f"I couldn't use that {_FIELD_LABELS[field]}. {question}"
        return question

    def _summary(self, candidate: TransactionCandidate) -> str:
        occurred_on = _required(candidate.occurred_on, name="occurred_on").isoformat()
        match candidate.type:
            case TransactionType.EXPENSE:
                account = self._account(candidate.account_id)
                amount = _format_money(
                    _required(candidate.amount_minor, name="amount_minor"),
                    account.currency,
                )
                category = self._category_label(
                    candidate.spending_category_id,
                    self._spending_categories,
                )
                return f"{amount} expense from {account.name} for {category} on {occurred_on}"
            case TransactionType.INCOME:
                account = self._account(candidate.account_id)
                amount = _format_money(
                    _required(candidate.amount_minor, name="amount_minor"),
                    account.currency,
                )
                category = self._category_label(
                    candidate.income_category_id,
                    self._income_categories,
                )
                return f"{amount} income to {account.name} from {category} on {occurred_on}"
            case TransactionType.TRANSFER:
                source = self._account(candidate.source_account_id)
                destination = self._account(candidate.destination_account_id)
                amount = _format_money(
                    _required(candidate.amount_minor, name="amount_minor"),
                    source.currency,
                )
                return (
                    f"{amount} transfer from {source.name} to {destination.name} on {occurred_on}"
                )
            case TransactionType.ADJUSTMENT:
                account = self._account(candidate.account_id)
                change = _required(candidate.balance_change_minor, name="balance_change_minor")
                direction = "increase" if change > 0 else "decrease"
                amount = _format_money(abs(change), account.currency)
                return f"{account.name} balance {direction} of {amount} on {occurred_on}"
            case None:
                raise ValueError("cannot summarize a candidate without a type")

    def _account(self, account_id: str | None) -> Account:
        resolved_id = _required(account_id, name="account_id")
        account = self._accounts.get(resolved_id)
        if account is None:
            raise ValueError(f"capture account is unavailable: {resolved_id}")
        return account

    def _category_label(
        self,
        category_id: str | None,
        repository: SpendingCategoryRepository | IncomeCategoryRepository,
    ) -> str:
        resolved_id = _required(category_id, name="category_id")
        category = repository.get(resolved_id)
        if category is None:
            raise ValueError(f"capture category is unavailable: {resolved_id}")
        categories = {item.id: item for item in repository.list()}
        return _category_path(category, categories=categories)

    def _transaction_response(self, session: CaptureSession) -> TransactionResponse | None:
        if session.transaction_id is None:
            return None
        transaction = self._transactions.get_transaction(session.transaction_id)
        return TransactionResponse.from_domain(transaction)


def _category_path(category: _CategoryT, *, categories: dict[str, _CategoryT]) -> str:
    names = [category.name]
    parent_id = category.parent_id
    visited = {category.id}
    while parent_id is not None and parent_id not in visited:
        visited.add(parent_id)
        parent = categories.get(parent_id)
        if parent is None:
            break
        names.append(parent.name)
        parent_id = parent.parent_id
    return " > ".join(reversed(names))


def _format_money(amount_minor: int, currency: str) -> str:
    sign = "-" if amount_minor < 0 else ""
    major, minor = divmod(abs(amount_minor), 100)
    return f"{sign}{currency} {major:,}.{minor:02d}"


def _required(value: _T | None, *, name: str) -> _T:
    if value is None:
        raise ValueError(f"capture candidate {name} is required")
    return value
