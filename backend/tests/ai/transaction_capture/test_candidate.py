from __future__ import annotations

from datetime import date

import pytest

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    TransactionCandidate,
    UserContribution,
)
from wallet.domain.transactions import TransactionType

TODAY = date(2026, 8, 4)


@pytest.mark.parametrize(
    ("candidate", "required", "missing"),
    [
        (
            TransactionCandidate(occurred_on=TODAY),
            (CandidateField.TYPE,),
            (CandidateField.TYPE,),
        ),
        (
            TransactionCandidate(type=TransactionType.EXPENSE, occurred_on=TODAY),
            (
                CandidateField.AMOUNT_MINOR,
                CandidateField.ACCOUNT_ID,
                CandidateField.SPENDING_CATEGORY_ID,
                CandidateField.OCCURRED_ON,
            ),
            (
                CandidateField.AMOUNT_MINOR,
                CandidateField.ACCOUNT_ID,
                CandidateField.SPENDING_CATEGORY_ID,
            ),
        ),
        (
            TransactionCandidate(type=TransactionType.INCOME, occurred_on=TODAY),
            (
                CandidateField.AMOUNT_MINOR,
                CandidateField.ACCOUNT_ID,
                CandidateField.INCOME_CATEGORY_ID,
                CandidateField.OCCURRED_ON,
            ),
            (
                CandidateField.AMOUNT_MINOR,
                CandidateField.ACCOUNT_ID,
                CandidateField.INCOME_CATEGORY_ID,
            ),
        ),
        (
            TransactionCandidate(type=TransactionType.TRANSFER, occurred_on=TODAY),
            (
                CandidateField.AMOUNT_MINOR,
                CandidateField.SOURCE_ACCOUNT_ID,
                CandidateField.DESTINATION_ACCOUNT_ID,
                CandidateField.OCCURRED_ON,
            ),
            (
                CandidateField.AMOUNT_MINOR,
                CandidateField.SOURCE_ACCOUNT_ID,
                CandidateField.DESTINATION_ACCOUNT_ID,
            ),
        ),
        (
            TransactionCandidate(type=TransactionType.ADJUSTMENT, occurred_on=TODAY),
            (
                CandidateField.ACCOUNT_ID,
                CandidateField.BALANCE_CHANGE_MINOR,
                CandidateField.OCCURRED_ON,
            ),
            (
                CandidateField.ACCOUNT_ID,
                CandidateField.BALANCE_CHANGE_MINOR,
            ),
        ),
    ],
    ids=("missing-type", "expense", "income", "transfer", "adjustment"),
)
def test_required_and_missing_fields_are_derived_in_stable_order(
    candidate: TransactionCandidate,
    required: tuple[CandidateField, ...],
    missing: tuple[CandidateField, ...],
) -> None:
    assert candidate.required_fields == required
    assert candidate.missing_fields == missing
    assert candidate.is_complete is (not missing)


def test_patch_preserves_unspecified_values_and_clears_explicit_none() -> None:
    candidate = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        occurred_on=TODAY,
        account_id="cash",
        spending_category_id="dining",
        description="Team lunch",
        merchant_name="Corner Cafe",
        notes="Reimbursable",
    )

    updated = candidate.apply(
        CandidatePatch(
            occurred_on=date(2026, 8, 1),
            account_id="checking",
            notes=None,
        )
    )

    assert updated == TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        occurred_on=date(2026, 8, 1),
        account_id="checking",
        spending_category_id="dining",
        description="Team lunch",
        merchant_name="Corner Cafe",
        notes=None,
    )


def test_type_change_keeps_shared_values_and_clears_irrelevant_values() -> None:
    expense = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        occurred_on=TODAY,
        account_id="cash",
        spending_category_id="dining",
        description="Team lunch",
        merchant_name="Corner Cafe",
        notes="Reimbursable",
    )

    transfer = expense.apply(
        CandidatePatch(
            type=TransactionType.TRANSFER,
            source_account_id="cash",
        )
    )
    adjustment = expense.apply(
        CandidatePatch(
            type=TransactionType.ADJUSTMENT,
            balance_change_minor=5000,
        )
    )

    assert transfer == TransactionCandidate(
        type=TransactionType.TRANSFER,
        amount_minor=4000,
        occurred_on=TODAY,
        source_account_id="cash",
        description="Team lunch",
        merchant_name="Corner Cafe",
        notes="Reimbursable",
    )
    assert adjustment == TransactionCandidate(
        type=TransactionType.ADJUSTMENT,
        occurred_on=TODAY,
        account_id="cash",
        balance_change_minor=5000,
        description="Team lunch",
        merchant_name="Corner Cafe",
        notes="Reimbursable",
    )


def test_clearing_type_retains_values_until_another_type_is_selected() -> None:
    candidate = TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        occurred_on=TODAY,
        account_id="cash",
        spending_category_id="dining",
    )

    untyped = candidate.apply(CandidatePatch(type=None))

    assert untyped == TransactionCandidate(
        amount_minor=4000,
        occurred_on=TODAY,
        account_id="cash",
        spending_category_id="dining",
    )
    assert untyped.missing_fields == (CandidateField.TYPE,)


@pytest.mark.parametrize(
    ("candidate", "invalid_fields"),
    [
        (
            TransactionCandidate(type=TransactionType.EXPENSE, amount_minor=-1),
            (CandidateField.AMOUNT_MINOR,),
        ),
        (
            TransactionCandidate(type=TransactionType.INCOME, amount_minor=0),
            (CandidateField.AMOUNT_MINOR,),
        ),
        (
            TransactionCandidate(type=TransactionType.TRANSFER, amount_minor=0),
            (CandidateField.AMOUNT_MINOR,),
        ),
        (
            TransactionCandidate(
                type=TransactionType.ADJUSTMENT,
                balance_change_minor=0,
            ),
            (CandidateField.BALANCE_CHANGE_MINOR,),
        ),
        (
            TransactionCandidate(
                type=TransactionType.TRANSFER,
                amount_minor=10000,
                source_account_id="checking",
                destination_account_id="checking",
            ),
            (CandidateField.DESTINATION_ACCOUNT_ID,),
        ),
        (
            TransactionCandidate(
                type=TransactionType.ADJUSTMENT,
                balance_change_minor=-2000,
            ),
            (),
        ),
    ],
    ids=(
        "negative-expense",
        "zero-income",
        "zero-transfer",
        "zero-adjustment",
        "same-account-transfer",
        "negative-adjustment",
    ),
)
def test_local_validity_is_derived_from_candidate_values(
    candidate: TransactionCandidate,
    invalid_fields: tuple[CandidateField, ...],
) -> None:
    assert candidate.locally_invalid_fields == invalid_fields
    assert candidate.is_locally_valid is (not invalid_fields)


def test_candidate_and_contribution_normalize_text_values() -> None:
    candidate = TransactionCandidate(
        account_id=" cash ",
        description=" Team lunch ",
    )

    assert candidate.account_id == "cash"
    assert candidate.description == "Team lunch"
    assert UserContribution("  Record it  ").content == "Record it"

    with pytest.raises(ValueError, match="user contribution"):
        UserContribution("  ")


def test_candidate_patch_distinguishes_no_change_from_explicit_clear() -> None:
    assert CandidatePatch().is_empty
    assert not CandidatePatch(account_id=None).is_empty
