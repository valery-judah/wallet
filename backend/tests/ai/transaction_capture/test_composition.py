from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

import wallet.infrastructure.ollama as ollama_module
from wallet.ai.llm import StructuredChatModel
from wallet.ai.transaction_capture import (
    CandidateField,
    CaptureOutcome,
    CaptureWorkflow,
    PhasedContributionProcessorFactory,
    UserContribution,
)
from wallet.ai.transaction_capture.ports import (
    CaptureReferenceProvider,
    ContributionProcessor,
)
from wallet.ai.transaction_capture.wallet_adapter import WalletCaptureAdapter
from wallet.api.deps import build_app_container
from wallet.config import Settings


class RecordingModel(StructuredChatModel):
    def __init__(self, response: str = "{}") -> None:
        self.call_count = 0
        self.response = response

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        self.call_count += 1
        if "mentions" in output_schema.get("properties", {}):
            mentions = (
                [{"kind": "action", "source_text": "expense"}] if "expense" in user_prompt else []
            )
            return json.dumps({"mentions": mentions})
        return self.response


class RecordingProcessorFactory:
    def __init__(self, model: StructuredChatModel) -> None:
        self._model = model
        self.references: CaptureReferenceProvider | None = None

    def build(
        self,
        *,
        references: CaptureReferenceProvider,
    ) -> ContributionProcessor:
        self.references = references
        return PhasedContributionProcessorFactory(
            extraction_model=self._model,
            semantic_model=self._model,
        ).build(
            references=references,
        )


def test_container_builds_capture_workflow_without_contacting_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ollama_module,
        "urlopen",
        lambda request, timeout: (_ for _ in ()).throw(AssertionError("Ollama must remain lazy")),
    )

    container = build_app_container(
        Settings(
            environment="test",
            seed_sample_data=True,
            ollama_base_url="http://localhost:11434",
            ollama_model="qwen3.5:9b",
        )
    )

    assert isinstance(container.capture_workflow, CaptureWorkflow)


def test_container_injects_capture_processor_factory_into_workflow() -> None:
    model = RecordingModel()
    factory = RecordingProcessorFactory(model)
    container = build_app_container(
        Settings(environment="test", seed_sample_data=True),
        capture_processor_factory=factory,
    )

    assert isinstance(factory.references, WalletCaptureAdapter)
    result = container.capture_workflow.receive(UserContribution("Something happened"))

    assert result.outcome is CaptureOutcome.AWAITING_INTERACTION
    assert model.call_count == 2


def test_progressive_capture_records_transaction_in_seeded_wallet() -> None:
    model = RecordingModel(
        json.dumps(
            {
                "hypotheses": [
                    {
                        "field": "type",
                        "mention_id": "m0",
                        "origin": "explicit",
                        "semantic_value": "expense",
                    }
                ],
                "clears": [],
            }
        )
    )
    container = build_app_container(
        Settings(environment="test", seed_sample_data=True),
        capture_processor_factory=PhasedContributionProcessorFactory(
            extraction_model=model,
            semantic_model=model,
        ),
    )
    transaction_count = len(container.transaction_service.list_transactions())
    balance_before = container.account_service.get_account("sample_account_wallet_ars")
    assert balance_before is not None

    capture_id: str | None = None
    results = []
    transaction_counts = []
    for contribution in ("Record an expense today.", "35", "Pocket wallet", "Coffee"):
        result = container.capture_workflow.receive(
            UserContribution(contribution),
            capture_id=capture_id,
        )
        capture_id = result.session.id
        results.append(result)
        transaction_counts.append(len(container.transaction_service.list_transactions()))

    assert [result.outcome for result in results] == [
        CaptureOutcome.AWAITING_INTERACTION,
        CaptureOutcome.AWAITING_INTERACTION,
        CaptureOutcome.AWAITING_INTERACTION,
        CaptureOutcome.AWAITING_CONFIRMATION,
    ]
    assert [
        result.session.pending_interaction.field
        for result in results[:-1]
        if result.session.pending_interaction is not None
    ] == [
        CandidateField.AMOUNT_MINOR,
        CandidateField.ACCOUNT_ID,
        CandidateField.SPENDING_CATEGORY_ID,
    ]
    assert model.call_count == 2
    assert transaction_counts == [
        transaction_count,
        transaction_count,
        transaction_count,
        transaction_count,
    ]
    assert len(container.transaction_service.list_transactions()) == transaction_count

    ready = results[-1]
    completed = container.capture_workflow.confirm(ready.session.id)
    assert len(container.transaction_service.list_transactions()) == transaction_count + 1
    assert completed.session.transaction_id is not None
    transaction = container.transaction_service.get_transaction(completed.session.transaction_id)
    assert transaction.occurred_on == date.today()
    assert [
        (
            posting.account_id,
            posting.category_id,
            posting.amount_minor,
            posting.currency,
        )
        for posting in transaction.postings
    ] == [
        ("sample_account_wallet_ars", None, -3500, "ARS"),
        (None, "category_food_coffee", 3500, "ARS"),
    ]
    balance_after = container.account_service.get_account("sample_account_wallet_ars")
    assert balance_after is not None
    assert (
        balance_after.current_balance.amount_minor
        == balance_before.current_balance.amount_minor - 3500
    )
