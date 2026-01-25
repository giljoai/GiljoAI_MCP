"""
Response schemas for GiljoAI MCP API endpoints.

Professional, production-grade Pydantic models for API responses.
Centralized location for all response schemas to ensure consistency
and type safety across the API surface.

Created: Handover 0501
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectSummaryResponse(BaseModel):
    """
    Project summary with metrics and status.

    Returns comprehensive project overview including job statistics,
    completion metrics, and activity timestamps for dashboard display.
    """

    id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")
    status: str = Field(..., description="Project status (staging/active/inactive/completed/cancelled)")
    mission: Optional[str] = Field(None, description="Project mission statement")

    # Job metrics
    total_jobs: int = Field(0, description="Total number of agent jobs")
    completed_jobs: int = Field(0, description="Number of completed jobs")
    failed_jobs: int = Field(0, description="Number of failed jobs")
    active_jobs: int = Field(0, description="Number of currently active jobs")
    pending_jobs: int = Field(0, description="Number of pending jobs")

    # Progress tracking
    completion_percentage: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Project completion percentage (0-100)"
    )

    # Timestamps
    created_at: datetime = Field(..., description="Project creation timestamp")
    activated_at: Optional[datetime] = Field(None, description="First activation timestamp")
    last_activity_at: Optional[datetime] = Field(None, description="Most recent activity timestamp")

    # Product context
    product_id: str = Field(..., description="Parent product UUID")
    product_name: str = Field(..., description="Parent product name")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "abc-123-def-456",
                "name": "Feature Development Sprint",
                "status": "active",
                "mission": "Implement user authentication system",
                "total_jobs": 10,
                "completed_jobs": 7,
                "failed_jobs": 1,
                "active_jobs": 1,
                "pending_jobs": 1,
                "completion_percentage": 70.0,
                "created_at": "2025-01-10T10:00:00Z",
                "activated_at": "2025-01-10T10:30:00Z",
                "last_activity_at": "2025-01-13T14:22:00Z",
                "product_id": "xyz-789",
                "product_name": "Authentication Platform",
            }
        }
    )


class ProjectLaunchResponse(BaseModel):
    """
    Project orchestrator launch response.

    Returns launch details including orchestrator job ID and
    thin-client launch prompt for starting the orchestrator instance.
    """

    project_id: str = Field(..., description="Project UUID")
    orchestrator_job_id: str = Field(..., description="Orchestrator agent job UUID")
    launch_prompt: str = Field(..., description="Thin-client launch prompt for orchestrator")
    status: str = Field(..., description="Project status after launch")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_id": "abc-123-def-456",
                "orchestrator_job_id": "orch-job-789",
                "launch_prompt": "Launch orchestrator for project...",
                "status": "active",
            }
        }
    )


class ProjectResponse(BaseModel):
    """
    Standard project response for lifecycle operations.

    Used for activation, deactivation, cancellation, and other
    state transition operations.
    """

    id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")
    status: str = Field(..., description="Project status")
    mission: Optional[str] = Field(None, description="Project mission")
    description: Optional[str] = Field(None, description="Project description")

    # Metadata
    config_data: Optional[dict[str, Any]] = Field(None, description="Project configuration data")
    meta_data: Optional[dict[str, Any]] = Field(None, description="Project metadata")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    activated_at: Optional[datetime] = Field(None, description="Activation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    # Product relation
    product_id: str = Field(..., description="Parent product UUID")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "abc-123-def-456",
                "name": "Feature Development Sprint",
                "status": "active",
                "mission": "Implement user authentication",
                "description": "Complete authentication system",
                "config_data": {},
                "meta_data": {},
                "created_at": "2025-01-10T10:00:00Z",
                "updated_at": "2025-01-13T14:22:00Z",
                "activated_at": "2025-01-10T10:30:00Z",
                "completed_at": None,
                "product_id": "xyz-789",
            }
        },
    )


# ============================================================================
# Orchestrator Succession Schemas - Handover 0505
# ============================================================================


class SuccessionRequest(BaseModel):
    """
    Request body for manual orchestrator succession trigger.

    Used by "Hand Over" button in AgentCardEnhanced.vue and /gil_handover command.
    """

    reason: str = Field(
        default="manual",
        description="Succession reason (manual, context_limit, phase_transition)"
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes about why succession was triggered"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "manual",
                "notes": "Switching orchestrator for new project phase",
            }
        }
    )


class SuccessionResponse(BaseModel):
    """
    Response for manual succession trigger.

    Handover 0358b: Updated for dual-model architecture (AgentJob + AgentExecution).
    Handover 0381: Clean contract - job_id (work order) + successor_agent_id (new executor).
    Agent ID Swap: Old orchestrator gets decommissioned ID, new orchestrator takes over original.
    Returns successor execution details and handover summary for launching new instance.
    """

    current_agent_id: str = Field(..., description="Decommissioned agent_id of old orchestrator (after swap)")
    job_id: str = Field(..., description="Work order UUID (persists across succession)")
    successor_agent_id: str = Field(..., description="Agent_id of new orchestrator (takes over original ID)")
    instance_number: int = Field(..., description="Successor instance number")
    launch_prompt: str = Field(..., description="Thin-client launch prompt for successor")
    handover_summary: Optional[str] = Field(None, description="Compressed handover summary")
    succession_reason: str = Field(..., description="Reason for succession")
    created_at: datetime = Field(..., description="Successor creation timestamp")
    decommissioned_agent_id: Optional[str] = Field(None, description="Decommissioned ID of old orchestrator")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "current_agent_id": "decomm-agent12-abc12345",
                "job_id": "job-456",
                "successor_agent_id": "agent-123",
                "instance_number": 2,
                "launch_prompt": "Continue orchestration from instance 1...",
                "handover_summary": "Project 60% complete, 3 active agents...",
                "succession_reason": "manual",
                "created_at": "2025-01-13T14:22:00Z",
                "decommissioned_agent_id": "decomm-agent12-abc12345",
            }
        },
    )


class SuccessionStatusResponse(BaseModel):
    """
    Response for checking orchestrator succession status.

    Indicates whether succession is needed based on context usage.
    """

    job_id: str = Field(..., description="Orchestrator job UUID")
    needs_succession: bool = Field(..., description="True if succession advisable (user can manually trigger)")
    context_used: int = Field(..., description="Tokens used from context budget")
    context_budget: int = Field(..., description="Total context budget in tokens")
    context_usage_pct: float = Field(..., description="Context usage percentage (0-100)")
    handover_to: Optional[str] = Field(None, description="Successor job ID if already handed over")
    succession_reason: Optional[str] = Field(None, description="Reason for succession if triggered")
    instance_number: int = Field(..., description="Current instance number")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "orch-job-123",
                "needs_succession": True,
                "context_used": 185000,
                "context_budget": 200000,
                "context_usage_pct": 92.5,
                "handover_to": None,
                "succession_reason": None,
                "instance_number": 1,
            }
        }
    )


class InitiateHandoverResponse(BaseModel):
    """
    Response for initiating orchestrator handover (Handover 0506).

    Returns a prompt for the retiring orchestrator to spawn its successor.
    The orchestrator pastes this prompt to gather context and spawn a new orchestrator.
    """

    prompt: str = Field(..., description="Prompt for retiring orchestrator to spawn successor")
    job_id: str = Field(..., description="Current orchestrator's job UUID")
    agent_id: str = Field(..., description="Current orchestrator's agent UUID")
    project_id: str = Field(..., description="Project UUID")
    instance_number: int = Field(..., description="Current instance number")
