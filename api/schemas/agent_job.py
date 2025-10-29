"""
Agent Job API Pydantic schemas for Handover 0019: Agent Job Management System.

Provides request/response models for:
- Job CRUD operations
- Job status management
- Agent messaging
- Job coordination and hierarchy
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# Job CRUD Schemas

class JobCreateRequest(BaseModel):
    """
    Schema for creating a new agent job (POST /api/agent-jobs).
    """
    agent_type: str = Field(..., min_length=1, max_length=100, description="Agent type: orchestrator, implementer, tester, etc.")
    mission: str = Field(..., min_length=1, description="Mission/instructions for the agent")
    spawned_by: Optional[str] = Field(None, description="Job ID of parent job that spawned this job")
    context_chunks: Optional[list[str]] = Field(None, description="Array of chunk_ids for context loading")

    model_config = ConfigDict(from_attributes=True)


class JobUpdateRequest(BaseModel):
    """
    Schema for updating a job (PATCH /api/agent-jobs/{job_id}).

    Only status can be updated directly. Use specialized endpoints for:
    - Acknowledge: POST /api/agent-jobs/{job_id}/acknowledge
    - Complete: POST /api/agent-jobs/{job_id}/complete
    - Fail: POST /api/agent-jobs/{job_id}/fail
    """
    status: Optional[str] = Field(None, description="Job status: pending, active, completed, failed")

    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    """
    Schema for job response (GET /api/agent-jobs/{job_id}).
    """
    id: int = Field(..., description="Database ID")
    job_id: str = Field(..., description="Unique job identifier (UUID)")
    tenant_key: str = Field(..., description="Tenant key for isolation")
    agent_type: str = Field(..., description="Agent type")
    mission: str = Field(..., description="Agent mission/instructions")
    status: str = Field(..., description="Job status: pending, active, completed, failed")
    spawned_by: Optional[str] = Field(None, description="Job ID of parent job")
    context_chunks: list[str] = Field(default_factory=list, description="Context chunk IDs")
    messages: list[dict[str, Any]] = Field(default_factory=list, description="Job messages")
    acknowledged: bool = Field(..., description="Has job been acknowledged by agent")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    created_at: datetime = Field(..., description="Job creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class JobCreateResponse(BaseModel):
    """
    Schema for job creation response (POST /api/agent-jobs).
    """
    job_id: str = Field(..., description="Created job ID")
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """
    Schema for job list response (GET /api/agent-jobs).
    """
    jobs: list[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs matching filters")

    model_config = ConfigDict(from_attributes=True)


# Agent Messaging Schemas

class MessageSendRequest(BaseModel):
    """
    Schema for sending a message to a job (POST /api/agent-jobs/{job_id}/messages).
    """
    role: str = Field(..., description="Message role: system, agent, orchestrator")
    type: str = Field(..., description="Message type: status, request, response, error")
    content: dict[str, Any] = Field(..., description="Message content")

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """
    Schema for message response.
    """
    message_id: str = Field(..., description="Message ID (index in messages array)")
    timestamp: str = Field(..., description="Message timestamp (ISO format)")
    role: str = Field(..., description="Message role")
    type: str = Field(..., description="Message type")
    content: dict[str, Any] = Field(..., description="Message content")
    acknowledged: bool = Field(default=False, description="Message acknowledgment status")

    model_config = ConfigDict(from_attributes=True)


# Job Coordination Schemas

class ChildJobSpec(BaseModel):
    """
    Schema for child job specification in spawn request.
    """
    agent_type: str = Field(..., min_length=1, max_length=100, description="Agent type for child job")
    mission: str = Field(..., min_length=1, description="Mission for child job")
    context_chunks: Optional[list[str]] = Field(None, description="Context chunks for child job")

    model_config = ConfigDict(from_attributes=True)


class JobSpawnRequest(BaseModel):
    """
    Schema for spawning child jobs (POST /api/agent-jobs/{job_id}/spawn-children).
    """
    children: list[ChildJobSpec] = Field(..., min_length=1, description="Child job specifications")

    model_config = ConfigDict(from_attributes=True)


class JobSpawnResponse(BaseModel):
    """
    Schema for spawn response.
    """
    parent_job_id: str = Field(..., description="Parent job ID")
    child_job_ids: list[str] = Field(..., description="Created child job IDs")
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(from_attributes=True)


class JobHierarchyResponse(BaseModel):
    """
    Schema for job hierarchy response (GET /api/agent-jobs/{job_id}/hierarchy).
    """
    parent: JobResponse = Field(..., description="Parent job details")
    children: list[JobResponse] = Field(default_factory=list, description="Child jobs")
    total_children: int = Field(..., description="Total number of child jobs")

    model_config = ConfigDict(from_attributes=True)


# Job Status Management Schemas

class JobAcknowledgeResponse(BaseModel):
    """
    Schema for job acknowledge response (POST /api/agent-jobs/{job_id}/acknowledge).
    """
    job_id: str = Field(..., description="Acknowledged job ID")
    status: str = Field(..., description="New status (active)")
    started_at: datetime = Field(..., description="Job start timestamp")
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(from_attributes=True)


class JobCompleteRequest(BaseModel):
    """
    Schema for completing a job (POST /api/agent-jobs/{job_id}/complete).
    """
    result: Optional[dict[str, Any]] = Field(None, description="Job result data")

    model_config = ConfigDict(from_attributes=True)


class JobCompleteResponse(BaseModel):
    """
    Schema for job complete response.
    """
    job_id: str = Field(..., description="Completed job ID")
    status: str = Field(..., description="New status (completed)")
    completed_at: datetime = Field(..., description="Job completion timestamp")
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(from_attributes=True)


class JobFailRequest(BaseModel):
    """
    Schema for failing a job (POST /api/agent-jobs/{job_id}/fail).
    """
    error: Optional[dict[str, Any]] = Field(None, description="Error details")

    model_config = ConfigDict(from_attributes=True)


class JobFailResponse(BaseModel):
    """
    Schema for job fail response.
    """
    job_id: str = Field(..., description="Failed job ID")
    status: str = Field(..., description="New status (failed)")
    completed_at: datetime = Field(..., description="Job completion timestamp")
    message: str = Field(..., description="Success message")

    model_config = ConfigDict(from_attributes=True)


# Kanban Board Schemas (Handover 0066)

class MessageCounts(BaseModel):
    """
    Schema for message counts in Kanban board.
    """
    unread_messages: int = Field(..., description="Count of unread messages (status='pending')")
    acknowledged_messages: int = Field(..., description="Count of acknowledged messages (status='acknowledged')")
    sent_messages: int = Field(..., description="Count of sent messages (from='developer' or from='user')")

    model_config = ConfigDict(from_attributes=True)


class KanbanJobCard(BaseModel):
    """
    Schema for a job card in Kanban board.
    """
    job_id: str = Field(..., description="Unique job identifier")
    agent_type: str = Field(..., description="Agent type")
    mission: str = Field(..., description="Agent mission/instructions")
    status: str = Field(..., description="Job status")
    acknowledged: bool = Field(..., description="Has job been acknowledged by agent")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    created_at: datetime = Field(..., description="Job creation timestamp")
    message_counts: MessageCounts = Field(..., description="Message counts for this job")

    model_config = ConfigDict(from_attributes=True)


class KanbanColumn(BaseModel):
    """
    Schema for a Kanban column.
    """
    status: str = Field(..., description="Column status: pending, active, completed, blocked")
    jobs: list[KanbanJobCard] = Field(..., description="Jobs in this column")

    model_config = ConfigDict(from_attributes=True)


class KanbanBoardResponse(BaseModel):
    """
    Schema for Kanban board response (GET /api/agent-jobs/kanban/{project_id}).
    """
    project_id: str = Field(..., description="Project ID")
    columns: list[KanbanColumn] = Field(..., description="Kanban columns (4: pending, active, completed, blocked)")

    model_config = ConfigDict(from_attributes=True)


class MessageThreadItem(BaseModel):
    """
    Schema for a message in the thread.
    """
    message_id: str = Field(..., description="Message ID (index in messages array)")
    from_: str = Field(..., alias="from", description="Message sender: developer, agent, user, system")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp (ISO format)")
    status: str = Field(..., description="Message status: pending, acknowledged")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MessageThreadResponse(BaseModel):
    """
    Schema for message thread response (GET /api/agent-jobs/{job_id}/message-thread).
    """
    job_id: str = Field(..., description="Job ID")
    messages: list[MessageThreadItem] = Field(..., description="Messages in chronological order")

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    """
    Schema for sending a message (POST /api/agent-jobs/{job_id}/send-message).
    """
    content: str = Field(..., min_length=1, description="Message content")

    model_config = ConfigDict(from_attributes=True)


class SendMessageResponse(BaseModel):
    """
    Schema for send message response.
    """
    message_id: str = Field(..., description="Created message ID")
    from_: str = Field(..., alias="from", description="Message sender (developer)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp (ISO format)")
    status: str = Field(..., description="Message status (pending)")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
