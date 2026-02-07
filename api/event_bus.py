"""
Event Bus for MCP Context to WebSocket Bridge

Simple in-memory event bus pattern that decouples MCP tools from WebSocket infrastructure.
Enables WebSocket broadcasts from MCP tool context where app.state is unavailable.

Pattern: Publish-Subscribe with async handlers
Thread-safe: Uses asyncio primitives
Scope: Application-wide singleton

Handover 0111 Issue #1: WebSocket Event Bus for MCP Context
Created: 2025-11-06
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List


logger = logging.getLogger(__name__)


class EventBus:
    """
    Simple in-memory event bus for decoupling MCP tools from WebSocket broadcasts.

    Design Goals:
    - Decouple MCP tools from FastAPI application state
    - Enable async event handling with multiple listeners
    - Provide production-grade reliability and error handling
    - Maintain multi-tenant isolation at listener level

    Usage:
        # Publish event (from MCP tool context)
        await event_bus.publish("project:mission_updated", {
            "tenant_key": "tenant_123",
            "project_id": "proj_456",
            "mission": "Updated mission text"
        })

        # Subscribe to events (at application startup)
        async def handle_mission_update(data: Dict):
            await ws_manager.broadcast_to_tenant(...)

        await event_bus.subscribe("project:mission_updated", handle_mission_update)
    """

    def __init__(self):
        """Initialize event bus with empty listener registry."""
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._event_counts: Dict[str, int] = {}

    async def publish(self, event_type: str, data: Dict[str, Any]) -> int:
        """
        Publish event to all registered listeners.

        Args:
            event_type: Event type (e.g., "project:mission_updated")
            data: Event payload dictionary (must include tenant_key for isolation)

        Returns:
            Number of handlers that successfully processed the event
        """
        if not event_type:
            raise ValueError("event_type cannot be empty")

        if not isinstance(data, dict):
            raise ValueError("data must be a dictionary")

        async with self._lock:
            listeners = self._listeners.get(event_type, []).copy()

        if not listeners:
            self.logger.debug(
                f"No listeners registered for event type: {event_type}",
                extra={"event_type": event_type, "data_keys": list(data.keys())},
            )
            return 0

        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1

        success_count = 0
        failed_count = 0

        self.logger.info(
            f"Publishing event: {event_type} to {len(listeners)} listener(s)",
            extra={
                "event_type": event_type,
                "listener_count": len(listeners),
                "tenant_key": data.get("tenant_key"),
            },
        )

        for handler in listeners:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, handler, data)

                success_count += 1

            except Exception as e:
                failed_count += 1
                self.logger.error(
                    f"Event handler failed for {event_type}: {e}",
                    extra={
                        "event_type": event_type,
                        "handler": handler.__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )

        self.logger.info(
            f"Event dispatched: {event_type} ({success_count} success, {failed_count} failed)",
            extra={
                "event_type": event_type,
                "success_count": success_count,
                "failed_count": failed_count,
            },
        )

        return success_count

    async def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Register async handler for event type.

        Args:
            event_type: Event type to listen for
            handler: Callable that receives event data dict
        """
        if not event_type:
            raise ValueError("event_type cannot be empty")

        if not callable(handler):
            raise ValueError("handler must be callable")

        async with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []

            if handler not in self._listeners[event_type]:
                self._listeners[event_type].append(handler)

                self.logger.info(
                    f"Registered handler for event: {event_type}",
                    extra={
                        "event_type": event_type,
                        "handler": handler.__name__,
                        "total_handlers": len(self._listeners[event_type]),
                    },
                )

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """Remove handler from event type."""
        if not event_type or event_type not in self._listeners:
            return False

        if handler in self._listeners[event_type]:
            self._listeners[event_type].remove(handler)
            self.logger.info(
                f"Unregistered handler for event: {event_type}",
                extra={
                    "event_type": event_type,
                    "handler": handler.__name__,
                },
            )
            return True

        return False

    def get_listener_count(self, event_type: str = None) -> int:
        """Get count of registered listeners."""
        if event_type:
            return len(self._listeners.get(event_type, []))
        return sum(len(handlers) for handlers in self._listeners.values())

    def clear(self) -> None:
        """Clear all listeners (for testing)."""
        self._listeners.clear()
        self._event_counts.clear()
        self.logger.info("Event bus cleared")
