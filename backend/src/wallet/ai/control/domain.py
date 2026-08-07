from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias, assert_never

from wallet.ai.capabilities.contract import CapabilityInput, CapabilityView
from wallet.domain._validation import normalize_nonblank

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_ACTION_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _normalize_id(value: str, *, field_name: str) -> str:
    normalized = normalize_nonblank(value, field_name=field_name)
    if _ID_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{field_name} has invalid syntax")
    return normalized


def _normalize_capability_id(value: str) -> str:
    normalized = normalize_nonblank(value, field_name="capability id")
    if _CAPABILITY_ID_PATTERN.fullmatch(normalized) is None:
        raise ValueError("capability id has invalid syntax")
    return normalized


def _normalize_content(value: str) -> str:
    content = value.strip()
    if not 1 <= len(content) <= 4_000:
        raise ValueError("content must contain between 1 and 4000 characters")
    return content


class ControlAction(StrEnum):
    HELP = "help"
    CANCEL = "cancel"
    RESTART = "restart"


@dataclass(frozen=True, slots=True)
class MessageSubmission:
    content: str
    kind: str = field(default="message", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", _normalize_content(self.content))


@dataclass(frozen=True, slots=True)
class ControlActionSubmission:
    action: ControlAction
    expected_task_id: str | None = None
    expected_conversation_version: int | None = None
    kind: str = field(default="control_action", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", ControlAction(self.action))
        if self.action is ControlAction.HELP:
            if self.expected_task_id is not None or self.expected_conversation_version is not None:
                raise ValueError("help cannot contain target or version fields")
            return
        if self.expected_task_id is None or self.expected_conversation_version is None:
            raise ValueError("cancel and restart require target and version fields")
        object.__setattr__(
            self,
            "expected_task_id",
            _normalize_id(self.expected_task_id, field_name="task id"),
        )
        if self.expected_conversation_version < 1:
            raise ValueError("expected conversation version must be positive")


@dataclass(frozen=True, slots=True)
class TaskActionSubmission:
    expected_task_id: str
    expected_conversation_version: int
    action: str
    payload: dict[str, object]
    kind: str = field(default="task_action", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "expected_task_id",
            _normalize_id(self.expected_task_id, field_name="task id"),
        )
        if self.expected_conversation_version < 1:
            raise ValueError("expected conversation version must be positive")
        if _ACTION_PATTERN.fullmatch(self.action) is None:
            raise ValueError("capability action has invalid syntax")
        object.__setattr__(self, "payload", dict(self.payload))


# Closed set of public turn inputs. Dispatchers must handle every variant and finish with
# assert_never() so mypy flags newly added, unhandled variants.
TurnSubmission: TypeAlias = MessageSubmission | ControlActionSubmission | TaskActionSubmission


@dataclass(frozen=True, slots=True)
class TurnRequest:
    request_id: str
    input: TurnSubmission
    conversation_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _normalize_id(self.request_id, field_name="request id"),
        )
        if self.conversation_id is not None:
            object.__setattr__(
                self,
                "conversation_id",
                _normalize_id(self.conversation_id, field_name="conversation id"),
            )


@dataclass(frozen=True, slots=True)
class ContinueCurrent:
    capability_input: CapabilityInput


@dataclass(frozen=True, slots=True)
class Start:
    capability_id: str
    content: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "capability_id", _normalize_capability_id(self.capability_id))
        if self.content is not None:
            object.__setattr__(self, "content", _normalize_content(self.content))


@dataclass(frozen=True, slots=True)
class Cancel:
    pass


@dataclass(frozen=True, slots=True)
class Restart:
    pass


@dataclass(frozen=True, slots=True)
class Help:
    pass


@dataclass(frozen=True, slots=True)
class Clarify:
    code: str

    def __post_init__(self) -> None:
        if _ACTION_PATTERN.fullmatch(self.code) is None:
            raise ValueError("clarification code has invalid syntax")


@dataclass(frozen=True, slots=True)
class Unsupported:
    pass


# Closed set of internal routes produced by TurnResolver. Each variant carries only the data
# required by its execution branch.
TurnInstruction: TypeAlias = (
    ContinueCurrent | Start | Cancel | Restart | Help | Clarify | Unsupported
)


@dataclass(frozen=True, slots=True)
class TurnGuard:
    expected_task_id: str
    expected_conversation_version: int


@dataclass(frozen=True, slots=True)
class ResolvedTurn:
    instruction: TurnInstruction
    guard: TurnGuard | None = None


@dataclass(frozen=True, slots=True)
class CapabilitySession:
    task_id: str
    capability_id: str
    version: int
    state: object
    view: CapabilityView

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _normalize_id(self.task_id, field_name="task id"))
        object.__setattr__(self, "capability_id", _normalize_capability_id(self.capability_id))
        if self.version < 1:
            raise ValueError("capability session version must be positive")


@dataclass(frozen=True, slots=True)
class PublicActionOffer:
    action: str
    label: str
    payload: dict[str, object] | None
    expected_task_id: str
    expected_conversation_version: int


@dataclass(frozen=True, slots=True)
class PublicCapabilityView:
    kind: str
    data: dict[str, object]
    available_actions: tuple[PublicActionOffer, ...]


@dataclass(frozen=True, slots=True)
class ActiveTaskView:
    id: str
    version: int
    view: PublicCapabilityView


@dataclass(frozen=True, slots=True)
class TurnOutcome:
    kind: str
    capability_id: str | None
    message: str
    view: CapabilityView | PublicCapabilityView | None = None
    result: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ConversationView:
    id: str
    version: int
    active_task: ActiveTaskView | None
    last_outcome: TurnOutcome | None


@dataclass(frozen=True, slots=True)
class TurnResponse:
    request_id: str
    conversation: ConversationView
    outcome: TurnOutcome


@dataclass(frozen=True, slots=True)
class Conversation:
    id: str
    version: int = 0
    current: CapabilitySession | None = None
    last_outcome: TurnOutcome | None = None
    recent_capability_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _normalize_id(self.id, field_name="conversation id"))
        if self.version < 0:
            raise ValueError("conversation version cannot be negative")
        if self.recent_capability_id is not None:
            object.__setattr__(
                self,
                "recent_capability_id",
                _normalize_capability_id(self.recent_capability_id),
            )


@dataclass(frozen=True, slots=True)
class TurnTransition:
    conversation: Conversation
    response: TurnResponse


def fingerprint_submission(submission: TurnSubmission) -> str:
    payload: dict[str, object]
    match submission:
        case MessageSubmission():
            payload = {"kind": submission.kind, "content": submission.content}
        case ControlActionSubmission():
            payload = {
                "kind": submission.kind,
                "action": submission.action.value,
                "expected_task_id": submission.expected_task_id,
                "expected_conversation_version": submission.expected_conversation_version,
            }
        case TaskActionSubmission():
            payload = {
                "kind": submission.kind,
                "expected_task_id": submission.expected_task_id,
                "expected_conversation_version": submission.expected_conversation_version,
                "action": submission.action,
                "payload": submission.payload,
            }
        case _ as unreachable:
            # Static exhaustiveness guard: mypy fails here if the union gains a variant.
            assert_never(unreachable)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def fingerprint_request(request: TurnRequest) -> str:
    canonical = json.dumps(
        {
            "conversation_id": request.conversation_id,
            "input_fingerprint": fingerprint_submission(request.input),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
