from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from enum import StrEnum
from io import StringIO

import pytest

from wallet.api.deps import build_app_container
from wallet.application.accounts import AccountService, OpenAccount
from wallet.application.spending_categories import CreateSpendingCategory, SpendingCategoryService
from wallet.application.transactions import CreatePosting, CreateTransaction, TransactionService
from wallet.config import Settings
from wallet.domain.accounts import AccountType
from wallet.domain.transactions import TransactionType
from wallet.infrastructure.memory import (
    InMemoryAccountRepository,
    InMemoryIncomeCategoryRepository,
    InMemorySpendingCategoryRepository,
    InMemoryTransactionRepository,
)
from wallet.observability import JsonLogFormatter, bind_log_context, error_details, log_event


class ExampleKind(StrEnum):
    VALUE = "value"


def test_json_formatter_emits_stable_envelope_and_restores_context() -> None:
    logger, output = _capturing_logger("wallet.tests.observability.envelope")

    with bind_log_context(
        trace_id="a" * 32,
        origin="conversation",
        request_id="request-1",
    ):
        log_event(
            logger,
            logging.INFO,
            "test.completed",
            data={"kind": ExampleKind.VALUE, "items": (1, 2)},
        )
    log_event(logger, logging.INFO, "test.context_restored")

    first, second = [json.loads(line) for line in output.getvalue().splitlines()]
    assert set(first) == {
        "schema_version",
        "timestamp",
        "level",
        "service",
        "environment",
        "event",
        "logger",
        "source",
        "trace_id",
        "context",
        "data",
        "error",
    }
    assert first["schema_version"] == 1
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", first["timestamp"])
    assert first["level"] == "INFO"
    assert first["service"] == "wallet-api"
    assert first["event"] == "test.completed"
    assert first["logger"] == "wallet.tests.observability.envelope"
    assert (
        first["source"]["function"]
        == "test_json_formatter_emits_stable_envelope_and_restores_context"
    )
    assert isinstance(first["source"]["line"], int)
    assert first["trace_id"] == "a" * 32
    assert first["context"] == {"origin": "conversation", "request_id": "request-1"}
    assert first["data"] == {"kind": "value", "items": [1, 2]}
    assert first["error"] is None
    assert second["trace_id"] is None
    assert second["context"] == {"origin": "internal"}


def test_expected_error_has_code_without_message_or_stacktrace() -> None:
    logger, output = _capturing_logger("wallet.tests.observability.expected")
    private_message = "private expected failure marker 7f34b6"
    error = ValueError(private_message)

    log_event(
        logger,
        logging.WARNING,
        "test.rejected",
        error=error_details(error, code="test_rejected", retryable=False),
    )

    record = json.loads(output.getvalue())
    assert record["error"] == {
        "type": "ValueError",
        "code": "test_rejected",
        "retryable": False,
    }
    assert private_message not in output.getvalue()


def test_unexpected_error_has_safe_traceback_without_exception_message() -> None:
    logger, output = _capturing_logger("wallet.tests.observability.unexpected")
    private_message = "private unexpected failure marker 8a45c7"

    try:
        raise RuntimeError(private_message)
    except RuntimeError as exc:
        log_event(
            logger,
            logging.ERROR,
            "test.failed",
            error=error_details(exc, code="unexpected_error", retryable=False),
            exc_info=exc,
        )

    record = json.loads(output.getvalue())
    assert record["error"]["type"] == "RuntimeError"
    assert record["error"]["stacktrace"]
    assert private_message not in output.getvalue()


def test_unstructured_dependency_record_becomes_runtime_event() -> None:
    logger, output = _capturing_logger("third_party.example")

    logger.info("dependency ready")

    record = json.loads(output.getvalue())
    assert record["event"] == "runtime.log"
    assert record["data"] == {"message": "dependency ready"}


def test_runtime_event_redacts_raw_urls() -> None:
    logger, output = _capturing_logger("third_party.http")

    logger.info("GET https://wallet.example/accounts/private-id?token=secret completed")

    assert "wallet.example" not in output.getvalue()
    assert "token=secret" not in output.getvalue()
    assert json.loads(output.getvalue())["data"]["message"] == "GET <url> completed"


def test_context_is_isolated_between_concurrent_executions() -> None:
    logger, output = _capturing_logger("wallet.tests.observability.concurrent")

    def emit(index: int) -> None:
        with bind_log_context(trace_id=f"{index:032x}", request_id=f"request-{index}"):
            log_event(logger, logging.INFO, "test.concurrent")

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(emit, range(8)))

    records = [json.loads(line) for line in output.getvalue().splitlines()]
    assert {(record["trace_id"], record["context"]["request_id"]) for record in records} == {
        (f"{index:032x}", f"request-{index}") for index in range(8)
    }


def test_bootstrap_emits_summary_without_seed_entity_success_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="wallet")

    container = build_app_container(Settings(environment="test", seed_sample_data=True))

    events = [getattr(record, "event", None) for record in caplog.records]
    assert events.count("bootstrap.completed") == 1
    assert not {
        "account.opened",
        "account.opening_balance.recorded",
        "category.created",
        "transaction.recorded",
    }.intersection(events)
    summary = next(
        record
        for record in caplog.records
        if getattr(record, "event", None) == "bootstrap.completed"
    )
    assert summary.event_context == {"origin": "bootstrap"}
    assert summary.event_data["sample_account_count"] > 0
    assert summary.event_data["sample_transaction_count"] == len(container.transactions.list())


def test_domain_write_events_exclude_financial_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    accounts = InMemoryAccountRepository()
    spending = InMemorySpendingCategoryRepository()
    income = InMemoryIncomeCategoryRepository()
    transactions = InMemoryTransactionRepository()
    account_service = AccountService(
        accounts=accounts,
        transactions=transactions,
        today=lambda: date(2026, 8, 6),
        generate_account_id=lambda: "account_private",
        generate_transaction_id=lambda: "transaction_opening",
        generate_posting_id=_ids("opening-posting"),
    )
    category_service = SpendingCategoryService(
        categories=spending,
        generate_category_id=lambda: "category_private",
    )
    transaction_service = TransactionService(
        accounts=accounts,
        spending_categories=spending,
        income_categories=income,
        transactions=transactions,
        generate_transaction_id=lambda: "transaction_expense",
        generate_posting_id=_ids("expense-posting"),
    )
    caplog.set_level(logging.INFO, logger="wallet")

    with bind_log_context(trace_id="b" * 32, origin="api"):
        account = account_service.open_account(
            OpenAccount(
                name="private account marker",
                type=AccountType.CASH,
                currency="USD",
                opening_balance_minor=987_654_321,
            )
        )
        category = category_service.create_spending_category(
            CreateSpendingCategory(name="private category marker")
        )
        transaction_service.create_transaction(
            CreateTransaction(
                type=TransactionType.EXPENSE,
                description="private transaction marker",
                postings=(
                    CreatePosting(
                        account_id=account.account.id,
                        amount_minor=-123_456_789,
                        currency="USD",
                    ),
                    CreatePosting(
                        category_id=category.id,
                        amount_minor=123_456_789,
                        currency="USD",
                    ),
                ),
            )
        )

    events = [
        record.event for record in caplog.records if getattr(record, "event", None) is not None
    ]
    assert events == [
        "account.opened",
        "account.opening_balance.recorded",
        "category.created",
        "transaction.recorded",
    ]
    serialized_metadata = repr(
        [record.event_data for record in caplog.records if hasattr(record, "event_data")]
    )
    assert "private account marker" not in serialized_metadata
    assert "private category marker" not in serialized_metadata
    assert "private transaction marker" not in serialized_metadata
    assert "987654321" not in serialized_metadata
    assert "123456789" not in serialized_metadata


def _capturing_logger(name: str) -> tuple[logging.Logger, StringIO]:
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger, output


def _ids(prefix: str):  # type: ignore[no-untyped-def]
    index = 0

    def generate() -> str:
        nonlocal index
        index += 1
        return f"{prefix}-{index}"

    return generate
