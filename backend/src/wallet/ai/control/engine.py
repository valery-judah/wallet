from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import date
from typing import assert_never

from wallet.ai.capabilities.contract import (
    ActiveCapabilityResult,
    CapabilityContext,
    CapabilityResult,
    CapabilityView,
    CompletedCapabilityResult,
)
from wallet.observability import bind_log_context, error_details, log_event

from .capability_registry import CapabilityRegistry
from .domain import (
    ActiveTaskView,
    Cancel,
    CapabilitySession,
    Clarify,
    ContinueCurrent,
    ControlAction,
    ControlActionSubmission,
    Conversation,
    ConversationView,
    Help,
    PublicActionOffer,
    PublicCapabilityView,
    ResolvedTurn,
    Restart,
    Start,
    TaskActionSubmission,
    TurnGuard,
    TurnOutcome,
    TurnRequest,
    TurnResponse,
    TurnTransition,
    Unsupported,
)
from .resolution import TurnResolver

logger = logging.getLogger(__name__)


def _resolved_capability_id(
    resolved: ResolvedTurn,
    conversation: Conversation,
) -> str | None:
    if isinstance(resolved.instruction, Start):
        return resolved.instruction.capability_id
    if conversation.current is not None:
        return conversation.current.capability_id
    return None


class InvalidTurnRequestError(ValueError):
    pass


class TurnGuardConflictError(RuntimeError):
    pass


class ConversationProcessingError(RuntimeError):
    pass


class ConversationEngine:
    """Apply one validated turn to a conversation without coordinating storage."""

    def __init__(
        self,
        *,
        capabilities: CapabilityRegistry,
        resolver: TurnResolver,
        generate_task_id: Callable[[], str],
        today: Callable[[], date] = date.today,
    ) -> None:
        self._capabilities = capabilities
        self._resolver = resolver
        self._generate_task_id = generate_task_id
        self._today = today

    def validate_request(self, request: TurnRequest) -> None:
        if request.conversation_id is not None:
            return
        if isinstance(request.input, TaskActionSubmission) or (
            isinstance(request.input, ControlActionSubmission)
            and request.input.action is not ControlAction.HELP
        ):
            raise InvalidTurnRequestError("guarded input requires a conversation id")

    def process(self, before: Conversation, request: TurnRequest) -> TurnTransition:
        context = CapabilityContext(
            conversation_id=before.id,
            request_id=request.request_id,
            operation_id=f"request:{request.request_id}",
            current_date=self._today(),
        )
        stage = "resolve"
        with bind_log_context(
            origin="conversation",
            request_id=request.request_id,
            conversation_id=before.id,
            operation_id=context.operation_id,
        ):
            try:
                resolved = self._resolver.resolve(request.input, before, self._capabilities)
                capability_id = _resolved_capability_id(resolved, before)
                with bind_log_context(
                    capability_id=capability_id,
                    task_id=None if before.current is None else before.current.task_id,
                ):
                    stage = "validate_resolution"
                    self._validate_resolved(resolved, before)
                    stage = "execute_capability"
                    next_current, outcome = self._execute(resolved, before, context)
            except (InvalidTurnRequestError, TurnGuardConflictError) as exc:
                log_event(
                    logger,
                    logging.WARNING,
                    "control.turn.validation_rejected",
                    data={
                        "stage": stage,
                        "conversation_version": before.version,
                        "input_kind": request.input.kind,
                    },
                    error=error_details(
                        exc,
                        code="turn_guard_conflict",
                        retryable=False,
                    ),
                )
                raise
            except Exception as exc:
                log_event(
                    logger,
                    logging.ERROR,
                    "control.turn.failed",
                    data={
                        "stage": stage,
                        "conversation_version": before.version,
                        "input_kind": request.input.kind,
                    },
                    error=error_details(
                        exc,
                        code="conversation_processing_failed",
                        retryable=True,
                    ),
                    exc_info=exc,
                )
                raise ConversationProcessingError() from exc

        next_version = before.version + 1
        projected_outcome = self._bind_outcome(
            outcome,
            task_id=None if next_current is None else next_current.task_id,
            conversation_version=next_version,
        )
        after = Conversation(
            id=before.id,
            version=next_version,
            current=next_current,
            last_outcome=projected_outcome,
            # Keep only capability identity as bounded routing memory. Capability state and
            # prior messages remain private and never enter the message-router prompt.
            recent_capability_id=outcome.capability_id or before.recent_capability_id,
        )
        response = TurnResponse(
            request_id=request.request_id,
            conversation=self.project(after),
            outcome=projected_outcome,
        )
        with bind_log_context(
            conversation_id=before.id,
            capability_id=outcome.capability_id,
            task_id=None if next_current is None else next_current.task_id,
        ):
            log_event(
                logger,
                logging.INFO,
                "control.turn.processed",
                data={
                    "before_version": before.version,
                    "after_version": next_version,
                    "instruction": type(resolved.instruction).__name__,
                    "outcome_kind": outcome.kind,
                    "active_task": next_current is not None,
                },
            )
        return TurnTransition(after, response)

    def project(self, conversation: Conversation) -> ConversationView:
        current_view = None
        if conversation.current is not None:
            current_view = ActiveTaskView(
                id=conversation.current.task_id,
                version=conversation.current.version,
                view=self._bind_view(
                    conversation.current.view,
                    conversation.current.task_id,
                    conversation.version,
                ),
            )
        return ConversationView(
            conversation.id,
            conversation.version,
            current_view,
            conversation.last_outcome,
        )

    def _validate_resolved(self, resolved: ResolvedTurn, conversation: Conversation) -> None:
        """Reject instructions that are illegal for the current conversation state."""

        if resolved.guard is not None:
            self._validate_guard(resolved.guard, conversation)
        match resolved.instruction:
            case ContinueCurrent():
                if conversation.current is None:
                    if resolved.guard is not None:
                        raise TurnGuardConflictError("no capability is current")
                    raise ConversationProcessingError("continue without a current capability")
            case Start(capability_id=capability_id):
                if conversation.current is not None or not self._capabilities.contains(
                    capability_id
                ):
                    raise ConversationProcessingError("invalid capability start")
            case Unsupported():
                if conversation.current is not None:
                    raise ConversationProcessingError(
                        "unsupported outcome is only legal while idle"
                    )
            case Cancel() | Restart() | Help() | Clarify():
                # These are legal while either idle or active. Their execution branches decide
                # whether to mutate the current task or return a no-op outcome.
                pass
            case _ as unreachable:
                # Static exhaustiveness guard: mypy fails here if the union gains a variant.
                assert_never(unreachable)

    def _validate_guard(self, guard: TurnGuard, conversation: Conversation) -> None:
        if (
            conversation.version != guard.expected_conversation_version
            or conversation.current is None
            or conversation.current.task_id != guard.expected_task_id
        ):
            raise TurnGuardConflictError("turn target or conversation version is stale")

    def _execute(
        self,
        resolved: ResolvedTurn,
        conversation: Conversation,
        context: CapabilityContext,
    ) -> tuple[CapabilitySession | None, TurnOutcome]:
        """Execute exactly one validated instruction and return the next task and outcome."""

        match resolved.instruction:
            case Start(capability_id=capability_id, content=content):
                capability = self._capabilities.get(capability_id)
                result = capability.start(content, context)
                return self._apply_capability_result(
                    capability_id=capability_id,
                    result=result,
                    active_version=1,
                    task_id=self._generate_task_id(),
                )
            case ContinueCurrent(capability_input=capability_input):
                current = conversation.current
                if current is None:
                    raise ConversationProcessingError("continue without current capability")
                capability = self._capabilities.get(current.capability_id)
                result = capability.handle(current.state, capability_input, context)
                return self._apply_capability_result(
                    capability_id=current.capability_id,
                    result=result,
                    active_version=current.version + 1,
                    task_id=current.task_id,
                )
            case Cancel():
                if conversation.current is None:
                    return None, TurnOutcome(
                        "nothing_to_cancel", None, "There is no current task to cancel."
                    )
                return None, TurnOutcome("current_task_cancelled", None, "Current task cancelled.")
            case Restart():
                current = conversation.current
                if current is None:
                    return None, TurnOutcome(
                        "nothing_to_restart", None, "There is no current task to restart."
                    )
                capability = self._capabilities.get(current.capability_id)
                result = capability.start(None, context)
                next_current, capability_outcome = self._apply_capability_result(
                    capability_id=current.capability_id,
                    result=result,
                    active_version=1,
                    task_id=self._generate_task_id(),
                )
                return next_current, TurnOutcome(
                    "restarted",
                    current.capability_id,
                    "Current task restarted.",
                    view=capability_outcome.view,
                    result=capability_outcome.result,
                )
            case Help():
                descriptions = "; ".join(
                    definition.description for definition in self._capabilities.definitions
                )
                return conversation.current, TurnOutcome(
                    "help", None, f"I can help with: {descriptions}"
                )
            case Clarify(code=code):
                kind, message = self._clarification(code)
                return conversation.current, TurnOutcome(kind, None, message)
            case Unsupported():
                return conversation.current, TurnOutcome(
                    "unsupported",
                    None,
                    "I cannot match that request to an available capability.",
                )
            case _ as unreachable:
                assert_never(unreachable)

    def _apply_capability_result(
        self,
        *,
        capability_id: str,
        result: CapabilityResult[object],
        active_version: int,
        task_id: str,
    ) -> tuple[CapabilitySession | None, TurnOutcome]:
        match result:
            case ActiveCapabilityResult(
                state=state,
                view=view,
                outcome_kind=outcome_kind,
                message=message,
            ):
                current = CapabilitySession(
                    task_id=task_id,
                    capability_id=capability_id,
                    version=active_version,
                    state=state,
                    view=view,
                )
                return current, TurnOutcome(
                    outcome_kind,
                    capability_id,
                    message,
                    view=view,
                )
            case CompletedCapabilityResult(
                view=view,
                outcome_kind=outcome_kind,
                message=message,
                domain_result=domain_result,
            ):
                return None, TurnOutcome(
                    outcome_kind,
                    capability_id,
                    message,
                    view=view,
                    result=domain_result,
                )
            case _ as unreachable:
                # Static exhaustiveness guard for the closed capability-result family.
                assert_never(unreachable)

    def _bind_outcome(
        self,
        outcome: TurnOutcome,
        *,
        task_id: str | None,
        conversation_version: int,
    ) -> TurnOutcome:
        if outcome.view is None:
            return outcome
        return replace(
            outcome,
            view=self._bind_view(outcome.view, task_id, conversation_version),
        )

    def _bind_view(
        self,
        view: CapabilityView | PublicCapabilityView,
        task_id: str | None,
        conversation_version: int,
    ) -> PublicCapabilityView:
        if isinstance(view, PublicCapabilityView):
            return view
        actions = tuple(
            PublicActionOffer(
                action=offer.action,
                label=offer.label,
                payload=offer.payload,
                expected_task_id=self._required_task_id(task_id),
                expected_conversation_version=conversation_version,
            )
            for offer in view.available_actions
        )
        return PublicCapabilityView(view.kind, dict(view.data), actions)

    @staticmethod
    def _required_task_id(task_id: str | None) -> str:
        if task_id is None:
            raise ConversationProcessingError("completed view cannot offer task actions")
        return task_id

    @staticmethod
    def _clarification(code: str) -> tuple[str, str]:
        clarifications = {
            "idle_route_ambiguous": (
                "clarify_idle_route",
                "Please clarify which task you want to perform.",
            ),
            "compound_instruction": (
                "split_compound_instruction",
                "Please send the control and the additional request as separate turns.",
            ),
        }
        try:
            return clarifications[code]
        except KeyError as exc:
            raise ConversationProcessingError("unknown clarification code") from exc
