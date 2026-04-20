# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Module-level service registry.

Holds references to singletons created at application startup (e.g.
the WebSocket manager) so that lower-layer code in src/giljo_mcp/
can access them without importing from api/.

Usage:
    # At startup (api/app.py lifespan or startup hooks):
    from giljo_mcp.app_registry.service_registry import set_websocket_manager
    set_websocket_manager(ws_manager)

    # At consumption (any src/giljo_mcp/ module):
    from giljo_mcp.app_registry.service_registry import get_websocket_manager
    ws = get_websocket_manager()
    if ws:
        await ws.broadcast_to_tenant(...)
"""

from typing import Any


_websocket_manager: Any | None = None


def set_websocket_manager(manager: Any) -> None:
    """Register the global WebSocket manager instance (called once at startup)."""
    global _websocket_manager  # noqa: PLW0603
    _websocket_manager = manager


def get_websocket_manager() -> Any | None:
    """Retrieve the global WebSocket manager, or None if not yet registered."""
    return _websocket_manager
