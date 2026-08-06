from __future__ import annotations

from datetime import date
from uuid import uuid4

from wallet.ai.transaction_capture.ports import CaptureIdGenerator, ContributionProcessorFactory
from wallet.ai.transaction_capture.processing import PhasedContributionProcessorFactory
from wallet.ai.transaction_capture.wallet_adapter import WalletCaptureAdapter
from wallet.ai.transaction_capture.workflow import CaptureWorkflow
from wallet.application.transactions import TransactionService
from wallet.config import Settings
from wallet.infrastructure.ollama import OllamaStructuredChatModel
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository
from wallet.ports.system import DateProvider


def build_capture_workflow(
    *,
    accounts: AccountRepository,
    spending_categories: SpendingCategoryRepository,
    income_categories: IncomeCategoryRepository,
    transactions: TransactionService,
    processor_factory: ContributionProcessorFactory,
    today: DateProvider | None = None,
    generate_capture_id: CaptureIdGenerator | None = None,
) -> CaptureWorkflow:
    """Wire capture interpretation, deterministic validation, and transaction creation."""

    resolved_today = today or date.today
    resolved_capture_id = generate_capture_id or _new_capture_id
    wallet = WalletCaptureAdapter(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
    )
    processor = processor_factory.build(
        references=wallet,
    )
    return CaptureWorkflow(
        processor=processor,
        validator=wallet,
        wallet=wallet,
        today=resolved_today,
        generate_capture_id=resolved_capture_id,
    )


def build_default_contribution_processor_factory(
    settings: Settings,
) -> ContributionProcessorFactory:
    """Build the default deterministic-first, Ollama-backed processor factory."""

    model = OllamaStructuredChatModel(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    return PhasedContributionProcessorFactory(
        extraction_model=model,
        semantic_model=model,
    )


def _new_capture_id() -> str:
    return f"capture_{uuid4().hex}"
