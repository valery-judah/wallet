from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from wallet.ai.capabilities.contract import (
    ActiveCapabilityResult,
    CapabilityContext,
    CapabilityDefinition,
    CapabilityInput,
    CapabilityMessage,
    CapabilityResult,
    CapabilityRoutingProfile,
    CapabilityView,
)
from wallet.ai.control.capability_registry import CapabilityRegistry
from wallet.ai.control.domain import (
    Cancel,
    CapabilitySession,
    Clarify,
    ContinueCurrent,
    ControlAction,
    ControlActionSubmission,
    Conversation,
    Help,
    MessageSubmission,
    Restart,
    Start,
    TaskActionSubmission,
    TurnSubmission,
    Unsupported,
)
from wallet.ai.control.resolution import ExactControlRecognizer, TurnResolver
from wallet.ai.control.routing import (
    ClarifyRouteDecision,
    CompoundControlRouteDecision,
    MessageRoutingContext,
    RouteDecision,
    StartRouteDecision,
    UnsupportedRouteDecision,
)


@dataclass(frozen=True)
class NoopCapability:
    definition: CapabilityDefinition

    def start(
        self,
        content: str | None,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        return _active(())

    def handle(
        self,
        state: tuple[str, ...],
        input: CapabilityInput,
        context: CapabilityContext,
    ) -> CapabilityResult[tuple[str, ...]]:
        return _active(state)


@dataclass
class RecordingRouter:
    decisions: list[RouteDecision]
    calls: list[tuple[str, MessageRoutingContext, tuple[CapabilityDefinition, ...]]] = field(
        default_factory=list
    )

    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        self.calls.append((message, context, definitions))
        return self.decisions.pop(0)


class ExplodingRouter:
    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        raise AssertionError("typed or exact input reached message routing")


class ExplodingExactRecognizer(ExactControlRecognizer):
    def match(self, content: str) -> Cancel | Restart | Help | None:
        raise AssertionError("typed input reached exact control recognition")


@pytest.mark.parametrize(
    ("submission", "instruction_type"),
    [
        (ControlActionSubmission(ControlAction.HELP), Help),
        (ControlActionSubmission(ControlAction.CANCEL, "test.alpha", 1), Cancel),
        (ControlActionSubmission(ControlAction.RESTART, "test.alpha", 1), Restart),
        (TaskActionSubmission("task-1", 1, "finish", {}), ContinueCurrent),
    ],
)
def test_typed_inputs_bypass_text_recognition_and_message_routing(
    submission: TurnSubmission,
    instruction_type: type[object],
) -> None:
    resolver = TurnResolver(
        router=ExplodingRouter(),
        exact_controls=ExplodingExactRecognizer(),
    )

    resolved = resolver.resolve(submission, Conversation("conversation-1"), _registry())

    assert isinstance(resolved.instruction, instruction_type)


@pytest.mark.parametrize(
    ("content", "instruction_type"),
    [
        (" cancel ", Cancel),
        ("STOP!", Cancel),
        ("Never   mind.", Cancel),
        ("restart", Restart),
        ("Start over?", Restart),
        ("help", Help),
        ("What can you do?", Help),
    ],
)
def test_exact_whole_message_controls_bypass_message_routing(
    content: str,
    instruction_type: type[object],
) -> None:
    resolved = TurnResolver(router=ExplodingRouter()).resolve(
        MessageSubmission(content),
        _current_conversation(),
        _registry(),
    )

    assert isinstance(resolved.instruction, instruction_type)


def test_active_ordinary_message_goes_directly_to_the_current_capability() -> None:
    content = "Preserve THIS punctuation!"

    resolved = TurnResolver(router=ExplodingRouter()).resolve(
        MessageSubmission(content),
        _current_conversation(),
        _registry(),
    )

    assert isinstance(resolved.instruction, ContinueCurrent)
    assert resolved.instruction.capability_input == CapabilityMessage(content)


def test_idle_message_routes_with_only_recent_capability_identity_as_memory() -> None:
    router = RecordingRouter([StartRouteDecision("test.alpha")])

    TurnResolver(router=router).resolve(
        MessageSubmission("one more time"),
        Conversation(
            "conversation-1",
            recent_capability_id="test.alpha",
        ),
        _registry(),
    )

    assert router.calls == [
        (
            "one more time",
            MessageRoutingContext(recent_capability_id="test.alpha"),
            _registry().definitions,
        )
    ]


@pytest.mark.parametrize(
    ("decision", "instruction_type", "clarification_code"),
    [
        (StartRouteDecision("test.alpha"), Start, None),
        (ClarifyRouteDecision(("test.alpha",)), Clarify, "idle_route_ambiguous"),
        (UnsupportedRouteDecision(), Unsupported, None),
        (CompoundControlRouteDecision(), Clarify, "compound_instruction"),
    ],
)
def test_idle_route_decisions_map_to_one_instruction(
    decision: RouteDecision,
    instruction_type: type[object],
    clarification_code: str | None,
) -> None:
    resolved = TurnResolver(router=RecordingRouter([decision])).resolve(
        MessageSubmission("complete message"),
        Conversation("conversation-1"),
        _registry(),
    )

    assert isinstance(resolved.instruction, instruction_type)
    if isinstance(resolved.instruction, Start):
        assert resolved.instruction.capability_id == "test.alpha"
        assert resolved.instruction.content == "complete message"
    if isinstance(resolved.instruction, Clarify):
        assert resolved.instruction.code == clarification_code


@pytest.mark.parametrize(
    "content",
    [
        "don't cancel",
        "the cancellation fee was 10",
        "paid at Cancel Wine Bar",
        "I restarted my subscription yesterday",
    ],
)
def test_false_controls_go_to_the_current_capability_without_routing(content: str) -> None:
    resolved = TurnResolver(router=ExplodingRouter()).resolve(
        MessageSubmission(content),
        _current_conversation(),
        _registry(),
    )

    assert isinstance(resolved.instruction, ContinueCurrent)
    assert resolved.instruction.capability_input == CapabilityMessage(content)


def _registry() -> CapabilityRegistry:
    return CapabilityRegistry(
        (
            NoopCapability(_definition("test.alpha")),
            NoopCapability(_definition("test.beta")),
        )
    )


def _definition(capability_id: str) -> CapabilityDefinition:
    return CapabilityDefinition(
        capability_id,
        f"Run {capability_id}.",
        CapabilityRoutingProfile(
            (f"The user requests {capability_id}.",),
            (f"Run {capability_id}.",),
        ),
    )


def _current_conversation() -> Conversation:
    return Conversation(
        "conversation-1",
        current=CapabilitySession(
            task_id="task-1",
            capability_id="test.alpha",
            version=1,
            state=("opaque",),
            view=CapabilityView("active_view", {}),
        ),
    )


def _active(state: tuple[str, ...]) -> CapabilityResult[tuple[str, ...]]:
    return ActiveCapabilityResult(
        state=state,
        view=CapabilityView("active_view", {}),
        outcome_kind="active",
        message="Active.",
    )
