# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
WebSocket Event Factory and schema re-exports.

The Pydantic event models live in giljo_mcp.events.models (split for the
800-line CI guardrail).  This module owns the EventFactory and re-exports
every symbol so that ``from giljo_mcp.events.schemas import EventFactory``
continues to work as the canonical import path.

Handover 0086A: Production-Grade Stage Project Architecture
Task 1.4: Create Standardized Event Schemas
Created: 2025-11-02
Relocated from api/events/schemas.py: 2026-04-18 (Sprint 003a)
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from giljo_mcp.events.models import (
    AgentCreatedData,
    AgentCreatedEvent,
    AgentSilentData,
    AgentSilentEvent,
    AgentStatusChangedData,
    AgentStatusChangedEvent,
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


# ============================================================================
# Event Factory
# ============================================================================


class EventFactory:
    """
    Factory for creating standardized WebSocket events.

    Provides static methods for consistent event creation with:
    - Automatic timestamp generation
    - Pydantic validation
    - Type-safe event construction
    - JSON serialization ready output

    All factory methods return dict ready for JSON serialization,
    compatible with WebSocket.send_json() and FastAPI response models.
    """

    @staticmethod
    def tenant_envelope(
        event_type: str,
        tenant_key: str,
        data: dict[str, Any],
        schema_version: str = "1.0",
    ) -> dict:
        """Create a canonical tenant-scoped event envelope."""
        if not tenant_key:
            raise ValueError("tenant_key cannot be empty")

        payload = dict(data or {})
        if "tenant_key" not in payload:
            payload["tenant_key"] = tenant_key
        elif payload.get("tenant_key") != tenant_key:
            raise ValueError("data.tenant_key must match tenant_key")

        return {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "schema_version": schema_version,
            "data": payload,
        }

    @staticmethod
    def project_mission_updated(
        project_id: str | UUID,
        tenant_key: str,
        mission: str,
        generated_by: Literal["orchestrator", "user"] = "orchestrator",
        user_config_applied: bool = False,
        field_toggles: dict[str, Any] = None,
    ) -> dict:
        """Create project:mission_updated event."""
        project_id_str = str(project_id) if isinstance(project_id, UUID) else project_id

        event = ProjectMissionUpdatedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=ProjectMissionUpdatedData(
                project_id=project_id_str,
                tenant_key=tenant_key,
                mission=mission,
                generated_by=generated_by,
                user_config_applied=user_config_applied,
                field_toggles=field_toggles,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def agent_created(
        project_id: str | UUID,
        tenant_key: str,
        agent: dict[str, Any],
    ) -> dict:
        """Create agent:created event."""
        project_id_str = str(project_id) if isinstance(project_id, UUID) else project_id

        event = AgentCreatedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=AgentCreatedData(
                project_id=project_id_str,
                tenant_key=tenant_key,
                agent=agent,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def agent_status_changed(
        job_id: str | UUID,
        tenant_key: str,
        old_status: str,
        new_status: str,
        agent_display_name: str,
        project_id: str | UUID | None = None,
        duration_seconds: float | None = None,
    ) -> dict:
        """Create agent:status_changed event."""
        job_id_str = str(job_id) if isinstance(job_id, UUID) else job_id
        project_id_str = str(project_id) if project_id and isinstance(project_id, UUID) else project_id

        event = AgentStatusChangedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=AgentStatusChangedData(
                job_id=job_id_str,
                project_id=project_id_str,
                tenant_key=tenant_key,
                old_status=old_status,
                status=new_status,
                agent_display_name=agent_display_name,
                duration_seconds=duration_seconds,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def agent_silent(
        job_id: str | UUID,
        tenant_key: str,
        agent_display_name: str,
        reason: str,
        project_id: str | UUID | None = None,
        project_name: str | None = None,
        execution_id: str | None = None,
    ) -> dict:
        """Create agent:silent event."""
        job_id_str = str(job_id) if isinstance(job_id, UUID) else job_id
        project_id_str = str(project_id) if project_id and isinstance(project_id, UUID) else project_id

        event = AgentSilentEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=AgentSilentData(
                job_id=job_id_str,
                tenant_key=tenant_key,
                agent_display_name=agent_display_name,
                reason=reason,
                project_id=project_id_str,
                project_name=project_name,
                execution_id=execution_id,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def message_sent(
        message_id: str,
        project_id: str | UUID,
        tenant_key: str,
        from_job_id: str,
        to_job_ids: list[str],
        from_agent: str | None,
        to_agent: str | None,
        message_type: str,
        content_preview: str,
        priority: int,
        message_timestamp: datetime | None = None,
        sender_sent_count: int | None = None,
        recipient_waiting_count: int | None = None,
    ) -> dict:
        """Create message:sent event."""
        project_id_str = str(project_id) if isinstance(project_id, UUID) else project_id

        msg_ts = (message_timestamp or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
        preview = (content_preview or "")[:200]

        event = MessageSentEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=MessageSentData(
                message_id=message_id,
                job_id=from_job_id,
                project_id=project_id_str,
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=message_type,
                message=preview,
                content=preview,
                content_preview=preview,
                tenant_key=tenant_key,
                priority=priority,
                timestamp=msg_ts,
                from_job_id=from_job_id,
                to_job_ids=to_job_ids,
                sender_sent_count=sender_sent_count,
                recipient_waiting_count=recipient_waiting_count,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def message_received(
        message_id: str,
        project_id: str | UUID,
        tenant_key: str,
        from_job_id: str,
        to_job_ids: list[str],
        from_agent: str | None,
        to_agent_ids: list[str],
        message_type: str,
        content_preview: str,
        priority: int,
        message_timestamp: datetime | None = None,
        waiting_count: int | None = None,
    ) -> dict:
        """Create message:received event."""
        project_id_str = str(project_id) if isinstance(project_id, UUID) else project_id

        msg_ts = (message_timestamp or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")
        preview = (content_preview or "")[:200]

        event = MessageReceivedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=MessageReceivedData(
                message_id=message_id,
                job_id=from_job_id,
                project_id=project_id_str,
                from_agent=from_agent,
                to_agent_ids=to_agent_ids,
                message_type=message_type,
                message=preview,
                content=preview,
                content_preview=preview,
                tenant_key=tenant_key,
                priority=priority,
                timestamp=msg_ts,
                from_job_id=from_job_id,
                to_job_ids=to_job_ids,
                waiting_count=waiting_count,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def message_acknowledged(
        message_id: str,
        project_id: str | UUID,
        tenant_key: str,
        from_job_id: str,
        to_job_ids: list[str],
        agent_id: str,
        message_ids: list[str],
        waiting_count: int | None = None,
        read_count: int | None = None,
    ) -> dict:
        """Create message:acknowledged event."""
        project_id_str = str(project_id) if isinstance(project_id, UUID) else project_id

        event = MessageAcknowledgedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=MessageAcknowledgedData(
                message_id=message_id,
                message_ids=message_ids,
                agent_id=agent_id,
                project_id=project_id_str,
                tenant_key=tenant_key,
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                from_job_id=from_job_id,
                to_job_ids=to_job_ids,
                waiting_count=waiting_count,
                read_count=read_count,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def setup_tool_connected(tenant_key: str, user_id: str, tool_name: str) -> dict:
        """Create setup:tool_connected event."""
        event = SetupToolConnectedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=SetupToolConnectedData(
                tenant_key=tenant_key,
                user_id=user_id,
                tool_name=tool_name,
                connected_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def setup_commands_installed(tenant_key: str, user_id: str, tool_name: str, command_count: int) -> dict:
        """Create setup:commands_installed event."""
        event = SetupCommandsInstalledEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=SetupCommandsInstalledData(
                tenant_key=tenant_key,
                user_id=user_id,
                tool_name=tool_name,
                command_count=command_count,
            ),
        )
        return event.model_dump(mode="json")

    @staticmethod
    def setup_agents_downloaded(tenant_key: str, user_id: str, agent_count: int) -> dict:
        """Create setup:agents_downloaded event."""
        event = SetupAgentsDownloadedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=SetupAgentsDownloadedData(
                tenant_key=tenant_key,
                user_id=user_id,
                agent_count=agent_count,
            ),
        )
        return event.model_dump(mode="json")


# ============================================================================
# Public API — re-export models + factory for single-import convenience
# ============================================================================

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
