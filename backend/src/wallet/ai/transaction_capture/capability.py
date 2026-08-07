from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import assert_never

from wallet.ai.capabilities.contract import (
    ActiveCapabilityResult,
    CapabilityAction,
    CapabilityContext,
    CapabilityDefinition,
    CapabilityInput,
    CapabilityMessage,
    CapabilityResult,
    CapabilityRoutingProfile,
    CompletedCapabilityResult,
)
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    CapturePhase,
    InteractionOption,
    PendingInteraction,
    PendingInteractionKind,
    PendingInteractionReason,
    TransactionCandidate,
    TransactionCaptureState,
    UserContribution,
)
from wallet.ai.transaction_capture.ports import (
    CandidateValidator,
    ContributionProcessor,
    WalletTransactionExecutor,
)
from wallet.ai.transaction_capture.presentation import (
    CapturePresentation,
    transaction_projection,
)
from wallet.ai.transaction_capture.processing import ContributionProcessingTrace
from wallet.observability import log_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _InteractionRequired:
    interaction: PendingInteraction
    clear_field: CandidateField | None = None


@dataclass(frozen=True, slots=True)
class _ReadyForExecution:
    pass


_CandidateAssessment = _InteractionRequired | _ReadyForExecution


class TransactionCaptureCapability:
    definition = CapabilityDefinition(
        id="transactions.capture",
        description="Collect and record one expense, income, transfer, or balance adjustment.",
        routing=CapabilityRoutingProfile(
            routes_when=(
                "The user wants to record an expense or purchase.",
                "The user wants to record income.",
                "The user wants to record a transfer between accounts.",
                "The user wants to set, increase, decrease, or otherwise adjust an "
                "account balance.",
                "The user is correcting or completing one of these transaction requests.",
                "This capability is current and the user supplies a short amount, account or "
                "category name, date, affirmation, rejection, or correction.",
            ),
            examples=(
                "Spent 40 dollars on groceries.",
                "Received 2000 salary.",
                "Transfer 100 from Cash to Savings.",
                "Set Cash balance to 250.",
                "Cash, while answering an active transaction question.",
                "Vacation wallet, while answering which account an active transaction uses.",
                "Coffee, while choosing a category for an active transaction.",
                "Tomorrow, while correcting the date of an active transaction.",
            ),
            counterexamples=(
                "How much did I spend this month?",
                "Show my recent transactions.",
                "What is my Cash balance?",
            ),
        ),
    )

    def __init__(
        self,
        *,
        processor: ContributionProcessor,
        validator: CandidateValidator,
        wallet: WalletTransactionExecutor,
        presentation: CapturePresentation,
    ) -> None:
        self._processor = processor
        self._validator = validator
        self._wallet = wallet
        self._presentation = presentation

    def start(
        self,
        content: str | None,
        context: CapabilityContext,
    ) -> CapabilityResult[TransactionCaptureState]:
        state = TransactionCaptureState.start(occurred_on=context.current_date)
        if content is None:
            return self._active_result(state, outcome_kind="question")
        return self._handle_contribution(state, content, context)

    def handle(
        self,
        state: TransactionCaptureState,
        input: CapabilityInput,
        context: CapabilityContext,
    ) -> CapabilityResult[TransactionCaptureState]:
        match input:
            case CapabilityMessage(content=content):
                if state.phase is CapturePhase.AWAITING_CONFIRMATION:
                    state = state.resume()
                return self._handle_contribution(state, content, context)
            case CapabilityAction(action=action, payload=payload):
                return self._handle_action(
                    state,
                    action=action,
                    payload=payload,
                    context=context,
                )
            case _ as unreachable:
                # Static exhaustiveness guard for the closed capability-input family.
                assert_never(unreachable)

    def _handle_action(
        self,
        state: TransactionCaptureState,
        *,
        action: str,
        payload: dict[str, object],
        context: CapabilityContext,
    ) -> CapabilityResult[TransactionCaptureState]:
        if action != "confirm" or payload:
            log_event(
                logger,
                logging.WARNING,
                "capture.action.rejected",
                data={
                    "action": action,
                    "phase": state.phase,
                    "payload_present": bool(payload),
                    "reason": "action_unavailable",
                },
            )
            return self._active_result(
                state,
                outcome_kind="action_unavailable",
                message="That action is not available for the current transaction capture.",
            )
        if state.phase is not CapturePhase.AWAITING_CONFIRMATION:
            log_event(
                logger,
                logging.WARNING,
                "capture.action.rejected",
                data={
                    "action": action,
                    "phase": state.phase,
                    "payload_present": False,
                    "reason": "confirmation_not_ready",
                },
            )
            return self._active_result(
                state,
                outcome_kind="action_unavailable",
                message="The transaction is not ready to confirm yet.",
            )
        assessment = self._assess(state.candidate)
        if isinstance(assessment, _InteractionRequired):
            corrected = self._require_interaction(state.resume(), assessment)
            log_event(
                logger,
                logging.WARNING,
                "capture.confirmation.invalidated",
                data={
                    "interaction_kind": assessment.interaction.kind,
                    "requested_field": assessment.interaction.field,
                },
            )
            return self._active_result(corrected, outcome_kind="question")
        transaction = self._wallet.execute(
            state.candidate,
            operation_id=context.operation_id,
        )
        return CompletedCapabilityResult(
            view=None,
            outcome_kind="recorded",
            message=self._presentation.recorded_message(state.candidate),
            domain_result=transaction_projection(transaction),
        )

    def _handle_contribution(
        self,
        state: TransactionCaptureState,
        content: str,
        context: CapabilityContext,
    ) -> CapabilityResult[TransactionCaptureState]:
        before_phase = state.phase
        processing = self._processor.process(
            UserContribution(content),
            candidate=state.candidate,
            pending_interaction=state.pending_interaction,
            on_date=context.current_date,
        )
        candidate_changed = processing.candidate != state.candidate
        if candidate_changed:
            state = state.update_candidate(processing.candidate)
        state = self._progress(state, processing.trace)
        outcome_kind = (
            "preview"
            if state.phase is CapturePhase.AWAITING_CONFIRMATION
            else "selection_required"
            if state.pending_interaction is not None
            and state.pending_interaction.kind is PendingInteractionKind.DISAMBIGUATE
            else "question"
        )
        pending = state.pending_interaction
        log_event(
            logger,
            logging.INFO,
            "capture.contribution.processed",
            data={
                "attempt_count": processing.trace.attempt_count,
                "applied_fields": [field.value for field in processing.trace.applied_fields],
                "ambiguity_fields": [item.field.value for item in processing.trace.ambiguities],
                "unresolved_fields": [field.value for field in processing.trace.unresolved_fields],
                "currency_conflict_fields": [
                    item.field.value for item in processing.trace.currency_conflicts
                ],
                "before_phase": before_phase,
                "after_phase": state.phase,
                "interaction_kind": None if pending is None else pending.kind,
                "requested_field": None if pending is None else pending.field,
                "candidate_changed": candidate_changed,
                "outcome_kind": outcome_kind,
            },
        )
        return self._active_result(state, outcome_kind=outcome_kind)

    def _progress(
        self,
        state: TransactionCaptureState,
        trace: ContributionProcessingTrace,
    ) -> TransactionCaptureState:
        processing_requirement = self._processing_requirement(trace)
        if processing_requirement is not None:
            return self._require_interaction(state, processing_requirement)
        assessment = self._assess(state.candidate)
        if isinstance(assessment, _InteractionRequired):
            return self._require_interaction(state, assessment)
        return state.await_confirmation()

    def _processing_requirement(
        self,
        trace: ContributionProcessingTrace,
    ) -> _InteractionRequired | None:
        if trace.clarification_needed:
            return _InteractionRequired(PendingInteraction(kind=PendingInteractionKind.CLARIFY))
        if trace.ambiguities:
            ambiguity = trace.ambiguities[0]
            return _InteractionRequired(
                PendingInteraction(
                    kind=PendingInteractionKind.DISAMBIGUATE,
                    field=ambiguity.field,
                    options=tuple(
                        InteractionOption(value=option.value, label=option.label)
                        for option in ambiguity.options
                    ),
                )
            )
        if trace.currency_conflicts:
            conflict = trace.currency_conflicts[0]
            return _InteractionRequired(
                PendingInteraction(
                    kind=PendingInteractionKind.CORRECT,
                    field=conflict.field,
                    reason=PendingInteractionReason.CURRENCY_CONFLICT,
                )
            )
        if trace.unresolved_fields:
            return _InteractionRequired(
                PendingInteraction(
                    kind=PendingInteractionKind.CORRECT,
                    field=trace.unresolved_fields[0],
                    reason=PendingInteractionReason.UNRESOLVED_VALUE,
                )
            )
        return None

    def _assess(self, candidate: TransactionCandidate) -> _CandidateAssessment:
        rules: tuple[Callable[[], _InteractionRequired | None], ...] = (
            lambda: self._local_validity_assessment(candidate),
            lambda: self._missing_fields_assessment(candidate),
            lambda: self._reference_validity_assessment(candidate),
        )
        for rule in rules:
            interaction = rule()
            if interaction is not None:
                return interaction
        return _ReadyForExecution()

    @staticmethod
    def _local_validity_assessment(
        candidate: TransactionCandidate,
    ) -> _InteractionRequired | None:
        if not candidate.locally_invalid_fields:
            return None
        field = candidate.locally_invalid_fields[0]
        return _InteractionRequired(
            PendingInteraction(kind=PendingInteractionKind.CORRECT, field=field),
            clear_field=field,
        )

    @staticmethod
    def _missing_fields_assessment(
        candidate: TransactionCandidate,
    ) -> _InteractionRequired | None:
        if not candidate.missing_fields:
            return None
        return _InteractionRequired(
            PendingInteraction(
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
            PendingInteraction(kind=PendingInteractionKind.CORRECT, field=field),
            clear_field=field,
        )

    @staticmethod
    def _require_interaction(
        state: TransactionCaptureState,
        requirement: _InteractionRequired,
    ) -> TransactionCaptureState:
        if requirement.clear_field is not None:
            state = state.update_candidate(
                state.candidate.apply(_clear_field(requirement.clear_field))
            )
        return state.request(requirement.interaction)

    def _active_result(
        self,
        state: TransactionCaptureState,
        *,
        outcome_kind: str,
        message: str | None = None,
    ) -> CapabilityResult[TransactionCaptureState]:
        return ActiveCapabilityResult(
            state=state,
            view=self._presentation.view(state),
            outcome_kind=outcome_kind,
            message=message or self._presentation.message(state),
        )


def _clear_field(field: CandidateField) -> CandidatePatch:
    updates: dict[CandidateField, CandidatePatch] = {
        CandidateField.TYPE: CandidatePatch(type=None),
        CandidateField.AMOUNT_MINOR: CandidatePatch(amount_minor=None),
        CandidateField.OCCURRED_ON: CandidatePatch(occurred_on=None),
        CandidateField.ACCOUNT_ID: CandidatePatch(account_id=None),
        CandidateField.SPENDING_CATEGORY_ID: CandidatePatch(spending_category_id=None),
        CandidateField.INCOME_CATEGORY_ID: CandidatePatch(income_category_id=None),
        CandidateField.SOURCE_ACCOUNT_ID: CandidatePatch(source_account_id=None),
        CandidateField.DESTINATION_ACCOUNT_ID: CandidatePatch(destination_account_id=None),
        CandidateField.BALANCE_CHANGE_MINOR: CandidatePatch(balance_change_minor=None),
        CandidateField.DESCRIPTION: CandidatePatch(description=None),
        CandidateField.MERCHANT_NAME: CandidatePatch(merchant_name=None),
        CandidateField.NOTES: CandidatePatch(notes=None),
        CandidateField.CURRENCY_CODE: CandidatePatch(currency_code=None),
    }
    return updates[field]
