from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from wallet.ai.transaction_capture.domain import UserContribution
from wallet.ai.transaction_capture.extraction import (
    ContributionExtractionError,
    LlmContributionExtractor,
    MentionKind,
    SourceEvidence,
)


@dataclass(frozen=True)
class ModelCall:
    system_prompt: str
    user_prompt: str
    output_schema: dict[str, Any]


@dataclass
class FakeStructuredChatModel:
    responses: list[str]
    calls: list[ModelCall] = field(default_factory=list)

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        self.calls.append(ModelCall(system_prompt, user_prompt, output_schema))
        return self.responses.pop(0)


def test_extractor_anchors_and_orders_linguistic_mentions_without_context() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                ("reference", "Cash"),
                ("action", "Move"),
                ("money", "$10"),
                ("reference", "Cash"),
            )
        ]
    )

    result = LlmContributionExtractor(model=model).extract(
        UserContribution("Move $10 from Cash to Cash")
    )

    assert [(item.id, item.kind, item.evidence) for item in result.mentions] == [
        ("m0", MentionKind.ACTION, SourceEvidence(0, 4, "Move")),
        ("m1", MentionKind.MONEY, SourceEvidence(5, 8, "$10")),
        ("m2", MentionKind.REFERENCE, SourceEvidence(14, 18, "Cash")),
        ("m3", MentionKind.REFERENCE, SourceEvidence(22, 26, "Cash")),
    ]
    call = model.calls[0]
    assert call.user_prompt == "Move $10 from Cash to Cash"
    assert "candidate" not in call.system_prompt
    assert "pending_interaction" not in call.system_prompt
    assert "account_id" not in call.system_prompt


def test_extractor_retries_unanchored_mention_then_returns_corrected_spans() -> None:
    model = FakeStructuredChatModel(
        responses=[_response(("money", "forty")), _response(("money", "40"))]
    )

    result = LlmContributionExtractor(model=model).extract(UserContribution("40"))

    assert result.mentions[0].evidence == SourceEvidence(0, 2, "40")
    assert not result.issues
    assert len(model.calls) == 2
    assert "does not identify" in model.calls[1].system_prompt


def test_extractor_returns_remaining_evidence_issues_after_retry() -> None:
    response = _response(("reference", "Savings"))
    model = FakeStructuredChatModel(responses=[response, response])

    result = LlmContributionExtractor(model=model).extract(UserContribution("Cash"))

    assert not result.mentions
    assert result.issues[0].source_text == "Savings"
    assert len(model.calls) == 2


def test_extractor_rejects_schema_invalid_output_after_retry() -> None:
    model = FakeStructuredChatModel(responses=["not json", '{"extra":true}'])

    with pytest.raises(ContributionExtractionError, match="invalid extraction"):
        LlmContributionExtractor(model=model).extract(UserContribution("anything"))

    assert len(model.calls) == 2


def _response(*mentions: tuple[str, str]) -> str:
    return json.dumps(
        {"mentions": [{"kind": kind, "source_text": text} for kind, text in mentions]}
    )
