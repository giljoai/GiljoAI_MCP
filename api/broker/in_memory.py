# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

from __future__ import annotations

import asyncio
from collections.abc import Callable

from api.broker.base import BrokerHandler, WebSocketBrokerMessage, WebSocketEventBroker


class InMemoryWebSocketEventBroker(WebSocketEventBroker):
    """
    Default broker for single-process LAN/WAN deployments.

    Note: This broker is per-process and does not provide cross-worker delivery.
    """

    def __init__(self) -> None:
        self._handlers: set[BrokerHandler] = set()
        self._lock = asyncio.Lock()

    def subscribe(self, handler: BrokerHandler) -> Callable[[], None]:
        self._handlers.add(handler)

        def _unsubscribe() -> None:
            self._handlers.discard(handler)

        return _unsubscribe

    async def publish(self, message: WebSocketBrokerMessage) -> None:
        # Snapshot handlers to avoid mutation during await.
        async with self._lock:
            handlers_snapshot = list(self._handlers)

        for handler in handlers_snapshot:
            await handler(message)
