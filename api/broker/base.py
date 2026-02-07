from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class WebSocketBrokerMessage:
    tenant_key: str
    event: dict[str, Any]
    exclude_client: Optional[str] = None
    origin: Optional[str] = None


BrokerHandler = Callable[[WebSocketBrokerMessage], Awaitable[None]]


class WebSocketEventBroker(ABC):
    """Cross-worker broker for tenant-scoped WebSocket events."""

    async def start(self) -> None:  # pragma: no cover
        return None

    async def stop(self) -> None:  # pragma: no cover
        return None

    @abstractmethod
    def subscribe(self, handler: BrokerHandler) -> Callable[[], None]:
        raise NotImplementedError

    @abstractmethod
    async def publish(self, message: WebSocketBrokerMessage) -> None:
        raise NotImplementedError
