from __future__ import annotations

import wallet.ai.transaction_capture as transaction_capture
import wallet.application as wallet_application
import wallet.domain as wallet_domain
import wallet.infrastructure as wallet_infrastructure
import wallet.ports as wallet_ports
from wallet.ai.transaction_capture.capability import TransactionCaptureCapability
from wallet.ai.transaction_capture.domain import TransactionCaptureState
from wallet.ai.transaction_capture.interpretation import (
    ContributionInterpreter,
    LlmContributionInterpreter,
)
from wallet.ai.transaction_capture.ports import (
    ContributionProcessor,
    ContributionProcessorFactory,
    WalletTransactionExecutor,
)
from wallet.ai.transaction_capture.processing import (
    ModelDrivenContributionProcessorFactory,
)


def test_transaction_capture_public_contract_is_exposed_from_ai_package() -> None:
    assert transaction_capture.TransactionCaptureCapability is TransactionCaptureCapability
    assert transaction_capture.TransactionCaptureState is TransactionCaptureState
    assert transaction_capture.ContributionProcessor is ContributionProcessor
    assert transaction_capture.ContributionProcessorFactory is ContributionProcessorFactory
    assert transaction_capture.ContributionInterpreter is ContributionInterpreter
    assert transaction_capture.LlmContributionInterpreter is LlmContributionInterpreter
    assert (
        transaction_capture.ModelDrivenContributionProcessorFactory
        is ModelDrivenContributionProcessorFactory
    )
    assert transaction_capture.WalletTransactionExecutor is WalletTransactionExecutor


def test_wallet_core_layers_do_not_export_transaction_capture_feature() -> None:
    assert not hasattr(wallet_domain, "TransactionCaptureState")
    assert not hasattr(wallet_application, "ConversationController")
    assert not hasattr(wallet_ports, "ContributionProcessor")
    assert not hasattr(wallet_infrastructure, "ConversationController")
