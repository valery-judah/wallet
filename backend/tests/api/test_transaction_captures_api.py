from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from importlib import import_module

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from wallet.ai.llm import StructuredChatTransportError
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    PendingInteraction,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.extraction import ContributionExtraction, SourceEvidence
from wallet.ai.transaction_capture.grounding import (
    GroundedInterpretation,
    GroundingAmbiguity,
    GroundingOption,
)
from wallet.ai.transaction_capture.ports import CaptureReferenceProvider
from wallet.ai.transaction_capture.processing import (
    CandidateReduction,
    ContributionAnalysisPath,
    ContributionProcessingResult,
    ContributionProcessingTrace,
)
from wallet.ai.transaction_capture.semantic import SemanticInterpretation
from wallet.api.app import create_app
from wallet.api.deps import AppContainer, build_app_container
from wallet.config import Settings
from wallet.domain.transactions import TransactionType

app_module = import_module("wallet.api.app")


@dataclass
class ApiProcessor:
    failures: set[str] = field(default_factory=set)

    def process(
        self,
        contribution: UserContribution,
        *,
        candidate: TransactionCandidate,
        pending_interaction: PendingInteraction | None,
        on_date: date,
    ) -> ContributionProcessingResult:
        if contribution.content in self.failures:
            raise StructuredChatTransportError("model unavailable")
        if contribution.content == "Spent 40 USD on groceries":
            patch = CandidatePatch(
                type=TransactionType.EXPENSE,
                amount_minor=4000,
                account_id="sample_account_cash_usd",
                spending_category_id="category_food_groceries",
            )
        elif contribution.content == "Spent 40 USD on groceries without an account":
            patch = CandidatePatch(
                type=TransactionType.EXPENSE,
                amount_minor=4000,
                spending_category_id="category_food_groceries",
            )
        elif contribution.content == "USD cash":
            patch = CandidatePatch(account_id="sample_account_cash_usd")
        elif contribution.content == "Make it 35":
            patch = CandidatePatch(amount_minor=3500)
        elif contribution.content == "Record an expense":
            patch = CandidatePatch(type=TransactionType.EXPENSE)
        elif contribution.content == "Ambiguous coffee":
            return _ambiguous_result(candidate)
        else:
            patch = CandidatePatch()
        next_candidate = candidate.apply(patch)
        return _processing_result(next_candidate, patch=patch)


@dataclass(frozen=True)
class ApiProcessorFactory:
    processor: ApiProcessor

    def build(self, *, references: CaptureReferenceProvider) -> ApiProcessor:
        return self.processor


@pytest.fixture
def processor() -> ApiProcessor:
    return ApiProcessor()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    processor: ApiProcessor,
) -> Iterator[TestClient]:
    factory = ApiProcessorFactory(processor)

    def build_test_container(settings: Settings) -> AppContainer:
        return build_app_container(settings, capture_processor_factory=factory)

    monkeypatch.setattr(app_module, "build_app_container", build_test_container)
    app = create_app(Settings(environment="test", seed_sample_data=True))
    with TestClient(app) as test_client:
        yield test_client


def test_complete_capture_previews_then_confirms_one_visible_transaction(
    client: TestClient,
) -> None:
    before = client.get("/api/v1/transactions").json()

    created = client.post(
        "/api/v1/transaction-captures",
        json={"content": "Spent 40 USD on groceries"},
    )

    assert created.status_code == 201
    preview = created.json()
    capture_id = preview["id"]
    assert preview == {
        "id": capture_id,
        "status": "awaiting_confirmation",
        "candidate": {
            "type": "expense",
            "amount_minor": 4000,
            "occurred_on": date.today().isoformat(),
            "account_id": "sample_account_cash_usd",
            "spending_category_id": "category_food_groceries",
            "income_category_id": None,
            "source_account_id": None,
            "destination_account_id": None,
            "balance_change_minor": None,
            "description": None,
            "merchant_name": None,
            "notes": None,
        },
        "interaction": None,
        "message": (
            "Ready to record: USD 40.00 expense from USD cash for "
            f"Food > Groceries on {date.today().isoformat()}. Confirm or cancel."
        ),
        "transaction": None,
    }
    assert client.get("/api/v1/transactions").json() == before
    assert client.get(f"/api/v1/transaction-captures/{capture_id}").json() == preview

    confirmed = client.post(f"/api/v1/transaction-captures/{capture_id}/confirm")

    assert confirmed.status_code == 200
    completed = confirmed.json()
    assert completed["status"] == "completed"
    assert completed["message"].startswith("Recorded: USD 40.00 expense")
    assert completed["interaction"] is None
    assert completed["transaction"]["type"] == "expense"
    assert completed["transaction"]["status"] == "posted"
    assert [
        (
            posting["account_id"],
            posting["category_id"],
            posting["amount_minor"],
            posting["currency"],
        )
        for posting in completed["transaction"]["postings"]
    ] == [
        ("sample_account_cash_usd", None, -4000, "USD"),
        (None, "category_food_groceries", 4000, "USD"),
    ]
    after = client.get("/api/v1/transactions").json()
    assert len(after) == len(before) + 1
    assert after[-1]["id"] == completed["transaction"]["id"]

    repeated = client.post(f"/api/v1/transaction-captures/{capture_id}/confirm")
    assert repeated.status_code == 200
    assert repeated.json()["transaction"]["id"] == completed["transaction"]["id"]
    assert len(client.get("/api/v1/transactions").json()) == len(after)


def test_progressive_capture_returns_prompt_and_accepts_preview_edits(
    client: TestClient,
) -> None:
    started = client.post(
        "/api/v1/transaction-captures",
        json={"content": "Spent 40 USD on groceries without an account"},
    )

    assert started.status_code == 201
    active = started.json()
    assert active["status"] == "active"
    assert active["message"] == "Which account did you use?"
    assert active["interaction"] == {
        "kind": "request_value",
        "field": "account_id",
        "options": [],
    }

    account = client.post(
        f"/api/v1/transaction-captures/{active['id']}/contributions",
        json={"content": "USD cash"},
    )
    assert account.status_code == 200
    assert account.json()["status"] == "awaiting_confirmation"

    edited = client.post(
        f"/api/v1/transaction-captures/{active['id']}/contributions",
        json={"content": "Make it 35"},
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "awaiting_confirmation"
    assert edited.json()["candidate"]["amount_minor"] == 3500
    assert edited.json()["message"].startswith("Ready to record: USD 35.00 expense")
    assert edited.json()["transaction"] is None


def test_disambiguation_exposes_only_structured_options_and_safe_copy(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/transaction-captures",
        json={"content": "Ambiguous coffee"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["message"] == "Which spending category did you mean?"
    assert payload["interaction"] == {
        "kind": "disambiguate",
        "field": "spending_category_id",
        "options": [
            {"value": "category_food_coffee", "label": "Food > Coffee"},
            {"value": "category_work_coffee", "label": "Work > Coffee"},
        ],
    }
    assert set(payload) == {
        "id",
        "status",
        "candidate",
        "interaction",
        "message",
        "transaction",
    }


def test_confirmation_revalidates_an_account_archived_after_preview(client: TestClient) -> None:
    preview = client.post(
        "/api/v1/transaction-captures",
        json={"content": "Spent 40 USD on groceries"},
    ).json()
    archived = client.post("/api/v1/accounts/sample_account_cash_usd/archive")
    assert archived.status_code == 200

    response = client.post(f"/api/v1/transaction-captures/{preview['id']}/confirm")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["candidate"]["account_id"] is None
    assert payload["interaction"] == {
        "kind": "correct",
        "field": "account_id",
        "options": [],
    }
    assert payload["message"] == "I couldn't use that account. Which account did you use?"
    assert payload["transaction"] is None


def test_cancel_is_idempotent_and_terminal(client: TestClient) -> None:
    active = client.post(
        "/api/v1/transaction-captures",
        json={"content": "Record an expense"},
    ).json()

    cancelled = client.post(f"/api/v1/transaction-captures/{active['id']}/cancel")
    repeated = client.post(f"/api/v1/transaction-captures/{active['id']}/cancel")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["message"] == "Capture cancelled."
    assert repeated.json() == cancelled.json()
    contribution = client.post(
        f"/api/v1/transaction-captures/{active['id']}/contributions",
        json={"content": "40"},
    )
    confirmation = client.post(f"/api/v1/transaction-captures/{active['id']}/confirm")
    assert contribution.status_code == 409
    assert confirmation.status_code == 409


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/transaction-captures/missing",
        "/api/v1/transaction-captures/missing/contributions",
        "/api/v1/transaction-captures/missing/confirm",
        "/api/v1/transaction-captures/missing/cancel",
    ],
)
def test_unknown_capture_returns_not_found(client: TestClient, path: str) -> None:
    response = (
        client.post(path, json={"content": "anything"})
        if path.endswith("contributions")
        else client.post(path)
        if path.endswith(("confirm", "cancel"))
        else client.get(path)
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "capture session not found: missing"}


@pytest.mark.parametrize("content", ["   ", "x" * 4_001])
def test_contribution_content_is_bounded(client: TestClient, content: str) -> None:
    response = client.post(
        "/api/v1/transaction-captures",
        json={"content": content},
    )

    assert response.status_code == 422


def test_model_transport_failure_returns_safe_bad_gateway(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    processor.failures.add("model down")

    response = client.post(
        "/api/v1/transaction-captures",
        json={"content": "model down"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Transaction capture is temporarily unavailable."}
    assert "model unavailable" not in response.text


def test_openapi_exposes_stable_transaction_capture_operations(client: TestClient) -> None:
    assert isinstance(client.app, FastAPI)
    schema = client.app.openapi()
    paths = schema["paths"]

    assert paths["/api/v1/transaction-captures"]["post"]["operationId"] == (
        "transaction-captures-create_transaction_capture"
    )
    assert paths["/api/v1/transaction-captures/{capture_id}"]["get"]["operationId"] == (
        "transaction-captures-get_transaction_capture"
    )
    assert (
        paths["/api/v1/transaction-captures/{capture_id}/contributions"]["post"]["operationId"]
        == "transaction-captures-add_transaction_capture_contribution"
    )
    assert (
        paths["/api/v1/transaction-captures/{capture_id}/confirm"]["post"]["operationId"]
        == "transaction-captures-confirm_transaction_capture"
    )
    assert (
        paths["/api/v1/transaction-captures/{capture_id}/cancel"]["post"]["operationId"]
        == "transaction-captures-cancel_transaction_capture"
    )


def _processing_result(
    candidate: TransactionCandidate,
    *,
    patch: CandidatePatch,
) -> ContributionProcessingResult:
    reduction = CandidateReduction(patch=patch, candidate=candidate)
    return ContributionProcessingResult(
        candidate=candidate,
        trace=ContributionProcessingTrace(
            analysis_path=ContributionAnalysisPath.MODEL_PIPELINE,
            extraction=ContributionExtraction(),
            semantic_interpretation=SemanticInterpretation(),
            grounded_interpretation=GroundedInterpretation(patch=patch),
            candidate_reduction=reduction,
        ),
    )


def _ambiguous_result(candidate: TransactionCandidate) -> ContributionProcessingResult:
    projected = candidate.apply(
        CandidatePatch(
            type=TransactionType.EXPENSE,
            amount_minor=3500,
            account_id="sample_account_cash_usd",
        )
    )
    ambiguity = GroundingAmbiguity(
        field=CandidateField.SPENDING_CATEGORY_ID,
        evidence=SourceEvidence(0, 6, "coffee"),
        options=(
            GroundingOption("category_food_coffee", "Food > Coffee"),
            GroundingOption("category_work_coffee", "Work > Coffee"),
        ),
        reason="ambiguous",
    )
    reduction = CandidateReduction(
        patch=CandidatePatch(),
        candidate=projected,
        blocking_ambiguities=(ambiguity,),
    )
    return ContributionProcessingResult(
        candidate=projected,
        trace=ContributionProcessingTrace(
            analysis_path=ContributionAnalysisPath.MODEL_PIPELINE,
            extraction=ContributionExtraction(),
            semantic_interpretation=SemanticInterpretation(),
            grounded_interpretation=GroundedInterpretation(ambiguities=(ambiguity,)),
            candidate_reduction=reduction,
        ),
    )
