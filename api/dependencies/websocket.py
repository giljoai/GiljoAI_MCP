# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
WebSocket Manager Dependency Injection for FastAPI.

Provides clean, testable access to WebSocket manager in FastAPI endpoints.
Ensures graceful degradation when WebSocket is unavailable.

Handover 0086A: Production-Grade Stage Project Architecture
Created: 2025-11-02
"""

import logging
from typing import Any

from fastapi import Depends, Request

from api.websocket import WebSocketManager

logger = logging.getLogger(__name__)


async def get_websocket_manager(request: Request) -> WebSocketManager | None:
    """
    Dependency that provides WebSocket manager instance.

    Returns None if WebSocket not initialized (graceful degradation).
    This allows endpoints to continue functioning even if WebSocket
    functionality is temporarily unavailable.

    Usage in endpoint:
        @router.post("/example")
        async def example(
            ws_manager: WebSocketManager = Depends(get_websocket_manager)
        ):
            if ws_manager:
                await ws_manager.broadcast_to_tenant(...)

    Returns:
        WebSocketManager instance or None if unavailable
    """
    # Check for WebSocket manager in app state
    ws_manager = getattr(request.app.state, "websocket_manager", None)

    if ws_manager is None:
        logger.debug(
            "WebSocket manager not available in app state",
            extra={"endpoint": request.url.path, "method": request.method},
        )

    return ws_manager


class WebSocketDependency:
    """
    Injectable WebSocket manager with helper methods.

    Provides tenant-aware broadcasting with proper error handling,
    multi-tenant isolation, and structured logging.

    This class wraps the WebSocket manager to provide a cleaner
    interface for FastAPI endpoints with built-in safety checks.
    """

    def __init__(
        self,
        manager: WebSocketManager | None = None,
        websocket_manager: WebSocketManager | None = None,
    ):
        """
        Initialize WebSocket dependency.

        Args:
            manager: Optional WebSocket manager instance
        """
        self.manager = manager or websocket_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def broadcast_to_tenant(
        self,
        tenant_key: str,
        event_type: str,
        data: dict[str, Any],
        schema_version: str = "1.0",
        exclude_client: str | None = None,
    ) -> int:
        """
        Broadcast event to all clients in a tenant.

        Ensures multi-tenant isolation by only sending to clients
        authenticated with the specified tenant_key.

        Args:
            tenant_key: Tenant identifier (required, cannot be empty)
            event_type: Event type (e.g., "project:mission_updated")
            data: Event payload dictionary
            schema_version: Event schema version for client compatibility
            exclude_client: Optional client ID to exclude from broadcast

        Returns:
            Number of clients that successfully received the message

        Raises:
            ValueError: If tenant_key is empty or None

        Example:
            >>> ws_dep = WebSocketDependency(manager)
            >>> sent = await ws_dep.broadcast_to_tenant(
            ...     tenant_key="tenant_123",
            ...     event_type="project:mission_updated",
            ...     data={"project_id": "...", "mission": "..."}
            ... )
            >>> print(f"Sent to {sent} clients")
        """
        # Validate required parameters
        if not tenant_key:
            raise ValueError("tenant_key cannot be empty")

        if not event_type:
            raise ValueError("event_type cannot be empty")

        # If no manager available, return 0 (graceful degradation)
        if not self.manager:
            self.logger.warning(
                "WebSocket manager not available for broadcast",
                extra={"tenant_key": tenant_key, "event_type": event_type},
            )
            return 0

        return await self.manager.broadcast_to_tenant(
            tenant_key=tenant_key,
            event_type=event_type,
            data=data,
            schema_version=schema_version,
            exclude_client=exclude_client,
        )

    def is_available(self) -> bool:
        """
        Check if WebSocket functionality is available.

        Returns:
            True if WebSocket manager is initialized and ready
        """
        return self.manager is not None


async def get_websocket_dependency(
    manager: WebSocketManager | None = Depends(get_websocket_manager),
) -> WebSocketDependency:
    """
    FastAPI dependency that provides WebSocketDependency instance.

    This is the primary dependency to use in endpoints that need
    WebSocket broadcasting capabilities.

    Usage:
        @router.post("/api/example")
        async def example(
            ws: WebSocketDependency = Depends(get_websocket_dependency)
        ):
            if ws.is_available():
                await ws.broadcast_to_tenant(...)

    Args:
        manager: WebSocket manager from get_websocket_manager dependency

    Returns:
        WebSocketDependency instance (always returns, even if manager is None)
    """
    return WebSocketDependency(manager)


# Create __init__.py for the dependencies module
__all__ = ["WebSocketDependency", "get_websocket_dependency", "get_websocket_manager"]
