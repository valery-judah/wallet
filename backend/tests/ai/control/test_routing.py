from __future__ import annotations

import json
import logging
from dataclasses import FrozenInstanceError, dataclass, field
from typing import Any, cast, get_args

import pytest

from wallet.ai.capabilities.contract import CapabilityDefinition, CapabilityRoutingProfile
from wallet.ai.control.routing import (
    ClarifyRouteDecision,
    CompoundControlRouteDecision,
    LlmMessageRouter,
    MessageRoutingContext,
    MessageRoutingError,
    RouteDecision,
    StartRouteDecision,
    UnsupportedRouteDecision,
)
from wallet.ai.llm import StructuredChatTransportError


@dataclass(frozen=True, slots=True)
class ModelCall:
    system_prompt: str
    user_prompt: str
    output_schema: dict[str, Any]


@dataclass
class FakeStructuredChatModel:
    responses: list[str | Exception]
    calls: list[ModelCall] = field(default_factory=list)

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        self.calls.append(ModelCall(system_prompt, user_prompt, output_schema))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_route_decision_is_a_closed_union_of_frozen_variants() -> None:
    decision = StartRouteDecision("test.alpha")

    assert get_args(RouteDecision) == (
        StartRouteDecision,
        ClarifyRouteDecision,
        UnsupportedRouteDecision,
        CompoundControlRouteDecision,
    )
    with pytest.raises(FrozenInstanceError):
        decision.capability_id = "test.beta"  # type: ignore[misc]


def test_route_decisions_validate_ids_and_distinct_candidates() -> None:
    with pytest.raises(ValueError, match="invalid syntax"):
        StartRouteDecision("Test.Alpha")
    with pytest.raises(ValueError, match="distinct"):
        ClarifyRouteDecision(("test.alpha", "test.alpha"))


def test_routing_context_is_frozen_and_validates_capability_ids() -> None:
    context = MessageRoutingContext(recent_capability_id="test.alpha")

    with pytest.raises(FrozenInstanceError):
        context.recent_capability_id = "test.beta"  # type: ignore[misc]
    with pytest.raises(ValueError, match="invalid syntax"):
        MessageRoutingContext(recent_capability_id="Test.Alpha")


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            '{"kind":"start","capability_id":"test.beta"}',
            StartRouteDecision("test.beta"),
        ),
        (
            '{"kind":"clarify","candidate_capability_ids":["test.alpha","test.beta"]}',
            ClarifyRouteDecision(("test.alpha", "test.beta")),
        ),
        ('{"kind":"unsupported"}', UnsupportedRouteDecision()),
        ('{"kind":"compound_control"}', CompoundControlRouteDecision()),
    ],
)
def test_llm_router_returns_each_closed_decision(
    response: str,
    expected: RouteDecision,
) -> None:
    model = FakeStructuredChatModel([response])

    decision = LlmMessageRouter(model=model).route(
        "Preserve THIS complete message!",
        MessageRoutingContext(),
        _definitions(),
    )

    assert decision == expected
    assert model.calls[0].user_prompt == "Preserve THIS complete message!"


def test_router_prompt_contains_only_control_level_context_and_dynamic_ids() -> None:
    model = FakeStructuredChatModel(['{"kind":"start","capability_id":"test.alpha"}'])

    LlmMessageRouter(model=model).route(
        "actually use Cash and make it 45",
        MessageRoutingContext(recent_capability_id="test.beta"),
        _definitions(),
    )

    call = model.calls[0]
    assert call.user_prompt == "actually use Cash and make it 45"
    assert '"recent_capability":{"id":"test.beta"' in call.system_prompt
    assert '"id":"test.alpha","is_recent":false' in call.system_prompt
    assert '"id":"test.beta","is_recent":true' in call.system_prompt
    assert '"routes_when"' in call.system_prompt
    assert '"examples"' in call.system_prompt
    assert '"counterexamples"' in call.system_prompt
    assert "a reference-only request to repeat the previous operation" in call.system_prompt
    assert "called only when no task is active" in call.system_prompt
    assert "continue" not in call.system_prompt
    assert "unsupported and compound_control contain only kind" in call.system_prompt
    assert "conversation_id" not in call.system_prompt
    assert "request_id" not in call.system_prompt
    assert "candidate.amount" not in call.system_prompt
    schemas = call.output_schema["oneOf"]
    assert isinstance(schemas, list)
    assert schemas[0]["properties"]["capability_id"]["enum"] == [
        "test.alpha",
        "test.beta",
    ]


@pytest.mark.parametrize(
    "invalid_response",
    [
        "not json",
        '{"kind":"start","capability_id":"invented.capability"}',
        '{"kind":"continue","capability_id":"test.beta"}',
        '{"kind":"clarify","candidate_capability_ids":["test.alpha","test.alpha"]}',
        '{"kind":"unsupported","capability_id":"test.alpha"}',
    ],
)
def test_router_retries_invalid_output_once_without_replaying_raw_output(
    invalid_response: str,
) -> None:
    model = FakeStructuredChatModel(
        [invalid_response, '{"kind":"start","capability_id":"test.beta"}']
    )

    decision = LlmMessageRouter(model=model).route(
        "new task", MessageRoutingContext(), _definitions()
    )

    assert decision == StartRouteDecision("test.beta")
    assert len(model.calls) == 2
    assert "RETRY_FEEDBACK" in model.calls[1].system_prompt
    assert "unsupported and compound_control contain only kind" in model.calls[1].system_prompt
    assert invalid_response not in model.calls[1].system_prompt


def test_router_retry_explains_variant_specific_fields() -> None:
    model = FakeStructuredChatModel(
        [
            '{"kind":"compound_control","candidate_capability_ids":["test.alpha"]}',
            '{"kind":"compound_control"}',
        ]
    )

    decision = LlmMessageRouter(model=model).route(
        "cancel and run alpha", MessageRoutingContext(), _definitions()
    )

    assert decision == CompoundControlRouteDecision()
    assert "unsupported/compound_control = kind only" in model.calls[1].system_prompt


def test_router_fails_after_two_invalid_outputs_without_logging_raw_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_output = "secret malformed model output"
    model = FakeStructuredChatModel([raw_output, raw_output])
    caplog.set_level(logging.INFO, logger="wallet.ai.control.routing")

    with pytest.raises(MessageRoutingError, match="invalid route"):
        LlmMessageRouter(model=model).route("message", MessageRoutingContext(), _definitions())

    event = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "control.routing.failed"
    )
    assert cast(Any, event).event_data["attempt_count"] == 2
    assert raw_output not in caplog.text


def test_router_does_not_retry_transport_failures() -> None:
    model = FakeStructuredChatModel(
        [StructuredChatTransportError("offline"), '{"kind":"unsupported"}']
    )

    with pytest.raises(StructuredChatTransportError, match="offline"):
        LlmMessageRouter(model=model).route("message", MessageRoutingContext(), _definitions())

    assert len(model.calls) == 1


def test_router_rejects_unregistered_routing_memory_before_model_call() -> None:
    model = FakeStructuredChatModel(['{"kind":"unsupported"}'])

    with pytest.raises(MessageRoutingError, match="recent capability is not registered"):
        LlmMessageRouter(model=model).route(
            "again",
            MessageRoutingContext(recent_capability_id="test.unknown"),
            _definitions(),
        )

    assert model.calls == []


def test_success_event_contains_route_metadata_without_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    model = FakeStructuredChatModel(
        [
            json.dumps(
                {
                    "kind": "clarify",
                    "candidate_capability_ids": ["test.alpha", "test.beta"],
                }
            )
        ]
    )
    caplog.set_level(logging.INFO, logger="wallet.ai.control.routing")

    LlmMessageRouter(model=model).route(
        "private message",
        MessageRoutingContext(recent_capability_id="test.beta"),
        _definitions(),
    )

    event = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "control.routing.completed"
    )
    event_data = cast(Any, event).event_data
    assert event_data["decision"] == "clarify"
    assert event_data["candidate_capability_ids"] == (
        "test.alpha",
        "test.beta",
    )
    assert event_data["recent_capability_id"] == "test.beta"
    assert "current_capability_id" not in event_data
    assert "private message" not in caplog.text


def _definitions() -> tuple[CapabilityDefinition, ...]:
    return (
        CapabilityDefinition(
            "test.alpha",
            "Run alpha.",
            CapabilityRoutingProfile(
                ("The user requests alpha.",),
                ("Run alpha.",),
                ("Run beta.",),
            ),
        ),
        CapabilityDefinition(
            "test.beta",
            "Run beta.",
            CapabilityRoutingProfile(
                ("The user requests beta.",),
                ("Run beta.",),
            ),
        ),
    )
