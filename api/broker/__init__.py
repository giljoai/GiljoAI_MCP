# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

from __future__ import annotations

import os

from api.broker.base import WebSocketEventBroker
from api.broker.in_memory import InMemoryWebSocketEventBroker
from api.broker.postgres_notify import PostgresNotifyWebSocketEventBroker


def _normalize_dsn(database_url: str) -> str:
    # SQLAlchemy async URLs often use "postgresql+asyncpg://"; asyncpg expects "postgresql://".
    return (
        database_url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
    )


def create_websocket_event_broker(
    *,
    config: object | None = None,
    database_url: str | None = None,
) -> WebSocketEventBroker:
    """
    Factory for WebSocket event brokers.

    Broker selection priority:
    1) Env var `GILJO_WS_BROKER` / `GILJO_WEBSOCKET_BROKER`
    2) Config path `server.websocket.broker` (if ConfigManager provided)
    3) Default: `in_memory`
    """
    broker_type = os.getenv("GILJO_WS_BROKER") or os.getenv("GILJO_WEBSOCKET_BROKER")

    if not broker_type and config is not None:
        get = getattr(config, "get", None)
        if callable(get):
            broker_type = get("server.websocket.broker", None) or get("websocket.broker", None)

    broker_type = (broker_type or "in_memory").strip().lower()

    if broker_type in {"in_memory", "memory"}:
        return InMemoryWebSocketEventBroker()

    if broker_type in {"postgres_notify", "postgres", "pg_notify", "listen_notify"}:
        if not database_url:
            raise ValueError("database_url is required for postgres_notify broker")
        return PostgresNotifyWebSocketEventBroker(dsn=_normalize_dsn(database_url))

    raise ValueError(f"Unsupported WebSocket broker type: {broker_type}")


def ensure_broker_supports_worker_count(broker: WebSocketEventBroker, worker_count: int) -> None:
    """BE-3008c: refuse to boot multi-worker on a per-process broker.

    With workers > 1 an in_memory broker silently drops cross-worker events —
    including the disconnect_tenant control message that revokes live sessions on
    user deactivation (TSK-9006) — the worst-to-diagnose failure shape. Fail loud
    at startup instead.
    """
    if worker_count > 1 and isinstance(broker, InMemoryWebSocketEventBroker):
        raise RuntimeError(
            f"WebSocket broker 'in_memory' cannot serve worker_count={worker_count}: "
            "cross-worker events (realtime updates AND live-session revocation) would "
            "be silently dropped. Set GILJO_WS_BROKER=postgres_notify or run 1 worker."
        )
