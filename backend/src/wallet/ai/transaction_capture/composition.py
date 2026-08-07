from __future__ import annotations

from wallet.ai.transaction_capture.capability import TransactionCaptureCapability
from wallet.ai.transaction_capture.ports import ContributionProcessorFactory
from wallet.ai.transaction_capture.presentation import CapturePresentation
from wallet.ai.transaction_capture.processing import ModelDrivenContributionProcessorFactory
from wallet.ai.transaction_capture.wallet_adapter import WalletCaptureAdapter
from wallet.application.transactions import TransactionService
from wallet.config import Settings
from wallet.infrastructure.ollama import OllamaStructuredChatModel
from wallet.ports.accounts import AccountRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository


def build_transaction_capture_capability(
    *,
    accounts: AccountRepository,
    spending_categories: SpendingCategoryRepository,
    income_categories: IncomeCategoryRepository,
    transactions: TransactionService,
    processor_factory: ContributionProcessorFactory,
) -> TransactionCaptureCapability:
    """Wire transaction interpretation and completion behind the capability contract."""

    wallet = WalletCaptureAdapter(
        accounts=accounts,
        spending_categories=spending_categories,
        income_categories=income_categories,
        transactions=transactions,
    )
    processor = processor_factory.build(
        references=wallet,
    )
    return TransactionCaptureCapability(
        processor=processor,
        validator=wallet,
        wallet=wallet,
        presentation=CapturePresentation(
            accounts=accounts,
            spending_categories=spending_categories,
            income_categories=income_categories,
        ),
    )


def build_default_contribution_processor_factory(
    settings: Settings,
) -> ContributionProcessorFactory:
    """Build the default model-driven transaction interpreter factory."""

    model = OllamaStructuredChatModel(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        context_length=settings.ollama_context_length,
    )
    return ModelDrivenContributionProcessorFactory(model=model)
