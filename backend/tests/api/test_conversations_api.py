from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from importlib import import_module
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wallet.ai.capabilities.contract import CapabilityDefinition
from wallet.ai.control.routing import (
    ClarifyRouteDecision,
    CompoundControlRouteDecision,
    MessageRoutingContext,
    MessageRoutingError,
    RouteDecision,
    StartRouteDecision,
    UnsupportedRouteDecision,
)
from wallet.ai.llm import StructuredChatTransportError
from wallet.ai.transaction_capture.domain import (
    CandidateField,
    CandidatePatch,
    InteractionOption,
    PendingInteraction,
    TransactionCandidate,
    UserContribution,
)
from wallet.ai.transaction_capture.interpretation import ReferenceAmbiguity
from wallet.ai.transaction_capture.ports import CaptureReferenceProvider
from wallet.ai.transaction_capture.processing import (
    ContributionProcessingResult,
    ContributionProcessingTrace,
    CurrencyConflict,
)
from wallet.api.app import create_app
from wallet.api.deps import AppContainer, build_app_container
from wallet.config import Settings
from wallet.domain.transactions import TransactionType

app_module = import_module("wallet.api.app")


@dataclass
class ApiProcessor:
    failures: set[str] = field(default_factory=set)
    received: list[str] = field(default_factory=list)

    def process(
        self,
        contribution: UserContribution,
        *,
        candidate: TransactionCandidate,
        pending_interaction: PendingInteraction | None,
        on_date: date,
    ) -> ContributionProcessingResult:
        self.received.append(contribution.content)
        if contribution.content in self.failures:
            raise StructuredChatTransportError("model unavailable")
        patches = {
            "Spent 40 USD on groceries": CandidatePatch(
                type=TransactionType.EXPENSE,
                amount_minor=4000,
                account_id="sample_account_cash_usd",
                spending_category_id="category_food_groceries",
            ),
            "Spent 40 USD on groceries without an account": CandidatePatch(
                type=TransactionType.EXPENSE,
                amount_minor=4000,
                spending_category_id="category_food_groceries",
            ),
            "USD cash": CandidatePatch(account_id="sample_account_cash_usd"),
            "Make it 35": CandidatePatch(amount_minor=3500),
            "Record an expense": CandidatePatch(type=TransactionType.EXPENSE),
            "40 USD from Cash for Groceries": CandidatePatch(
                amount_minor=4000,
                account_id="sample_account_cash_usd",
                spending_category_id="category_food_groceries",
            ),
        }
        if contribution.content == "Ambiguous coffee expense":
            return _ambiguous_result(candidate)
        if contribution.content == "40 USD from Daily checking for groceries":
            projected = candidate.apply(
                CandidatePatch(
                    type=TransactionType.EXPENSE,
                    amount_minor=4000,
                    spending_category_id="category_food_groceries",
                    currency_code="USD",
                )
            )
            return ContributionProcessingResult(
                candidate=projected,
                trace=ContributionProcessingTrace(
                    attempt_count=1,
                    applied_fields=(
                        CandidateField.TYPE,
                        CandidateField.AMOUNT_MINOR,
                        CandidateField.SPENDING_CATEGORY_ID,
                        CandidateField.CURRENCY_CODE,
                    ),
                    currency_conflicts=(CurrencyConflict(CandidateField.ACCOUNT_ID, "USD", "ARS"),),
                ),
            )
        patch = patches.get(contribution.content, CandidatePatch())
        next_candidate = candidate.apply(patch)
        return ContributionProcessingResult(
            candidate=next_candidate,
            trace=ContributionProcessingTrace(
                attempt_count=1,
                applied_fields=(),
            ),
        )


@dataclass(frozen=True)
class ApiProcessorFactory:
    processor: ApiProcessor

    def build(self, *, references: CaptureReferenceProvider) -> ApiProcessor:
        return self.processor


class ApiMessageRouter:
    """Deterministic routing fixture; production routing is tested separately."""

    def __init__(self) -> None:
        self.failures: set[str] = set()
        self.received: list[str] = []

    def route(
        self,
        message: str,
        context: MessageRoutingContext,
        definitions: tuple[CapabilityDefinition, ...],
    ) -> RouteDecision:
        self.received.append(message)
        if message in self.failures:
            raise MessageRoutingError("routing failed")
        if message == "cancel this and record income":
            return CompoundControlRouteDecision()
        if message == "hello there":
            return UnsupportedRouteDecision()
        if message == "Summary expense":
            return ClarifyRouteDecision(("transactions.capture", "wallet.current_state"))
        if "balance" in message.casefold() or "overview" in message.casefold():
            return StartRouteDecision("wallet.current_state")
        return StartRouteDecision("transactions.capture")


@pytest.fixture
def processor() -> ApiProcessor:
    return ApiProcessor()


@pytest.fixture
def message_router() -> ApiMessageRouter:
    return ApiMessageRouter()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    processor: ApiProcessor,
    message_router: ApiMessageRouter,
) -> Iterator[TestClient]:
    factory = ApiProcessorFactory(processor)

    def build_test_container(settings: Settings) -> AppContainer:
        return build_app_container(
            settings,
            capture_processor_factory=factory,
            message_router=message_router,
        )

    monkeypatch.setattr(app_module, "build_app_container", build_test_container)
    app = create_app(Settings(environment="test", seed_sample_data=True))
    with TestClient(app) as test_client:
        yield test_client


def test_first_post_creates_routes_and_confirms_transaction_capture(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    before = client.get("/api/v1/transactions").json()

    preview = _message(client, "request-1", "Spent 40 USD on groceries")

    assert preview["request_id"] == "request-1"
    assert preview["conversation"]["version"] == 1
    task = preview["conversation"]["active_task"]
    assert task["id"].startswith("task_")
    assert task["version"] == 1
    assert task["view"]["data"]["phase"] == "awaiting_confirmation"
    assert task["view"]["data"]["candidate"]["amount_minor"] == 4000
    offer = task["view"]["available_actions"][0]
    assert offer == {
        "action": "confirm",
        "label": "Confirm",
        "payload": {},
        "expected_task_id": task["id"],
        "expected_conversation_version": 1,
    }
    assert "capability_id" not in preview["outcome"]
    assert client.get("/api/v1/transactions").json() == before

    confirm_payload = _task_action_payload(
        "request-2",
        preview["conversation"]["id"],
        offer,
    )
    completed_response = client.post("/api/v1/turns", json=confirm_payload)
    replay = client.post("/api/v1/turns", json=confirm_payload)

    assert completed_response.status_code == 200
    completed = completed_response.json()
    assert replay.json() == completed
    assert completed["conversation"]["active_task"] is None
    assert completed["outcome"]["kind"] == "recorded"
    assert completed["outcome"]["result"]["type"] == "expense"
    after = client.get("/api/v1/transactions").json()
    assert len(after) == len(before) + 1
    assert after[-1]["id"] == completed["outcome"]["result"]["id"]

    preview_trace = _trace_for_request(caplog.records, "request-1")
    confirm_trace = completed_response.headers["X-Trace-ID"]
    replay_trace = replay.headers["X-Trace-ID"]
    assert _events_for_trace(caplog.records, preview_trace) == [
        "control.turn.received",
        "capture.contribution.processed",
        "control.turn.processed",
        "control.turn.committed",
        "http.request.completed",
    ]
    assert _events_for_trace(caplog.records, confirm_trace) == [
        "control.turn.received",
        "transaction.recorded",
        "control.turn.processed",
        "control.turn.committed",
        "http.request.completed",
    ]
    assert _events_for_trace(caplog.records, replay_trace) == [
        "control.turn.received",
        "control.turn.replayed",
        "http.request.completed",
    ]


@pytest.mark.parametrize(
    ("content", "outcome_kind"),
    [
        ("hello there", "unsupported"),
        ("help", "help"),
        ("cancel", "nothing_to_cancel"),
        ("restart", "nothing_to_restart"),
        ("Summary expense", "clarify_idle_route"),
    ],
)
def test_first_idle_outcome_still_establishes_a_conversation(
    client: TestClient,
    processor: ApiProcessor,
    content: str,
    outcome_kind: str,
) -> None:
    response = _message(client, f"request-{outcome_kind}", content)

    assert response["conversation"]["version"] == 1
    assert response["conversation"]["active_task"] is None
    assert response["outcome"]["kind"] == outcome_kind
    assert (
        client.get(f"/api/v1/conversations/{response['conversation']['id']}").json()
        == response["conversation"]
    )
    assert processor.received == []


def test_progressive_messages_keep_the_same_opaque_task_until_cancel(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    started = _message(client, "request-1", "Record an expense")
    conversation_id = started["conversation"]["id"]
    task_id = started["conversation"]["active_task"]["id"]

    compound = _message(
        client,
        "request-2",
        "cancel this and record income",
        conversation_id,
    )
    ready = _message(
        client,
        "request-3",
        "40 USD from Cash for Groceries",
        conversation_id,
    )
    cancelled = _message(client, "request-4", "cancel", conversation_id)

    assert started["outcome"]["message"] == "How much?"
    assert compound["outcome"]["kind"] == "question"
    assert compound["conversation"]["active_task"]["id"] == task_id
    assert "cancel this and record income" in processor.received
    assert ready["conversation"]["active_task"]["id"] == task_id
    assert ready["conversation"]["active_task"]["view"]["data"]["phase"] == (
        "awaiting_confirmation"
    )
    assert cancelled["outcome"]["kind"] == "current_task_cancelled"
    assert cancelled["conversation"]["active_task"] is None


def test_control_layer_processes_help_and_cancel_before_capability(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    helped = _typed_help(client, "request-1")
    conversation_id = helped["conversation"]["id"]
    started = _message(client, "request-2", "Record an expense", conversation_id)
    calls_before_cancel = list(processor.received)
    cancelled = _control(client, "request-3", started, "cancel")

    assert "transactions.capture" not in helped["outcome"]["message"]
    assert "wallet.current_state" not in helped["outcome"]["message"]
    assert "Collect and record" in helped["outcome"]["message"]
    assert started["conversation"]["active_task"] is not None
    assert cancelled["outcome"]["kind"] == "current_task_cancelled"
    assert processor.received == calls_before_cancel == ["Record an expense"]


def test_progressive_correction_and_disambiguation_use_unified_turns(client: TestClient) -> None:
    missing = _message(
        client,
        "request-1",
        "Spent 40 USD on groceries without an account",
    )
    conversation_id = missing["conversation"]["id"]
    assert missing["outcome"]["view"]["data"]["interaction"] == {
        "kind": "request_value",
        "field": "account_id",
        "options": [],
    }

    ready = _message(client, "request-2", "USD cash", conversation_id)
    edited = _message(client, "request-3", "Make it 35", conversation_id)
    assert ready["outcome"]["view"]["data"]["phase"] == "awaiting_confirmation"
    assert edited["outcome"]["view"]["data"]["candidate"]["amount_minor"] == 3500

    ambiguous = _message(client, "request-4", "Ambiguous coffee expense")
    assert ambiguous["outcome"]["kind"] == "selection_required"
    assert ambiguous["outcome"]["view"]["data"]["interaction"]["options"] == [
        {"value": "category_food_coffee", "label": "Food > Coffee"},
        {"value": "category_work_coffee", "label": "Work > Coffee"},
    ]


def test_confirmation_revalidates_wallet_references(client: TestClient) -> None:
    transactions_before = client.get("/api/v1/transactions").json()
    preview = _message(client, "request-1", "Spent 40 USD on groceries")
    assert client.post("/api/v1/accounts/sample_account_cash_usd/archive").status_code == 200

    response = _task_action(client, "request-2", preview, "confirm")
    data = response["outcome"]["view"]["data"]

    assert response["outcome"]["kind"] == "question"
    assert data["phase"] == "active"
    assert data["candidate"]["account_id"] is None
    assert data["interaction"] == {
        "kind": "correct",
        "field": "account_id",
        "options": [],
    }
    assert client.get("/api/v1/transactions").json() == transactions_before


def test_currency_conflict_preserves_currency_and_requests_compatible_account(
    client: TestClient,
) -> None:
    response = _message(client, "request-1", "40 USD from Daily checking for groceries")
    data = response["outcome"]["view"]["data"]

    assert data["candidate"]["currency_code"] == "USD"
    assert data["candidate"]["account_id"] is None
    assert data["interaction"] == {
        "kind": "correct",
        "field": "account_id",
        "reason": "currency_conflict",
        "options": [],
    }
    assert response["outcome"]["message"] == (
        "That account's currency does not match USD. Which account did you use?"
    )


def test_supplied_unknown_conversation_returns_not_found_without_processing(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": "request-1",
            "conversation_id": "missing",
            "input": {"kind": "message", "content": "Record an expense"},
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "conversation not found: missing"}
    assert processor.received == []


@pytest.mark.parametrize(
    "input_payload",
    [
        {
            "kind": "task_action",
            "expected_task_id": "task-1",
            "expected_conversation_version": 1,
            "action": "confirm",
            "payload": {},
        },
        {
            "kind": "control_action",
            "action": "cancel",
            "expected_task_id": "task-1",
            "expected_conversation_version": 1,
        },
        {
            "kind": "control_action",
            "action": "restart",
            "expected_task_id": "task-1",
            "expected_conversation_version": 1,
        },
    ],
)
def test_guarded_input_without_conversation_is_rejected(
    client: TestClient,
    input_payload: dict[str, object],
) -> None:
    response = client.post(
        "/api/v1/turns",
        json={"request_id": "request-1", "input": input_payload},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "guarded input requires a conversation id"}


def test_failed_initial_request_publishes_no_response_and_same_id_can_retry(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    processor.failures.add("Record an expense")
    request = {
        "request_id": "request-1",
        "input": {"kind": "message", "content": "Record an expense"},
    }

    failed = client.post("/api/v1/turns", json=request)
    processor.failures.clear()
    retried = client.post("/api/v1/turns", json=request)

    assert failed.status_code == 502
    assert failed.json() == {"detail": "Conversation processing is temporarily unavailable."}
    assert retried.status_code == 200
    assert retried.json()["conversation"]["version"] == 1
    assert processor.received == ["Record an expense", "Record an expense"]


def test_failed_continuation_preserves_state_and_same_id_can_retry(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    started = _message(client, "request-1", "Record an expense")
    processor.failures.add("model fails")
    request = {
        "request_id": "request-2",
        "conversation_id": started["conversation"]["id"],
        "input": {"kind": "message", "content": "model fails"},
    }

    failed = client.post("/api/v1/turns", json=request)
    unchanged = client.get(f"/api/v1/conversations/{started['conversation']['id']}").json()
    processor.failures.clear()
    retried = client.post("/api/v1/turns", json=request)

    assert failed.status_code == 502
    assert unchanged == started["conversation"]
    assert retried.status_code == 200
    assert retried.json()["conversation"]["version"] == 2


def test_failed_routing_preserves_state_and_same_id_can_retry(
    client: TestClient,
    message_router: ApiMessageRouter,
    processor: ApiProcessor,
) -> None:
    started = _message(client, "request-1", "Summary expense")
    assert started["conversation"]["active_task"] is None
    message_router.failures.add("routing fails")
    request = {
        "request_id": "request-2",
        "conversation_id": started["conversation"]["id"],
        "input": {"kind": "message", "content": "routing fails"},
    }

    failed = client.post("/api/v1/turns", json=request)
    unchanged = client.get(f"/api/v1/conversations/{started['conversation']['id']}").json()
    message_router.failures.clear()
    retried = client.post("/api/v1/turns", json=request)

    assert failed.status_code == 502
    assert unchanged == started["conversation"]
    assert retried.status_code == 200
    assert retried.json()["conversation"]["version"] == 2
    assert message_router.received[-2:] == ["routing fails", "routing fails"]
    assert processor.received == ["routing fails"]


def test_global_request_replay_and_changed_payload_or_target_conflict(client: TestClient) -> None:
    first_request = {
        "request_id": "request-1",
        "input": {"kind": "message", "content": "Record an expense"},
    }
    first = client.post("/api/v1/turns", json=first_request)
    replay = client.post("/api/v1/turns", json=first_request)
    second = _message(client, "request-2", "hello there")

    changed_input = client.post(
        "/api/v1/turns",
        json={
            "request_id": "request-1",
            "input": {"kind": "message", "content": "different"},
        },
    )
    changed_target = client.post(
        "/api/v1/turns",
        json={
            "request_id": "request-1",
            "conversation_id": second["conversation"]["id"],
            "input": {"kind": "message", "content": "Record an expense"},
        },
    )

    assert replay.json() == first.json()
    assert changed_input.status_code == 409
    assert changed_target.status_code == 409


def test_concurrent_duplicate_initial_request_creates_and_processes_once(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    request = {
        "request_id": "request-1",
        "input": {"kind": "message", "content": "Record an expense"},
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(lambda _: client.post("/api/v1/turns", json=request), range(2))
        )

    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert processor.received == ["Record an expense"]


def test_restart_replaces_task_id_and_wrong_or_stale_guards_do_no_work(
    client: TestClient,
    processor: ApiProcessor,
) -> None:
    started = _message(client, "request-1", "Record an expense")
    old_task = started["conversation"]["active_task"]
    calls = list(processor.received)

    wrong = client.post(
        "/api/v1/turns",
        json={
            "request_id": "request-2",
            "conversation_id": started["conversation"]["id"],
            "input": {
                "kind": "control_action",
                "action": "restart",
                "expected_task_id": "task-wrong",
                "expected_conversation_version": started["conversation"]["version"],
            },
        },
    )
    stale = client.post(
        "/api/v1/turns",
        json={
            "request_id": "request-3",
            "conversation_id": started["conversation"]["id"],
            "input": {
                "kind": "control_action",
                "action": "restart",
                "expected_task_id": old_task["id"],
                "expected_conversation_version": started["conversation"]["version"] + 1,
            },
        },
    )
    restarted = _control(client, "request-4", started, "restart")
    new_task = restarted["conversation"]["active_task"]

    assert wrong.status_code == stale.status_code == 409
    assert processor.received == calls
    assert restarted["outcome"]["kind"] == "restarted"
    assert new_task["id"] != old_task["id"]
    assert new_task["version"] == 1
    assert new_task["view"]["data"]["candidate"]["type"] is None


def test_help_rebinds_action_version_and_old_offer_becomes_stale(client: TestClient) -> None:
    transactions_before = client.get("/api/v1/transactions").json()
    preview = _message(client, "request-1", "Spent 40 USD on groceries")
    old_offer = preview["conversation"]["active_task"]["view"]["available_actions"][0]
    helped = _typed_help(client, "request-2", preview["conversation"]["id"])
    rebound_offer = helped["conversation"]["active_task"]["view"]["available_actions"][0]

    stale = client.post(
        "/api/v1/turns",
        json=_task_action_payload(
            "request-3",
            preview["conversation"]["id"],
            old_offer,
        ),
    )

    assert rebound_offer["expected_task_id"] == old_offer["expected_task_id"]
    assert rebound_offer["expected_conversation_version"] == helped["conversation"]["version"]
    assert stale.status_code == 409
    assert client.get("/api/v1/transactions").json() == transactions_before


def test_task_rejects_premature_unknown_and_payload_actions_without_writing(
    client: TestClient,
) -> None:
    transactions_before = client.get("/api/v1/transactions").json()
    started = _message(client, "request-1", "Record an expense")

    premature = _task_action(client, "request-2", started, "confirm")
    unknown = _task_action(client, "request-3", premature, "unknown")
    malformed = _task_action(
        client,
        "request-4",
        unknown,
        "confirm",
        payload={"unexpected": True},
    )

    assert premature["outcome"]["kind"] == "action_unavailable"
    assert unknown["outcome"]["kind"] == "action_unavailable"
    assert malformed["outcome"]["kind"] == "action_unavailable"
    assert client.get("/api/v1/transactions").json() == transactions_before


def test_active_message_stays_with_workflow_then_idle_message_starts_wallet_state(
    client: TestClient,
    message_router: ApiMessageRouter,
    processor: ApiProcessor,
) -> None:
    account_before = client.get("/api/v1/accounts/sample_account_cash_usd").json()
    transactions_before = client.get("/api/v1/transactions").json()
    preview = _message(client, "request-1", "Spent 40 USD on groceries")
    conversation_id = preview["conversation"]["id"]
    task_id = preview["conversation"]["active_task"]["id"]

    continued = _message(client, "request-2", "Show my current balances", conversation_id)
    assert continued["conversation"]["active_task"]["id"] == task_id
    assert continued["outcome"]["kind"] == "preview"
    assert processor.received[-1] == "Show my current balances"
    assert "Show my current balances" not in message_router.received

    completed = _task_action(client, "request-3", continued, "confirm")
    state = _message(client, "request-4", "Show my current balances", conversation_id)

    assert completed["outcome"]["kind"] == "recorded"
    assert state["outcome"]["kind"] == "state_shown"
    assert state["conversation"]["active_task"] is None
    state_account = next(
        account
        for account in state["outcome"]["view"]["data"]["accounts"]
        if account["id"] == "sample_account_cash_usd"
    )
    assert state_account["balance_minor"] == (
        account_before["current_balance"]["amount_minor"] - 4_000
    )
    assert len(client.get("/api/v1/transactions").json()) == len(transactions_before) + 1


def test_two_concurrent_confirmations_create_exactly_one_transaction(client: TestClient) -> None:
    transactions_before = client.get("/api/v1/transactions").json()
    preview = _message(client, "request-1", "Spent 40 USD on groceries")
    task = preview["conversation"]["active_task"]

    def confirm(request_id: str) -> Any:
        return client.post(
            "/api/v1/turns",
            json={
                "request_id": request_id,
                "conversation_id": preview["conversation"]["id"],
                "input": {
                    "kind": "task_action",
                    "expected_task_id": task["id"],
                    "expected_conversation_version": preview["conversation"]["version"],
                    "action": "confirm",
                    "payload": {},
                },
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(confirm, ("confirm-a", "confirm-b")))

    assert sorted(response.status_code for response in responses) == [200, 409]
    assert len(client.get("/api/v1/transactions").json()) == len(transactions_before) + 1


@pytest.mark.parametrize("content", ["   ", "x" * 4_001])
def test_message_content_is_bounded(client: TestClient, content: str) -> None:
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": "request-1",
            "input": {"kind": "message", "content": content},
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {
            "request_id": "bad id",
            "input": {"kind": "message", "content": "hello"},
        },
        {
            "request_id": "request-1",
            "input": {"kind": "capability_start", "capability_id": "transactions.capture"},
        },
        {
            "request_id": "request-1",
            "input": {
                "kind": "capability_action",
                "expected_capability_id": "transactions.capture",
                "expected_conversation_version": 1,
                "action": "confirm",
            },
        },
        {
            "request_id": "request-1",
            "input": {"kind": "message", "content": "hello", "server_field": True},
        },
    ],
)
def test_schema_rejects_invalid_ids_removed_inputs_and_server_fields(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    assert client.post("/api/v1/turns", json=payload).status_code == 422


def test_public_response_excludes_internal_capability_and_model_data(client: TestClient) -> None:
    response = _message(client, "request-1", "Spent 40 USD on groceries")
    serialized = str(response).casefold()

    assert "current_capability" not in serialized
    assert "capability_id" not in serialized
    assert "transactions.capture" not in serialized
    assert "processing_trace" not in serialized
    assert "semantic_interpretation" not in serialized
    assert "grounded_interpretation" not in serialized
    assert "interpretation_evidence" not in serialized
    assert "reference_mapping" not in serialized
    assert "raw_model_output" not in serialized
    assert "model_prompt" not in serialized


def test_private_financial_message_is_not_logged_by_default(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_content = "Expense secret-marker-7f34b6"

    response = _message(client, "request-1", private_content)

    assert response["conversation"]["active_task"] is not None
    assert private_content not in caplog.text


def test_openapi_exposes_only_unified_turn_and_conversation_read(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()
    paths = schema["paths"]
    serialized = str(schema)

    assert "/api/v1/turns" in paths
    assert paths["/api/v1/turns"].keys() == {"post"}
    assert "/api/v1/conversations/{conversation_id}" in paths
    assert "/api/v1/conversations" not in paths
    assert "/api/v1/conversations/{conversation_id}/turns" not in paths
    assert "transaction-captures" not in serialized
    assert "CapabilityStartTurnInput" not in serialized
    assert "CapabilityActionTurnInput" not in serialized
    assert "CapabilityViewResponse" not in serialized
    assert "current_capability" not in serialized
    assert "expected_capability_id" not in serialized


def _message(
    client: TestClient,
    request_id: str,
    content: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": request_id,
            "conversation_id": conversation_id,
            "input": {"kind": "message", "content": content},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _trace_for_request(records: list[Any], request_id: str) -> str:
    record = next(
        record
        for record in records
        if getattr(record, "event", None) == "control.turn.received"
        and getattr(record, "event_context", {}).get("request_id") == request_id
    )
    return str(record.event_context["trace_id"])


def _events_for_trace(records: list[Any], trace_id: str) -> list[str]:
    return [
        record.event
        for record in records
        if getattr(record, "event", None) is not None
        and getattr(record, "event_context", {}).get("trace_id") == trace_id
    ]


def _typed_help(
    client: TestClient,
    request_id: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": request_id,
            "conversation_id": conversation_id,
            "input": {"kind": "control_action", "action": "help"},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _task_action(
    client: TestClient,
    request_id: str,
    previous: dict[str, Any],
    action: str,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, Any]:
    task = previous["conversation"]["active_task"]
    assert task is not None
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": request_id,
            "conversation_id": previous["conversation"]["id"],
            "input": {
                "kind": "task_action",
                "expected_task_id": task["id"],
                "expected_conversation_version": previous["conversation"]["version"],
                "action": action,
                "payload": {} if payload is None else payload,
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _control(
    client: TestClient,
    request_id: str,
    previous: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    task = previous["conversation"]["active_task"]
    assert task is not None
    response = client.post(
        "/api/v1/turns",
        json={
            "request_id": request_id,
            "conversation_id": previous["conversation"]["id"],
            "input": {
                "kind": "control_action",
                "action": action,
                "expected_task_id": task["id"],
                "expected_conversation_version": previous["conversation"]["version"],
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _task_action_payload(
    request_id: str,
    conversation_id: str,
    offer: dict[str, Any],
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "conversation_id": conversation_id,
        "input": {
            "kind": "task_action",
            "expected_task_id": offer["expected_task_id"],
            "expected_conversation_version": offer["expected_conversation_version"],
            "action": offer["action"],
            "payload": offer["payload"],
        },
    }


def _ambiguous_result(candidate: TransactionCandidate) -> ContributionProcessingResult:
    projected = candidate.apply(
        CandidatePatch(
            type=TransactionType.EXPENSE,
            amount_minor=3500,
            account_id="sample_account_cash_usd",
        )
    )
    ambiguity = ReferenceAmbiguity(
        field=CandidateField.SPENDING_CATEGORY_ID,
        options=(
            InteractionOption("category_food_coffee", "Food > Coffee"),
            InteractionOption("category_work_coffee", "Work > Coffee"),
        ),
    )
    return ContributionProcessingResult(
        candidate=projected,
        trace=ContributionProcessingTrace(
            attempt_count=1,
            applied_fields=(
                CandidateField.TYPE,
                CandidateField.AMOUNT_MINOR,
                CandidateField.ACCOUNT_ID,
            ),
            ambiguities=(ambiguity,),
        ),
    )
