"""
Handover 0379e: SaaS Broker (Pub/Sub) + Loopback Elimination

These tests enforce the broker abstraction and its integration with the WebSocketManager:
- InMemory broker delivers published events to subscribers
- When a broker is attached, broadcasts fan out without duplicates
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


pytestmark = pytest.mark.asyncio


async def test_in_memory_broker_publish_subscribe_delivers_event():
    from api.broker.base import WebSocketBrokerMessage
    from api.broker.in_memory import InMemoryWebSocketEventBroker

    broker = InMemoryWebSocketEventBroker()
    await broker.start()

    handler = AsyncMock()
    broker.subscribe(handler)

    message = WebSocketBrokerMessage(
        tenant_key="tenant-a",
        event={
            "type": "project:mission_updated",
            "timestamp": "2025-01-01T00:00:00Z",
            "schema_version": "1.0",
            "data": {"tenant_key": "tenant-a", "project_id": "p1", "mission": "hello"},
        },
    )

    await broker.publish(message)

    handler.assert_awaited_once()
    delivered = handler.call_args.args[0]
    assert delivered.tenant_key == "tenant-a"
    assert delivered.event["type"] == "project:mission_updated"


async def test_websocket_manager_broker_fanout_without_duplicates():
    """
    Simulate multi-worker deployment:
    - worker A broadcasts locally AND publishes to broker
    - worker B receives broker event and broadcasts to its local sockets
    - worker A does NOT re-broadcast its own broker message (no duplicates)
    """
    from api.broker.in_memory import InMemoryWebSocketEventBroker
    from api.websocket import WebSocketManager

    broker = InMemoryWebSocketEventBroker()
    await broker.start()

    ws_a = WebSocketManager()
    ws_b = WebSocketManager()

    ws_a.attach_broker(broker)
    ws_b.attach_broker(broker)

    tenant_key = "tenant-1"

    ws_a_socket = SimpleNamespace(send_json=AsyncMock())
    ws_a.active_connections["client-a"] = ws_a_socket
    ws_a.auth_contexts["client-a"] = {"tenant_key": tenant_key}

    ws_b_socket = SimpleNamespace(send_json=AsyncMock())
    ws_b.active_connections["client-b"] = ws_b_socket
    ws_b.auth_contexts["client-b"] = {"tenant_key": tenant_key}

    await ws_a.broadcast_to_tenant(
        tenant_key=tenant_key,
        event_type="project:mission_updated",
        data={"project_id": "proj-1", "mission": "hello"},
    )

    assert ws_a_socket.send_json.await_count == 1
    assert ws_b_socket.send_json.await_count == 1
