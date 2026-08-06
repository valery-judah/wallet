from __future__ import annotations

from typing import Any, Protocol


class StructuredChatError(RuntimeError):
    pass


class StructuredChatTransportError(StructuredChatError):
    pass


class StructuredChatResponseError(StructuredChatError):
    pass


class StructuredChatModel(Protocol):
    """Model-agnostic port for schema-constrained chat completion."""

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> str:
        """Return one structured response as JSON text."""
