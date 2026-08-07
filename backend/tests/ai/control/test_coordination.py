from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from wallet.ai.control.coordination import TurnExecutionCoordinator
from wallet.ai.control.domain import (
    Conversation,
    ConversationView,
    MessageSubmission,
    TurnOutcome,
    TurnRequest,
    TurnResponse,
    TurnTransition,
)
from wallet.ai.control.registry import (
    ConversationNotFoundError,
    ConversationRegistry,
    TurnReplayRegistry,
)


def test_coordinator_replays_a_concurrent_duplicate_first_turn_once() -> None:
    coordinator = _coordinator()
    request = TurnRequest("request-1", MessageSubmission("begin"))
    entered = Event()
    release = Event()
    calls = 0

    def process(before: Conversation) -> TurnTransition:
        nonlocal calls
        calls += 1
        entered.set()
        if not release.wait(timeout=2):
            raise TimeoutError("process was not released")
        return _transition(before, request)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(coordinator.execute, request, process)
        assert entered.wait(timeout=1)
        replay = executor.submit(coordinator.execute, request, process)
        assert not replay.done()
        release.set()
        first_response = first.result(timeout=1)
        replay_response = replay.result(timeout=1)

    assert calls == 1
    assert first_response == replay_response
    assert first_response.conversation.id == "conversation-1"


def test_coordinator_failed_create_publishes_nothing_and_retries_with_a_new_id() -> None:
    coordinator = _coordinator()
    request = TurnRequest("request-1", MessageSubmission("retry"))

    def fail(before: Conversation) -> TurnTransition:
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        coordinator.execute(request, fail)
    with pytest.raises(ConversationNotFoundError):
        coordinator.read("conversation-1")

    response = coordinator.execute(request, lambda before: _transition(before, request))

    assert response.conversation.id == "conversation-2"


def test_coordinator_failed_update_preserves_state_and_allows_retry() -> None:
    coordinator = _coordinator()
    created_request = TurnRequest("request-1", MessageSubmission("create"))
    created = coordinator.execute(
        created_request,
        lambda before: _transition(before, created_request),
    )
    update_request = TurnRequest(
        "request-2",
        MessageSubmission("update"),
        created.conversation.id,
    )
    before = coordinator.read(created.conversation.id)

    def fail(conversation: Conversation) -> TurnTransition:
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        coordinator.execute(update_request, fail)
    assert coordinator.read(created.conversation.id) == before

    updated = coordinator.execute(
        update_request,
        lambda conversation: _transition(conversation, update_request),
    )

    assert updated.conversation.version == 2


def _coordinator() -> TurnExecutionCoordinator:
    conversation_ids = iter(("conversation-1", "conversation-2", "conversation-3"))
    return TurnExecutionCoordinator(
        conversations=ConversationRegistry(),
        turn_replays=TurnReplayRegistry(),
        generate_conversation_id=lambda: next(conversation_ids),
    )


def _transition(before: Conversation, request: TurnRequest) -> TurnTransition:
    outcome = TurnOutcome("processed", None, "Processed.")
    after = Conversation(
        before.id,
        before.version + 1,
        last_outcome=outcome,
    )
    response = TurnResponse(
        request.request_id,
        ConversationView(after.id, after.version, None, outcome),
        outcome,
    )
    return TurnTransition(after, response)
