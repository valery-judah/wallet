from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date

from wallet.ai.llm import StructuredChatModel
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    PendingInteraction,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.interpretation import (
    ContributionInterpretation,
    ContributionInterpreter,
    InterpretationEvidence,
    LlmContributionInterpreter,
    ReferenceAmbiguity,
)
from wallet.ai.transaction_capture.ports import (
    CaptureReferenceCatalog,
    CaptureReferenceProvider,
)
from wallet.domain.transactions import TransactionType


@dataclass(frozen=True, slots=True)
class CurrencyConflict:
    field: CandidateField
    expected_currency: str
    actual_currency: str


@dataclass(frozen=True, slots=True)
class ContributionProcessingTrace:
    attempt_count: int
    applied_fields: tuple[CandidateField, ...]
    ambiguities: tuple[ReferenceAmbiguity, ...] = ()
    unresolved_fields: tuple[CandidateField, ...] = ()
    currency_conflicts: tuple[CurrencyConflict, ...] = ()
    clarification_needed: bool = False
    evidence: tuple[InterpretationEvidence, ...] = ()


@dataclass(frozen=True, slots=True)
class ContributionProcessingResult:
    candidate: TransactionCandidate
    trace: ContributionProcessingTrace


class ModelDrivenContributionProcessor:
    """Apply one permissive model interpretation behind deterministic validation."""

    def __init__(
        self,
        *,
        interpreter: ContributionInterpreter,
        references: CaptureReferenceProvider,
    ) -> None:
        self._interpreter = interpreter
        self._references = references

    def process(
        self,
        contribution: UserContribution,
        *,
        candidate: TransactionCandidate,
        pending_interaction: PendingInteraction | None,
        on_date: date,
    ) -> ContributionProcessingResult:
        reference_snapshot = self._references.capture_references()
        interpretation = self._interpreter.interpret(
            contribution,
            candidate=candidate,
            pending_interaction=pending_interaction,
            references=reference_snapshot,
            on_date=on_date,
        )
        return _apply_interpretation(
            candidate,
            interpretation=interpretation,
            references=reference_snapshot,
        )


@dataclass(frozen=True, slots=True)
class ModelDrivenContributionProcessorFactory:
    model: StructuredChatModel

    def build(
        self,
        *,
        references: CaptureReferenceProvider,
    ) -> ModelDrivenContributionProcessor:
        return ModelDrivenContributionProcessor(
            interpreter=LlmContributionInterpreter(model=self.model),
            references=references,
        )


def _apply_interpretation(
    candidate: TransactionCandidate,
    *,
    interpretation: ContributionInterpretation,
    references: CaptureReferenceCatalog,
) -> ContributionProcessingResult:
    patch = interpretation.patch
    projected = candidate.apply(patch)
    ambiguities = tuple(
        item for item in interpretation.ambiguities if projected.is_relevant(item.field)
    )
    unresolved = tuple(
        field for field in interpretation.unresolved_fields if projected.is_relevant(field)
    )

    invalid_references = _invalid_reference_fields(projected, references=references)
    unresolved = _distinct((*unresolved, *invalid_references))
    conflicts = _currency_conflicts(projected, references=references)

    for ambiguity in ambiguities:
        patch = _clear_patch_field(patch, ambiguity.field)
    for field in unresolved:
        patch = _clear_patch_field(patch, field)
    for conflict in conflicts:
        patch = _clear_patch_field(patch, conflict.field)
    reduced = candidate.apply(patch)

    return ContributionProcessingResult(
        candidate=reduced,
        trace=ContributionProcessingTrace(
            attempt_count=interpretation.attempt_count,
            applied_fields=_changed_fields(candidate, reduced),
            ambiguities=ambiguities,
            unresolved_fields=unresolved,
            currency_conflicts=conflicts,
            clarification_needed=interpretation.clarification_needed,
            evidence=interpretation.evidence,
        ),
    )


def _invalid_reference_fields(
    candidate: TransactionCandidate,
    *,
    references: CaptureReferenceCatalog,
) -> tuple[CandidateField, ...]:
    account_ids = {reference.id for reference in references.accounts}
    spending_ids = {reference.id for reference in references.spending_categories}
    income_ids = {reference.id for reference in references.income_categories}
    invalid: list[CandidateField] = []
    for field, available in (
        (CandidateField.ACCOUNT_ID, account_ids),
        (CandidateField.SOURCE_ACCOUNT_ID, account_ids),
        (CandidateField.DESTINATION_ACCOUNT_ID, account_ids),
        (CandidateField.SPENDING_CATEGORY_ID, spending_ids),
        (CandidateField.INCOME_CATEGORY_ID, income_ids),
    ):
        value = getattr(candidate, field.value)
        if candidate.is_relevant(field) and value is not None and value not in available:
            invalid.append(field)
    return tuple(invalid)


def _currency_conflicts(
    candidate: TransactionCandidate,
    *,
    references: CaptureReferenceCatalog,
) -> tuple[CurrencyConflict, ...]:
    accounts = {reference.id: reference for reference in references.accounts}
    expected = candidate.currency_code
    conflicts: list[CurrencyConflict] = []
    for field in _account_fields(candidate.type):
        account_id = getattr(candidate, field.value)
        reference = accounts.get(account_id)
        if reference is None or expected is None or reference.currency == expected:
            continue
        conflicts.append(CurrencyConflict(field, expected, reference.currency))

    if candidate.type is TransactionType.TRANSFER:
        source = (
            None
            if candidate.source_account_id is None
            else accounts.get(candidate.source_account_id)
        )
        destination = (
            None
            if candidate.destination_account_id is None
            else accounts.get(candidate.destination_account_id)
        )
        if (
            source is not None
            and destination is not None
            and source.currency != destination.currency
            and all(item.field is not CandidateField.DESTINATION_ACCOUNT_ID for item in conflicts)
        ):
            conflicts.append(
                CurrencyConflict(
                    CandidateField.DESTINATION_ACCOUNT_ID,
                    source.currency,
                    destination.currency,
                )
            )
    return tuple(conflicts)


def _account_fields(transaction_type: TransactionType | None) -> tuple[CandidateField, ...]:
    if transaction_type in {
        TransactionType.EXPENSE,
        TransactionType.INCOME,
        TransactionType.ADJUSTMENT,
    }:
        return (CandidateField.ACCOUNT_ID,)
    if transaction_type is TransactionType.TRANSFER:
        return (CandidateField.SOURCE_ACCOUNT_ID, CandidateField.DESTINATION_ACCOUNT_ID)
    return ()


def _changed_fields(
    before: TransactionCandidate,
    after: TransactionCandidate,
) -> tuple[CandidateField, ...]:
    return tuple(
        CandidateField(field.name)
        for field in fields(TransactionCandidate)
        if getattr(before, field.name) != getattr(after, field.name)
    )


def _clear_patch_field(patch: CandidatePatch, field: CandidateField) -> CandidatePatch:
    return replace(patch, **{field.value: None})


def _distinct(values: tuple[CandidateField, ...]) -> tuple[CandidateField, ...]:
    return tuple(dict.fromkeys(values))
