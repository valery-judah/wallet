from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from wallet.ai.capabilities.contract import Capability, CapabilityDefinition


class CapabilityRegistry:
    def __init__(self, handlers: tuple[Capability[Any], ...]) -> None:
        capabilities: dict[str, Capability[Any]] = {}
        for handler in handlers:
            capability_id = handler.definition.id
            if capability_id in capabilities:
                raise ValueError(f"duplicate capability id: {capability_id}")
            capabilities[capability_id] = handler
        if not capabilities:
            raise ValueError("capability registry cannot be empty")
        self._handlers: Mapping[str, Capability[Any]] = MappingProxyType(capabilities)

    @property
    def definitions(self) -> tuple[CapabilityDefinition, ...]:
        return tuple(handler.definition for handler in self._handlers.values())

    def contains(self, capability_id: str) -> bool:
        return capability_id in self._handlers

    def get(self, capability_id: str) -> Capability[Any]:
        try:
            return self._handlers[capability_id]
        except KeyError as exc:
            raise KeyError(f"unregistered capability: {capability_id}") from exc
