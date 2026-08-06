from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from wallet.ai.transaction_capture.domain import CandidateField, CandidatePatch
from wallet.ai.transaction_capture.extraction import ContributionExtraction, SourceEvidence
from wallet.ai.transaction_capture.ports import CaptureReference, CaptureReferenceCatalog
from wallet.ai.transaction_capture.semantic import (
    FieldClear,
    FieldHypothesis,
    InterpretationOrigin,
    SemanticInterpretation,
)
from wallet.domain.transactions import TransactionType

GroundedValue = TransactionType | int | date | str | None


class GroundedOperation(StrEnum):
    SET = "set"
    CLEAR = "clear"


@dataclass(frozen=True, slots=True)
class GroundingOption:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class GroundedFieldUpdate:
    field: CandidateField
    value: GroundedValue
    operation: GroundedOperation
    evidence: SourceEvidence
    origin: InterpretationOrigin


@dataclass(frozen=True, slots=True)
class GroundingAmbiguity:
    field: CandidateField
    evidence: SourceEvidence
    options: tuple[GroundingOption, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class UnresolvedField:
    field: CandidateField
    evidence: SourceEvidence
    reason: str


@dataclass(frozen=True, slots=True)
class UnsupportedClaim:
    field: CandidateField
    mention_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class GroundedInterpretation:
    accepted_hypotheses: tuple[GroundedFieldUpdate, ...] = ()
    ambiguities: tuple[GroundingAmbiguity, ...] = ()
    unresolved_fields: tuple[UnresolvedField, ...] = ()
    unsupported_claims: tuple[UnsupportedClaim, ...] = ()
    patch: CandidatePatch = CandidatePatch()


class ContributionGrounder:
    """Validate evidence, normalize scalar mentions, and link wallet references."""

    def ground(
        self,
        interpretation: SemanticInterpretation,
        *,
        extraction: ContributionExtraction,
        references: CaptureReferenceCatalog,
        today: date,
    ) -> GroundedInterpretation:
        accepted: list[GroundedFieldUpdate] = []
        ambiguities: list[GroundingAmbiguity] = []
        unresolved: list[UnresolvedField] = []
        unsupported: list[UnsupportedClaim] = []
        patch = CandidatePatch()

        claims: tuple[FieldHypothesis | FieldClear, ...] = (
            *interpretation.hypotheses,
            *interpretation.clears,
        )
        for claim in claims:
            mention = extraction.mention(claim.mention_id)
            if mention is None:
                unsupported.append(
                    UnsupportedClaim(
                        field=claim.field,
                        mention_id=claim.mention_id,
                        reason="semantic claim does not cite a verified mention",
                    )
                )
                continue
            field = claim.field
            evidence = mention.evidence
            if isinstance(claim, FieldClear):
                update = GroundedFieldUpdate(
                    field=field,
                    value=None,
                    operation=GroundedOperation.CLEAR,
                    evidence=evidence,
                    origin=claim.origin,
                )
                accepted.append(update)
                patch = _with_patch_value(patch, field=field, value=None)
                continue

            outcome = _ground_hypothesis(
                claim,
                evidence=evidence,
                references=references,
                today=today,
            )
            match outcome:
                case GroundedFieldUpdate():
                    accepted.append(outcome)
                    patch = _with_patch_value(patch, field=field, value=outcome.value)
                case GroundingAmbiguity():
                    ambiguities.append(outcome)
                case UnresolvedField():
                    unresolved.append(outcome)

        return GroundedInterpretation(
            accepted_hypotheses=tuple(accepted),
            ambiguities=tuple(ambiguities),
            unresolved_fields=tuple(unresolved),
            unsupported_claims=tuple(unsupported),
            patch=patch,
        )


def _ground_hypothesis(
    hypothesis: FieldHypothesis,
    *,
    evidence: SourceEvidence,
    references: CaptureReferenceCatalog,
    today: date,
) -> GroundedFieldUpdate | GroundingAmbiguity | UnresolvedField:
    field = hypothesis.field
    value: GroundedValue
    if field is CandidateField.TYPE:
        if hypothesis.semantic_value is None:
            return _unresolved(field, evidence, "unknown transaction type")
        value = hypothesis.semantic_value
    elif field in {CandidateField.AMOUNT_MINOR, CandidateField.BALANCE_CHANGE_MINOR}:
        normalized = _normalize_money(evidence.text)
        if normalized is None:
            return _unresolved(field, evidence, "unsupported monetary value")
        value = abs(normalized) if field is CandidateField.AMOUNT_MINOR else normalized
    elif field is CandidateField.OCCURRED_ON:
        normalized_date = _normalize_date(evidence.text, today=today)
        if normalized_date is None:
            return _unresolved(field, evidence, "unsupported date value")
        value = normalized_date
    elif field in _REFERENCE_FIELDS:
        catalog = _reference_catalog_for_field(field, references=references)
        matches = _resolve_reference(evidence.text, catalog)
        if len(matches) > 1:
            return GroundingAmbiguity(
                field=field,
                evidence=evidence,
                options=tuple(
                    GroundingOption(value=reference.id, label=reference.label)
                    for reference in matches
                ),
                reason="reference mention matches multiple selectable wallet records",
            )
        if not matches:
            return _unresolved(field, evidence, "reference is not selectable in this wallet")
        value = matches[0].id
    else:
        value = evidence.text
    return GroundedFieldUpdate(
        field=field,
        value=value,
        operation=GroundedOperation.SET,
        evidence=evidence,
        origin=hypothesis.origin,
    )


def _unresolved(
    field: CandidateField,
    evidence: SourceEvidence,
    reason: str,
) -> UnresolvedField:
    return UnresolvedField(field=field, evidence=evidence, reason=reason)


def _normalize_money(value: str) -> int | None:
    match = _MONEY.fullmatch(value.strip())
    if match is None:
        return None
    normalized = match.group("amount").replace(",", ".")
    try:
        return int(Decimal(normalized) * 100)
    except InvalidOperation:  # pragma: no cover - regular expression guards the value
        return None


def _normalize_date(value: str, *, today: date) -> date | None:
    normalized = value.strip().casefold().rstrip(".,")
    relative = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "tomorrow": today + timedelta(days=1),
    }
    if normalized in relative:
        return relative[normalized]
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _resolve_reference(
    mention: str,
    references: tuple[CaptureReference, ...],
) -> tuple[CaptureReference, ...]:
    normalized = _searchable(mention)
    full_matches = tuple(
        reference for reference in references if _searchable(reference.label) == normalized
    )
    if full_matches:
        return _sorted_references(full_matches)
    leaf_matches = tuple(
        reference
        for reference in references
        if _searchable(reference.label.rsplit(" > ", maxsplit=1)[-1]) == normalized
    )
    return _sorted_references(leaf_matches)


def _sorted_references(
    references: tuple[CaptureReference, ...],
) -> tuple[CaptureReference, ...]:
    return tuple(sorted(references, key=lambda item: (_searchable(item.label), item.id)))


def _reference_catalog_for_field(
    field: CandidateField,
    *,
    references: CaptureReferenceCatalog,
) -> tuple[CaptureReference, ...]:
    if field in {
        CandidateField.ACCOUNT_ID,
        CandidateField.SOURCE_ACCOUNT_ID,
        CandidateField.DESTINATION_ACCOUNT_ID,
    }:
        return references.accounts
    if field is CandidateField.SPENDING_CATEGORY_ID:
        return references.spending_categories
    if field is CandidateField.INCOME_CATEGORY_ID:
        return references.income_categories
    raise RuntimeError(f"field is not a wallet reference: {field.value}")


def _with_patch_value(
    patch: CandidatePatch,
    *,
    field: CandidateField,
    value: GroundedValue,
) -> CandidatePatch:
    match field:
        case CandidateField.TYPE:
            assert value is None or isinstance(value, TransactionType)
            return replace(patch, type=value)
        case CandidateField.AMOUNT_MINOR:
            assert value is None or isinstance(value, int)
            return replace(patch, amount_minor=value)
        case CandidateField.OCCURRED_ON:
            assert value is None or isinstance(value, date)
            return replace(patch, occurred_on=value)
        case CandidateField.ACCOUNT_ID:
            assert value is None or isinstance(value, str)
            return replace(patch, account_id=value)
        case CandidateField.SPENDING_CATEGORY_ID:
            assert value is None or isinstance(value, str)
            return replace(patch, spending_category_id=value)
        case CandidateField.INCOME_CATEGORY_ID:
            assert value is None or isinstance(value, str)
            return replace(patch, income_category_id=value)
        case CandidateField.SOURCE_ACCOUNT_ID:
            assert value is None or isinstance(value, str)
            return replace(patch, source_account_id=value)
        case CandidateField.DESTINATION_ACCOUNT_ID:
            assert value is None or isinstance(value, str)
            return replace(patch, destination_account_id=value)
        case CandidateField.BALANCE_CHANGE_MINOR:
            assert value is None or isinstance(value, int)
            return replace(patch, balance_change_minor=value)
        case CandidateField.DESCRIPTION:
            assert value is None or isinstance(value, str)
            return replace(patch, description=value)
        case CandidateField.MERCHANT_NAME:
            assert value is None or isinstance(value, str)
            return replace(patch, merchant_name=value)
        case CandidateField.NOTES:
            assert value is None or isinstance(value, str)
            return replace(patch, notes=value)


def _searchable(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


_REFERENCE_FIELDS = {
    CandidateField.ACCOUNT_ID,
    CandidateField.SPENDING_CATEGORY_ID,
    CandidateField.INCOME_CATEGORY_ID,
    CandidateField.SOURCE_ACCOUNT_ID,
    CandidateField.DESTINATION_ACCOUNT_ID,
}

_MONEY = re.compile(
    r"(?ix)"
    r"(?:ars|usd|eur|gbp|\$|€|£)?\s*"
    r"(?P<amount>[+-]?\d+(?:[.,]\d{1,2})?)"
    r"\s*(?:ars|usd|eur|gbp|pesos?|dollars?|euros?|pounds?)?"
)
