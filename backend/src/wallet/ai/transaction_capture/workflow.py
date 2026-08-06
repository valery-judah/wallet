from __future__ import annotations

from _thread import LockType
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from threading import Lock

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


@dataclass(slots=True)
class _CaptureSessionEntry:
    session: CaptureSession
    lock: LockType = field(default_factory=Lock, repr=False)


class _CaptureSessionRegistry:
    """Own process-local capture sessions and their synchronization boundaries."""

    def __init__(self) -> None:
        self._entries: dict[str, _CaptureSessionEntry] = {}
        self._lock = Lock()

    def publish(self, session: CaptureSession) -> None:
        entry = _CaptureSessionEntry(session=session)
        with self._lock:
            if session.id in self._entries:
                raise ValueError(f"capture session already exists: {session.id}")
            self._entries[session.id] = entry

    @contextmanager
    def access(self, capture_id: str) -> Iterator[_CaptureSessionEntry]:
        with self._lock:
            entry = self._entries.get(capture_id)
        if entry is None:
            raise CaptureSessionNotFoundError(capture_id)
        with entry.lock:
            yield entry


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
        self._registry = _CaptureSessionRegistry()
        self._processor = processor
        self._validator = validator
        self._wallet = wallet
        self._today = today
        self._generate_capture_id = generate_capture_id

    def receive(
        self,
        contribution: UserContribution,
        *,
        capture_id: str | None = None,
    ) -> CaptureResult:
        """Apply the next user contribution to a new or existing capture session."""

        on_date = self._today()
        if capture_id is None:
            session = CaptureSession.start(
                id=self._generate_capture_id(),
                occurred_on=on_date,
            )
            result = self._handle_contribution(session, contribution, on_date=on_date)
            self._registry.publish(result.session)
            return result

        with self._registry.access(capture_id) as entry:
            session = entry.session
            if session.status in {CaptureStatus.COMPLETED, CaptureStatus.CANCELLED}:
                raise InvalidCaptureTransitionError(
                    f"cannot add contribution while status is {session.status.value}"
                )
            if session.status is CaptureStatus.AWAITING_CONFIRMATION:
                session = session.resume()
            result = self._handle_contribution(session, contribution, on_date=on_date)
            entry.session = result.session
            return result

    def get(self, capture_id: str) -> CaptureResult:
        """Return the current process-local capture state."""

        with self._registry.access(capture_id) as entry:
            return self._result(entry.session, processing_trace=None)

    def confirm(self, capture_id: str) -> CaptureResult:
        """Revalidate and execute a capture that is awaiting confirmation."""

        with self._registry.access(capture_id) as entry:
            session = entry.session
            if session.status is CaptureStatus.COMPLETED:
                return self._result(session, processing_trace=None)
            if session.status is not CaptureStatus.AWAITING_CONFIRMATION:
                raise InvalidCaptureTransitionError(
                    f"cannot confirm capture while status is {session.status.value}"
                )

            assessment = self._assess(session.candidate)
            match assessment:
                case _InteractionRequired():
                    result = self._require_interaction(
                        session.resume(),
                        assessment,
                        processing_trace=None,
                    )
                case _ReadyForExecution():
                    result = self._execute(session, processing_trace=None)
            entry.session = result.session
            return result

    def cancel(self, capture_id: str) -> CaptureResult:
        """Cancel an active or awaiting-confirmation capture."""

        with self._registry.access(capture_id) as entry:
            session = entry.session
            if session.status is CaptureStatus.COMPLETED:
                raise InvalidCaptureTransitionError(
                    "cannot cancel capture while status is completed"
                )
            session = session.cancel()
            entry.session = session
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
            session = session.update_candidate(processing.candidate)
        return self._progress(session, processing_trace=processing.trace)

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
                session = session.await_confirmation()
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
        session = session.request(requirement.interaction)
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
        session = session.complete(transaction_id=transaction_id)
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
