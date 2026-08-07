from __future__ import annotations

import logging

import pytest

from wallet.ai.control.domain import (
    Conversation,
    ConversationView,
    MessageSubmission,
    TurnOutcome,
    TurnRequest,
    TurnResponse,
)
from wallet.ai.control.registry import (
    ConversationNotFoundError,
    ConversationRegistry,
    RequestIdConflictError,
    TurnReplayRegistry,
)


def test_conversation_registry_commits_only_successful_transitions() -> None:
    registry = ConversationRegistry()
    initial = Conversation("conversation-1")

    def fail(conversation: Conversation) -> tuple[Conversation, str]:
        raise RuntimeError("transition failed")

    with pytest.raises(RuntimeError, match="transition failed"):
        registry.create(initial, fail)
    with pytest.raises(ConversationNotFoundError):
        registry.read(initial.id)

    created = Conversation(initial.id, 1)
    assert registry.create(initial, lambda _: (created, "created")) == "created"
    with pytest.raises(RuntimeError, match="transition failed"):
        registry.update(initial.id, fail)
    assert registry.read(initial.id) == created

    updated = Conversation(initial.id, 2)
    assert registry.update(initial.id, lambda _: (updated, "updated")) == "updated"
    assert registry.read(initial.id) == updated


def test_turn_replay_returns_stored_response_and_executes_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    registry = TurnReplayRegistry()
    request = TurnRequest("request-1", MessageSubmission("same input"))
    response = _response(request)
    calls = 0
    caplog.set_level(logging.INFO, logger="wallet.ai.control.registry")

    def execute() -> TurnResponse:
        nonlocal calls
        calls += 1
        return response

    first = registry.replay_or_execute(request, execute)
    replay = registry.replay_or_execute(request, execute)

    assert first is response
    assert replay is response
    assert calls == 1
    replay_record = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "control.turn.replayed"
    )
    assert replay_record.event_data["conversation_version"] == 1
    assert "same input" not in caplog.text


def test_turn_replay_rejects_changed_input_or_target_before_execution() -> None:
    registry = TurnReplayRegistry()
    request = TurnRequest(
        "request-1",
        MessageSubmission("original input"),
        "conversation-1",
    )
    registry.replay_or_execute(request, lambda: _response(request))

    changed_requests = (
        TurnRequest(
            "request-1",
            MessageSubmission("changed input"),
            "conversation-1",
        ),
        TurnRequest(
            "request-1",
            MessageSubmission("original input"),
            "conversation-2",
        ),
    )
    for changed in changed_requests:
        with pytest.raises(RequestIdConflictError):
            registry.replay_or_execute(
                changed,
                lambda: pytest.fail("conflicting replay must not execute"),
            )


def test_turn_replay_does_not_store_failed_execution() -> None:
    registry = TurnReplayRegistry()
    request = TurnRequest("request-1", MessageSubmission("retry me"))
    response = _response(request)
    calls = 0

    def fail() -> TurnResponse:
        nonlocal calls
        calls += 1
        raise RuntimeError("processing failed")

    def succeed() -> TurnResponse:
        nonlocal calls
        calls += 1
        return response

    with pytest.raises(RuntimeError, match="processing failed"):
        registry.replay_or_execute(request, fail)

    assert registry.replay_or_execute(request, succeed) is response
    assert calls == 2


def _response(request: TurnRequest) -> TurnResponse:
    outcome = TurnOutcome("completed", None, "Completed.")
    return TurnResponse(
        request_id=request.request_id,
        conversation=ConversationView("conversation-1", 1, None, outcome),
        outcome=outcome,
    )
