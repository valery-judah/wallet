from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, dataclass
from typing import get_args, get_origin

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
from wallet.ai.control.domain import (
    ControlAction,
    ControlActionSubmission,
    MessageSubmission,
    TaskActionSubmission,
    TurnRequest,
    fingerprint_request,
    fingerprint_submission,
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


def test_capability_definition_and_registry_accept_a_closed_static_registration() -> None:
    definition = _definition("test.alpha")
    handler = NoopCapability(definition)

    registry = CapabilityRegistry((handler,))

    assert registry.definitions == (definition,)
    assert registry.get("test.alpha") is handler


@pytest.mark.parametrize(
    ("definition", "message"),
    [
        (lambda: CapabilityDefinition(" ", "Description", _routing()), "blank"),
        (
            lambda: CapabilityDefinition("Test.Alpha", "Description", _routing()),
            "invalid syntax",
        ),
        (lambda: CapabilityDefinition("test.alpha", " ", _routing()), "blank"),
    ],
)
def test_capability_definition_rejects_invalid_metadata(
    definition: Callable[[], CapabilityDefinition],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        definition()


def test_registry_rejects_empty_and_duplicate_handlers() -> None:
    alpha = _definition("test.alpha")
    alpha_handler = NoopCapability(alpha)

    with pytest.raises(ValueError, match="cannot be empty"):
        CapabilityRegistry(())
    with pytest.raises(ValueError, match="duplicate"):
        CapabilityRegistry((alpha_handler, alpha_handler))


def test_routing_profile_requires_positive_nonblank_coverage() -> None:
    with pytest.raises(ValueError, match="condition cannot be empty"):
        CapabilityRoutingProfile((), ("Example",))
    with pytest.raises(ValueError, match="example cannot be empty"):
        CapabilityRoutingProfile(("Own this request",), ())
    with pytest.raises(ValueError, match="counterexample.*blank"):
        CapabilityRoutingProfile(("Own this request",), ("Example",), (" ",))

    profile = CapabilityRoutingProfile(
        ("  Own this request.  ",),
        ("  Do the thing.  ",),
        ("  Do another thing.  ",),
    )

    assert profile.routes_when == ("Own this request.",)
    assert profile.examples == ("Do the thing.",)
    assert profile.counterexamples == ("Do another thing.",)


def test_capability_contracts_are_closed_unions_of_concrete_variants() -> None:
    result_variants = tuple(
        get_origin(variant) or variant for variant in get_args(CapabilityResult[object])
    )

    assert get_args(CapabilityInput) == (CapabilityMessage, CapabilityAction)
    assert result_variants == (ActiveCapabilityResult, CompletedCapabilityResult)


def test_result_variants_accept_their_distinct_shapes_and_copy_domain_results() -> None:
    active = _active(("opaque",))
    domain_result = {"id": "result-1"}
    completed = CompletedCapabilityResult(
        view=CapabilityView("completed_view", {"safe": True}),
        outcome_kind="completed",
        message="Done.",
        domain_result=domain_result,
    )
    domain_result["id"] = "changed"

    assert active.state == ("opaque",)
    assert completed.domain_result == {"id": "result-1"}
    with pytest.raises(FrozenInstanceError):
        active.message = "Changed."  # type: ignore[misc]


def test_active_result_requires_non_none_state_and_view() -> None:
    view = CapabilityView("active_view", {})

    with pytest.raises(ValueError, match="requires state and view"):
        ActiveCapabilityResult(None, view, "active", "Active.")
    with pytest.raises(ValueError, match="requires state and view"):
        ActiveCapabilityResult((), None, "active", "Active.")  # type: ignore[arg-type]


def test_completed_result_rejects_a_view_that_offers_active_actions() -> None:
    view = CapabilityView(
        "completed_view",
        {},
        (CapabilityActionOffer("continue", "Continue"),),
    )

    with pytest.raises(ValueError, match="cannot offer actions"):
        CompletedCapabilityResult(view, "completed", "Done.")


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (
            lambda: ActiveCapabilityResult(
                (), CapabilityView("active_view", {}), "not-valid", "Active."
            ),
            "outcome kind",
        ),
        (
            lambda: CompletedCapabilityResult(None, "completed", " "),
            "blank",
        ),
    ],
)
def test_result_variants_preserve_common_validation(
    result: Callable[[], CapabilityResult[tuple[str, ...]]],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        result()


def test_submission_fingerprint_is_canonical_and_sensitive_to_every_input_field() -> None:
    action_a = TaskActionSubmission(
        "task-1",
        4,
        "finish",
        {"second": 2, "first": 1},
    )
    action_b = TaskActionSubmission(
        "task-1",
        4,
        "finish",
        {"first": 1, "second": 2},
    )
    changed = (
        MessageSubmission("message"),
        MessageSubmission("changed"),
        ControlActionSubmission(ControlAction.HELP),
        ControlActionSubmission(ControlAction.CANCEL, "task-1", 4),
        ControlActionSubmission(ControlAction.CANCEL, "task-1", 5),
        TaskActionSubmission("task-1", 4, "other", {"first": 1, "second": 2}),
        TaskActionSubmission("task-1", 4, "finish", {"first": 9, "second": 2}),
    )

    assert fingerprint_submission(action_a) == fingerprint_submission(action_b)
    assert len({fingerprint_submission(submission) for submission in changed}) == len(changed)

    initial = TurnRequest("request-1", MessageSubmission("same"))
    continued = TurnRequest("request-2", MessageSubmission("same"), "conversation-1")
    other_target = TurnRequest("request-3", MessageSubmission("same"), "conversation-2")
    assert fingerprint_request(initial) != fingerprint_request(continued)
    assert fingerprint_request(continued) != fingerprint_request(other_target)


def test_submission_values_apply_narrow_normalization_without_rewriting_content() -> None:
    message = MessageSubmission("  Preserve THIS punctuation!  ")
    action = CapabilityAction("finish", {"answer": " unchanged "})

    assert message.content == "Preserve THIS punctuation!"
    assert action.payload == {"answer": " unchanged "}


def _definition(capability_id: str) -> CapabilityDefinition:
    return CapabilityDefinition(capability_id, f"Run {capability_id}.", _routing())


def _routing() -> CapabilityRoutingProfile:
    return CapabilityRoutingProfile(
        routes_when=("The user asks to run the test capability.",),
        examples=("Run the test capability.",),
    )


def _active(state: tuple[str, ...]) -> CapabilityResult[tuple[str, ...]]:
    return ActiveCapabilityResult(
        state=state,
        view=CapabilityView("active_view", {}),
        outcome_kind="active",
        message="Active.",
    )
