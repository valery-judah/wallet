from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from wallet.ai.llm import StructuredChatModel
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    PendingInteraction,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.extraction import (
    ContributionExtraction,
    ContributionExtractor,
    ExtractedMention,
    LlmContributionExtractor,
    MentionKind,
    SourceEvidence,
)
from wallet.ai.transaction_capture.grounding import (
    ContributionGrounder,
    GroundedInterpretation,
    GroundingAmbiguity,
    UnresolvedField,
)
from wallet.ai.transaction_capture.ports import (
    CaptureReference,
    CaptureReferenceCatalog,
    CaptureReferenceProvider,
)
from wallet.ai.transaction_capture.semantic import (
    ContributionSemanticInterpreter,
    FieldHypothesis,
    InterpretationOrigin,
    LlmContributionSemanticInterpreter,
    SemanticCandidateContext,
    SemanticContext,
    SemanticInterpretation,
    SemanticPendingInteraction,
    SemanticReferenceState,
    SemanticReferenceValue,
    SemanticReferenceVocabulary,
)
from wallet.domain.transactions import TransactionType


class ContributionAnalysisPath(StrEnum):
    DETERMINISTIC_PENDING = "deterministic_pending"
    MODEL_PIPELINE = "model_pipeline"


@dataclass(frozen=True, slots=True)
class CandidateReduction:
    patch: CandidatePatch
    candidate: TransactionCandidate
    blocking_ambiguities: tuple[GroundingAmbiguity, ...] = ()
    blocking_unresolved_fields: tuple[UnresolvedField, ...] = ()


@dataclass(frozen=True, slots=True)
class ContributionProcessingTrace:
    analysis_path: ContributionAnalysisPath
    extraction: ContributionExtraction
    semantic_interpretation: SemanticInterpretation
    grounded_interpretation: GroundedInterpretation
    candidate_reduction: CandidateReduction


@dataclass(frozen=True, slots=True)
class ContributionProcessingResult:
    candidate: TransactionCandidate
    trace: ContributionProcessingTrace


class CandidateReducer:
    """Apply grounded field operations and clear evidenced unresolved replacements."""

    def reduce(
        self,
        candidate: TransactionCandidate,
        interpretation: GroundedInterpretation,
    ) -> CandidateReduction:
        patch = interpretation.patch
        projected = candidate.apply(patch)
        blocking_ambiguities = tuple(
            issue for issue in interpretation.ambiguities if projected.is_relevant(issue.field)
        )
        blocking_unresolved = tuple(
            issue
            for issue in interpretation.unresolved_fields
            if projected.is_relevant(issue.field)
        )
        for issue in blocking_ambiguities:
            patch = _clear_patch_field(patch, issue.field)
        for unresolved_issue in blocking_unresolved:
            patch = _clear_patch_field(patch, unresolved_issue.field)
        reduced = candidate.apply(patch)
        return CandidateReduction(
            patch=patch,
            candidate=reduced,
            blocking_ambiguities=blocking_ambiguities,
            blocking_unresolved_fields=blocking_unresolved,
        )


class DeterministicPendingAnswerHandler:
    """Produce extraction and semantics for safe exact pending answers."""

    def try_handle(
        self,
        contribution: UserContribution,
        *,
        pending_interaction: PendingInteraction | None,
        references: CaptureReferenceCatalog,
    ) -> tuple[ContributionExtraction, SemanticInterpretation] | None:
        pending = pending_interaction
        if pending is None or pending.field is None:
            return None
        field = pending.field
        semantic_value: TransactionType | None = None
        kind: MentionKind
        if field is CandidateField.TYPE:
            semantic_value = _exact_transaction_type(contribution.content)
            if semantic_value is None:
                return None
            kind = MentionKind.ACTION
        elif field in {CandidateField.AMOUNT_MINOR, CandidateField.BALANCE_CHANGE_MINOR}:
            if _EXACT_AMOUNT.fullmatch(contribution.content.strip()) is None:
                return None
            kind = MentionKind.MONEY
        else:
            field_references = _references_for_field(
                field,
                pending_interaction=pending,
                references=references,
            )
            if (
                field_references is None
                or len(_matching_references(contribution.content, field_references)) != 1
            ):
                return None
            kind = MentionKind.REFERENCE

        evidence = SourceEvidence(
            start=0,
            end=len(contribution.content),
            text=contribution.content,
        )
        extraction = ContributionExtraction(
            mentions=(ExtractedMention(id="m0", kind=kind, evidence=evidence),)
        )
        semantic = SemanticInterpretation(
            hypotheses=(
                FieldHypothesis(
                    field=field,
                    mention_id="m0",
                    origin=InterpretationOrigin.CONTEXTUAL,
                    semantic_value=semantic_value,
                ),
            )
        )
        return extraction, semantic


class PhasedContributionProcessor:
    """Run extraction, semantics, grounding, and reduction for one contribution."""

    def __init__(
        self,
        *,
        pending_answers: DeterministicPendingAnswerHandler,
        extractor: ContributionExtractor,
        semantic_interpreter: ContributionSemanticInterpreter,
        grounder: ContributionGrounder,
        reducer: CandidateReducer,
        references: CaptureReferenceProvider,
    ) -> None:
        self._pending_answers = pending_answers
        self._extractor = extractor
        self._semantic_interpreter = semantic_interpreter
        self._grounder = grounder
        self._reducer = reducer
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
        deterministic = self._pending_answers.try_handle(
            contribution,
            pending_interaction=pending_interaction,
            references=reference_snapshot,
        )
        if deterministic is None:
            analysis_path = ContributionAnalysisPath.MODEL_PIPELINE
            extraction = self._extractor.extract(contribution)
            context = _semantic_context(
                candidate=candidate,
                pending_interaction=pending_interaction,
                today=on_date,
                references=reference_snapshot,
            )
            semantic = self._semantic_interpreter.interpret(
                contribution,
                extraction=extraction,
                context=context,
            )
        else:
            analysis_path = ContributionAnalysisPath.DETERMINISTIC_PENDING
            extraction, semantic = deterministic
        grounded = self._grounder.ground(
            semantic,
            extraction=extraction,
            references=reference_snapshot,
            today=on_date,
        )
        reduction = self._reducer.reduce(candidate, grounded)
        trace = ContributionProcessingTrace(
            analysis_path=analysis_path,
            extraction=extraction,
            semantic_interpretation=semantic,
            grounded_interpretation=grounded,
            candidate_reduction=reduction,
        )
        return ContributionProcessingResult(candidate=reduction.candidate, trace=trace)


@dataclass(frozen=True, slots=True)
class PhasedContributionProcessorFactory:
    """Build wallet-bound processors with separate extraction and semantic models."""

    extraction_model: StructuredChatModel
    semantic_model: StructuredChatModel

    def build(
        self,
        *,
        references: CaptureReferenceProvider,
    ) -> PhasedContributionProcessor:
        return PhasedContributionProcessor(
            pending_answers=DeterministicPendingAnswerHandler(),
            extractor=LlmContributionExtractor(model=self.extraction_model),
            semantic_interpreter=LlmContributionSemanticInterpreter(model=self.semantic_model),
            grounder=ContributionGrounder(),
            reducer=CandidateReducer(),
            references=references,
        )


def _references_for_field(
    field: CandidateField,
    *,
    pending_interaction: PendingInteraction,
    references: CaptureReferenceCatalog,
) -> tuple[CaptureReference, ...] | None:
    if pending_interaction.options:
        return tuple(
            CaptureReference(id=option.value, label=option.label)
            for option in pending_interaction.options
        )
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
    return None


def _semantic_context(
    *,
    candidate: TransactionCandidate,
    pending_interaction: PendingInteraction | None,
    today: date,
    references: CaptureReferenceCatalog,
) -> SemanticContext:
    return SemanticContext(
        today=today,
        candidate=SemanticCandidateContext(
            type=candidate.type,
            amount_minor=candidate.amount_minor,
            occurred_on=candidate.occurred_on,
            account=_semantic_reference(candidate.account_id, references.accounts),
            spending_category=_semantic_reference(
                candidate.spending_category_id,
                references.spending_categories,
            ),
            income_category=_semantic_reference(
                candidate.income_category_id,
                references.income_categories,
            ),
            source_account=_semantic_reference(
                candidate.source_account_id,
                references.accounts,
            ),
            destination_account=_semantic_reference(
                candidate.destination_account_id,
                references.accounts,
            ),
            balance_change_minor=candidate.balance_change_minor,
            description=candidate.description,
            merchant_name=candidate.merchant_name,
            notes=candidate.notes,
        ),
        pending_interaction=(
            None
            if pending_interaction is None
            else SemanticPendingInteraction(
                kind=pending_interaction.kind,
                field=pending_interaction.field,
                option_labels=tuple(option.label for option in pending_interaction.options),
            )
        ),
        references=SemanticReferenceVocabulary(
            account_labels=tuple(reference.label for reference in references.accounts),
            spending_category_labels=tuple(
                reference.label for reference in references.spending_categories
            ),
            income_category_labels=tuple(
                reference.label for reference in references.income_categories
            ),
        ),
    )


def _semantic_reference(
    reference_id: str | None,
    references: tuple[CaptureReference, ...],
) -> SemanticReferenceValue:
    if reference_id is None:
        return SemanticReferenceValue(SemanticReferenceState.UNSET)
    match = next((reference for reference in references if reference.id == reference_id), None)
    if match is None:
        return SemanticReferenceValue(SemanticReferenceState.UNAVAILABLE)
    return SemanticReferenceValue(SemanticReferenceState.AVAILABLE, label=match.label)


def _matching_references(
    text: str,
    references: tuple[CaptureReference, ...],
) -> tuple[CaptureReference, ...]:
    answer = _searchable(text)
    return tuple(
        reference
        for reference in references
        if answer
        in {
            _searchable(reference.label),
            _searchable(reference.label.rsplit(" > ", maxsplit=1)[-1]),
        }
    )


def _exact_transaction_type(content: str) -> TransactionType | None:
    answers = {
        "expense": TransactionType.EXPENSE,
        "an expense": TransactionType.EXPENSE,
        "income": TransactionType.INCOME,
        "an income": TransactionType.INCOME,
        "transfer": TransactionType.TRANSFER,
        "a transfer": TransactionType.TRANSFER,
        "adjustment": TransactionType.ADJUSTMENT,
        "an adjustment": TransactionType.ADJUSTMENT,
    }
    return answers.get(_searchable(content))


def _searchable(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


_EXACT_AMOUNT = re.compile(
    r"(?ix)"
    r"(?:ars|usd|eur|gbp|\$|€|£)?\s*"
    r"[+-]?\d+(?:[.,]\d{1,2})?"
    r"\s*(?:ars|usd|eur|gbp|pesos?|dollars?|euros?|pounds?)?"
)


def _clear_patch_field(patch: CandidatePatch, field: CandidateField) -> CandidatePatch:
    match field:
        case CandidateField.TYPE:
            return replace(patch, type=None)
        case CandidateField.AMOUNT_MINOR:
            return replace(patch, amount_minor=None)
        case CandidateField.OCCURRED_ON:
            return replace(patch, occurred_on=None)
        case CandidateField.ACCOUNT_ID:
            return replace(patch, account_id=None)
        case CandidateField.SPENDING_CATEGORY_ID:
            return replace(patch, spending_category_id=None)
        case CandidateField.INCOME_CATEGORY_ID:
            return replace(patch, income_category_id=None)
        case CandidateField.SOURCE_ACCOUNT_ID:
            return replace(patch, source_account_id=None)
        case CandidateField.DESTINATION_ACCOUNT_ID:
            return replace(patch, destination_account_id=None)
        case CandidateField.BALANCE_CHANGE_MINOR:
            return replace(patch, balance_change_minor=None)
        case CandidateField.DESCRIPTION:
            return replace(patch, description=None)
        case CandidateField.MERCHANT_NAME:
            return replace(patch, merchant_name=None)
        case CandidateField.NOTES:
            return replace(patch, notes=None)
