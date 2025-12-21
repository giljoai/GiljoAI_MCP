"""
Pydantic models for agent_jobs endpoints.

Request/response models for agent job operations with validation.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Spawn Agent Models
# ============================================================================

class SpawnAgentRequest(BaseModel):
    """Request model for spawning a new agent job."""

    agent_type: str = Field(..., description="Agent type (orchestrator, implementer, etc.)")
    agent_name: Optional[str] = Field(None, description="Human-readable agent name")
    mission: str = Field(..., description="Agent mission/instructions")
    project_id: str = Field(..., description="Project UUID")
    parent_job_id: Optional[str] = Field(None, description="Parent job UUID")
    context_chunks: list[str] = Field(default_factory=list, description="Context chunk IDs")


class SpawnAgentResponse(BaseModel):
    """Response model for agent spawn operation."""

    success: bool = Field(..., description="Whether spawn succeeded")
    agent_job_id: str = Field(..., description="Created agent job ID")
    agent_prompt: str = Field(..., description="Generated agent prompt")
    mission_stored: bool = Field(..., description="Whether mission was stored")
    thin_client: bool = Field(..., description="Whether using thin client architecture")


# ============================================================================
# Job Lifecycle Models
# ============================================================================

class JobAcknowledgeResponse(BaseModel):
    """Response model for job acknowledgment."""

    job_id: str
    status: str
    started_at: Optional[datetime]
    message: str


class JobCompleteRequest(BaseModel):
    """Request model for job completion."""

    result: Optional[str] = Field(None, description="Completion result/summary")


class JobCompleteResponse(BaseModel):
    """Response model for job completion."""

    job_id: str
    status: str
    completed_at: Optional[datetime]
    message: str


class JobErrorRequest(BaseModel):
    """Request model for reporting job error."""

    error: str = Field(..., description="Error message/details")


class JobErrorResponse(BaseModel):
    """Response model for job error reporting."""

    job_id: str
    status: str
    completed_at: Optional[datetime]
    message: str


# ============================================================================
# Job Status Models
# ============================================================================

class JobResponse(BaseModel):
    """Response model for job details."""

    id: str  # Changed from int to str for UUID (0366 series)
    job_id: str
    tenant_key: str
    project_id: Optional[str] = None
    agent_type: str
    agent_name: Optional[str] = None
    mission: str
    status: str
    progress: int = 0
    spawned_by: Optional[str] = None
    tool_type: str = "universal"
    context_chunks: list[str] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    mission_acknowledged_at: Optional[datetime] = None  # Handover 0297
    # Numeric steps summary for TODO-style progress (Handover 0297)
    # When present, represents completed/total steps for dashboard Steps column.
    steps: Optional[dict[str, int]] = None


class PendingJobsResponse(BaseModel):
    """Response model for pending jobs list."""

    jobs: list[JobResponse]
    count: int


class JobMissionResponse(BaseModel):
    """Response model for job mission retrieval."""

    job_id: str
    mission: str
    context_chunks: list[str]
    status: str


# ============================================================================
# Progress Reporting Models
# ============================================================================

class ProgressReportRequest(BaseModel):
    """Request model for progress reporting."""

    progress_percent: int = Field(..., ge=0, le=100, description="Progress percentage")
    status_message: Optional[str] = Field(None, description="Progress status message")
    current_task: Optional[str] = Field(None, description="Current task description")


class ProgressReportResponse(BaseModel):
    """Response model for progress reporting."""

    job_id: str
    progress_percent: int
    message: str


# ============================================================================
# Orchestration Models
# ============================================================================

class OrchestrateProjectRequest(BaseModel):
    """Request model for project orchestration."""

    project_id: UUID = Field(..., description="Project UUID to orchestrate")


class OrchestrationResponse(BaseModel):
    """Response model for orchestration operation."""

    success: bool
    project_id: str
    message: Optional[str] = None
    result: Optional[dict[str, Any]] = None


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""

    project_id: str
    status: str
    agent_count: int
    completed_count: int
    failed_count: int
    active_count: int
    progress_percent: int


class JobListResponse(BaseModel):
    """Response model for job list with pagination (Handover 0135)."""

    jobs: list[JobResponse]
    total: int
    limit: int
    offset: int


# ============================================================================
# Job Operations Models (Handover 0107)
# ============================================================================

class CancelJobRequest(BaseModel):
    """Request model for job cancellation."""

    reason: str = Field(..., description="Reason for cancellation")


class CancelJobResponse(BaseModel):
    """Response model for job cancellation."""

    success: bool
    job_id: str
    status: str
    message: str


class ForceFailJobRequest(BaseModel):
    """Request model for force-failing a job."""

    reason: str = Field(..., description="Reason for forced failure")


class ForceFailJobResponse(BaseModel):
    """Response model for force-failing a job."""

    success: bool
    job_id: str
    status: str
    message: str


class JobHealthResponse(BaseModel):
    """Response model for job health metrics."""

    job_id: str
    status: str
    last_progress_at: Optional[datetime] = None
    last_message_check_at: Optional[datetime] = None
    minutes_since_progress: Optional[float] = None
    is_stale: bool


# ============================================================================
# Mission Update Models (Handover 0244b)
# ============================================================================

class UpdateMissionRequest(BaseModel):
    """Request model for updating agent mission."""

    mission: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Updated mission/instructions for the agent"
    )


class UpdateMissionResponse(BaseModel):
    """Response model for mission update."""

    success: bool = Field(..., description="Whether update succeeded")
    job_id: str = Field(..., description="Job ID that was updated")
    mission: str = Field(..., description="Updated mission text")


# ============================================================================
# Agent Execution Models (Handover 0366d-1)
# ============================================================================

class AgentExecutionResponse(BaseModel):
    """Response model for agent execution instance (Handover 0366d-1)."""

    agent_id: str
    job_id: str
    instance_number: int
    status: str
    progress: int = 0
    spawned_by: Optional[str] = None
    succeeded_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
