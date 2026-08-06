from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from threading import RLock

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    CaptureSession,
    CaptureStatus,
    InteractionOption,
    InvalidCaptureTransitionError,
    PendingInteraction,
    PendingInteractionKind,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.ports import (
    CandidateValidator,
    CaptureIdGenerator,
    ContributionProcessor,
    WalletTransactionExecutor,
)
from wallet.ai.transaction_capture.processing import ContributionProcessingTrace
from wallet.ports.system import DateProvider


class CaptureSessionNotFoundError(LookupError):
    pass


class CaptureOutcome(StrEnum):
    AWAITING_INTERACTION = "awaiting_interaction"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class CaptureResult:
    outcome: CaptureOutcome
    session: CaptureSession
    processing_trace: ContributionProcessingTrace | None = None


@dataclass(frozen=True, slots=True)
class _InteractionRequired:
    interaction: PendingInteraction
    clear_field: CandidateField | None = None


@dataclass(frozen=True, slots=True)
class _ReadyForExecution:
    pass


_CandidateAssessment = _InteractionRequired | _ReadyForExecution


class CaptureWorkflow:
    """Coordinate transaction-capture lifecycles through the ``receive`` command.

    Sessions belong to this workflow instance and do not survive process restarts.
    """

    def __init__(
        self,
        *,
        processor: ContributionProcessor,
        validator: CandidateValidator,
        wallet: WalletTransactionExecutor,
        today: DateProvider,
        generate_capture_id: CaptureIdGenerator,
    ) -> None:
        self._sessions: dict[str, CaptureSession] = {}
        self._processor = processor
        self._validator = validator
        self._wallet = wallet
        self._today = today
        self._generate_capture_id = generate_capture_id
        self._registry_lock = RLock()
        self._session_locks: dict[str, RLock] = {}

    def receive(
        self,
        contribution: UserContribution,
        *,
        capture_id: str | None = None,
    ) -> CaptureResult:
        """Apply the next user contribution to a new or existing capture session."""

        on_date = self._today()
        if capture_id is None:
            session, session_lock = self._start(on_date=on_date)
            try:
                with session_lock:
                    return self._handle_contribution(session, contribution, on_date=on_date)
            except Exception:
                self._discard(session.id)
                raise

        session_lock = self._lock_for(capture_id)
        with session_lock:
            session = self._load(capture_id)
            if session.status in {CaptureStatus.COMPLETED, CaptureStatus.CANCELLED}:
                raise InvalidCaptureTransitionError(
                    f"cannot add contribution while status is {session.status.value}"
                )
            original_session = session
            if session.status is CaptureStatus.AWAITING_CONFIRMATION:
                session = session.resume()
            try:
                return self._handle_contribution(session, contribution, on_date=on_date)
            except Exception:
                self._store(original_session)
                raise

    def get(self, capture_id: str) -> CaptureResult:
        """Return the current process-local capture state."""

        session_lock = self._lock_for(capture_id)
        with session_lock:
            return self._result(self._load(capture_id), processing_trace=None)

    def confirm(self, capture_id: str) -> CaptureResult:
        """Revalidate and execute a capture that is awaiting confirmation."""

        session_lock = self._lock_for(capture_id)
        with session_lock:
            session = self._load(capture_id)
            if session.status is CaptureStatus.COMPLETED:
                return self._result(session, processing_trace=None)
            if session.status is not CaptureStatus.AWAITING_CONFIRMATION:
                raise InvalidCaptureTransitionError(
                    f"cannot confirm capture while status is {session.status.value}"
                )

            assessment = self._assess(session.candidate)
            match assessment:
                case _InteractionRequired():
                    session = self._store(session.resume())
                    return self._require_interaction(
                        session,
                        assessment,
                        processing_trace=None,
                    )
                case _ReadyForExecution():
                    return self._execute(session, processing_trace=None)

    def cancel(self, capture_id: str) -> CaptureResult:
        """Cancel an active or awaiting-confirmation capture."""

        session_lock = self._lock_for(capture_id)
        with session_lock:
            session = self._load(capture_id)
            if session.status is CaptureStatus.COMPLETED:
                raise InvalidCaptureTransitionError(
                    "cannot cancel capture while status is completed"
                )
            session = self._store(session.cancel())
            return self._result(session, processing_trace=None)

    def _handle_contribution(
        self,
        session: CaptureSession,
        contribution: UserContribution,
        *,
        on_date: date,
    ) -> CaptureResult:
        processing = self._processor.process(
            contribution,
            candidate=session.candidate,
            pending_interaction=session.pending_interaction,
            on_date=on_date,
        )
        if processing.candidate != session.candidate:
            session = self._store(session.update_candidate(processing.candidate))
        return self._progress(session, processing_trace=processing.trace)

    def _start(self, *, on_date: date) -> tuple[CaptureSession, RLock]:
        session = CaptureSession.start(
            id=self._generate_capture_id(),
            occurred_on=on_date,
        )
        session_lock = RLock()
        with self._registry_lock:
            self._sessions[session.id] = session
            self._session_locks[session.id] = session_lock
        return session, session_lock

    def _lock_for(self, capture_id: str) -> RLock:
        with self._registry_lock:
            session_lock = self._session_locks.get(capture_id)
        if session_lock is None:
            raise CaptureSessionNotFoundError(capture_id)
        return session_lock

    def _discard(self, capture_id: str) -> None:
        with self._registry_lock:
            self._sessions.pop(capture_id, None)
            self._session_locks.pop(capture_id, None)

    def _load(self, capture_id: str) -> CaptureSession:
        session = self._sessions.get(capture_id)
        if session is None:
            raise CaptureSessionNotFoundError(capture_id)
        return session

    def _store(self, session: CaptureSession) -> CaptureSession:
        self._sessions[session.id] = session
        return session

    def _progress(
        self,
        session: CaptureSession,
        *,
        processing_trace: ContributionProcessingTrace,
    ) -> CaptureResult:
        processing_requirement = self._processing_requirement(processing_trace)
        if processing_requirement is not None:
            return self._require_interaction(
                session,
                processing_requirement,
                processing_trace=processing_trace,
            )
        assessment = self._assess(session.candidate)
        match assessment:
            case _InteractionRequired():
                return self._require_interaction(
                    session,
                    assessment,
                    processing_trace=processing_trace,
                )
            case _ReadyForExecution():
                session = self._store(session.await_confirmation())
                return self._result(session, processing_trace=processing_trace)

    def _processing_requirement(
        self,
        trace: ContributionProcessingTrace,
    ) -> _InteractionRequired | None:
        if trace.extraction.issues or trace.semantic_interpretation.issues:
            return _InteractionRequired(
                interaction=PendingInteraction(kind=PendingInteractionKind.CLARIFY)
            )
        reduction = trace.candidate_reduction
        if reduction.blocking_ambiguities:
            ambiguity = reduction.blocking_ambiguities[0]
            return _InteractionRequired(
                interaction=PendingInteraction(
                    kind=PendingInteractionKind.DISAMBIGUATE,
                    field=ambiguity.field,
                    options=tuple(
                        InteractionOption(value=option.value, label=option.label)
                        for option in ambiguity.options
                    ),
                )
            )
        if reduction.blocking_unresolved_fields:
            unresolved = reduction.blocking_unresolved_fields[0]
            return _InteractionRequired(
                interaction=PendingInteraction(
                    kind=PendingInteractionKind.CORRECT,
                    field=unresolved.field,
                )
            )
        return None

    def _assess(
        self,
        candidate: TransactionCandidate,
    ) -> _CandidateAssessment:
        rules: tuple[Callable[[], _InteractionRequired | None], ...] = (
            lambda: self._local_validity_assessment(candidate),
            lambda: self._missing_fields_assessment(candidate),
            lambda: self._reference_validity_assessment(candidate),
        )
        for rule in rules:
            if interaction := rule():
                return interaction
        return _ReadyForExecution()

    def _local_validity_assessment(
        self,
        candidate: TransactionCandidate,
    ) -> _InteractionRequired | None:
        if not candidate.locally_invalid_fields:
            return None
        field = candidate.locally_invalid_fields[0]
        return _InteractionRequired(
            interaction=PendingInteraction(
                kind=PendingInteractionKind.CORRECT,
                field=field,
            ),
            clear_field=field,
        )

    def _missing_fields_assessment(
        self,
        candidate: TransactionCandidate,
    ) -> _InteractionRequired | None:
        if not candidate.missing_fields:
            return None
        return _InteractionRequired(
            interaction=PendingInteraction(
                kind=PendingInteractionKind.REQUEST_VALUE,
                field=candidate.missing_fields[0],
            )
        )

    def _reference_validity_assessment(
        self,
        candidate: TransactionCandidate,
    ) -> _InteractionRequired | None:
        field = self._validator.invalid_field(candidate)
        if field is None:
            return None
        return _InteractionRequired(
            interaction=PendingInteraction(
                kind=PendingInteractionKind.CORRECT,
                field=field,
            ),
            clear_field=field,
        )

    def _require_interaction(
        self,
        session: CaptureSession,
        requirement: _InteractionRequired,
        *,
        processing_trace: ContributionProcessingTrace | None,
    ) -> CaptureResult:
        if requirement.clear_field is not None:
            session = session.update_candidate(
                session.candidate.apply(_clear_field(requirement.clear_field))
            )
        session = self._store(session.request(requirement.interaction))
        return CaptureResult(
            outcome=CaptureOutcome.AWAITING_INTERACTION,
            session=session,
            processing_trace=processing_trace,
        )

    def _execute(
        self,
        session: CaptureSession,
        *,
        processing_trace: ContributionProcessingTrace | None,
    ) -> CaptureResult:
        transaction_id = self._wallet.execute(session.candidate)
        session = self._store(session.complete(transaction_id=transaction_id))
        return self._result(session, processing_trace=processing_trace)

    def _result(
        self,
        session: CaptureSession,
        *,
        processing_trace: ContributionProcessingTrace | None,
    ) -> CaptureResult:
        return CaptureResult(
            outcome=_outcome_for_status(session.status),
            session=session,
            processing_trace=processing_trace,
        )


def _clear_field(field: CandidateField) -> CandidatePatch:
    match field:
        case CandidateField.TYPE:
            return CandidatePatch(type=None)
        case CandidateField.AMOUNT_MINOR:
            return CandidatePatch(amount_minor=None)
        case CandidateField.OCCURRED_ON:
            return CandidatePatch(occurred_on=None)
        case CandidateField.ACCOUNT_ID:
            return CandidatePatch(account_id=None)
        case CandidateField.SPENDING_CATEGORY_ID:
            return CandidatePatch(spending_category_id=None)
        case CandidateField.INCOME_CATEGORY_ID:
            return CandidatePatch(income_category_id=None)
        case CandidateField.SOURCE_ACCOUNT_ID:
            return CandidatePatch(source_account_id=None)
        case CandidateField.DESTINATION_ACCOUNT_ID:
            return CandidatePatch(destination_account_id=None)
        case CandidateField.BALANCE_CHANGE_MINOR:
            return CandidatePatch(balance_change_minor=None)
        case CandidateField.DESCRIPTION:
            return CandidatePatch(description=None)
        case CandidateField.MERCHANT_NAME:
            return CandidatePatch(merchant_name=None)
        case CandidateField.NOTES:
            return CandidatePatch(notes=None)


def _outcome_for_status(status: CaptureStatus) -> CaptureOutcome:
    match status:
        case CaptureStatus.ACTIVE:
            return CaptureOutcome.AWAITING_INTERACTION
        case CaptureStatus.AWAITING_CONFIRMATION:
            return CaptureOutcome.AWAITING_CONFIRMATION
        case CaptureStatus.COMPLETED:
            return CaptureOutcome.COMPLETED
        case CaptureStatus.CANCELLED:
            return CaptureOutcome.CANCELLED
