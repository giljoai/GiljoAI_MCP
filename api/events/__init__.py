"""
WebSocket Events Module

Provides standardized event schemas and factory methods for WebSocket
communications in GiljoAI MCP.

Handover 0086A: Production-Grade Stage Project Architecture
Task 1.4: Create Standardized Event Schemas
Created: 2025-11-02
"""

from api.events.schemas import (
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
