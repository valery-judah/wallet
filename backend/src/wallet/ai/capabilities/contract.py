from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Generic, Protocol, TypeAlias, TypeVar

from wallet.domain._validation import normalize_nonblank

StateT = TypeVar("StateT")

_CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_ACTION_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _normalize_outcome_kind(value: str) -> str:
    if _ACTION_PATTERN.fullmatch(value) is None:
        raise ValueError("capability outcome kind has invalid syntax")
    return value


def _normalize_result_message(value: str) -> str:
    return normalize_nonblank(value, field_name="capability result message")


def _normalize_routing_texts(
    values: tuple[str, ...],
    *,
    field_name: str,
    required: bool,
) -> tuple[str, ...]:
    normalized = tuple(normalize_nonblank(value, field_name=field_name) for value in values)
    if required and not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


@dataclass(frozen=True, slots=True)
class CapabilityRoutingProfile:
    """Control-level examples that define when a capability owns a message."""

    routes_when: tuple[str, ...]
    examples: tuple[str, ...]
    counterexamples: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "routes_when",
            _normalize_routing_texts(
                self.routes_when,
                field_name="capability routing condition",
                required=True,
            ),
        )
        object.__setattr__(
            self,
            "examples",
            _normalize_routing_texts(
                self.examples,
                field_name="capability routing example",
                required=True,
            ),
        )
        object.__setattr__(
            self,
            "counterexamples",
            _normalize_routing_texts(
                self.counterexamples,
                field_name="capability routing counterexample",
                required=False,
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    id: str
    description: str
    routing: CapabilityRoutingProfile

    def __post_init__(self) -> None:
        capability_id = normalize_nonblank(self.id, field_name="capability id")
        if _CAPABILITY_ID_PATTERN.fullmatch(capability_id) is None:
            raise ValueError("capability id has invalid syntax")
        object.__setattr__(self, "id", capability_id)
        object.__setattr__(
            self,
            "description",
            normalize_nonblank(self.description, field_name="capability description"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityContext:
    conversation_id: str
    request_id: str
    operation_id: str
    current_date: date


@dataclass(frozen=True, slots=True)
class CapabilityMessage:
    content: str


@dataclass(frozen=True, slots=True)
class CapabilityAction:
    action: str
    payload: dict[str, object]

    def __post_init__(self) -> None:
        if _ACTION_PATTERN.fullmatch(self.action) is None:
            raise ValueError("capability action has invalid syntax")
        object.__setattr__(self, "payload", dict(self.payload))


# Closed set of inputs accepted by every capability. Exhaustive dispatchers end with
# assert_never() so mypy flags newly added, unhandled input channels.
CapabilityInput: TypeAlias = CapabilityMessage | CapabilityAction


@dataclass(frozen=True, slots=True)
class CapabilityActionOffer:
    action: str
    label: str
    payload: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if _ACTION_PATTERN.fullmatch(self.action) is None:
            raise ValueError("capability action offer has invalid syntax")
        object.__setattr__(
            self,
            "label",
            normalize_nonblank(self.label, field_name="capability action label"),
        )
        if self.payload is not None:
            object.__setattr__(self, "payload", dict(self.payload))


@dataclass(frozen=True, slots=True)
class CapabilityView:
    kind: str
    data: dict[str, object]
    available_actions: tuple[CapabilityActionOffer, ...] = ()

    def __post_init__(self) -> None:
        if _ACTION_PATTERN.fullmatch(self.kind) is None:
            raise ValueError("capability view kind has invalid syntax")
        object.__setattr__(self, "data", dict(self.data))
        object.__setattr__(self, "available_actions", tuple(self.available_actions))


@dataclass(frozen=True, slots=True)
class ActiveCapabilityResult(Generic[StateT]):
    state: StateT
    view: CapabilityView
    outcome_kind: str
    message: str

    def __post_init__(self) -> None:
        if self.state is None or self.view is None:
            raise ValueError("active capability result requires state and view")
        object.__setattr__(self, "outcome_kind", _normalize_outcome_kind(self.outcome_kind))
        object.__setattr__(
            self,
            "message",
            _normalize_result_message(self.message),
        )


@dataclass(frozen=True, slots=True)
class CompletedCapabilityResult:
    view: CapabilityView | None
    outcome_kind: str
    message: str
    domain_result: dict[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome_kind", _normalize_outcome_kind(self.outcome_kind))
        object.__setattr__(self, "message", _normalize_result_message(self.message))
        if self.domain_result is not None:
            object.__setattr__(self, "domain_result", dict(self.domain_result))
        if self.view is not None and self.view.available_actions:
            raise ValueError("completed capability result cannot offer actions")


# Closed set of capability lifecycle results. The concrete variant makes active and completed
# payload shapes distinct before the control engine applies them.
CapabilityResult: TypeAlias = ActiveCapabilityResult[StateT] | CompletedCapabilityResult


class Capability(Protocol[StateT]):
    definition: CapabilityDefinition

    def start(
        self,
        content: str | None,
        context: CapabilityContext,
    ) -> CapabilityResult[StateT]: ...

    def handle(
        self,
        state: StateT,
        input: CapabilityInput,
        context: CapabilityContext,
    ) -> CapabilityResult[StateT]: ...
