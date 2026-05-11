# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
WebSocket Event Schema Registry (re-export shim)

Canonical location: giljo_mcp.events.schemas
This module re-exports all symbols for backward compatibility with api/ consumers.

Relocated: 2026-04-18 (Sprint 003a)
"""

from giljo_mcp.events.schemas import (
    AgentCreatedData,
    AgentCreatedEvent,
    AgentSilentData,
    AgentSilentEvent,
    AgentStatusChangedData,
    AgentStatusChangedEvent,
    EventFactory,
    EventMetadata,
    MessageAcknowledgedData,
    MessageAcknowledgedEvent,
    MessageReceivedData,
    MessageReceivedEvent,
    MessageSentData,
    MessageSentEvent,
    ProjectMissionUpdatedData,
    ProjectMissionUpdatedEvent,
    SetupAgentsDownloadedData,
    SetupAgentsDownloadedEvent,
    SetupCommandsInstalledData,
    SetupCommandsInstalledEvent,
    SetupToolConnectedData,
    SetupToolConnectedEvent,
    WebSocketEvent,
)


__all__ = [
    "AgentCreatedData",
    "AgentCreatedEvent",
    "AgentSilentData",
    "AgentSilentEvent",
    "AgentStatusChangedData",
    "AgentStatusChangedEvent",
    "EventFactory",
    "EventMetadata",
    "MessageAcknowledgedData",
    "MessageAcknowledgedEvent",
    "MessageReceivedData",
    "MessageReceivedEvent",
    "MessageSentData",
    "MessageSentEvent",
    "ProjectMissionUpdatedData",
    "ProjectMissionUpdatedEvent",
    "SetupAgentsDownloadedData",
    "SetupAgentsDownloadedEvent",
    "SetupCommandsInstalledData",
    "SetupCommandsInstalledEvent",
    "SetupToolConnectedData",
    "SetupToolConnectedEvent",
    "WebSocketEvent",
]
