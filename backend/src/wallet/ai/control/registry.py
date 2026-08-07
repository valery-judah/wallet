from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import TypeVar

from wallet.observability import bind_log_context, error_details, log_event

from .domain import Conversation, TurnRequest, TurnResponse, fingerprint_request

logger = logging.getLogger(__name__)


class ConversationNotFoundError(LookupError):
    pass


class RequestIdConflictError(RuntimeError):
    pass


_ResultT = TypeVar("_ResultT")


@dataclass(slots=True)
class _ConversationEntry:
    conversation: Conversation
    lock: Lock = field(default_factory=Lock, repr=False)


class ConversationRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, _ConversationEntry] = {}
        self._membership_lock = Lock()

    def create(
        self,
        initial: Conversation,
        transition: Callable[[Conversation], tuple[Conversation, _ResultT]],
    ) -> _ResultT:
        conversation, result = transition(initial)
        entry = _ConversationEntry(conversation=conversation)
        with self._membership_lock:
            if conversation.id in self._entries:
                raise ValueError(f"conversation already exists: {conversation.id}")
            self._entries[conversation.id] = entry
        return result

    def _entry(self, conversation_id: str) -> _ConversationEntry:
        with self._membership_lock:
            entry = self._entries.get(conversation_id)
        if entry is None:
            raise ConversationNotFoundError(conversation_id)
        return entry

    def read(self, conversation_id: str) -> Conversation:
        entry = self._entry(conversation_id)
        with entry.lock:
            return entry.conversation

    def update(
        self,
        conversation_id: str,
        transition: Callable[[Conversation], tuple[Conversation, _ResultT]],
    ) -> _ResultT:
        entry = self._entry(conversation_id)
        with entry.lock:
            conversation, result = transition(entry.conversation)
            entry.conversation = conversation
            return result


@dataclass(frozen=True, slots=True)
class _StoredTurnReplay:
    request_fingerprint: str
    response_snapshot: TurnResponse


@dataclass(slots=True)
class _TurnReplayEntry:
    stored: _StoredTurnReplay | None = None
    lock: Lock = field(default_factory=Lock, repr=False)


class TurnReplayRegistry:
    """Serialize global turn IDs and replay successful response snapshots."""

    def __init__(self) -> None:
        self._entries: dict[str, _TurnReplayEntry] = {}
        self._membership_lock = Lock()

    def replay_or_execute(
        self,
        request: TurnRequest,
        execute: Callable[[], TurnResponse],
    ) -> TurnResponse:
        fingerprint = fingerprint_request(request)
        with self._membership_lock:
            entry = self._entries.setdefault(request.request_id, _TurnReplayEntry())
        with entry.lock:
            stored = entry.stored
            if stored is not None:
                if stored.request_fingerprint != fingerprint:
                    conflict = RequestIdConflictError(request.request_id)
                    log_event(
                        logger,
                        logging.WARNING,
                        "control.turn.replay_conflict",
                        data={"target": request.conversation_id or "new"},
                        error=error_details(
                            conflict,
                            code="request_id_conflict",
                            retryable=False,
                        ),
                    )
                    raise conflict
                with bind_log_context(
                    conversation_id=stored.response_snapshot.conversation.id,
                ):
                    log_event(
                        logger,
                        logging.INFO,
                        "control.turn.replayed",
                        data={
                            "conversation_version": (stored.response_snapshot.conversation.version),
                            "outcome_kind": stored.response_snapshot.outcome.kind,
                        },
                    )
                return stored.response_snapshot

            response = execute()
            entry.stored = _StoredTurnReplay(fingerprint, response)
            with bind_log_context(conversation_id=response.conversation.id):
                log_event(
                    logger,
                    logging.INFO,
                    "control.turn.committed",
                    data={
                        "conversation_version": response.conversation.version,
                        "outcome_kind": response.outcome.kind,
                    },
                )
            return response
