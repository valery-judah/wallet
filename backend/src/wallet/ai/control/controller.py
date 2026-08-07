from __future__ import annotations

import logging

from wallet.observability import bind_log_context, error_details, log_event

from .coordination import TurnExecutionCoordinator
from .domain import ConversationView, TurnRequest, TurnResponse
from .engine import ConversationEngine, InvalidTurnRequestError
from .registry import ConversationNotFoundError

logger = logging.getLogger(__name__)


class ConversationController:
    """Expose conversation use cases through an explicit engine/coordinator boundary."""

    def __init__(
        self,
        *,
        engine: ConversationEngine,
        coordinator: TurnExecutionCoordinator,
    ) -> None:
        self._engine = engine
        self._coordinator = coordinator

    def get_conversation(self, conversation_id: str) -> ConversationView:
        return self._engine.project(self._coordinator.read(conversation_id))

    def submit_turn(self, request: TurnRequest) -> TurnResponse:
        with bind_log_context(
            origin="conversation",
            request_id=request.request_id,
            conversation_id=request.conversation_id,
            operation_id=f"request:{request.request_id}",
        ):
            log_event(
                logger,
                logging.INFO,
                "control.turn.received",
                data={"input_kind": request.input.kind},
            )
            try:
                self._engine.validate_request(request)
            except InvalidTurnRequestError as exc:
                log_event(
                    logger,
                    logging.WARNING,
                    "control.turn.validation_rejected",
                    data={"input_kind": request.input.kind},
                    error=error_details(
                        exc,
                        code="invalid_turn_request",
                        retryable=False,
                    ),
                )
                raise
            try:
                return self._coordinator.execute(
                    request,
                    lambda before: self._engine.process(before, request),
                )
            except ConversationNotFoundError as exc:
                log_event(
                    logger,
                    logging.WARNING,
                    "control.turn.failed",
                    data={"stage": "load_conversation", "input_kind": request.input.kind},
                    error=error_details(
                        exc,
                        code="conversation_not_found",
                        retryable=False,
                    ),
                )
                raise
