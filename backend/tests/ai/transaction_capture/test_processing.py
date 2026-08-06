from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    InteractionOption,
    PendingInteraction,
    PendingInteractionKind,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.extraction import (
    ContributionExtraction,
    ExtractedMention,
    MentionKind,
    SourceEvidence,
)
from wallet.ai.transaction_capture.grounding import (
    ContributionGrounder,
    GroundedInterpretation,
    GroundingAmbiguity,
    GroundingOption,
)
from wallet.ai.transaction_capture.ports import CaptureReference, CaptureReferenceCatalog
from wallet.ai.transaction_capture.processing import (
    CandidateReducer,
    ContributionAnalysisPath,
    DeterministicPendingAnswerHandler,
    PhasedContributionProcessor,
)
from wallet.ai.transaction_capture.semantic import (
    FieldHypothesis,
    InterpretationOrigin,
    SemanticContext,
    SemanticInterpretation,
    SemanticReferenceState,
)
from wallet.domain.transactions import TransactionType

TODAY = date(2026, 8, 5)


@dataclass
class RecordingReferences:
    calls: int = 0
    catalog: CaptureReferenceCatalog | None = None

    def capture_references(self) -> CaptureReferenceCatalog:
        self.calls += 1
        return self.catalog or _references()


@dataclass
class StubExtractor:
    extraction: ContributionExtraction
    contributions: list[UserContribution] = field(default_factory=list)

    def extract(self, contribution: UserContribution) -> ContributionExtraction:
        self.contributions.append(contribution)
        return self.extraction


@dataclass
class StubSemanticInterpreter:
    interpretation: SemanticInterpretation
    contexts: list[SemanticContext] = field(default_factory=list)

    def interpret(
        self,
        contribution: UserContribution,
        *,
        extraction: ContributionExtraction,
        context: SemanticContext,
    ) -> SemanticInterpretation:
        self.contexts.append(context)
        return self.interpretation


def test_processor_uses_one_snapshot_and_calls_both_model_stages() -> None:
    references = RecordingReferences()
    extraction = _extraction("expense", MentionKind.ACTION)
    extractor = StubExtractor(extraction)
    semantic = StubSemanticInterpreter(
        SemanticInterpretation(
            hypotheses=(
                FieldHypothesis(
                    CandidateField.TYPE,
                    "m0",
                    InterpretationOrigin.EXPLICIT,
                    TransactionType.EXPENSE,
                ),
            )
        )
    )
    processor = _processor(extractor, semantic, references=references)

    result = processor.process(
        UserContribution("expense"),
        candidate=TransactionCandidate(occurred_on=TODAY, account_id="cash"),
        pending_interaction=None,
        on_date=TODAY,
    )

    assert references.calls == 1
    assert len(extractor.contributions) == 1
    assert semantic.contexts[0].references.account_labels == ("Cash", "Savings")
    assert semantic.contexts[0].candidate.account.state is SemanticReferenceState.AVAILABLE
    assert semantic.contexts[0].candidate.account.label == "Cash"
    assert result.candidate.type is TransactionType.EXPENSE
    assert result.trace.analysis_path is ContributionAnalysisPath.MODEL_PIPELINE
    assert result.trace.extraction == extraction


@pytest.mark.parametrize(
    ("field", "answer", "expected_type"),
    [
        (CandidateField.TYPE, "income", TransactionType.INCOME),
        (CandidateField.AMOUNT_MINOR, "$35", None),
        (CandidateField.BALANCE_CHANGE_MINOR, "-20", None),
        (CandidateField.ACCOUNT_ID, "Cash", None),
        (CandidateField.SPENDING_CATEGORY_ID, "Groceries", None),
        (CandidateField.INCOME_CATEGORY_ID, "Payroll", None),
        (CandidateField.SOURCE_ACCOUNT_ID, "Cash", None),
        (CandidateField.DESTINATION_ACCOUNT_ID, "Savings", None),
    ],
)
def test_exact_pending_answers_bypass_both_model_stages(
    field: CandidateField,
    answer: str,
    expected_type: TransactionType | None,
) -> None:
    extractor = StubExtractor(ContributionExtraction())
    semantic = StubSemanticInterpreter(SemanticInterpretation())
    processor = _processor(extractor, semantic)

    result = processor.process(
        UserContribution(answer),
        candidate=TransactionCandidate(occurred_on=TODAY),
        pending_interaction=PendingInteraction(
            kind=PendingInteractionKind.REQUEST_VALUE,
            field=field,
        ),
        on_date=TODAY,
    )

    assert not extractor.contributions
    assert not semantic.contexts
    assert result.trace.analysis_path is ContributionAnalysisPath.DETERMINISTIC_PENDING
    assert result.trace.semantic_interpretation.hypotheses[0].semantic_value == expected_type


def test_clarification_reply_uses_full_model_pipeline() -> None:
    extractor = StubExtractor(ContributionExtraction())
    semantic = StubSemanticInterpreter(SemanticInterpretation())

    _processor(extractor, semantic).process(
        UserContribution("I meant the other account"),
        candidate=TransactionCandidate(occurred_on=TODAY),
        pending_interaction=PendingInteraction(kind=PendingInteractionKind.CLARIFY),
        on_date=TODAY,
    )

    assert len(extractor.contributions) == 1
    assert len(semantic.contexts) == 1


def test_projection_marks_excluded_or_type_irrelevant_references_without_ids() -> None:
    semantic = StubSemanticInterpreter(SemanticInterpretation())
    _processor(StubExtractor(ContributionExtraction()), semantic).process(
        UserContribution("nothing"),
        candidate=TransactionCandidate(
            type=TransactionType.TRANSFER,
            account_id="duplicate_excluded",
            source_account_id="cash",
            occurred_on=TODAY,
        ),
        pending_interaction=None,
        on_date=TODAY,
    )

    candidate = semantic.contexts[0].candidate
    assert candidate.account.state is SemanticReferenceState.UNAVAILABLE
    assert candidate.account.label is None
    assert candidate.source_account.state is SemanticReferenceState.AVAILABLE
    assert candidate.source_account.label == "Cash"
    assert candidate.spending_category.state is SemanticReferenceState.UNSET


def test_semantic_projection_excludes_candidate_catalog_and_option_ids() -> None:
    references = RecordingReferences(
        catalog=CaptureReferenceCatalog(
            accounts=(CaptureReference("account_secret_7f29", "Daily checking"),),
            spending_categories=(
                CaptureReference("category_secret_104", "Personal > Groceries"),
                CaptureReference("category_secret_392", "Business > Groceries"),
            ),
            income_categories=(),
        )
    )
    semantic = StubSemanticInterpreter(SemanticInterpretation())
    _processor(
        StubExtractor(ContributionExtraction()),
        semantic,
        references=references,
    ).process(
        UserContribution("neither option"),
        candidate=TransactionCandidate(
            type=TransactionType.EXPENSE,
            account_id="account_secret_7f29",
            occurred_on=TODAY,
        ),
        pending_interaction=PendingInteraction(
            kind=PendingInteractionKind.DISAMBIGUATE,
            field=CandidateField.SPENDING_CATEGORY_ID,
            options=(
                InteractionOption("category_secret_104", "Personal > Groceries"),
                InteractionOption("category_secret_392", "Business > Groceries"),
            ),
        ),
        on_date=TODAY,
    )

    projected = repr(semantic.contexts[0])
    assert "Daily checking" in projected
    assert "Personal > Groceries" in projected
    assert "account_secret_7f29" not in projected
    assert "category_secret_104" not in projected
    assert "category_secret_392" not in projected


def test_exact_disambiguation_answer_uses_trusted_option_and_catalog_ids() -> None:
    extractor = StubExtractor(ContributionExtraction())
    semantic = StubSemanticInterpreter(SemanticInterpretation())

    result = _processor(extractor, semantic).process(
        UserContribution("Work > Coffee"),
        candidate=TransactionCandidate(type=TransactionType.EXPENSE, occurred_on=TODAY),
        pending_interaction=PendingInteraction(
            kind=PendingInteractionKind.DISAMBIGUATE,
            field=CandidateField.SPENDING_CATEGORY_ID,
            options=(
                InteractionOption("personal_coffee", "Personal > Coffee"),
                InteractionOption("work_coffee", "Work > Coffee"),
            ),
        ),
        on_date=TODAY,
    )

    assert not extractor.contributions
    assert not semantic.contexts
    assert result.trace.analysis_path is ContributionAnalysisPath.DETERMINISTIC_PENDING
    assert result.candidate.spending_category_id == "work_coffee"


def test_reducer_clears_stale_value_and_blocks_ambiguous_replacement() -> None:
    candidate = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=1000,
        occurred_on=TODAY,
        account_id="old_account",
        spending_category_id="groceries",
    )
    ambiguity = GroundingAmbiguity(
        field=CandidateField.ACCOUNT_ID,
        evidence=SourceEvidence(4, 8, "Cash"),
        options=(
            GroundingOption("cash_ars", "Cash ARS"),
            GroundingOption("cash_usd", "Cash USD"),
        ),
        reason="ambiguous",
    )

    reduction = CandidateReducer().reduce(
        candidate,
        GroundedInterpretation(ambiguities=(ambiguity,)),
    )

    assert reduction.candidate.account_id is None
    assert reduction.patch == CandidatePatch(account_id=None)
    assert reduction.blocking_ambiguities == (ambiguity,)


def _processor(
    extractor: StubExtractor,
    semantic: StubSemanticInterpreter,
    *,
    references: RecordingReferences | None = None,
) -> PhasedContributionProcessor:
    return PhasedContributionProcessor(
        pending_answers=DeterministicPendingAnswerHandler(),
        extractor=extractor,
        semantic_interpreter=semantic,
        grounder=ContributionGrounder(),
        reducer=CandidateReducer(),
        references=references or RecordingReferences(),
    )


def _extraction(text: str, kind: MentionKind) -> ContributionExtraction:
    return ContributionExtraction(
        mentions=(ExtractedMention("m0", kind, SourceEvidence(0, len(text), text)),)
    )


def _references() -> CaptureReferenceCatalog:
    return CaptureReferenceCatalog(
        accounts=(
            CaptureReference("cash", "Cash"),
            CaptureReference("savings", "Savings"),
        ),
        spending_categories=(
            CaptureReference("groceries", "Food > Groceries"),
            CaptureReference("personal_coffee", "Personal > Coffee"),
            CaptureReference("work_coffee", "Work > Coffee"),
        ),
        income_categories=(CaptureReference("payroll", "Salary > Payroll"),),
    )
