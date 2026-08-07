from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CapturePhase,
    InteractionOption,
    InvalidCaptureTransitionError,
    PendingInteraction,
    PendingInteractionKind,
    PendingInteractionReason,
    TransactionCandidate,
    TransactionCaptureState,
)
from wallet.domain.transactions import TransactionType

TODAY = date(2026, 8, 4)


def _ready_candidate() -> TransactionCandidate:
    return TransactionCandidate(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        occurred_on=TODAY,
        account_id="cash",
        spending_category_id="dining",
    )


def _ready_state() -> TransactionCaptureState:
    return TransactionCaptureState(
        candidate=_ready_candidate(),
        pending_interaction=None,
        phase=CapturePhase.ACTIVE,
    )


def test_state_transitions_return_immutable_snapshots() -> None:
    started = TransactionCaptureState.start(occurred_on=TODAY)
    interaction = PendingInteraction(
        kind=PendingInteractionKind.REQUEST_VALUE,
        field=CandidateField.AMOUNT_MINOR,
    )

    awaiting = started.request(interaction)
    updated = awaiting.update_candidate(
        TransactionCandidate(
            type=TransactionType.EXPENSE,
            amount_minor=4000,
            occurred_on=TODAY,
        )
    )

    assert started.pending_interaction is None
    assert awaiting.pending_interaction == interaction
    assert updated.pending_interaction is None
    assert updated.candidate.amount_minor == 4000

    with pytest.raises(FrozenInstanceError):
        started.phase = CapturePhase.AWAITING_CONFIRMATION  # type: ignore[misc]


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (
            TransactionCaptureState.start(occurred_on=TODAY),
            "candidate is incomplete",
        ),
        (
            TransactionCaptureState(
                candidate=TransactionCandidate(
                    type=TransactionType.ADJUSTMENT,
                    occurred_on=TODAY,
                    account_id="cash",
                    balance_change_minor=0,
                ),
                pending_interaction=None,
                phase=CapturePhase.ACTIVE,
            ),
            "candidate is invalid",
        ),
        (
            _ready_state().request(
                PendingInteraction(
                    kind=PendingInteractionKind.CORRECT,
                    field=CandidateField.ACCOUNT_ID,
                )
            ),
            "pending interaction must be resolved",
        ),
    ],
    ids=("incomplete", "locally-invalid", "pending-interaction"),
)
def test_state_confirmation_enforces_candidate_invariants(
    state: TransactionCaptureState,
    message: str,
) -> None:
    with pytest.raises(InvalidCaptureTransitionError, match=message):
        state.await_confirmation()

    assert state.phase is CapturePhase.ACTIVE


def test_confirmation_can_resume_for_edits_without_losing_candidate() -> None:
    awaiting_confirmation = _ready_state().await_confirmation()

    resumed = awaiting_confirmation.resume()

    assert awaiting_confirmation.phase is CapturePhase.AWAITING_CONFIRMATION
    assert resumed.phase is CapturePhase.ACTIVE
    assert resumed.candidate == awaiting_confirmation.candidate


def test_state_rejects_interaction_while_awaiting_confirmation() -> None:
    with pytest.raises(ValueError, match="only active capture can have a pending interaction"):
        TransactionCaptureState(
            candidate=_ready_candidate(),
            pending_interaction=PendingInteraction(
                kind=PendingInteractionKind.REQUEST_VALUE,
                field=CandidateField.ACCOUNT_ID,
            ),
            phase=CapturePhase.AWAITING_CONFIRMATION,
        )


def test_pending_disambiguation_requires_immutable_options() -> None:
    options = (
        InteractionOption("food_coffee", "Food > Coffee"),
        InteractionOption("work_coffee", "Work > Coffee"),
    )

    interaction = PendingInteraction(
        kind=PendingInteractionKind.DISAMBIGUATE,
        field=CandidateField.SPENDING_CATEGORY_ID,
        options=options,
    )

    assert interaction.options == options
    with pytest.raises(ValueError, match="at least two options"):
        PendingInteraction(
            kind=PendingInteractionKind.DISAMBIGUATE,
            field=CandidateField.SPENDING_CATEGORY_ID,
            options=(options[0],),
        )
    with pytest.raises(ValueError, match="only disambiguation"):
        PendingInteraction(
            kind=PendingInteractionKind.REQUEST_VALUE,
            field=CandidateField.SPENDING_CATEGORY_ID,
            options=options,
        )


def test_general_clarification_is_the_only_fieldless_interaction() -> None:
    assert PendingInteraction(PendingInteractionKind.CLARIFY).field is None
    with pytest.raises(ValueError, match="cannot target one field"):
        PendingInteraction(PendingInteractionKind.CLARIFY, CandidateField.TYPE)
    with pytest.raises(ValueError, match="requires a candidate field"):
        PendingInteraction(PendingInteractionKind.REQUEST_VALUE)


def test_candidate_normalizes_capture_currency_context() -> None:
    candidate = TransactionCandidate(currency_code=" usd ")

    assert candidate.currency_code == "USD"
    with pytest.raises(ValueError, match="three letters"):
        TransactionCandidate(currency_code="dollars")


def test_only_corrections_can_carry_internal_interaction_reasons() -> None:
    correction = PendingInteraction(
        PendingInteractionKind.CORRECT,
        CandidateField.ACCOUNT_ID,
        reason=PendingInteractionReason.CURRENCY_CONFLICT,
    )

    assert correction.reason is PendingInteractionReason.CURRENCY_CONFLICT
    with pytest.raises(ValueError, match="only corrections"):
        PendingInteraction(
            PendingInteractionKind.REQUEST_VALUE,
            CandidateField.ACCOUNT_ID,
            reason=PendingInteractionReason.UNRESOLVED_VALUE,
        )
