from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date

import pytest

from wallet.ai.capabilities.contract import (
    ActiveCapabilityResult,
    CapabilityActionOffer,
    CapabilityContext,
    CapabilityDefinition,
    CapabilityInput,
    CapabilityMessage,
    CapabilityResult,
    CapabilityRoutingProfile,
    CapabilityView,
    CompletedCapabilityResult,
)
from wallet.ai.control.capability_registry import CapabilityRegistry
from wallet.ai.control.domain import (
    ControlAction,
    ControlActionSubmission,
    Conversation,
    MessageSubmission,
    PublicCapabilityView,
    TaskActionSubmission,
    TurnRequest,
)
from wallet.ai.control.engine import (
    ConversationEngine,
    ConversationProcessingError,
    InvalidTurnRequestError,
    TurnGuardConflictError,
)
from wallet.ai.control.resolution import TurnResolver
from wallet.ai.control.routing import (
    MessageRoutingContext,
    RouteDecision,
    StartRouteDecision,
)

TODAY = date(2026, 8, 6)


@dataclass
class RecordingCapability:
    contexts: list[CapabilityContext] = field(default_factory=list)
    handles: int = 0
    fail_start: bool = False
    complete_on_restart: bool = False

    @property
    def definition(self) -> CapabilityDefinition:
        return CapabilityDefinition(
            "test.engine",
            "Exercise the engine.",
            CapabilityRoutingProfile(
                ("The user asks to exercise the engine.",),
                ("Exercise the engine.",),
            ),
        )

    def start(
        self,
        content: str | None,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        self.contexts.append(context)
        if self.fail_start:
            raise RuntimeError("capability failed")
        if content is None and self.complete_on_restart:
            return CompletedCapabilityResult(
                CapabilityView("restart_completed", {"safe": True}),
                "restart_completed",
                "Restart completed the capability.",
                {"completed": True},
            )
        return ActiveCapabilityResult(
            (() if content is None else (content,)),
            CapabilityView(
                "recording",
                {"content": content},
                (CapabilityActionOffer("finish", "Finish", {}),),
            ),
            "started",
            "Started.",
        )

    def handle(
        self,
        state: tuple[str, ...],
        input: CapabilityInput,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        self.contexts.append(context)
        self.handles += 1
        assert isinstance(input, CapabilityMessage)
        return CompletedCapabilityResult(
            None,
            "completed",
            "Completed.",
            {"messages": [*state, input.content]},
        )


@dataclass
class FixedRouter:
    decisions: deque[RouteDecision]

    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        if self.decisions:
            return self.decisions.popleft()
        raise AssertionError("fixed router has no idle decision")


def test_engine_applies_lifecycle_versions_context_and_public_projection() -> None:
    capability = RecordingCapability()
    engine = _engine(capability)
    initial = Conversation("conversation-1")

    started = engine.process(
        initial,
        TurnRequest("request-1", MessageSubmission("begin")),
    )
    task = started.response.conversation.active_task
    assert task is not None
    assert started.conversation.version == 1
    assert started.conversation.recent_capability_id == capability.definition.id
    assert task.id == "task-1"
    assert task.version == 1
    assert isinstance(started.response.outcome.view, PublicCapabilityView)
    assert started.response.outcome.view.available_actions[0].expected_task_id == "task-1"
    assert started.response.outcome.view.available_actions[0].expected_conversation_version == 1
    assert capability.contexts[0].operation_id == "request:request-1"
    assert capability.contexts[0].current_date == TODAY

    completed = engine.process(
        started.conversation,
        TurnRequest(
            "request-2",
            MessageSubmission("complete"),
            started.conversation.id,
        ),
    )

    assert completed.conversation.version == 2
    assert completed.conversation.current is None
    assert completed.conversation.recent_capability_id == capability.definition.id
    assert completed.response.conversation.active_task is None
    assert completed.response.outcome.kind == "completed"


def test_engine_rejects_initial_guard_and_stale_guard_before_capability_work() -> None:
    capability = RecordingCapability()
    engine = _engine(capability)
    guarded = TurnRequest(
        "request-1",
        TaskActionSubmission("task-1", 1, "finish", {}),
    )

    with pytest.raises(InvalidTurnRequestError):
        engine.validate_request(guarded)

    started = engine.process(
        Conversation("conversation-1"),
        TurnRequest("request-2", MessageSubmission("begin")),
    )
    stale = TurnRequest(
        "request-3",
        TaskActionSubmission("task-1", 99, "finish", {}),
        "conversation-1",
    )
    with pytest.raises(TurnGuardConflictError):
        engine.process(started.conversation, stale)

    assert capability.handles == 0


def test_engine_wraps_capability_failure_without_returning_a_transition() -> None:
    capability = RecordingCapability(fail_start=True)
    engine = _engine(capability)

    with pytest.raises(ConversationProcessingError) as caught:
        engine.process(
            Conversation("conversation-1"),
            TurnRequest("request-1", MessageSubmission("begin")),
        )

    assert isinstance(caught.value.__cause__, RuntimeError)


def test_restart_projects_a_completed_capability_result_without_an_active_task() -> None:
    capability = RecordingCapability(complete_on_restart=True)
    engine = _engine(capability)
    started = engine.process(
        Conversation("conversation-1"),
        TurnRequest("request-1", MessageSubmission("begin")),
    )
    task = started.conversation.current
    assert task is not None

    restarted = engine.process(
        started.conversation,
        TurnRequest(
            "request-2",
            ControlActionSubmission(
                ControlAction.RESTART,
                task.task_id,
                started.conversation.version,
            ),
            started.conversation.id,
        ),
    )

    assert restarted.conversation.current is None
    assert restarted.response.outcome.kind == "restarted"
    assert restarted.response.outcome.result == {"completed": True}
    assert isinstance(restarted.response.outcome.view, PublicCapabilityView)


def _engine(capability: RecordingCapability) -> ConversationEngine:
    task_ids = iter(("task-1", "task-2"))
    router = FixedRouter(deque((StartRouteDecision(capability.definition.id),)))
    return ConversationEngine(
        capabilities=CapabilityRegistry((capability,)),
        resolver=TurnResolver(router=router),
        generate_task_id=lambda: next(task_ids),
        today=lambda: TODAY,
    )
