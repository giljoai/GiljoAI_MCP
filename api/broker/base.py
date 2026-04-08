# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class WebSocketBrokerMessage:
    tenant_key: str
    event: dict[str, Any]
    exclude_client: str | None = None
    origin: str | None = None


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
