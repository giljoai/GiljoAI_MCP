# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Protocol interfaces for dependency inversion between layers."""

from giljo_mcp.protocols.websocket import WebSocketBroadcaster


__all__ = [
    "WebSocketBroadcaster",
]
