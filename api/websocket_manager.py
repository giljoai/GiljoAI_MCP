# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Compatibility shim for WebSocket manager imports.

Provides ConnectionInfo used by legacy tests and re-exports WebSocketManager
from api.websocket.
"""

from dataclasses import dataclass
from typing import Any, Optional

from api.websocket import WebSocketManager

__all__ = ["ConnectionInfo", "WebSocketManager"]


@dataclass
class ConnectionInfo:
    websocket: Any
    user_id: Optional[str]
    tenant_key: str
    username: Optional[str] = None

    async def send_json(self, data: dict):
        """Delegate send_json to underlying websocket for compatibility."""
        if not hasattr(self.websocket, "send_json"):
            raise RuntimeError("Underlying websocket does not support send_json")
        return await self.websocket.send_json(data)
