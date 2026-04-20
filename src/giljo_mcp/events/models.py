# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
WebSocket Event Pydantic models.

Contains all data and event models for WebSocket communications.
The EventFactory (which constructs these models) lives in schemas.py.

Handover 0086A: Production-Grade Stage Project Architecture
Created: 2025-11-02
Split from schemas.py: 2026-04-18 (Sprint 003a, CI guardrail: 800 line limit)
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Base Event Structures
# ============================================================================


class EventMetadata(BaseModel):
    """
    Standard metadata for all WebSocket events.

    Ensures consistent structure across all event types with:
    - Event type identification
    - ISO 8601 timestamp with timezone
    - Schema version for backwards compatibility
    """

    type: str = Field(..., description="Event type (e.g., 'project:mission_updated')")
    timestamp: str = Field(..., description="ISO 8601 timestamp with timezone")
    schema_version: str = Field(default="1.0", description="Event schema version")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is valid ISO 8601 format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from e


# ============================================================================
# Project Events
# ============================================================================


class ProjectMissionUpdatedData(BaseModel):
    """Data payload for project:mission_updated event."""

    project_id: str = Field(..., description="Project UUID as string")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    mission: str = Field(..., min_length=1, description="Generated mission text")
    generated_by: Literal["orchestrator", "user"] = Field(
        default="orchestrator", description="Source of mission generation"
    )
    user_config_applied: bool = Field(default=False, description="Whether user configuration was applied")
    field_toggles: dict[str, Any] = Field(None, description="Field toggle config used in generation")


class ProjectMissionUpdatedEvent(BaseModel):
    """Complete event structure for project:mission_updated."""

    type: Literal["project:mission_updated"] = "project:mission_updated"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: ProjectMissionUpdatedData

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "project:mission_updated",
                "timestamp": "2025-11-02T10:30:00Z",
                "schema_version": "1.0",
                "data": {
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_key": "tenant_123",
                    "mission": "Implement user authentication with OAuth2",
                    "generated_by": "orchestrator",
                    "user_config_applied": True,
                    "field_toggles": {"product_core": {"toggle": True}, "git_history": {"toggle": False}},
                },
            }
        }
    }


# ============================================================================
# Agent Events
# ============================================================================


class AgentCreatedData(BaseModel):
    """Data payload for agent:created event."""

    project_id: str = Field(..., description="Project UUID as string")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    agent: dict[str, Any] = Field(..., description="Complete agent job data")

    @field_validator("agent")
    @classmethod
    def validate_agent_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate agent data contains minimum required fields."""
        required_fields = ["id", "agent_display_name", "status"]
        missing = [f for f in required_fields if f not in v]
        if missing:
            raise ValueError(f"Agent data missing required fields: {missing}")
        return v


class AgentCreatedEvent(BaseModel):
    """Complete event structure for agent:created."""

    type: Literal["agent:created"] = "agent:created"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: AgentCreatedData

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "agent:created",
                "timestamp": "2025-11-02T10:31:00Z",
                "schema_version": "1.0",
                "data": {
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_key": "tenant_123",
                    "agent": {
                        "id": "660e8400-e29b-41d4-a716-446655440000",
                        "agent_display_name": "orchestrator",
                        "status": "pending",
                        "mission": "Coordinate project implementation",
                        "mode": "claude",
                    },
                },
            }
        }
    }


class AgentStatusChangedData(BaseModel):
    """Data payload for agent:status_changed event."""

    job_id: str = Field(..., description="Agent job UUID as string")
    project_id: str | None = Field(None, description="Project UUID if applicable")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    old_status: str = Field(..., min_length=1, description="Previous status")
    status: str = Field(..., min_length=1, description="New status")
    agent_display_name: str = Field(..., min_length=1, description="Human-readable display name for UI")
    duration_seconds: float | None = Field(None, ge=0, description="Job duration for completed/failed status")

    @field_validator("status")
    @classmethod
    def validate_status_transition(cls, v: str, info) -> str:
        """Validate status is a known agent status value."""
        valid_statuses = {"waiting", "working", "blocked", "complete", "silent", "decommissioned", "idle", "sleeping"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid agent status: {v}. Must be one of {valid_statuses}")
        return v


class AgentStatusChangedEvent(BaseModel):
    """Complete event structure for agent:status_changed."""

    type: Literal["agent:status_changed"] = "agent:status_changed"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: AgentStatusChangedData

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "agent:status_changed",
                "timestamp": "2025-11-02T10:32:00Z",
                "schema_version": "1.0",
                "data": {
                    "job_id": "660e8400-e29b-41d4-a716-446655440000",
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant_key": "tenant_123",
                    "old_status": "pending",
                    "status": "active",
                    "agent_display_name": "orchestrator",
                    "duration_seconds": None,
                },
            }
        }
    }


class AgentSilentData(BaseModel):
    """Data payload for agent:silent event."""

    job_id: str = Field(..., description="Agent job UUID as string")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    agent_display_name: str = Field(..., min_length=1, description="Human-readable display name for UI")
    reason: str = Field(..., min_length=1, description="Reason for silence detection")
    project_id: str | None = Field(None, description="Project UUID if applicable")
    project_name: str | None = Field(None, description="Project name for display")
    execution_id: str | None = Field(None, description="Agent execution UUID")


class AgentSilentEvent(BaseModel):
    """Complete event structure for agent:silent."""

    type: Literal["agent:silent"] = "agent:silent"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: AgentSilentData

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "agent:silent",
                "timestamp": "2025-11-02T10:32:00Z",
                "schema_version": "1.0",
                "data": {
                    "job_id": "660e8400-e29b-41d4-a716-446655440000",
                    "tenant_key": "tenant_123",
                    "agent_display_name": "implementor",
                    "reason": "Agent stopped communicating",
                    "project_id": "550e8400-e29b-41d4-a716-446655440000",
                    "project_name": "My Project",
                    "execution_id": "770e8400-e29b-41d4-a716-446655440000",
                },
            }
        }
    }


# ============================================================================
# Message Events
# ============================================================================


class MessageSentData(BaseModel):
    """Data payload for message:sent event."""

    message_id: str = Field(..., description="Unique message identifier")
    job_id: str = Field(..., description="Sender agent job UUID")
    project_id: str = Field(..., description="Project UUID as string")
    from_agent: str | None = Field(default=None, description="Sender display label")
    to_agent: str | None = Field(default=None, description="Recipient display label")
    message_type: str = Field(..., description="Message type (task, info, error, etc.)")
    message: str = Field(default="", description="Message preview")
    content: str = Field(default="", description="Message preview")
    content_preview: str = Field(default="", description="Message preview")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    sender_sent_count: int | None = Field(default=None, description="Sender's total messages sent count")
    recipient_waiting_count: int | None = Field(default=None, description="Recipient's messages waiting count")
    priority: int = Field(default=1, ge=0, le=2, description="Message priority (0-2)")
    timestamp: str = Field(..., description="Message timestamp (ISO 8601)")
    from_job_id: str = Field(..., description="Sender agent job ID")
    to_job_ids: list[str] = Field(default_factory=list, description="Recipient agent job IDs")


class MessageSentEvent(BaseModel):
    """Complete event structure for message:sent."""

    type: Literal["message:sent"] = "message:sent"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: MessageSentData


class MessageReceivedData(BaseModel):
    """Data payload for message:received event."""

    message_id: str = Field(..., description="Unique message identifier")
    job_id: str = Field(..., description="Sender agent job UUID")
    project_id: str = Field(..., description="Project UUID as string")
    from_agent: str | None = Field(default=None, description="Sender display label")
    to_agent_ids: list[str] = Field(default_factory=list, description="Recipient agent IDs")
    message_type: str = Field(..., description="Message type (task, info, error, etc.)")
    message: str = Field(default="", description="Message preview")
    content: str = Field(default="", description="Message preview")
    content_preview: str = Field(default="", description="Message preview")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    waiting_count: int | None = Field(default=None, description="Recipient's messages waiting count")
    priority: int = Field(default=1, ge=0, le=2, description="Message priority (0-2)")
    timestamp: str = Field(..., description="Message timestamp (ISO 8601)")
    from_job_id: str = Field(..., description="Sender agent job ID")
    to_job_ids: list[str] = Field(default_factory=list, description="Recipient agent job IDs")


class MessageReceivedEvent(BaseModel):
    """Complete event structure for message:received."""

    type: Literal["message:received"] = "message:received"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: MessageReceivedData


class MessageAcknowledgedData(BaseModel):
    """Data payload for message:acknowledged event."""

    message_id: str = Field(..., description="Primary message identifier")
    message_ids: list[str] = Field(default_factory=list, description="All acknowledged message IDs")
    agent_id: str = Field(..., description="Acknowledging agent job ID (legacy)")
    project_id: str = Field(..., description="Project UUID as string")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    timestamp: str = Field(..., description="Acknowledgment timestamp (ISO 8601)")
    from_job_id: str = Field(..., description="Acknowledging agent job ID")
    to_job_ids: list[str] = Field(default_factory=list, description="Target agent job IDs")
    waiting_count: int | None = Field(default=None, description="Acknowledging agent's messages waiting count")
    read_count: int | None = Field(default=None, description="Acknowledging agent's messages read count")


class MessageAcknowledgedEvent(BaseModel):
    """Complete event structure for message:acknowledged."""

    type: Literal["message:acknowledged"] = "message:acknowledged"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: MessageAcknowledgedData


# ============================================================================
# Setup Wizard Events
# ============================================================================


class SetupToolConnectedData(BaseModel):
    """Data payload for setup:tool_connected event."""

    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    user_id: str = Field(..., min_length=1, description="User identifier")
    tool_name: str = Field(..., min_length=1, description="AI tool name (claude_code, codex_cli, gemini_cli)")
    connected_at: str = Field(..., description="ISO 8601 timestamp of connection")


class SetupToolConnectedEvent(BaseModel):
    """Complete event structure for setup:tool_connected."""

    type: Literal["setup:tool_connected"] = "setup:tool_connected"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: SetupToolConnectedData


class SetupCommandsInstalledData(BaseModel):
    """Data payload for setup:commands_installed event."""

    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    user_id: str = Field(..., min_length=1, description="User identifier")
    tool_name: str = Field(..., min_length=1, description="AI tool name")
    command_count: int = Field(..., ge=0, description="Number of commands installed")


class SetupCommandsInstalledEvent(BaseModel):
    """Complete event structure for setup:commands_installed."""

    type: Literal["setup:commands_installed"] = "setup:commands_installed"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: SetupCommandsInstalledData


class SetupAgentsDownloadedData(BaseModel):
    """Data payload for setup:agents_downloaded event."""

    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    user_id: str = Field(..., min_length=1, description="User identifier")
    agent_count: int = Field(..., ge=0, description="Number of agent templates downloaded")


class SetupAgentsDownloadedEvent(BaseModel):
    """Complete event structure for setup:agents_downloaded."""

    type: Literal["setup:agents_downloaded"] = "setup:agents_downloaded"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    schema_version: str = Field(default="1.0", description="Event schema version")
    data: SetupAgentsDownloadedData


# ============================================================================
# Event Type Union
# ============================================================================

WebSocketEvent = (
    ProjectMissionUpdatedEvent
    | AgentCreatedEvent
    | AgentStatusChangedEvent
    | AgentSilentEvent
    | MessageSentEvent
    | MessageReceivedEvent
    | MessageAcknowledgedEvent
    | SetupToolConnectedEvent
    | SetupCommandsInstalledEvent
    | SetupAgentsDownloadedEvent
)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "AgentCreatedData",
    "AgentCreatedEvent",
    "AgentSilentData",
    "AgentSilentEvent",
    "AgentStatusChangedData",
    "AgentStatusChangedEvent",
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
