from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pytest

from wallet.ai.llm import StructuredChatTransportError
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    PendingInteraction,
    PendingInteractionKind,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.interpretation import (
    ContributionInterpretationError,
    LlmContributionInterpreter,
)
from wallet.ai.transaction_capture.ports import (
    CaptureAccountReference,
    CaptureCategoryReference,
    CaptureReferenceCatalog,
)
from wallet.domain.transactions import TransactionType

TODAY = date(2026, 8, 6)


@dataclass(frozen=True)
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


def test_interpreter_maps_permissive_model_updates_to_trusted_wallet_ids() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                updates={
                    "type": "expense",
                    "amount_minor": 4000,
                    "account_key": "account_1",
                    "spending_category_key": "spending_0",
                    "currency_code": "USD",
                },
                evidence=[{"field": "account_id", "source_text": "cache"}],
            )
        ]
    )

    result = _interpreter(model).interpret(
        UserContribution("40 USD cache on groceries"),
        candidate=TransactionCandidate(occurred_on=TODAY),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.patch == CandidatePatch(
        type=TransactionType.EXPENSE,
        amount_minor=4000,
        account_id="cash_usd",
        spending_category_id="groceries",
        currency_code="USD",
    )
    assert result.evidence[0].source_text == "cache"
    call = model.calls[0]
    assert call.user_prompt == "40 USD cache on groceries"
    assert '"currency":"USD","key":"account_1","label":"USD cash"' in call.system_prompt
    assert "cash_usd" not in call.system_prompt
    assert "groceries" in call.system_prompt
    assert call.output_schema["properties"]["updates"]["properties"]["account_key"] == {
        "type": "string",
        "enum": ["account_0", "account_1"],
    }


def test_interpreter_preserves_omitted_fields_and_supports_explicit_clears() -> None:
    model = FakeStructuredChatModel(
        responses=[_response(updates={"amount_minor": 4500}, clear_fields=["notes"])]
    )

    result = _interpreter(model).interpret(
        UserContribution("Actually 45 and remove the note"),
        candidate=TransactionCandidate(
            type=TransactionType.EXPENSE,
            amount_minor=4000,
            account_id="cash_usd",
            spending_category_id="groceries",
            occurred_on=TODAY,
            notes="old note",
        ),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.patch == CandidatePatch(amount_minor=4500, notes=None)


def test_interpreter_maps_validated_reference_ambiguity_to_public_options() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                updates={"type": "expense", "amount_minor": 3500},
                ambiguities=[
                    {
                        "field": "spending_category_id",
                        "candidate_keys": ["spending_1", "spending_2"],
                    }
                ],
            )
        ]
    )

    result = _interpreter(model).interpret(
        UserContribution("Spent 35 on Coffee"),
        candidate=TransactionCandidate(occurred_on=TODAY),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.ambiguities[0].field is CandidateField.SPENDING_CATEGORY_ID
    assert [(item.value, item.label) for item in result.ambiguities[0].options] == [
        ("coffee_food", "Food > Coffee"),
        ("coffee_work", "Work > Coffee"),
    ]


def test_interpreter_projects_unqualified_shared_leaf_selection_as_ambiguity() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(updates={"spending_category_key": "spending_1"}),
        ]
    )

    result = _interpreter(model).interpret(
        UserContribution("Coffee"),
        candidate=TransactionCandidate(type=TransactionType.EXPENSE, occurred_on=TODAY),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.attempt_count == 1
    assert result.ambiguities[0].field is CandidateField.SPENDING_CATEGORY_ID
    assert [option.value for option in result.ambiguities[0].options] == [
        "coffee_food",
        "coffee_work",
    ]


def test_interpreter_accepts_parent_qualified_shared_leaf_selection() -> None:
    model = FakeStructuredChatModel(
        responses=[_response(updates={"spending_category_key": "spending_1"})]
    )

    result = _interpreter(model).interpret(
        UserContribution("Food > Coffee"),
        candidate=TransactionCandidate(type=TransactionType.EXPENSE, occurred_on=TODAY),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.patch == CandidatePatch(spending_category_id="coffee_food")
    assert result.attempt_count == 1


def test_interpreter_normalizes_non_transfer_account_reference_slot() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                updates={
                    "type": "expense",
                    "source_account_key": "account_1",
                }
            )
        ]
    )

    result = _interpreter(model).interpret(
        UserContribution("40 USD cache on groceries"),
        candidate=TransactionCandidate(occurred_on=TODAY),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.patch == CandidatePatch(
        type=TransactionType.EXPENSE,
        account_id="cash_usd",
    )


def test_interpreter_prefers_explicit_child_over_selected_category_parent() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                updates={
                    "type": "income",
                    "income_category_key": "income_0",
                }
            )
        ]
    )

    result = _interpreter(model).interpret(
        UserContribution("Received Payroll"),
        candidate=TransactionCandidate(occurred_on=TODAY),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.patch == CandidatePatch(
        type=TransactionType.INCOME,
        income_category_id="payroll",
    )


def test_invalid_optional_evidence_does_not_block_valid_interpretation() -> None:
    model = FakeStructuredChatModel(
        responses=[
            _response(
                updates={"account_key": "account_1"},
                evidence=[
                    {"field": "account_key", "source_text": "cache"},
                    {"field": "not_a_field", "source_text": "ignored"},
                    {"field": "amount_minor", "source_text": "   "},
                ],
            )
        ]
    )

    result = _interpreter(model).interpret(
        UserContribution("USD cache"),
        candidate=TransactionCandidate(type=TransactionType.EXPENSE, occurred_on=TODAY),
        pending_interaction=None,
        references=_references(),
        on_date=TODAY,
    )

    assert result.patch == CandidatePatch(account_id="cash_usd")
    assert result.evidence == (result.evidence[0],)
    assert result.evidence[0].field is CandidateField.ACCOUNT_ID
    assert result.evidence[0].source_text == "cache"


def _response(
    *,
    updates: dict[str, object] | None = None,
    clear_fields: list[str] | None = None,
    ambiguities: list[dict[str, object]] | None = None,
    unresolved_fields: list[str] | None = None,
    clarification_needed: bool = False,
    evidence: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps(
        {
            "updates": updates or {},
            "clear_fields": clear_fields or [],
            "ambiguities": ambiguities or [],
            "unresolved_fields": unresolved_fields or [],
            "clarification_needed": clarification_needed,
            "evidence": evidence or [],
        }
    )


@pytest.mark.parametrize(
    "invalid",
    [
        _response(updates={"account_key": "invented"}),
        _response(updates={"amount_minor": None}),
        _response(updates={"notes": "new"}, clear_fields=["notes"]),
        _response(updates={"type": "expense"}, clarification_needed=True),
        _response(
            ambiguities=[
                {
                    "field": "account_id",
                    "candidate_keys": ["spending_0", "spending_1"],
                }
            ]
        ),
    ],
)
def test_interpreter_retries_invalid_or_context_inconsistent_output(invalid: str) -> None:
    model = FakeStructuredChatModel(
        responses=[invalid, _response(updates={"account_key": "account_1"})]
    )

    result = _interpreter(model).interpret(
        UserContribution("USD cash"),
        candidate=TransactionCandidate(type=TransactionType.EXPENSE, occurred_on=TODAY),
        pending_interaction=PendingInteraction(
            PendingInteractionKind.REQUEST_VALUE,
            CandidateField.ACCOUNT_ID,
        ),
        references=_references(),
        on_date=TODAY,
    )

    assert result.patch == CandidatePatch(account_id="cash_usd")
    assert result.attempt_count == 2
    assert "RETRY_FEEDBACK" in model.calls[1].system_prompt


def test_interpreter_raises_after_invalid_retry_exhaustion() -> None:
    invalid = _response(updates={"account_key": "invented"})
    model = FakeStructuredChatModel(responses=[invalid, invalid])

    with pytest.raises(ContributionInterpretationError, match="invalid transaction"):
        _interpreter(model).interpret(
            UserContribution("unknown"),
            candidate=TransactionCandidate(occurred_on=TODAY),
            pending_interaction=None,
            references=_references(),
            on_date=TODAY,
        )

    assert len(model.calls) == 2


def test_interpreter_does_not_retry_transport_failure() -> None:
    model = FakeStructuredChatModel(responses=[StructuredChatTransportError("model unavailable")])

    with pytest.raises(StructuredChatTransportError):
        _interpreter(model).interpret(
            UserContribution("anything"),
            candidate=TransactionCandidate(occurred_on=TODAY),
            pending_interaction=None,
            references=_references(),
            on_date=TODAY,
        )

    assert len(model.calls) == 1


def _interpreter(model: FakeStructuredChatModel) -> LlmContributionInterpreter:
    return LlmContributionInterpreter(model=model)


def _references() -> CaptureReferenceCatalog:
    return CaptureReferenceCatalog(
        accounts=(
            CaptureAccountReference("checking", "Daily checking", "ARS"),
            CaptureAccountReference("cash_usd", "USD cash", "USD"),
        ),
        spending_categories=(
            CaptureCategoryReference("groceries", "Food > Groceries"),
            CaptureCategoryReference("coffee_food", "Food > Coffee"),
            CaptureCategoryReference("coffee_work", "Work > Coffee"),
        ),
        income_categories=(
            CaptureCategoryReference("salary", "Salary"),
            CaptureCategoryReference("payroll", "Salary > Payroll"),
        ),
    )
