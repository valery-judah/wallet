from __future__ import annotations

from typing import assert_never

from wallet.ai.capabilities.contract import CapabilityAction, CapabilityMessage

from .capability_registry import CapabilityRegistry
from .domain import (
    Cancel,
    Clarify,
    ContinueCurrent,
    ControlAction,
    ControlActionSubmission,
    Conversation,
    Help,
    MessageSubmission,
    ResolvedTurn,
    Restart,
    Start,
    TaskActionSubmission,
    TurnGuard,
    TurnSubmission,
    Unsupported,
)
from .routing import (
    ClarifyRouteDecision,
    CompoundControlRouteDecision,
    MessageRouter,
    MessageRoutingContext,
    StartRouteDecision,
    UnsupportedRouteDecision,
)


class ExactControlRecognizer:
    _CONTROLS: dict[str, type[Cancel] | type[Restart] | type[Help]] = {
        "cancel": Cancel,
        "stop": Cancel,
        "never mind": Cancel,
        "restart": Restart,
        "start over": Restart,
        "help": Help,
        "what can you do": Help,
    }

    def match(self, content: str) -> Cancel | Restart | Help | None:
        normalized = " ".join(content.casefold().split()).rstrip(".!?")
        instruction = self._CONTROLS.get(normalized)
        return None if instruction is None else instruction()


class TurnResolver:
    def __init__(
        self,
        *,
        router: MessageRouter,
        exact_controls: ExactControlRecognizer | None = None,
    ) -> None:
        self._router = router
        self._exact_controls = exact_controls or ExactControlRecognizer()

    def resolve(
        self,
        submission: TurnSubmission,
        conversation: Conversation,
        registry: CapabilityRegistry,
    ) -> ResolvedTurn:
        """Translate one public submission into exactly one internal instruction.

        Resolution chooses a route but never executes capability behavior.
        """

        match submission:
            case ControlActionSubmission():
                return self._resolve_control_action(submission)
            case TaskActionSubmission():
                return ResolvedTurn(
                    ContinueCurrent(
                        CapabilityAction(submission.action, submission.payload),
                    ),
                    TurnGuard(
                        submission.expected_task_id,
                        submission.expected_conversation_version,
                    ),
                )
            case MessageSubmission():
                return self._resolve_message(submission, conversation, registry)
            case _ as unreachable:
                # Static exhaustiveness guard: mypy fails here if the union gains a variant.
                assert_never(unreachable)

    @staticmethod
    def _resolve_control_action(submission: ControlActionSubmission) -> ResolvedTurn:
        """Translate a typed control and preserve the guard required for mutations."""

        instruction: Cancel | Restart
        match submission.action:
            case ControlAction.HELP:
                return ResolvedTurn(Help())
            case ControlAction.CANCEL:
                instruction = Cancel()
            case ControlAction.RESTART:
                instruction = Restart()
            case _ as unreachable:
                assert_never(unreachable)

        task_id = submission.expected_task_id
        version = submission.expected_conversation_version
        if task_id is None or version is None:
            raise ValueError("mutating control is missing its guard")
        return ResolvedTurn(instruction, TurnGuard(task_id, version))

    def _resolve_message(
        self,
        submission: MessageSubmission,
        conversation: Conversation,
        registry: CapabilityRegistry,
    ) -> ResolvedTurn:
        exact = self._exact_controls.match(submission.content)
        if exact is not None:
            return ResolvedTurn(exact)
        if conversation.current is not None:
            # An active capability owns every non-control message. The LLM router selects new
            # work only while idle, so it cannot redirect or replace the current task.
            return ResolvedTurn(
                ContinueCurrent(
                    CapabilityMessage(submission.content),
                ),
            )
        decision = self._router.route(
            submission.content,
            MessageRoutingContext(
                recent_capability_id=conversation.recent_capability_id,
            ),
            registry.definitions,
        )
        match decision:
            case StartRouteDecision(capability_id=capability_id):
                return ResolvedTurn(
                    Start(capability_id, submission.content),
                )
            case ClarifyRouteDecision():
                return ResolvedTurn(
                    Clarify("idle_route_ambiguous"),
                )
            case UnsupportedRouteDecision():
                return ResolvedTurn(Unsupported())
            case CompoundControlRouteDecision():
                return ResolvedTurn(Clarify("compound_instruction"))
            case _ as unreachable:
                # Static exhaustiveness guard for the closed route-decision family.
                assert_never(unreachable)
