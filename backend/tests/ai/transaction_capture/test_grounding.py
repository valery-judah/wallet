from __future__ import annotations

from datetime import date

import pytest

from wallet.ai.transaction_capture.domain import CandidateField, CandidatePatch
from wallet.ai.transaction_capture.extraction import (
    ContributionExtraction,
    ExtractedMention,
    MentionKind,
    SourceEvidence,
)
from wallet.ai.transaction_capture.grounding import (
    ContributionGrounder,
    GroundedInterpretation,
    GroundedOperation,
    GroundingOption,
)
from wallet.ai.transaction_capture.ports import CaptureReference, CaptureReferenceCatalog
from wallet.ai.transaction_capture.semantic import (
    FieldClear,
    FieldHypothesis,
    InterpretationOrigin,
    SemanticInterpretation,
)
from wallet.domain.transactions import TransactionType

TODAY = date(2026, 8, 5)


def test_grounder_builds_patch_from_verified_mentions() -> None:
    texts = ("Spent", "40 pesos", "Daily checking", "Groceries", "yesterday", "Corner Market")
    fields = (
        CandidateField.TYPE,
        CandidateField.AMOUNT_MINOR,
        CandidateField.ACCOUNT_ID,
        CandidateField.SPENDING_CATEGORY_ID,
        CandidateField.OCCURRED_ON,
        CandidateField.MERCHANT_NAME,
    )
    interpretation = SemanticInterpretation(
        hypotheses=tuple(
            FieldHypothesis(
                field,
                f"m{index}",
                InterpretationOrigin.INFERRED if index == 0 else InterpretationOrigin.EXPLICIT,
                TransactionType.EXPENSE if index == 0 else None,
            )
            for index, field in enumerate(fields)
        )
    )

    grounded = _ground(interpretation, _extraction(*texts))

    assert grounded.patch == CandidatePatch(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        occurred_on=date(2026, 8, 4),
        account_id="account_checking",
        spending_category_id="spending_groceries",
        merchant_name="Corner Market",
    )
    assert grounded.accepted_hypotheses[1].evidence.text == "40 pesos"
    assert not grounded.ambiguities
    assert not grounded.unresolved_fields


def test_unknown_mention_id_is_unsupported_and_cannot_mutate_patch() -> None:
    grounded = _ground(
        SemanticInterpretation(
            hypotheses=(
                FieldHypothesis(
                    CandidateField.ACCOUNT_ID,
                    "invented",
                    InterpretationOrigin.EXPLICIT,
                ),
            )
        ),
        ContributionExtraction(),
    )

    assert grounded.patch.is_empty
    assert grounded.unsupported_claims[0].mention_id == "invented"


@pytest.mark.parametrize(
    ("mention", "field", "expected"),
    [
        ("$45", CandidateField.AMOUNT_MINOR, 4500),
        ("45 pesos", CandidateField.AMOUNT_MINOR, 4500),
        ("-20.25 dollars", CandidateField.BALANCE_CHANGE_MINOR, -2025),
        ("2026-08-01", CandidateField.OCCURRED_ON, date(2026, 8, 1)),
        ("today", CandidateField.OCCURRED_ON, TODAY),
        ("yesterday", CandidateField.OCCURRED_ON, date(2026, 8, 4)),
        ("tomorrow", CandidateField.OCCURRED_ON, date(2026, 8, 6)),
    ],
)
def test_money_and_dates_are_normalized_deterministically(
    mention: str,
    field: CandidateField,
    expected: object,
) -> None:
    grounded = _ground(
        SemanticInterpretation(
            hypotheses=(FieldHypothesis(field, "m0", InterpretationOrigin.EXPLICIT),)
        ),
        _extraction(mention),
    )

    assert grounded.accepted_hypotheses[0].value == expected


def test_full_reference_label_wins_before_leaf_alias_matching() -> None:
    grounded = _ground(
        SemanticInterpretation(
            hypotheses=(
                FieldHypothesis(
                    CandidateField.SPENDING_CATEGORY_ID,
                    "m0",
                    InterpretationOrigin.EXPLICIT,
                ),
            )
        ),
        _extraction("Food > Coffee"),
        references=_references(
            spending=(
                CaptureReference("coffee_food", "Food > Coffee"),
                CaptureReference("coffee_work", "Work > Coffee"),
            )
        ),
    )

    assert grounded.patch == CandidatePatch(spending_category_id="coffee_food")
    assert not grounded.ambiguities


def test_ambiguous_leaf_alias_returns_sorted_choices_without_patch() -> None:
    grounded = _ground(
        SemanticInterpretation(
            hypotheses=(
                FieldHypothesis(
                    CandidateField.SPENDING_CATEGORY_ID,
                    "m0",
                    InterpretationOrigin.EXPLICIT,
                ),
            )
        ),
        _extraction("Coffee"),
        references=_references(
            spending=(
                CaptureReference("coffee_work", "Work > Coffee"),
                CaptureReference("coffee_food", "Food > Coffee"),
            )
        ),
    )

    assert grounded.patch.is_empty
    assert grounded.ambiguities[0].options == (
        GroundingOption("coffee_food", "Food > Coffee"),
        GroundingOption("coffee_work", "Work > Coffee"),
    )


def test_unmatched_reference_is_an_unresolved_field() -> None:
    grounded = _ground(
        SemanticInterpretation(
            hypotheses=(
                FieldHypothesis(
                    CandidateField.ACCOUNT_ID,
                    "m0",
                    InterpretationOrigin.EXPLICIT,
                ),
            )
        ),
        _extraction("Mystery account"),
    )

    assert grounded.patch.is_empty
    assert grounded.unresolved_fields[0].field is CandidateField.ACCOUNT_ID


def test_explicit_clear_uses_extracted_evidence() -> None:
    grounded = _ground(
        SemanticInterpretation(
            clears=(FieldClear(CandidateField.NOTES, "m0", InterpretationOrigin.EXPLICIT),)
        ),
        _extraction("remove the note"),
    )

    assert grounded.patch == CandidatePatch(notes=None)
    assert grounded.accepted_hypotheses[0].operation is GroundedOperation.CLEAR


def _ground(
    interpretation: SemanticInterpretation,
    extraction: ContributionExtraction,
    *,
    references: CaptureReferenceCatalog | None = None,
) -> GroundedInterpretation:
    return ContributionGrounder().ground(
        interpretation,
        extraction=extraction,
        references=references or _references(),
        today=TODAY,
    )


def _extraction(*texts: str) -> ContributionExtraction:
    offset = 0
    mentions: list[ExtractedMention] = []
    for index, text in enumerate(texts):
        mentions.append(
            ExtractedMention(
                id=f"m{index}",
                kind=MentionKind.REFERENCE,
                evidence=SourceEvidence(offset, offset + len(text), text),
            )
        )
        offset += len(text) + 1
    return ContributionExtraction(mentions=tuple(mentions))


def _references(
    *,
    spending: tuple[CaptureReference, ...] | None = None,
) -> CaptureReferenceCatalog:
    return CaptureReferenceCatalog(
        accounts=(
            CaptureReference("account_checking", "Daily checking"),
            CaptureReference("account_wallet", "Pocket wallet"),
        ),
        spending_categories=spending
        or (CaptureReference("spending_groceries", "Food > Groceries"),),
        income_categories=(CaptureReference("income_payroll", "Salary > Payroll"),),
    )
