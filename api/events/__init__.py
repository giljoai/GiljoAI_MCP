# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
WebSocket Events Module (re-export shim)

Canonical location: giljo_mcp.events
This module re-exports core symbols for backward compatibility with api/ consumers.

Relocated: 2026-04-18 (Sprint 003a)
"""

from giljo_mcp.events.schemas import (
    AgentCreatedData,
    AgentCreatedEvent,
    AgentStatusChangedData,
    AgentStatusChangedEvent,
    EventFactory,
    EventMetadata,
    ProjectMissionUpdatedData,
    ProjectMissionUpdatedEvent,
    WebSocketEvent,
)


__all__ = [
    "AgentCreatedData",
    "AgentCreatedEvent",
    "AgentStatusChangedData",
    "AgentStatusChangedEvent",
    # Factory
    "EventFactory",
    # Metadata
    "EventMetadata",
    "ProjectMissionUpdatedData",
    # Event Models
    "ProjectMissionUpdatedEvent",
    # Type Unions
    "WebSocketEvent",
]
