"""
Tests for Event Bus and WebSocket Event Listener

Tests the EventBus pattern for decoupling MCP tools from WebSocket infrastructure.

Handover 0111 Issue #1: WebSocket Event Bus for MCP Context
Created: 2025-11-06
"""

import asyncio
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.event_bus import EventBus
from api.websocket_event_listener import WebSocketEventListener


class TestEventBus:
    """Test EventBus publish/subscribe functionality."""

    @pytest.mark.asyncio
    async def test_event_bus_publish_subscribe(self):
        """Test basic publish/subscribe pattern."""
        event_bus = EventBus()
        received_events: List[Dict] = []

        async def handler(data: Dict):
            received_events.append(data)

        await event_bus.subscribe("test:event", handler)
        sent = await event_bus.publish("test:event", {"message": "hello"})

        assert sent == 1
        assert len(received_events) == 1
        assert received_events[0]["message"] == "hello"

    @pytest.mark.asyncio
    async def test_event_bus_multiple_listeners(self):
        """Test multiple handlers for same event."""
        event_bus = EventBus()
        received_1: List[Dict] = []
        received_2: List[Dict] = []

        async def handler_1(data: Dict):
            received_1.append(data)

        async def handler_2(data: Dict):
            received_2.append(data)

        await event_bus.subscribe("test:event", handler_1)
        await event_bus.subscribe("test:event", handler_2)
        sent = await event_bus.publish("test:event", {"message": "broadcast"})

        assert sent == 2
        assert len(received_1) == 1
        assert len(received_2) == 1

    @pytest.mark.asyncio
    async def test_event_bus_no_listeners(self):
        """Test publishing to event with no listeners."""
        event_bus = EventBus()
        sent = await event_bus.publish("unknown:event", {"test": True})
        assert sent == 0

    @pytest.mark.asyncio
    async def test_event_bus_unsubscribe(self):
        """Test unsubscribing from events."""
        event_bus = EventBus()
        received_events: List[Dict] = []

        async def handler(data: Dict):
            received_events.append(data)

        await event_bus.subscribe("test:event", handler)
        await event_bus.publish("test:event", {"message": "first"})
        assert len(received_events) == 1

        removed = event_bus.unsubscribe("test:event", handler)
        assert removed is True

        await event_bus.publish("test:event", {"message": "second"})
        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_event_bus_error_handling(self):
        """Test that handler errors don't break event bus."""
        event_bus = EventBus()
        received_good: List[Dict] = []

        async def bad_handler(data: Dict):
            raise RuntimeError("Handler error")

        async def good_handler(data: Dict):
            received_good.append(data)

        await event_bus.subscribe("test:event", bad_handler)
        await event_bus.subscribe("test:event", good_handler)
        sent = await event_bus.publish("test:event", {"test": True})

        assert sent == 1
        assert len(received_good) == 1

    @pytest.mark.asyncio
    async def test_event_bus_validation(self):
        """Test input validation."""
        event_bus = EventBus()

        with pytest.raises(ValueError, match="event_type cannot be empty"):
            await event_bus.publish("", {"test": True})

        with pytest.raises(ValueError, match="data must be a dictionary"):
            await event_bus.publish("test:event", "not a dict")


class TestWebSocketEventListener:
    """Test WebSocketEventListener functionality."""

    @pytest.mark.asyncio
    async def test_websocket_listener_mission_updated(self):
        """Test mission update event broadcast."""
        event_bus = EventBus()
        ws_manager = MagicMock()
        ws_manager.broadcast_event_to_tenant = AsyncMock(return_value=1)

        listener = WebSocketEventListener(event_bus, ws_manager)
        await listener.start()

        await event_bus.publish("project:mission_updated", {
            "tenant_key": "tenant_123",
            "project_id": "proj_456",
            "mission": "Updated mission",
            "user_config_applied": True,
            "token_estimate": 500,
        })

        await asyncio.sleep(0.01)

        ws_manager.broadcast_event_to_tenant.assert_awaited_once()
        call_kwargs = ws_manager.broadcast_event_to_tenant.call_args.kwargs
        assert call_kwargs["tenant_key"] == "tenant_123"
        assert call_kwargs["event"]["type"] == "project:mission_updated"
        assert call_kwargs["event"]["data"]["project_id"] == "proj_456"

    @pytest.mark.asyncio
    async def test_websocket_listener_agent_created(self):
        """Test agent creation event broadcast."""
        event_bus = EventBus()
        ws_manager = MagicMock()
        ws_manager.broadcast_event_to_tenant = AsyncMock(return_value=1)

        listener = WebSocketEventListener(event_bus, ws_manager)
        await listener.start()

        await event_bus.publish("agent:created", {
            "tenant_key": "tenant_123",
            "project_id": "proj_456",
            "agent_id": "agent_789",
            "agent_type": "implementer",
            "agent_name": "Backend Implementer",
            "status": "pending",
        })

        await asyncio.sleep(0.01)

        ws_manager.broadcast_event_to_tenant.assert_awaited_once()
        call_kwargs = ws_manager.broadcast_event_to_tenant.call_args.kwargs
        assert call_kwargs["tenant_key"] == "tenant_123"
        assert call_kwargs["event"]["type"] == "agent:created"
        assert call_kwargs["event"]["data"]["agent"]["id"] == "agent_789"

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self):
        """Test that events are isolated by tenant."""
        event_bus = EventBus()
        ws_manager = MagicMock()
        ws_manager.broadcast_event_to_tenant = AsyncMock(return_value=1)

        listener = WebSocketEventListener(event_bus, ws_manager)
        await listener.start()

        await event_bus.publish("project:mission_updated", {
            "tenant_key": "tenant_A",
            "project_id": "proj_1",
            "mission": "Mission A",
            "user_config_applied": False,
            "token_estimate": 100,
        })

        await asyncio.sleep(0.01)

        ws_manager.broadcast_event_to_tenant.assert_awaited_once()
        call_kwargs = ws_manager.broadcast_event_to_tenant.call_args.kwargs
        assert call_kwargs["tenant_key"] == "tenant_A"
        assert call_kwargs["event"]["type"] == "project:mission_updated"
