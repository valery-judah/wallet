from __future__ import annotations

from uuid import uuid4

from wallet.ai.control.capability_registry import CapabilityRegistry
from wallet.ai.control.controller import ConversationController
from wallet.ai.control.coordination import TurnExecutionCoordinator
from wallet.ai.control.engine import ConversationEngine
from wallet.ai.control.registry import ConversationRegistry, TurnReplayRegistry
from wallet.ai.control.resolution import TurnResolver
from wallet.ai.control.routing import LlmMessageRouter, MessageRouter
from wallet.ai.transaction_capture.capability import TransactionCaptureCapability
from wallet.ai.wallet_state.capability import CurrentWalletStateCapability
from wallet.config import Settings
from wallet.infrastructure.ollama import OllamaStructuredChatModel


def build_conversation_controller(
    transaction_capture: TransactionCaptureCapability,
    current_wallet_state: CurrentWalletStateCapability,
    message_router: MessageRouter,
) -> ConversationController:
    capabilities = CapabilityRegistry(
        (
            transaction_capture,
            current_wallet_state,
        )
    )
    engine = ConversationEngine(
        capabilities=capabilities,
        resolver=TurnResolver(router=message_router),
        generate_task_id=lambda: f"task_{uuid4().hex}",
    )
    coordinator = TurnExecutionCoordinator(
        conversations=ConversationRegistry(),
        turn_replays=TurnReplayRegistry(),
        generate_conversation_id=lambda: f"conversation_{uuid4().hex}",
    )
    return ConversationController(engine=engine, coordinator=coordinator)


def build_default_message_router(settings: Settings) -> MessageRouter:
    """Build the authoritative Ollama-backed natural-language router."""

    return LlmMessageRouter(
        model=OllamaStructuredChatModel(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
            context_length=settings.ollama_context_length,
        )
    )
