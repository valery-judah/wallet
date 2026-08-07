from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Protocol, TypeVar

from wallet.ai.capabilities.contract import CapabilityActionOffer, CapabilityView
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CapturePhase,
    PendingInteraction,
    PendingInteractionKind,
    PendingInteractionReason,
    TransactionCandidate,
    TransactionCaptureState,
)
from wallet.domain.accounts import Account
from wallet.domain.transactions import Transaction, TransactionType
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository


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
    CandidateField.CURRENCY_CODE: "Which currency should I use?",
}

_FIELD_LABELS: dict[CandidateField, str] = {
    field: field.value.replace("_id", "").replace("_minor", "").replace("_", " ")
    for field in CandidateField
}


class CapturePresentation:
    def __init__(
        self,
        *,
        accounts: AccountRepository,
        spending_categories: SpendingCategoryRepository,
        income_categories: IncomeCategoryRepository,
    ) -> None:
        self._accounts = accounts
        self._spending_categories = spending_categories
        self._income_categories = income_categories

    def view(self, state: TransactionCaptureState) -> CapabilityView:
        interaction = state.pending_interaction
        interaction_data: dict[str, object] | None = None
        if interaction is not None:
            interaction_data = {
                "kind": interaction.kind.value,
                "field": None if interaction.field is None else interaction.field.value,
                "options": [
                    {"value": option.value, "label": option.label} for option in interaction.options
                ],
            }
            if interaction.reason is not None:
                interaction_data["reason"] = interaction.reason.value
        actions = (
            (CapabilityActionOffer(action="confirm", label="Confirm", payload={}),)
            if state.phase is CapturePhase.AWAITING_CONFIRMATION
            else ()
        )
        return CapabilityView(
            kind="transaction_capture",
            data={
                "phase": state.phase.value,
                "candidate": candidate_projection(state.candidate),
                "interaction": interaction_data,
            },
            available_actions=actions,
        )

    def message(self, state: TransactionCaptureState) -> str:
        if state.phase is CapturePhase.ACTIVE:
            return self._interaction_message(state.pending_interaction, state.candidate)
        return f"Ready to record: {self.summary(state.candidate)}. Confirm or cancel."

    def recorded_message(self, candidate: TransactionCandidate) -> str:
        return f"Recorded: {self.summary(candidate)}."

    def summary(self, candidate: TransactionCandidate) -> str:
        occurred_on = _required(candidate.occurred_on, name="occurred_on").isoformat()
        match candidate.type:
            case TransactionType.EXPENSE:
                account = self._account(candidate.account_id)
                amount = _format_money(
                    _required(candidate.amount_minor, name="amount_minor"), account.currency
                )
                category = self._category_label(
                    candidate.spending_category_id, self._spending_categories
                )
                return f"{amount} expense from {account.name} for {category} on {occurred_on}"
            case TransactionType.INCOME:
                account = self._account(candidate.account_id)
                amount = _format_money(
                    _required(candidate.amount_minor, name="amount_minor"), account.currency
                )
                category = self._category_label(
                    candidate.income_category_id, self._income_categories
                )
                return f"{amount} income to {account.name} from {category} on {occurred_on}"
            case TransactionType.TRANSFER:
                source = self._account(candidate.source_account_id)
                destination = self._account(candidate.destination_account_id)
                amount = _format_money(
                    _required(candidate.amount_minor, name="amount_minor"), source.currency
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

    def _interaction_message(
        self,
        interaction: PendingInteraction | None,
        candidate: TransactionCandidate,
    ) -> str:
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
            if interaction.reason is PendingInteractionReason.CURRENCY_CONFLICT:
                currency = candidate.currency_code or "the stated currency"
                return (
                    f"That {_FIELD_LABELS[field]}'s currency does not match {currency}. {question}"
                )
            return f"I couldn't use that {_FIELD_LABELS[field]}. {question}"
        return question

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


def candidate_projection(candidate: TransactionCandidate) -> dict[str, object]:
    return {
        "type": None if candidate.type is None else candidate.type.value,
        "amount_minor": candidate.amount_minor,
        "occurred_on": (
            None if candidate.occurred_on is None else candidate.occurred_on.isoformat()
        ),
        "account_id": candidate.account_id,
        "spending_category_id": candidate.spending_category_id,
        "income_category_id": candidate.income_category_id,
        "source_account_id": candidate.source_account_id,
        "destination_account_id": candidate.destination_account_id,
        "balance_change_minor": candidate.balance_change_minor,
        "description": candidate.description,
        "merchant_name": candidate.merchant_name,
        "notes": candidate.notes,
        "currency_code": candidate.currency_code,
    }


def transaction_projection(transaction: Transaction) -> dict[str, object]:
    return {
        "id": transaction.id,
        "occurred_on": transaction.occurred_on.isoformat(),
        "posted_on": (None if transaction.posted_on is None else transaction.posted_on.isoformat()),
        "description": transaction.description,
        "merchant_name": transaction.merchant_name,
        "notes": transaction.notes,
        "status": transaction.status.value,
        "type": transaction.type.value,
        "postings": [
            {
                "id": posting.id,
                "account_id": posting.account_id,
                "category_id": posting.category_id,
                "amount_minor": posting.amount_minor,
                "currency": posting.currency,
                "memo": posting.memo,
            }
            for posting in transaction.postings
        ],
        "created_on": transaction.created_on.isoformat(),
        "updated_on": transaction.updated_on.isoformat(),
    }


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


def json_scalar(value: date | Enum | str | int | None) -> str | int | None:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    return value
