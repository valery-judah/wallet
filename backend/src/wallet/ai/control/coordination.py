from __future__ import annotations

from collections.abc import Callable

from .domain import Conversation, TurnRequest, TurnResponse, TurnTransition
from .registry import ConversationRegistry, TurnReplayRegistry


class TurnExecutionCoordinator:
    """Coordinate replay and atomic process-local conversation updates."""

    def __init__(
        self,
        *,
        conversations: ConversationRegistry,
        turn_replays: TurnReplayRegistry,
        generate_conversation_id: Callable[[], str],
    ) -> None:
        self._conversations = conversations
        self._turn_replays = turn_replays
        self._generate_conversation_id = generate_conversation_id

    def read(self, conversation_id: str) -> Conversation:
        return self._conversations.read(conversation_id)

    def execute(
        self,
        request: TurnRequest,
        process: Callable[[Conversation], TurnTransition],
    ) -> TurnResponse:
        return self._turn_replays.replay_or_execute(
            request,
            lambda: self._execute_once(request, process),
        )

    def _execute_once(
        self,
        request: TurnRequest,
        process: Callable[[Conversation], TurnTransition],
    ) -> TurnResponse:
        def transition(before: Conversation) -> tuple[Conversation, TurnResponse]:
            processed = process(before)
            return processed.conversation, processed.response

        if request.conversation_id is None:
            initial = Conversation(id=self._generate_conversation_id())
            return self._conversations.create(initial, transition)
        return self._conversations.update(request.conversation_id, transition)
