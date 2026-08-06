from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from typing import TypeVar

from wallet.domain._validation import normalize_nonblank
from wallet.domain.transactions import TransactionType


class CaptureStatus(StrEnum):
    ACTIVE = "active"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CandidateField(StrEnum):
    TYPE = "type"
    AMOUNT_MINOR = "amount_minor"
    OCCURRED_ON = "occurred_on"
    ACCOUNT_ID = "account_id"
    SPENDING_CATEGORY_ID = "spending_category_id"
    INCOME_CATEGORY_ID = "income_category_id"
    SOURCE_ACCOUNT_ID = "source_account_id"
    DESTINATION_ACCOUNT_ID = "destination_account_id"
    BALANCE_CHANGE_MINOR = "balance_change_minor"
    DESCRIPTION = "description"
    MERCHANT_NAME = "merchant_name"
    NOTES = "notes"


class PendingInteractionKind(StrEnum):
    REQUEST_VALUE = "request_value"
    CORRECT = "correct"
    DISAMBIGUATE = "disambiguate"
    CLARIFY = "clarify"


class InvalidCaptureTransitionError(ValueError):
    pass


class _Unset:
    pass


_UNSET = _Unset()
_T = TypeVar("_T")


_REQUIRED_FIELDS: dict[TransactionType, tuple[CandidateField, ...]] = {
    TransactionType.EXPENSE: (
        CandidateField.AMOUNT_MINOR,
        CandidateField.ACCOUNT_ID,
        CandidateField.SPENDING_CATEGORY_ID,
        CandidateField.OCCURRED_ON,
    ),
    TransactionType.INCOME: (
        CandidateField.AMOUNT_MINOR,
        CandidateField.ACCOUNT_ID,
        CandidateField.INCOME_CATEGORY_ID,
        CandidateField.OCCURRED_ON,
    ),
    TransactionType.TRANSFER: (
        CandidateField.AMOUNT_MINOR,
        CandidateField.SOURCE_ACCOUNT_ID,
        CandidateField.DESTINATION_ACCOUNT_ID,
        CandidateField.OCCURRED_ON,
    ),
    TransactionType.ADJUSTMENT: (
        CandidateField.ACCOUNT_ID,
        CandidateField.BALANCE_CHANGE_MINOR,
        CandidateField.OCCURRED_ON,
    ),
}

_RELEVANT_FIELDS: dict[TransactionType, frozenset[str]] = {
    TransactionType.EXPENSE: frozenset(
        {
            "amount_minor",
            "occurred_on",
            "account_id",
            "spending_category_id",
            "description",
            "merchant_name",
            "notes",
        }
    ),
    TransactionType.INCOME: frozenset(
        {
            "amount_minor",
            "occurred_on",
            "account_id",
            "income_category_id",
            "description",
            "merchant_name",
            "notes",
        }
    ),
    TransactionType.TRANSFER: frozenset(
        {
            "amount_minor",
            "occurred_on",
            "source_account_id",
            "destination_account_id",
            "description",
            "merchant_name",
            "notes",
        }
    ),
    TransactionType.ADJUSTMENT: frozenset(
        {
            "occurred_on",
            "account_id",
            "balance_change_minor",
            "description",
            "merchant_name",
            "notes",
        }
    ),
}


def candidate_field_is_relevant(
    field: CandidateField,
    *,
    transaction_type: TransactionType | None,
) -> bool:
    """Return whether a field participates in the supplied transaction type."""

    if field is CandidateField.TYPE:
        return True
    if transaction_type is None:
        return field in {
            CandidateField.DESCRIPTION,
            CandidateField.MERCHANT_NAME,
            CandidateField.NOTES,
        }
    return field.value in _RELEVANT_FIELDS[transaction_type]


@dataclass(frozen=True, slots=True)
class CandidatePatch:
    """Sparse update where omitted fields are preserved and explicit ``None`` clears."""

    type: TransactionType | None | _Unset = _UNSET
    amount_minor: int | None | _Unset = _UNSET
    occurred_on: date | None | _Unset = _UNSET
    account_id: str | None | _Unset = _UNSET
    spending_category_id: str | None | _Unset = _UNSET
    income_category_id: str | None | _Unset = _UNSET
    source_account_id: str | None | _Unset = _UNSET
    destination_account_id: str | None | _Unset = _UNSET
    balance_change_minor: int | None | _Unset = _UNSET
    description: str | None | _Unset = _UNSET
    merchant_name: str | None | _Unset = _UNSET
    notes: str | None | _Unset = _UNSET

    @property
    def is_empty(self) -> bool:
        return all(
            isinstance(value, _Unset)
            for value in (
                self.type,
                self.amount_minor,
                self.occurred_on,
                self.account_id,
                self.spending_category_id,
                self.income_category_id,
                self.source_account_id,
                self.destination_account_id,
                self.balance_change_minor,
                self.description,
                self.merchant_name,
                self.notes,
            )
        )


@dataclass(frozen=True, slots=True)
class UserContribution:
    content: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "content",
            normalize_nonblank(self.content, field_name="user contribution"),
        )


@dataclass(frozen=True, slots=True)
class TransactionCandidate:
    """Progressively assembled transaction data with local completeness rules."""

    type: TransactionType | None = None
    amount_minor: int | None = None
    occurred_on: date | None = None
    account_id: str | None = None
    spending_category_id: str | None = None
    income_category_id: str | None = None
    source_account_id: str | None = None
    destination_account_id: str | None = None
    balance_change_minor: int | None = None
    description: str | None = None
    merchant_name: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.type is not None:
            object.__setattr__(self, "type", TransactionType(self.type))
        for field_name in (
            "account_id",
            "spending_category_id",
            "income_category_id",
            "source_account_id",
            "destination_account_id",
            "description",
            "merchant_name",
            "notes",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_optional_value(
                    getattr(self, field_name),
                    field_name=field_name.replace("_", " "),
                ),
            )

    @property
    def required_fields(self) -> tuple[CandidateField, ...]:
        if self.type is None:
            return (CandidateField.TYPE,)
        return _REQUIRED_FIELDS[self.type]

    def is_relevant(self, field: CandidateField) -> bool:
        """Return whether a field participates in the candidate's current type."""

        return candidate_field_is_relevant(field, transaction_type=self.type)

    @property
    def missing_fields(self) -> tuple[CandidateField, ...]:
        return tuple(field for field in self.required_fields if getattr(self, field.value) is None)

    @property
    def locally_invalid_fields(self) -> tuple[CandidateField, ...]:
        invalid: list[CandidateField] = []
        if self.type in {
            TransactionType.EXPENSE,
            TransactionType.INCOME,
            TransactionType.TRANSFER,
        }:
            if self.amount_minor is not None and self.amount_minor <= 0:
                invalid.append(CandidateField.AMOUNT_MINOR)
        if self.type is TransactionType.ADJUSTMENT and self.balance_change_minor == 0:
            invalid.append(CandidateField.BALANCE_CHANGE_MINOR)
        if (
            self.type is TransactionType.TRANSFER
            and self.source_account_id is not None
            and self.source_account_id == self.destination_account_id
        ):
            invalid.append(CandidateField.DESTINATION_ACCOUNT_ID)
        return tuple(invalid)

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields

    @property
    def is_locally_valid(self) -> bool:
        return not self.locally_invalid_fields

    def apply(self, patch: CandidatePatch) -> TransactionCandidate:
        next_type = _patched(self.type, patch.type)
        type_changed = next_type != self.type
        relevant_fields = (
            _RELEVANT_FIELDS[next_type] if type_changed and next_type is not None else None
        )
        return TransactionCandidate(
            type=next_type,
            amount_minor=_keep_if_relevant(
                "amount_minor",
                _patched(self.amount_minor, patch.amount_minor),
                relevant_fields,
            ),
            occurred_on=_keep_if_relevant(
                "occurred_on",
                _patched(self.occurred_on, patch.occurred_on),
                relevant_fields,
            ),
            account_id=_keep_if_relevant(
                "account_id",
                _patched(self.account_id, patch.account_id),
                relevant_fields,
            ),
            spending_category_id=_keep_if_relevant(
                "spending_category_id",
                _patched(self.spending_category_id, patch.spending_category_id),
                relevant_fields,
            ),
            income_category_id=_keep_if_relevant(
                "income_category_id",
                _patched(self.income_category_id, patch.income_category_id),
                relevant_fields,
            ),
            source_account_id=_keep_if_relevant(
                "source_account_id",
                _patched(self.source_account_id, patch.source_account_id),
                relevant_fields,
            ),
            destination_account_id=_keep_if_relevant(
                "destination_account_id",
                _patched(self.destination_account_id, patch.destination_account_id),
                relevant_fields,
            ),
            balance_change_minor=_keep_if_relevant(
                "balance_change_minor",
                _patched(self.balance_change_minor, patch.balance_change_minor),
                relevant_fields,
            ),
            description=_keep_if_relevant(
                "description",
                _patched(self.description, patch.description),
                relevant_fields,
            ),
            merchant_name=_keep_if_relevant(
                "merchant_name",
                _patched(self.merchant_name, patch.merchant_name),
                relevant_fields,
            ),
            notes=_keep_if_relevant(
                "notes",
                _patched(self.notes, patch.notes),
                relevant_fields,
            ),
        )


@dataclass(frozen=True, slots=True)
class InteractionOption:
    value: str
    label: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            normalize_nonblank(self.value, field_name="interaction option value"),
        )
        object.__setattr__(
            self,
            "label",
            normalize_nonblank(self.label, field_name="interaction option label"),
        )


@dataclass(frozen=True, slots=True)
class PendingInteraction:
    kind: PendingInteractionKind
    field: CandidateField | None = None
    options: tuple[InteractionOption, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", PendingInteractionKind(self.kind))
        if self.field is not None:
            object.__setattr__(self, "field", CandidateField(self.field))
        object.__setattr__(self, "options", tuple(self.options))
        if self.kind is PendingInteractionKind.CLARIFY and self.field is not None:
            raise ValueError("general clarification cannot target one field")
        if self.kind is not PendingInteractionKind.CLARIFY and self.field is None:
            raise ValueError("field interaction requires a candidate field")
        if self.kind is PendingInteractionKind.DISAMBIGUATE and len(self.options) < 2:
            raise ValueError("disambiguation requires at least two options")
        if self.kind is not PendingInteractionKind.DISAMBIGUATE and self.options:
            raise ValueError("only disambiguation can include options")


@dataclass(frozen=True, slots=True)
class CaptureSession:
    """Immutable in-memory lifecycle state enforcing active/completed invariants."""

    id: str
    candidate: TransactionCandidate
    pending_interaction: PendingInteraction | None
    status: CaptureStatus
    transaction_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "id",
            normalize_nonblank(self.id, field_name="capture session id"),
        )
        object.__setattr__(self, "status", CaptureStatus(self.status))
        object.__setattr__(
            self,
            "transaction_id",
            _normalize_optional_value(
                self.transaction_id,
                field_name="transaction id",
            ),
        )
        self._assert_consistent_state()

    @classmethod
    def start(cls, *, id: str, occurred_on: date) -> CaptureSession:
        return cls(
            id=id,
            candidate=TransactionCandidate(occurred_on=occurred_on),
            pending_interaction=None,
            status=CaptureStatus.ACTIVE,
            transaction_id=None,
        )

    def update_candidate(self, candidate: TransactionCandidate) -> CaptureSession:
        self._assert_active("update candidate")
        return replace(
            self,
            candidate=candidate,
            pending_interaction=None,
        )

    def request(self, interaction: PendingInteraction) -> CaptureSession:
        self._assert_active("request interaction")
        return replace(self, pending_interaction=interaction)

    def await_confirmation(self) -> CaptureSession:
        self._assert_active("request confirmation")
        if self.pending_interaction is not None:
            raise InvalidCaptureTransitionError("pending interaction must be resolved")
        if not self.candidate.is_complete:
            raise InvalidCaptureTransitionError("transaction candidate is incomplete")
        if not self.candidate.is_locally_valid:
            raise InvalidCaptureTransitionError("transaction candidate is invalid")
        return replace(self, status=CaptureStatus.AWAITING_CONFIRMATION)

    def resume(self) -> CaptureSession:
        self._assert_status(
            CaptureStatus.AWAITING_CONFIRMATION,
            action="resume capture",
        )
        return replace(self, status=CaptureStatus.ACTIVE)

    def cancel(self) -> CaptureSession:
        if self.status is CaptureStatus.CANCELLED:
            return self
        if self.status not in {CaptureStatus.ACTIVE, CaptureStatus.AWAITING_CONFIRMATION}:
            raise InvalidCaptureTransitionError(
                f"cannot cancel capture while status is {self.status.value}"
            )
        return replace(
            self,
            pending_interaction=None,
            status=CaptureStatus.CANCELLED,
        )

    def complete(self, *, transaction_id: str) -> CaptureSession:
        self._assert_status(
            CaptureStatus.AWAITING_CONFIRMATION,
            action="complete capture",
        )
        if self.pending_interaction is not None:
            raise InvalidCaptureTransitionError("pending interaction must be resolved")
        if not self.candidate.is_complete:
            raise InvalidCaptureTransitionError("transaction candidate is incomplete")
        if not self.candidate.is_locally_valid:
            raise InvalidCaptureTransitionError("transaction candidate is invalid")
        return replace(
            self,
            transaction_id=normalize_nonblank(
                transaction_id,
                field_name="transaction id",
            ),
            status=CaptureStatus.COMPLETED,
        )

    def _assert_active(self, action: str) -> None:
        self._assert_status(CaptureStatus.ACTIVE, action=action)

    def _assert_status(self, expected: CaptureStatus, *, action: str) -> None:
        if self.status is not expected:
            raise InvalidCaptureTransitionError(
                f"cannot {action} while status is {self.status.value}"
            )

    def _assert_consistent_state(self) -> None:
        if self.status is CaptureStatus.COMPLETED and self.transaction_id is None:
            raise ValueError("completed capture must have a transaction id")
        if self.status is not CaptureStatus.COMPLETED and self.transaction_id is not None:
            raise ValueError("only completed capture can have a transaction id")
        if self.status is not CaptureStatus.ACTIVE and self.pending_interaction is not None:
            raise ValueError("only active capture can have a pending interaction")
        if self.status is CaptureStatus.AWAITING_CONFIRMATION:
            if not self.candidate.is_complete:
                raise ValueError("confirmation requires a complete candidate")
            if not self.candidate.is_locally_valid:
                raise ValueError("confirmation requires a locally valid candidate")


def _normalize_optional_value(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)


def _patched(current: _T, update: _T | _Unset) -> _T:
    if isinstance(update, _Unset):
        return current
    return update


def _keep_if_relevant(
    field_name: str,
    value: _T,
    relevant_fields: frozenset[str] | None,
) -> _T | None:
    if relevant_fields is not None and field_name not in relevant_fields:
        return None
    return value
