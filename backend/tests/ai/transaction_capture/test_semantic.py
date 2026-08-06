from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pytest

from wallet.ai.transaction_capture.domain import (
    CandidateField,
    PendingInteractionKind,
    UserContribution,
)
from wallet.ai.transaction_capture.extraction import (
    ContributionExtraction,
    ExtractedMention,
    MentionKind,
    SourceEvidence,
)
from wallet.ai.transaction_capture.semantic import (
    FieldClear,
    FieldHypothesis,
    InterpretationOrigin,
    LlmContributionSemanticInterpreter,
    SemanticCandidateContext,
    SemanticContext,
    SemanticInterpretationError,
    SemanticPendingInteraction,
    SemanticReferenceState,
    SemanticReferenceValue,
    SemanticReferenceVocabulary,
)
from wallet.domain.transactions import TransactionType

TODAY = date(2026, 8, 5)


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


def test_llm_assigns_semantics_to_verified_mentions_without_wallet_ids() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                hypotheses=[
                    _hypothesis("type", "m0", value="expense", origin="inferred"),
                    _hypothesis("amount_minor", "m1"),
                    _hypothesis("account_id", "m2"),
                ]
            )
        ]
    )
    contribution = UserContribution("Spent 40 pesos from Daily checking")
    extraction = _extraction(
        (MentionKind.ACTION, "Spent", 0),
        (MentionKind.MONEY, "40 pesos", 6),
        (MentionKind.REFERENCE, "Daily checking", 20),
    )

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        contribution,
        extraction=extraction,
        context=_context(),
    )

    assert result.hypotheses == (
        FieldHypothesis(
            CandidateField.TYPE,
            "m0",
            InterpretationOrigin.INFERRED,
            TransactionType.EXPENSE,
        ),
        FieldHypothesis(CandidateField.AMOUNT_MINOR, "m1", InterpretationOrigin.EXPLICIT),
        FieldHypothesis(CandidateField.ACCOUNT_ID, "m2", InterpretationOrigin.EXPLICIT),
    )
    call = model.calls[0]
    assert call.user_prompt == contribution.content
    assert '"id":"m2"' in call.system_prompt
    assert "Daily checking" in call.system_prompt
    assert "account_checking" not in call.system_prompt
    assert "Never emit source text, wallet IDs" in call.system_prompt


def test_semantic_interpreter_retries_unknown_mention_then_accepts_correction() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(hypotheses=[_hypothesis("amount_minor", "invented")]),
            _response(hypotheses=[_hypothesis("amount_minor", "m0")]),
        ]
    )

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("40"),
        extraction=_extraction((MentionKind.MONEY, "40", 0)),
        context=_context(),
    )

    assert result.hypotheses[0].mention_id == "m0"
    assert not result.issues
    assert len(model.calls) == 2
    assert "unknown mention" in model.calls[1].system_prompt


def test_non_type_model_value_is_ignored_in_favor_of_verified_evidence() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                hypotheses=[
                    _hypothesis("amount_minor", "m0", value="hallucinated normalized value")
                ]
            )
        ]
    )

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("40 pesos"),
        extraction=_extraction((MentionKind.MONEY, "40 pesos", 0)),
        context=_context(),
    )

    assert result.hypotheses == (
        FieldHypothesis(CandidateField.AMOUNT_MINOR, "m0", InterpretationOrigin.EXPLICIT),
    )
    assert not result.issues
    assert len(model.calls) == 1


def test_incompatible_field_remains_a_blocking_issue_after_retry() -> None:
    response = _response(
        hypotheses=[
            _hypothesis("type", "m0", value="expense", origin="inferred"),
            _hypothesis("source_account_id", "m1"),
        ]
    )
    model = FakeStructuredChatModel(responses=[response, response])

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("Spent from Cash"),
        extraction=_extraction(
            (MentionKind.ACTION, "Spent", 0),
            (MentionKind.REFERENCE, "Cash", 11),
        ),
        context=_context(),
    )

    assert [item.field for item in result.hypotheses] == [CandidateField.TYPE]
    assert result.issues[0].field is CandidateField.SOURCE_ACCOUNT_ID
    assert "incompatible" in result.issues[0].reason
    assert len(model.calls) == 2


def test_relevance_validation_uses_safe_candidate_transaction_type() -> None:
    response = _response(hypotheses=[_hypothesis("account_id", "m0")])
    model = FakeStructuredChatModel(responses=[response, response])
    candidate = _candidate_context(transaction_type=TransactionType.TRANSFER)

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("Cash"),
        extraction=_extraction((MentionKind.REFERENCE, "Cash", 0)),
        context=_context(candidate=candidate),
    )

    assert not result.hypotheses
    assert result.issues[0].field is CandidateField.ACCOUNT_ID
    assert "incompatible" in result.issues[0].reason


def test_scalar_field_with_wrong_mention_kind_is_retried() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(hypotheses=[_hypothesis("occurred_on", "m0")]),
            _response(),
        ]
    )

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("Record an expense"),
        extraction=_extraction((MentionKind.ACTION, "Record", 0)),
        context=_context(),
    )

    assert not result.hypotheses
    assert not result.issues
    assert "requires a date_time mention" in model.calls[1].system_prompt


def test_clear_requires_a_verified_change_mention() -> None:
    good = _response(clears=[_clear("notes", "m0")])
    model = FakeStructuredChatModel(responses=[good])

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("remove notes"),
        extraction=_extraction((MentionKind.CHANGE, "remove notes", 0)),
        context=_context(),
    )

    assert result.clears == (FieldClear(CandidateField.NOTES, "m0", InterpretationOrigin.EXPLICIT),)


def test_non_change_clear_retries_and_returns_an_issue() -> None:
    response = _response(clears=[_clear("notes", "m0")])
    model = FakeStructuredChatModel(responses=[response, response])

    result = LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("notes"),
        extraction=_extraction((MentionKind.FREE_TEXT, "notes", 0)),
        context=_context(),
    )

    assert not result.clears
    assert "requires a change" in result.issues[0].reason


def test_semantic_interpreter_rejects_schema_invalid_output_after_retry() -> None:
    model = FakeStructuredChatModel(responses=["```json\n{}\n```", '{"unexpected":true}'])
    interpreter = LlmContributionSemanticInterpreter(model=model)

    with pytest.raises(SemanticInterpretationError, match="invalid semantic interpretation"):
        interpreter.interpret(
            UserContribution("anything"),
            extraction=ContributionExtraction(),
            context=_context(),
        )

    assert len(model.calls) == 2


def test_prompt_serializes_only_safe_candidate_values_labels_and_pending_options() -> None:
    model = FakeStructuredChatModel(responses=[_response()])
    context = _context(
        candidate=SemanticCandidateContext(
            type=TransactionType.EXPENSE,
            amount_minor=3500,
            occurred_on=TODAY,
            account=SemanticReferenceValue(
                SemanticReferenceState.AVAILABLE,
                label="Daily checking",
            ),
            spending_category=SemanticReferenceValue(SemanticReferenceState.UNAVAILABLE),
            income_category=SemanticReferenceValue(SemanticReferenceState.UNSET),
            source_account=SemanticReferenceValue(SemanticReferenceState.UNSET),
            destination_account=SemanticReferenceValue(SemanticReferenceState.UNSET),
            balance_change_minor=None,
            description="Weekly groceries",
            merchant_name="Market",
            notes="Use coupon",
        ),
        pending=SemanticPendingInteraction(
            kind=PendingInteractionKind.REQUEST_VALUE,
            field=CandidateField.AMOUNT_MINOR,
            option_labels=("Personal > Groceries",),
        ),
    )

    LlmContributionSemanticInterpreter(model=model).interpret(
        UserContribution("not sure"),
        extraction=ContributionExtraction(),
        context=context,
    )

    prompt = model.calls[0].system_prompt
    assert '"field":"amount_minor"' in prompt
    assert '"amount_minor":3500' in prompt
    assert '"label":"Daily checking"' in prompt
    assert '"state":"unavailable"' in prompt
    assert '"options":["Personal > Groceries"]' in prompt
    assert "Weekly groceries" in prompt
    assert "Market" in prompt
    assert "Use coupon" in prompt


def _hypothesis(
    field_name: str,
    mention_id: str,
    *,
    value: str | None = None,
    origin: str = "explicit",
) -> dict[str, object]:
    return {
        "field": field_name,
        "mention_id": mention_id,
        "origin": origin,
        "semantic_value": value,
    }


def _clear(field_name: str, mention_id: str) -> dict[str, object]:
    return {"field": field_name, "mention_id": mention_id, "origin": "explicit"}


def _response(
    *,
    hypotheses: list[dict[str, object]] | None = None,
    clears: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps({"hypotheses": hypotheses or [], "clears": clears or []})


def _extraction(*mentions: tuple[MentionKind, str, int]) -> ContributionExtraction:
    return ContributionExtraction(
        mentions=tuple(
            ExtractedMention(
                id=f"m{index}",
                kind=kind,
                evidence=SourceEvidence(start, start + len(text), text),
            )
            for index, (kind, text, start) in enumerate(mentions)
        )
    )


def _context(
    *,
    candidate: SemanticCandidateContext | None = None,
    pending: SemanticPendingInteraction | None = None,
) -> SemanticContext:
    return SemanticContext(
        candidate=candidate or _candidate_context(),
        pending_interaction=pending,
        today=TODAY,
        references=SemanticReferenceVocabulary(
            account_labels=("Daily checking",),
            spending_category_labels=("Food > Groceries",),
            income_category_labels=("Salary > Payroll",),
        ),
    )


def _candidate_context(
    *,
    transaction_type: TransactionType | None = None,
) -> SemanticCandidateContext:
    unset = SemanticReferenceValue(SemanticReferenceState.UNSET)
    return SemanticCandidateContext(
        type=transaction_type,
        amount_minor=None,
        occurred_on=TODAY,
        account=unset,
        spending_category=unset,
        income_category=unset,
        source_account=unset,
        destination_account=unset,
        balance_change_minor=None,
        description=None,
        merchant_name=None,
        notes=None,
    )
