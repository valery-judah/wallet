from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CaptureSession,
    CaptureStatus,
    InteractionOption,
    InvalidCaptureTransitionError,
    PendingInteraction,
    PendingInteractionKind,
    TransactionCandidate,
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


def _ready_session() -> CaptureSession:
    return CaptureSession(
        id="capture_1",
        candidate=_ready_candidate(),
        pending_interaction=None,
        status=CaptureStatus.ACTIVE,
    )


def test_session_transitions_return_immutable_snapshots() -> None:
    started = CaptureSession.start(id=" capture_1 ", occurred_on=TODAY)
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

    assert started.id == "capture_1"
    assert started.pending_interaction is None
    assert awaiting.pending_interaction == interaction
    assert updated.pending_interaction is None
    assert updated.candidate.amount_minor == 4000

    with pytest.raises(FrozenInstanceError):
        started.status = CaptureStatus.COMPLETED  # type: ignore[misc]


@pytest.mark.parametrize(
    ("session", "message"),
    [
        (
            CaptureSession.start(id="capture_1", occurred_on=TODAY),
            "candidate is incomplete",
        ),
        (
            CaptureSession(
                id="capture_1",
                candidate=TransactionCandidate(
                    type=TransactionType.ADJUSTMENT,
                    occurred_on=TODAY,
                    account_id="cash",
                    balance_change_minor=0,
                ),
                pending_interaction=None,
                status=CaptureStatus.ACTIVE,
            ),
            "candidate is invalid",
        ),
        (
            _ready_session().request(
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
def test_session_confirmation_enforces_candidate_invariants(
    session: CaptureSession,
    message: str,
) -> None:
    with pytest.raises(InvalidCaptureTransitionError, match=message):
        session.await_confirmation()

    assert session.status is CaptureStatus.ACTIVE
    assert session.transaction_id is None


def test_completed_session_is_terminal_and_tracks_wallet_transaction() -> None:
    active = _ready_session()
    awaiting_confirmation = active.await_confirmation()

    completed = awaiting_confirmation.complete(transaction_id=" transaction_1 ")

    assert active.status is CaptureStatus.ACTIVE
    assert awaiting_confirmation.status is CaptureStatus.AWAITING_CONFIRMATION
    assert completed.status is CaptureStatus.COMPLETED
    assert completed.transaction_id == "transaction_1"

    interaction = PendingInteraction(
        kind=PendingInteractionKind.CORRECT,
        field=CandidateField.ACCOUNT_ID,
    )
    with pytest.raises(InvalidCaptureTransitionError, match="status is completed"):
        completed.update_candidate(completed.candidate)
    with pytest.raises(InvalidCaptureTransitionError, match="status is completed"):
        completed.request(interaction)
    with pytest.raises(InvalidCaptureTransitionError, match="status is completed"):
        completed.complete(transaction_id="transaction_2")


def test_confirmation_can_resume_for_edits_or_cancel_without_losing_candidate() -> None:
    awaiting_confirmation = _ready_session().await_confirmation()

    resumed = awaiting_confirmation.resume()
    cancelled = awaiting_confirmation.cancel()

    assert resumed.status is CaptureStatus.ACTIVE
    assert resumed.candidate == awaiting_confirmation.candidate
    assert cancelled.status is CaptureStatus.CANCELLED
    assert cancelled.candidate == awaiting_confirmation.candidate
    assert cancelled.cancel() is cancelled


def test_session_rejects_inconsistent_constructed_state() -> None:
    with pytest.raises(ValueError, match="completed capture must have a transaction id"):
        CaptureSession(
            id="capture_1",
            candidate=_ready_candidate(),
            pending_interaction=None,
            status=CaptureStatus.COMPLETED,
        )

    with pytest.raises(ValueError, match="only completed capture can have a transaction id"):
        CaptureSession(
            id="capture_1",
            candidate=_ready_candidate(),
            pending_interaction=None,
            status=CaptureStatus.ACTIVE,
            transaction_id="transaction_1",
        )

    with pytest.raises(ValueError, match="only active capture can have a pending interaction"):
        CaptureSession(
            id="capture_1",
            candidate=_ready_candidate(),
            pending_interaction=PendingInteraction(
                kind=PendingInteractionKind.REQUEST_VALUE,
                field=CandidateField.ACCOUNT_ID,
            ),
            status=CaptureStatus.COMPLETED,
            transaction_id="transaction_1",
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
