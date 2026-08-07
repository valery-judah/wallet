from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import get_args

import pytest

from wallet.ai.control.domain import (
    Cancel,
    Clarify,
    ContinueCurrent,
    Conversation,
    Help,
    Restart,
    Start,
    TurnInstruction,
    Unsupported,
)


def test_turn_instruction_is_a_closed_union_of_every_variant() -> None:
    assert get_args(TurnInstruction) == (
        ContinueCurrent,
        Start,
        Cancel,
        Restart,
        Help,
        Clarify,
        Unsupported,
    )


def test_start_normalizes_its_capability_id_and_content() -> None:
    instruction = Start(" transactions.capture ", "  record lunch  ")

    assert instruction.capability_id == "transactions.capture"
    assert instruction.content == "record lunch"


@pytest.mark.parametrize(
    ("capability_id", "content", "message"),
    [
        ("Transactions.Capture", None, "capability id has invalid syntax"),
        ("transactions.capture", "   ", "content must contain between 1 and 4000 characters"),
    ],
)
def test_start_rejects_invalid_values(
    capability_id: str,
    content: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Start(capability_id, content)


def test_clarify_rejects_an_invalid_code() -> None:
    with pytest.raises(ValueError, match="clarification code has invalid syntax"):
        Clarify("idle-route-ambiguous")


def test_turn_instruction_variants_are_immutable() -> None:
    instruction = Start("transactions.capture", None)

    with pytest.raises(FrozenInstanceError):
        instruction.content = "replacement"


def test_conversation_validates_bounded_routing_memory() -> None:
    conversation = Conversation(
        "conversation-1",
        recent_capability_id="wallet.current_state",
    )

    assert conversation.recent_capability_id == "wallet.current_state"
    with pytest.raises(ValueError, match="capability id has invalid syntax"):
        Conversation("conversation-1", recent_capability_id="Wallet.CurrentState")
