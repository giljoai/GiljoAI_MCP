# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Protocol interfaces for dependency inversion between layers."""

from giljo_mcp.protocols.websocket import WebSocketBroadcaster


__all__ = [
    "WebSocketBroadcaster",
]
