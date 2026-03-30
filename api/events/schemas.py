"""
WebSocket Event Schema Registry

Standardized event schemas for all WebSocket communications in GiljoAI MCP.
Provides type-safe, validated event structures with Pydantic models.

Handover 0086A: Production-Grade Stage Project Architecture
Task 1.4: Create Standardized Event Schemas
Created: 2025-11-02

Architecture:
- All events have: type, timestamp, schema_version, data
- Pydantic validation ensures strict type safety
- EventFactory provides consistent event creation
- Schema versioning enables backwards compatibility
- TypeScript generation support for frontend

Example Usage:
    >>> from api.events.schemas import EventFactory
    >>> event = EventFactory.project_mission_updated(
    ...     project_id=UUID("..."),
    ...     tenant_key="tenant_123",
    ...     mission="Implement feature X"
    ... )
    >>> await ws_manager.broadcast_to_tenant(
    ...     tenant_key="tenant_123",
    ...     event_type="project:mission_updated",
    ...     data=event["data"]
    ... )
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

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
        """
        Validate timestamp is valid ISO 8601 format.

        Accepts both 'Z' suffix and '+00:00' timezone formats.

        Args:
            v: Timestamp string to validate

        Returns:
            Validated timestamp string

        Raises:
            ValueError: If timestamp is not valid ISO 8601
        """
        try:
            # Handle both 'Z' suffix and '+00:00' format
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}") from e


# ============================================================================
# Project Events
# ============================================================================


class ProjectMissionUpdatedData(BaseModel):
    """
    Data payload for project:mission_updated event.

    Emitted when a project's mission is updated by the orchestrator
    or user configuration.
    """

    project_id: str = Field(..., description="Project UUID as string")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    mission: str = Field(..., min_length=1, description="Generated mission text")
    generated_by: Literal["orchestrator", "user"] = Field(
        default="orchestrator", description="Source of mission generation"
    )
    user_config_applied: bool = Field(default=False, description="Whether user configuration was applied")
    field_toggles: dict[str, Any] = Field(None, description="Field toggle config used in generation")


class ProjectMissionUpdatedEvent(BaseModel):
    """
    Complete event structure for project:mission_updated.

    Broadcast to all tenant clients when a project's mission is updated.
    Frontend uses this to update UI and show "Optimized for you" badge.
    """

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
    """
    Data payload for agent:created event.

    Emitted when a new agent job is created and staged for execution.
    Contains complete agent configuration for UI visualization.
    """

    project_id: str = Field(..., description="Project UUID as string")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    agent: dict[str, Any] = Field(..., description="Complete agent job data")

    @field_validator("agent")
    @classmethod
    def validate_agent_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Validate agent data contains minimum required fields.

        Args:
            v: Agent data dictionary

        Returns:
            Validated agent data

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["id", "agent_display_name", "status"]
        missing = [f for f in required_fields if f not in v]
        if missing:
            raise ValueError(f"Agent data missing required fields: {missing}")
        return v


class AgentCreatedEvent(BaseModel):
    """
    Complete event structure for agent:created.

    Broadcast to all tenant clients when a new agent is created.
    Frontend uses this to add the agent to the visualization grid.
    """

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
    """
    Data payload for agent:status_changed event.

    Emitted when an agent's status changes (e.g., pending → active → completed).
    Enables real-time status tracking in the frontend.
    """

    job_id: str = Field(..., description="Agent job UUID as string")
    project_id: str | None = Field(None, description="Project UUID if applicable")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    old_status: str = Field(..., min_length=1, description="Previous status")
    new_status: str = Field(..., min_length=1, description="New status")
    agent_display_name: str = Field(..., min_length=1, description="Human-readable display name for UI")
    duration_seconds: float | None = Field(None, ge=0, description="Job duration for completed/failed status")

    @field_validator("new_status")
    @classmethod
    def validate_status_transition(cls, v: str, info) -> str:
        """
        Validate status is a known agent status value.

        Args:
            v: New status value
            info: Validation context

        Returns:
            Validated status value

        Raises:
            ValueError: If status is not recognized
        """
        valid_statuses = {"waiting", "working", "blocked", "complete", "silent", "decommissioned"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid agent status: {v}. Must be one of {valid_statuses}")
        return v


class AgentStatusChangedEvent(BaseModel):
    """
    Complete event structure for agent:status_changed.

    Broadcast to all tenant clients when an agent's status changes.
    Frontend uses this to update agent card status and visual indicators.
    """

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
                    "new_status": "active",
                    "agent_display_name": "orchestrator",
                    "duration_seconds": None,
                },
            }
        }
    }


class AgentSilentData(BaseModel):
    """
    Data payload for agent:silent event.

    Emitted when the silence detector marks an agent as silent.
    Used by the frontend notification bell to alert users about
    unresponsive agents.
    """

    job_id: str = Field(..., description="Agent job UUID as string")
    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")
    agent_display_name: str = Field(..., min_length=1, description="Human-readable display name for UI")
    reason: str = Field(..., min_length=1, description="Reason for silence detection")
    project_id: str | None = Field(None, description="Project UUID if applicable")
    project_name: str | None = Field(None, description="Project name for display")
    execution_id: str | None = Field(None, description="Agent execution UUID")


class AgentSilentEvent(BaseModel):
    """
    Complete event structure for agent:silent.

    Broadcast to all tenant clients when an agent is detected as silent.
    Frontend notification bell handler listens for this event type.
    """

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

    # Compatibility aliases for content preview fields
    message: str = Field(default="", description="Message preview")
    content: str = Field(default="", description="Message preview")
    content_preview: str = Field(default="", description="Message preview")

    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")

    # Counter values (Handover 0387g)
    sender_sent_count: int | None = Field(default=None, description="Sender's total messages sent count")
    recipient_waiting_count: int | None = Field(default=None, description="Recipient's messages waiting count")
    priority: int = Field(default=1, ge=0, le=2, description="Message priority (0-2)")
    timestamp: str = Field(..., description="Message timestamp (ISO 8601)")

    # Explicit identifiers to remove ambiguity in clients
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

    # Compatibility aliases for content preview fields
    message: str = Field(default="", description="Message preview")
    content: str = Field(default="", description="Message preview")
    content_preview: str = Field(default="", description="Message preview")

    tenant_key: str = Field(..., min_length=1, description="Tenant identifier")

    # Counter values (Handover 0387g)
    waiting_count: int | None = Field(default=None, description="Recipient's messages waiting count")
    priority: int = Field(default=1, ge=0, le=2, description="Message priority (0-2)")
    timestamp: str = Field(..., description="Message timestamp (ISO 8601)")

    # Explicit identifiers to remove ambiguity in clients
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

    # Explicit identifiers to remove ambiguity in clients
    from_job_id: str = Field(..., description="Acknowledging agent job ID")
    to_job_ids: list[str] = Field(default_factory=list, description="Target agent job IDs")

    # Counter values (Handover 0387g)
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
# Union type of all WebSocket events for validation.
#
# Use this for type hints when accepting any WebSocket event.

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
        """
        Create project:mission_updated event.

        Args:
            project_id: Project UUID (str or UUID object)
            tenant_key: Tenant identifier
            mission: Generated mission text
            generated_by: Source of generation ("orchestrator" or "user")
            user_config_applied: Whether user configuration was applied
            field_toggles: Field toggle config used in generation

        Returns:
            Event dict ready for JSON serialization

        Example:
            >>> event = EventFactory.project_mission_updated(
            ...     project_id="550e8400-e29b-41d4-a716-446655440000",
            ...     tenant_key="tenant_123",
            ...     mission="Build feature X",
            ...     user_config_applied=True
            ... )
            >>> await ws.send_json(event)
        """
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
        """
        Create agent:created event.

        Args:
            project_id: Project UUID (str or UUID object)
            tenant_key: Tenant identifier
            agent: Complete agent job data (must include: id, agent_display_name, status)

        Returns:
            Event dict ready for JSON serialization

        Raises:
            ValidationError: If agent data is missing required fields

        Example:
            >>> event = EventFactory.agent_created(
            ...     project_id="550e8400-e29b-41d4-a716-446655440000",
            ...     tenant_key="tenant_123",
            ...     agent={
            ...         "id": "660e8400-e29b-41d4-a716-446655440000",
            ...         "agent_display_name": "orchestrator",
            ...         "status": "pending",
            ...         "mission": "Coordinate implementation"
            ...     }
            ... )
            >>> await ws.send_json(event)
        """
        # Convert UUID to string if needed
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
        """
        Create agent:status_changed event.

        Args:
            job_id: Agent job UUID (str or UUID object)
            tenant_key: Tenant identifier
            old_status: Previous status
            new_status: New status (pending, active, completed, failed, cancelled)
            agent_display_name: Human-readable display name for UI
            project_id: Optional project UUID
            duration_seconds: Optional job duration (for completed/failed)

        Returns:
            Event dict ready for JSON serialization

        Raises:
            ValidationError: If status values are invalid

        Example:
            >>> event = EventFactory.agent_status_changed(
            ...     job_id="660e8400-e29b-41d4-a716-446655440000",
            ...     tenant_key="tenant_123",
            ...     old_status="pending",
            ...     new_status="active",
            ...     agent_display_name="orchestrator",
            ...     project_id="550e8400-e29b-41d4-a716-446655440000"
            ... )
            >>> await ws.send_json(event)
        """
        # Convert UUIDs to strings if needed
        job_id_str = str(job_id) if isinstance(job_id, UUID) else job_id
        project_id_str = str(project_id) if project_id and isinstance(project_id, UUID) else project_id

        event = AgentStatusChangedEvent(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data=AgentStatusChangedData(
                job_id=job_id_str,
                project_id=project_id_str,
                tenant_key=tenant_key,
                old_status=old_status,
                new_status=new_status,
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
        """
        Create agent:silent event.

        Emitted by the silence detector when an agent stops communicating.
        Used by the frontend notification bell to alert users.

        Args:
            job_id: Agent job UUID (str or UUID object)
            tenant_key: Tenant identifier
            agent_display_name: Human-readable display name for UI
            reason: Reason the agent was marked silent
            project_id: Optional project UUID
            project_name: Optional project name for display
            execution_id: Optional agent execution UUID

        Returns:
            Event dict ready for JSON serialization

        Example:
            >>> event = EventFactory.agent_silent(
            ...     job_id="660e8400-e29b-41d4-a716-446655440000",
            ...     tenant_key="tenant_123",
            ...     agent_display_name="implementor",
            ...     reason="Agent stopped communicating",
            ...     project_id="550e8400-e29b-41d4-a716-446655440000",
            ...     project_name="My Project",
            ... )
            >>> await ws.send_json(event)
        """
        # Convert UUIDs to strings if needed
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
# Public API
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
