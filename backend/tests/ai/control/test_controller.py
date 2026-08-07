from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from threading import Event

import pytest

from wallet.ai.capabilities.contract import (
    ActiveCapabilityResult,
    CapabilityAction,
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
from wallet.ai.control.controller import ConversationController
from wallet.ai.control.coordination import TurnExecutionCoordinator
from wallet.ai.control.domain import (
    ControlAction,
    ControlActionSubmission,
    MessageSubmission,
    TaskActionSubmission,
    TurnRequest,
)
from wallet.ai.control.engine import (
    ConversationEngine,
    ConversationProcessingError,
    InvalidTurnRequestError,
    TurnGuardConflictError,
)
from wallet.ai.control.registry import (
    ConversationNotFoundError,
    ConversationRegistry,
    RequestIdConflictError,
    TurnReplayRegistry,
)
from wallet.ai.control.resolution import TurnResolver
from wallet.ai.control.routing import (
    ClarifyRouteDecision,
    MessageRoutingContext,
    RouteDecision,
    StartRouteDecision,
    UnsupportedRouteDecision,
)

TODAY = date(2026, 8, 6)


@dataclass
class FakeCapability:
    capability_id: str
    starts: list[tuple[str | None, CapabilityContext]] = field(default_factory=list)
    handles: list[tuple[tuple[str, ...], CapabilityInput, CapabilityContext]] = field(
        default_factory=list
    )
    fail_next_start: bool = False
    fail_messages: set[str] = field(default_factory=set)

    @property
    def definition(self) -> CapabilityDefinition:
        return CapabilityDefinition(
            id=self.capability_id,
            description="Exercise a fake task.",
            routing=CapabilityRoutingProfile(
                routes_when=("The user requests the fake task.",),
                examples=("Run the fake task.",),
            ),
        )

    def start(
        self,
        content: str | None,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        self.starts.append((content, context))
        if self.fail_next_start:
            self.fail_next_start = False
            raise RuntimeError("start failed")
        state = () if content is None else (content,)
        return self._active(state, "started")

    def handle(
        self,
        state: tuple[str, ...],
        input: CapabilityInput,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        self.handles.append((state, input, context))
        if isinstance(input, CapabilityMessage):
            if input.content in self.fail_messages:
                raise RuntimeError("handle failed")
            if input.content == "complete":
                return self._completed(state)
            return self._active((*state, input.content), "continued")
        if isinstance(input, CapabilityAction) and input.action == "finish":
            return self._completed(state)
        return self._active(state, "action_unavailable")

    @staticmethod
    def _active(state: tuple[str, ...], outcome: str) -> CapabilityResult[tuple[str, ...]]:
        return ActiveCapabilityResult(
            state,
            CapabilityView(
                "fake",
                {"messages": list(state)},
                (CapabilityActionOffer("finish", "Finish", {}),),
            ),
            outcome,
            "Fake task is active.",
        )

    @staticmethod
    def _completed(state: tuple[str, ...]) -> CapabilityResult[tuple[str, ...]]:
        return CompletedCapabilityResult(
            None,
            "completed",
            "Fake task completed.",
            {"messages": list(state)},
        )


@dataclass
class BlockingFakeCapability(FakeCapability):
    entered: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)

    def handle(
        self,
        state: tuple[str, ...],
        input: CapabilityInput,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        if isinstance(input, CapabilityMessage) and input.content == "block":
            self.entered.set()
            if not self.release.wait(timeout=2):
                raise TimeoutError("blocking capability was not released")
        return super().handle(state, input, context)


@dataclass
class BlockingStartCapability(FakeCapability):
    entered: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)

    def start(
        self,
        content: str | None,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        self.entered.set()
        if not self.release.wait(timeout=2):
            raise TimeoutError("blocking start was not released")
        return super().start(content, context)


@dataclass
class StubRouter:
    decisions: deque[RouteDecision]
    calls: list[str] = field(default_factory=list)

    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        self.calls.append(message)
        if self.decisions:
            return self.decisions.popleft()
        raise AssertionError("stub router has no decision for an idle message")


def test_first_message_creates_conversation_and_starts_selected_task() -> None:
    alpha = FakeCapability("test.alpha")
    beta = FakeCapability("test.beta")
    router = _start_router("test.alpha")
    controller = _controller(alpha, beta, router=router)

    started = controller.submit_turn(
        TurnRequest("request-1", MessageSubmission("  preserve THIS punctuation!  "))
    )
    conversation_id = started.conversation.id
    task = started.conversation.active_task
    assert task is not None

    continued = controller.submit_turn(
        TurnRequest(
            "request-2",
            MessageSubmission("a later ordinary message"),
            conversation_id,
        )
    )

    assert started.conversation.version == 1
    assert task.id == "task-1"
    assert task.version == 1
    assert continued.conversation.active_task is not None
    assert continued.conversation.active_task.id == task.id
    assert continued.conversation.active_task.version == 2
    assert router.calls == ["preserve THIS punctuation!"]
    assert alpha.starts[0][0] == "preserve THIS punctuation!"
    assert alpha.starts[0][1].operation_id == "request:request-1"
    assert alpha.starts[0][1].request_id == "request-1"
    assert isinstance(alpha.handles[0][1], CapabilityMessage)
    assert beta.starts == []


def test_exact_controls_bypass_while_other_messages_stay_with_active_task() -> None:
    alpha = FakeCapability("test.alpha")
    router = StubRouter(deque([StartRouteDecision("test.alpha")]))
    controller = _controller(alpha, router=router)
    started = controller.submit_turn(TurnRequest("request-1", MessageSubmission("alpha work")))
    conversation_id = started.conversation.id

    ordinary = controller.submit_turn(
        TurnRequest("request-2", MessageSubmission("don't cancel"), conversation_id)
    )
    compound = controller.submit_turn(
        TurnRequest(
            "request-3",
            MessageSubmission("cancel this and start something else"),
            conversation_id,
        )
    )
    cancelled = controller.submit_turn(
        TurnRequest("request-4", MessageSubmission("Cancel!"), conversation_id)
    )

    assert ordinary.outcome.kind == "continued"
    assert compound.outcome.kind == "continued"
    assert len(alpha.handles) == 2
    assert router.calls == ["alpha work"]
    assert cancelled.outcome.kind == "current_task_cancelled"
    assert cancelled.conversation.active_task is None


def test_task_action_guard_global_replay_and_conflicts_precede_capability_work() -> None:
    alpha = FakeCapability("test.alpha")
    controller = _controller(alpha, router=_start_router("test.alpha"))
    started = controller.submit_turn(TurnRequest("request-1", MessageSubmission("start")))
    task = started.conversation.active_task
    assert task is not None
    request = TurnRequest(
        "request-2",
        TaskActionSubmission(task.id, started.conversation.version, "finish", {}),
        started.conversation.id,
    )

    completed = controller.submit_turn(request)
    replay = controller.submit_turn(request)

    assert replay == completed
    assert completed.conversation.active_task is None
    assert len(alpha.handles) == 1
    with pytest.raises(RequestIdConflictError):
        controller.submit_turn(
            TurnRequest(
                "request-2",
                MessageSubmission("different input"),
                started.conversation.id,
            )
        )
    with pytest.raises(TurnGuardConflictError):
        controller.submit_turn(
            TurnRequest(
                "request-3",
                TaskActionSubmission(task.id, 1, "finish", {}),
                started.conversation.id,
            )
        )
    assert len(alpha.handles) == 1


def test_request_id_is_global_across_conversations() -> None:
    alpha = FakeCapability("test.alpha")
    router = StubRouter(
        deque(
            [
                StartRouteDecision("test.alpha"),
                StartRouteDecision("test.alpha"),
            ]
        )
    )
    controller = _controller(alpha, router=router)
    first = controller.submit_turn(TurnRequest("request-1", MessageSubmission("first")))
    second = controller.submit_turn(TurnRequest("request-2", MessageSubmission("second")))

    with pytest.raises(RequestIdConflictError):
        controller.submit_turn(
            TurnRequest("request-1", MessageSubmission("continue"), second.conversation.id)
        )

    assert controller.get_conversation(first.conversation.id) == first.conversation
    assert controller.get_conversation(second.conversation.id) == second.conversation


def test_failed_initial_request_publishes_nothing_and_can_be_retried() -> None:
    alpha = FakeCapability("test.alpha", fail_next_start=True)
    router = StubRouter(
        deque(
            [
                StartRouteDecision("test.alpha"),
                StartRouteDecision("test.alpha"),
            ]
        )
    )
    controller = _controller(alpha, router=router)
    request = TurnRequest("request-1", MessageSubmission("initial"))

    with pytest.raises(ConversationProcessingError):
        controller.submit_turn(request)
    with pytest.raises(ConversationNotFoundError):
        controller.get_conversation("conversation-1")

    retried = controller.submit_turn(request)

    assert retried.conversation.id == "conversation-2"
    assert retried.conversation.version == 1
    assert retried.conversation.active_task is not None
    assert [content for content, _ in alpha.starts] == ["initial", "initial"]


def test_failed_continuation_preserves_state_and_does_not_consume_request_id() -> None:
    alpha = FakeCapability("test.alpha", fail_messages={"retry me"})
    controller = _controller(alpha, router=_start_router("test.alpha"))
    started = controller.submit_turn(TurnRequest("request-1", MessageSubmission("initial")))
    request = TurnRequest(
        "request-2",
        MessageSubmission("retry me"),
        started.conversation.id,
    )

    with pytest.raises(ConversationProcessingError):
        controller.submit_turn(request)
    assert controller.get_conversation(started.conversation.id) == started.conversation

    alpha.fail_messages.clear()
    retried = controller.submit_turn(request)

    assert retried.conversation.version == 2
    assert retried.outcome.kind == "continued"
    assert len(alpha.handles) == 2


def test_help_hides_capability_ids_and_restart_replaces_task_identity() -> None:
    alpha = FakeCapability("test.alpha")
    controller = _controller(alpha, router=_start_router("test.alpha"))
    started = controller.submit_turn(TurnRequest("request-1", MessageSubmission("old state")))
    old_task = started.conversation.active_task
    assert old_task is not None

    helped = controller.submit_turn(
        TurnRequest(
            "request-2",
            ControlActionSubmission(ControlAction.HELP),
            started.conversation.id,
        )
    )
    restarted = controller.submit_turn(
        TurnRequest(
            "request-3",
            ControlActionSubmission(
                ControlAction.RESTART,
                old_task.id,
                helped.conversation.version,
            ),
            started.conversation.id,
        )
    )

    new_task = restarted.conversation.active_task
    assert helped.conversation.active_task is not None
    assert helped.conversation.active_task.id == old_task.id
    assert "test.alpha" not in helped.outcome.message
    assert "fake task" in helped.outcome.message
    assert new_task is not None
    assert new_task.id != old_task.id
    assert new_task.version == 1
    assert [content for content, _ in alpha.starts] == ["old state", None]


def test_guarded_input_without_conversation_is_rejected_before_id_generation() -> None:
    alpha = FakeCapability("test.alpha")
    controller = _controller(alpha)

    with pytest.raises(InvalidTurnRequestError):
        controller.submit_turn(
            TurnRequest(
                "request-1",
                TaskActionSubmission("task-missing", 1, "finish", {}),
            )
        )
    with pytest.raises(InvalidTurnRequestError):
        controller.submit_turn(
            TurnRequest(
                "request-2",
                ControlActionSubmission(ControlAction.CANCEL, "task-missing", 1),
            )
        )
    with pytest.raises(ConversationNotFoundError):
        controller.get_conversation("conversation-1")


def test_concurrent_duplicate_initial_request_executes_once() -> None:
    alpha = BlockingStartCapability("test.alpha")
    controller = _controller(alpha, router=_start_router("test.alpha"))
    request = TurnRequest("request-1", MessageSubmission("start"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(controller.submit_turn, request)
        assert alpha.entered.wait(timeout=1)
        duplicate = executor.submit(controller.submit_turn, request)
        assert not duplicate.done()
        alpha.release.set()
        first_response = first.result(timeout=1)
        duplicate_response = duplicate.result(timeout=1)

    assert first_response == duplicate_response
    assert len(alpha.starts) == 1
    assert first_response.conversation.id == "conversation-1"


def test_same_conversation_serializes_while_another_can_progress() -> None:
    alpha = BlockingFakeCapability("test.alpha")
    router = StubRouter(
        deque(
            [
                StartRouteDecision("test.alpha"),
                StartRouteDecision("test.alpha"),
            ]
        )
    )
    controller = _controller(alpha, router=router)
    first = controller.submit_turn(TurnRequest("start-1", MessageSubmission("first")))
    second = controller.submit_turn(TurnRequest("start-2", MessageSubmission("second")))

    with ThreadPoolExecutor(max_workers=3) as executor:
        blocked = executor.submit(
            controller.submit_turn,
            TurnRequest("request-1", MessageSubmission("block"), first.conversation.id),
        )
        assert alpha.entered.wait(timeout=1)
        same_conversation = executor.submit(
            controller.submit_turn,
            TurnRequest("request-2", MessageSubmission("after block"), first.conversation.id),
        )
        other_conversation = executor.submit(
            controller.submit_turn,
            TurnRequest("request-3", MessageSubmission("independent"), second.conversation.id),
        )

        assert other_conversation.result(timeout=1).outcome.kind == "continued"
        assert not same_conversation.done()
        alpha.release.set()
        assert blocked.result(timeout=1).outcome.kind == "continued"
        assert same_conversation.result(timeout=1).outcome.kind == "continued"


def test_read_waits_for_complete_post_turn_state() -> None:
    alpha = BlockingFakeCapability("test.alpha")
    controller = _controller(alpha, router=_start_router("test.alpha"))
    started = controller.submit_turn(TurnRequest("start", MessageSubmission("first")))

    with ThreadPoolExecutor(max_workers=2) as executor:
        blocked = executor.submit(
            controller.submit_turn,
            TurnRequest("request-1", MessageSubmission("block"), started.conversation.id),
        )
        assert alpha.entered.wait(timeout=1)
        read = executor.submit(controller.get_conversation, started.conversation.id)
        assert not read.done()
        alpha.release.set()
        completed_turn = blocked.result(timeout=1)
        observed = read.result(timeout=1)

    assert observed == completed_turn.conversation
    assert observed.version == 2


def test_idle_outcomes_create_and_reuse_an_idle_conversation() -> None:
    alpha = FakeCapability("test.alpha")
    router = StubRouter(
        deque(
            [
                ClarifyRouteDecision(),
                UnsupportedRouteDecision(),
            ]
        )
    )
    controller = _controller(alpha, router=router)

    ambiguous = controller.submit_turn(TurnRequest("request-1", MessageSubmission("maybe")))
    unsupported = controller.submit_turn(
        TurnRequest(
            "request-2",
            MessageSubmission("unknown"),
            ambiguous.conversation.id,
        )
    )

    assert ambiguous.conversation.version == 1
    assert ambiguous.conversation.active_task is None
    assert ambiguous.outcome.kind == "clarify_idle_route"
    assert unsupported.conversation.version == 2
    assert unsupported.conversation.active_task is None
    assert unsupported.outcome.kind == "unsupported"
    assert alpha.starts == []


def _start_router(capability_id: str) -> StubRouter:
    return StubRouter(deque([StartRouteDecision(capability_id)]))


def _controller(
    *capabilities: FakeCapability,
    router: StubRouter | None = None,
) -> ConversationController:
    resolved_router = router or _start_router(capabilities[0].capability_id)
    conversation_ids = iter(f"conversation-{index}" for index in range(1, 20))
    task_ids = iter(f"task-{index}" for index in range(1, 40))
    engine = ConversationEngine(
        capabilities=CapabilityRegistry(capabilities),
        resolver=TurnResolver(router=resolved_router),
        generate_task_id=lambda: next(task_ids),
        today=lambda: TODAY,
    )
    coordinator = TurnExecutionCoordinator(
        conversations=ConversationRegistry(),
        turn_replays=TurnReplayRegistry(),
        generate_conversation_id=lambda: next(conversation_ids),
    )
    return ConversationController(engine=engine, coordinator=coordinator)
