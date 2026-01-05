"""
Pydantic models for projects endpoints.

Request/response models for project operations with validation.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# CRUD Models
# ============================================================================

class ProjectCreate(BaseModel):
    """Request model for project creation."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="User-written project description (what you want to accomplish)")
    mission: str = Field(
        default="", description="AI-generated mission statement (initially empty, filled by orchestrator)"
    )
    product_id: Optional[str] = Field(None, description="Product ID to associate with")
    status: str = Field(default="inactive", description="Project status (Handover 0050b: defaults to inactive)")
    context_budget: int = Field(default=150000, description="Token budget for the project")
    # Handover 0260: Execution mode for Claude Code CLI toggle
    execution_mode: str = Field(
        default="multi_terminal",
        description="Execution mode: 'multi_terminal' (manual) or 'claude_code_cli' (single terminal with Task tool)"
    )


class ProjectUpdate(BaseModel):
    """Request model for project updates."""
    name: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    status: Optional[str] = None
    # Handover 0260: Execution mode for Claude Code CLI toggle
    execution_mode: Optional[str] = Field(
        None,
        description="Execution mode: 'multi_terminal' (manual) or 'claude_code_cli' (single terminal with Task tool)"
    )


class AgentSimple(BaseModel):
    """Simple agent schema for project response."""
    id: str  # job_id
    job_id: str
    agent_type: str
    agent_name: Optional[str] = None
    status: str
    thin_client: bool = True


class ProjectResponse(BaseModel):
    """Response model for project details."""
    id: str
    alias: str
    name: str
    description: Optional[str] = None
    mission: str
    status: str
    staging_status: Optional[str] = None
    product_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    context_budget: Optional[int] = 150000  # Nullable after project reset
    context_used: Optional[int] = 0  # Nullable after project reset
    agent_count: int
    message_count: int
    agents: List[AgentSimple] = []
    # Handover 0260: Execution mode for Claude Code CLI toggle
    execution_mode: str = "multi_terminal"


class DeletedProjectResponse(BaseModel):
    """Response model for deleted project listing."""
    id: str
    alias: str
    name: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    deleted_at: datetime
    days_until_purge: int
    purge_date: datetime


class ProjectDeleteResponse(BaseModel):
    """Response model for project soft delete."""

    success: bool = Field(..., description="Whether the delete operation succeeded")
    message: str = Field(..., description="User-readable result message")
    deleted_at: Optional[datetime] = Field(
        None,
        description="Timestamp when project was marked as deleted (soft delete)",
    )


class PurgedProject(BaseModel):
    """Response model for a purged project entry."""

    id: str
    name: str
    tenant_key: str
    deleted_at: Optional[datetime] = None


class ProjectPurgeResponse(BaseModel):
    """Response model for project purge operations."""

    success: bool
    purged_count: int
    projects: List[PurgedProject] = []
    message: Optional[str] = None


# ============================================================================
# Summary/Status Models
# ============================================================================

class AgentSummary(BaseModel):
    """Summary of an agent used in the project (Handover 0062)."""
    id: str
    name: str
    type: str
    status: str
    job_mission: Optional[str] = None
    job_id: Optional[str] = None


class MessageSummary(BaseModel):
    """Summary of a message in the project (Handover 0062)."""
    id: str
    from_agent: str
    to_agents: List[str]
    content: str
    timestamp: str


class ProjectSummaryResponse(BaseModel):
    """Comprehensive project summary for after-action review (Handover 0062)."""
    project_id: str
    project_name: str
    description: str
    mission: Optional[str] = None
    status: str
    agents: List[AgentSummary]
    messages: List[MessageSummary]
    created_at: str
    completed_at: Optional[str] = None


# ============================================================================
# Lifecycle Models
# ============================================================================

class StagingCancellationResponse(BaseModel):
    """Response model for staging cancellation (Handover 0108)."""
    success: bool = Field(..., description="Whether staging cancellation succeeded")
    agents_deleted: int = Field(..., description="Number of agents deleted/soft-deleted")
    agents_protected: int = Field(..., description="Number of agents protected (already launched)")
    staging_status: Optional[str] = Field(None, description="Updated staging_status (should be None)")
    message: str = Field(..., description="User-readable result message")
    rollback_timestamp: Optional[str] = Field(None, description="ISO timestamp of rollback")


# ============================================================================
# Completion Models
# ============================================================================

class ProjectCloseOutResponse(BaseModel):
    """Response for project close-out operation (Handover 0113)."""
    success: bool
    message: str
    agents_decommissioned: int
    decommissioned_agent_ids: list[str]
    project_status: str


class ContinueWorkingResponse(BaseModel):
    """Response for continue working operation (Handover 0113)."""
    success: bool
    message: str
    agents_resumed: int
    resumed_agent_ids: list[str]
    project_status: str


# ============================================================================
# Orchestrator Models (Handover 0135)
# ============================================================================

class OrchestratorJobResponse(BaseModel):
    """Orchestrator job details for project."""

    id: Optional[int] = None  # Deprecated after AgentExecution refactor (Handover 0366a)
    job_id: str
    agent_id: str  # Alias for backward compatibility
    agent_type: str
    agent_name: Optional[str]
    mission: str
    status: str
    progress: int
    tool_type: str
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    instance_number: Optional[int] = 1  # Handover 0080 - orchestrator succession  # Handover 0080 - orchestrator succession


class OrchestratorResponse(BaseModel):
    """Response for GET /{project_id}/orchestrator."""

    success: bool
    orchestrator: Optional[OrchestratorJobResponse] = None  # Handover 0506: Optional when no orchestrator exists
