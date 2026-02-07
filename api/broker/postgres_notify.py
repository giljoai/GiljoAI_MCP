from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Optional

import asyncpg

from api.broker.base import BrokerHandler, WebSocketBrokerMessage, WebSocketEventBroker


logger = logging.getLogger(__name__)


class PostgresNotifyWebSocketEventBroker(WebSocketEventBroker):
    """
    PostgreSQL LISTEN/NOTIFY broker for multi-worker / multi-instance deployments.

    Baseline implementation publishes the full event payload as JSON. Keep payloads small.
    """

    def __init__(self, *, dsn: str, channel: str = "giljo_ws_events") -> None:
        self._dsn = dsn
        self._channel = channel
        self._handlers: set[BrokerHandler] = set()
        self._listen_conn: Optional[asyncpg.Connection] = None
        self._publish_pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._listen_conn or self._publish_pool:
            return

        self._listen_conn = await asyncpg.connect(self._dsn)
        self._listen_conn.add_listener(self._channel, self._on_notification)
        self._publish_pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)

    async def stop(self) -> None:
        if self._listen_conn:
            try:
                self._listen_conn.remove_listener(self._channel, self._on_notification)
            except Exception:
                logger.debug("Failed removing postgres listener", exc_info=True)
            try:
                await self._listen_conn.close()
            except Exception:
                logger.debug("Failed closing postgres listen connection", exc_info=True)
            self._listen_conn = None

        if self._publish_pool:
            try:
                await self._publish_pool.close()
            except Exception:
                logger.debug("Failed closing postgres pool", exc_info=True)
            self._publish_pool = None

    def subscribe(self, handler: BrokerHandler) -> Callable[[], None]:
        self._handlers.add(handler)

        def _unsubscribe() -> None:
            self._handlers.discard(handler)

        return _unsubscribe

    async def publish(self, message: WebSocketBrokerMessage) -> None:
        if not self._publish_pool:
            raise RuntimeError("PostgresNotifyWebSocketEventBroker is not started")

        payload = self._serialize(message)
        async with self._publish_pool.acquire() as conn:
            await conn.execute("SELECT pg_notify($1, $2)", self._channel, payload)

    @staticmethod
    def _serialize(message: WebSocketBrokerMessage) -> str:
        return json.dumps(
            {
                "tenant_key": message.tenant_key,
                "event": message.event,
                "exclude_client": message.exclude_client,
                "origin": message.origin,
            }
        )

    @staticmethod
    def _deserialize(payload: str) -> WebSocketBrokerMessage:
        decoded = json.loads(payload)
        return WebSocketBrokerMessage(
            tenant_key=decoded["tenant_key"],
            event=decoded["event"],
            exclude_client=decoded.get("exclude_client"),
            origin=decoded.get("origin"),
        )

    def _on_notification(self, _connection: asyncpg.Connection, _pid: int, _channel: str, payload: str) -> None:
        asyncio.create_task(self._handle_payload(payload))

    async def _handle_payload(self, payload: str) -> None:
        try:
            message = self._deserialize(payload)
        except Exception:
            logger.warning("Failed to deserialize broker payload", exc_info=True)
            return

        async with self._lock:
            handlers_snapshot = list(self._handlers)

        for handler in handlers_snapshot:
            try:
                await handler(message)
            except Exception:
                logger.warning("Broker handler failed", exc_info=True)
