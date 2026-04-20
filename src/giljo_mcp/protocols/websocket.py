# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
WebSocket broadcaster protocol.

Defines the interface that src/giljo_mcp/ code (e.g. AgentHealthMonitor)
needs from the WebSocket layer.  The concrete implementation lives in
api/websocket.WebSocketManager and satisfies this protocol implicitly
(structural subtyping).

Created: 2026-04-18 (Sprint 003a) to break the backward import from
src/giljo_mcp/monitoring/agent_health_monitor.py into api/websocket.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WebSocketBroadcaster(Protocol):
    """Minimal broadcast interface consumed by lower-layer monitoring code."""

    async def broadcast_agent_auto_failed(
        self,
        tenant_key: str,
        job_id: str,
        agent_display_name: str,
        reason: str,
    ) -> None: ...

    async def broadcast_health_alert(
        self,
        tenant_key: str,
        job_id: str,
        agent_display_name: str,
        health_status: Any,
    ) -> None: ...
