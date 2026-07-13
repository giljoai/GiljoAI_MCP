# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WebSocketBrokerMessage:
    tenant_key: str
    event: dict[str, Any]
    exclude_client: str | None = None
    origin: str | None = None
    # TSK-9006: control-plane discriminator carried on the SAME giljo_ws_events
    # channel (no new channel per ADR-009 tenant-scoping). None => a normal event
    # broadcast; "disconnect_tenant" => close every live socket in ``tenant_key``
    # (user deactivation must bite live sockets across workers). ``event`` is an
    # empty envelope for control messages.
    control: str | None = None


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
