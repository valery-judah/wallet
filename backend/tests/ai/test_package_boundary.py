from __future__ import annotations

import wallet.ai.transaction_capture as transaction_capture
import wallet.application as wallet_application
import wallet.domain as wallet_domain
import wallet.infrastructure as wallet_infrastructure
import wallet.ports as wallet_ports
from wallet.ai.transaction_capture.domain import CaptureSession
from wallet.ai.transaction_capture.extraction import (
    ContributionExtractor,
    LlmContributionExtractor,
)
from wallet.ai.transaction_capture.ports import (
    CaptureIdGenerator,
    ContributionProcessor,
    ContributionProcessorFactory,
    WalletTransactionExecutor,
)
from wallet.ai.transaction_capture.processing import (
    DeterministicPendingAnswerHandler,
    PhasedContributionProcessorFactory,
)
from wallet.ai.transaction_capture.semantic import (
    LlmContributionSemanticInterpreter,
    SemanticCandidateContext,
    SemanticPendingInteraction,
    SemanticReferenceState,
    SemanticReferenceValue,
    SemanticReferenceVocabulary,
)
from wallet.ai.transaction_capture.workflow import CaptureWorkflow


def test_transaction_capture_public_contract_is_exposed_from_ai_package() -> None:
    assert transaction_capture.CaptureWorkflow is CaptureWorkflow
    assert transaction_capture.CaptureSession is CaptureSession
    assert transaction_capture.CaptureIdGenerator is CaptureIdGenerator
    assert transaction_capture.ContributionProcessor is ContributionProcessor
    assert transaction_capture.ContributionProcessorFactory is ContributionProcessorFactory
    assert transaction_capture.ContributionExtractor is ContributionExtractor
    assert (
        transaction_capture.DeterministicPendingAnswerHandler is DeterministicPendingAnswerHandler
    )
    assert transaction_capture.LlmContributionExtractor is LlmContributionExtractor
    assert (
        transaction_capture.LlmContributionSemanticInterpreter is LlmContributionSemanticInterpreter
    )
    assert (
        transaction_capture.PhasedContributionProcessorFactory is PhasedContributionProcessorFactory
    )
    assert transaction_capture.WalletTransactionExecutor is WalletTransactionExecutor
    assert transaction_capture.SemanticCandidateContext is SemanticCandidateContext
    assert transaction_capture.SemanticPendingInteraction is SemanticPendingInteraction
    assert transaction_capture.SemanticReferenceState is SemanticReferenceState
    assert transaction_capture.SemanticReferenceValue is SemanticReferenceValue
    assert transaction_capture.SemanticReferenceVocabulary is SemanticReferenceVocabulary


def test_wallet_core_layers_do_not_export_transaction_capture_feature() -> None:
    assert not hasattr(wallet_domain, "CaptureSession")
    assert not hasattr(wallet_application, "CaptureWorkflow")
    assert not hasattr(wallet_ports, "ContributionProcessor")
    assert not hasattr(wallet_infrastructure, "CaptureWorkflow")
