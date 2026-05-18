# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Pydantic models for projects endpoints.

Request/response models for project operations with validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from giljo_mcp.schemas.responses.project import ProjectBase


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
    product_id: str = Field(
        ..., description="Product ID to associate with (required; projects must belong to a product)"
    )
    status: str = Field(default="inactive", description="Project status (Handover 0050b: defaults to inactive)")
    # Handover 0260: Execution mode for Claude Code CLI toggle
    execution_mode: str = Field(
        default="multi_terminal",
        description="Execution mode: 'multi_terminal' (manual) or 'claude_code_cli' (single terminal with Task tool)",
    )
    # Handover 0440a: Project taxonomy fields
    project_type_id: str | None = Field(None, description="Project type ID for taxonomy classification")
    series_number: int | None = Field(None, description="Sequential number within a project type (e.g., 1 in BE-0001)")
    subseries: str | None = Field(None, description="Single-letter subseries suffix (e.g., 'a' in BE-0001a)")


class ProjectUpdate(BaseModel):
    """Request model for project updates."""

    name: str | None = None
    description: str | None = None
    mission: str | None = None
    status: str | None = None
    # Handover 0260: Execution mode for Claude Code CLI toggle
    execution_mode: str | None = Field(
        None,
        description="Execution mode: 'multi_terminal' (manual) or 'claude_code_cli' (single terminal with Task tool)",
    )
    # Handover 0440a: Project taxonomy fields
    project_type_id: str | None = None
    series_number: int | None = None
    subseries: str | None = None
    # CE-OPT-4: UI visibility flag
    hidden: bool | None = None
    # Handover 0904/0960: Orchestrator auto check-in
    auto_checkin_enabled: bool | None = None
    auto_checkin_interval: int | None = Field(
        None,
        description="Auto check-in interval in minutes (5, 10, 15, 20, 30, 40, or 60)",
    )


class AgentSimple(BaseModel):
    """Simple agent schema for project response."""

    id: str  # job_id
    job_id: str
    agent_display_name: str
    agent_name: str | None = None
    status: str
    thin_client: bool = True


class ProjectTypeInfo(BaseModel):
    """Nested project type info for project responses (Handover 0440c)."""

    id: str
    abbreviation: str
    label: str
    color: str

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(ProjectBase):
    """Response model for project details (REST).

    Inherits the universal field set from
    ``giljo_mcp.schemas.responses.project.ProjectBase`` and adds the
    presentation extras the REST consumer (frontend project page) depends
    on: ``alias``, ``staging_status``, ``implementation_launched_at``, agent
    counts + list, and the nested REST-local ``ProjectTypeInfo``.

    Overrides inherited fields to preserve the REST wire contract:
      * timestamps as ``datetime`` (Pydantic v2 normalizes to ``...Z`` ISO);
      * ``mission`` as required ``str`` (REST never emits null mission);
      * ``execution_mode`` defaults to ``"multi_terminal"`` (REST never null).
    """

    # REST-specific required identity
    alias: str

    # Override base ``str | None`` defaults with REST-strict contract types
    mission: str
    execution_mode: str = "multi_terminal"

    # Override base ``str | None`` timestamps with ``datetime`` for Z-normalized wire
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    # Detail-only fields (not on MCP ProjectData)
    staging_status: str | None = None
    # CE-0036: implementation_launched_at must flow through the REST API for
    # the frontend's useProjectCloseout guard (staging_status='staging_complete'
    # && !implementation_launched_at → button hidden). CE-0028b added this to
    # the MCP-side response schema but missed the REST schema — the one the
    # project page actually consumes — so the Close Project button never
    # appeared after impl-end. CE-0038 keeps this on the REST subclass (not
    # on ProjectBase) because the MCP ProjectData compact shape intentionally
    # omits it.
    implementation_launched_at: datetime | None = None

    # REST presentation extras
    agent_count: int
    message_count: int
    agents: list[AgentSimple] = Field(default_factory=list)

    # Nested taxonomy info (REST-local ProjectTypeInfo above; MCP has its own)
    project_type: ProjectTypeInfo | None = None  # Handover 0440c: Nested type with color


class DeletedProjectResponse(BaseModel):
    """Response model for deleted project listing."""

    id: str
    alias: str
    name: str
    product_id: str | None = None
    product_name: str | None = None
    deleted_at: datetime
    days_until_purge: int
    purge_date: datetime


class ProjectDeleteResponse(BaseModel):
    """Response model for project soft delete."""

    success: bool = Field(..., description="Whether the delete operation succeeded")
    message: str = Field(..., description="User-readable result message")
    deleted_at: datetime | None = Field(
        None,
        description="Timestamp when project was marked as deleted (soft delete)",
    )


class PurgedProject(BaseModel):
    """Response model for a purged project entry."""

    id: str
    name: str
    tenant_key: str
    deleted_at: datetime | None = None


class ProjectPurgeResponse(BaseModel):
    """Response model for project purge operations."""

    success: bool
    purged_count: int
    projects: list[PurgedProject] = []
    message: str | None = None


# ============================================================================
# Summary/Status Models
# ============================================================================


class AgentSummary(BaseModel):
    """Summary of an agent used in the project (Handover 0062)."""

    id: str
    name: str
    type: str
    status: str
    job_mission: str | None = None
    job_id: str | None = None


class MessageSummary(BaseModel):
    """Summary of a message in the project (Handover 0062)."""

    id: str
    from_agent: str
    to_agents: list[str]
    content: str
    timestamp: str


class ProjectSummaryResponse(BaseModel):
    """Comprehensive project summary for after-action review (Handover 0062)."""

    project_id: str
    project_name: str
    description: str
    mission: str | None = None
    status: str
    agents: list[AgentSummary]
    messages: list[MessageSummary]
    created_at: str
    completed_at: str | None = None


# ============================================================================
# Lifecycle Models
# ============================================================================


class StagingCancellationResponse(BaseModel):
    """Response model for staging cancellation (Handover 0108)."""

    success: bool = Field(..., description="Whether staging cancellation succeeded")
    agents_deleted: int = Field(..., description="Number of agents deleted/soft-deleted")
    agents_protected: int = Field(..., description="Number of agents protected (already launched)")
    staging_status: str | None = Field(None, description="Updated staging_status (should be None)")
    message: str = Field(..., description="User-readable result message")
    rollback_timestamp: str | None = Field(None, description="ISO timestamp of rollback")


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

    job_id: str
    agent_id: str  # Alias for backward compatibility
    agent_display_name: str
    agent_name: str | None
    mission: str
    status: str
    progress: int
    tool_type: str
    created_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None


class OrchestratorResponse(BaseModel):
    """Response for GET /{project_id}/orchestrator."""

    success: bool
    orchestrator: OrchestratorJobResponse | None = None  # Handover 0506: Optional when no orchestrator exists


# ============================================================================
# Taxonomy Endpoint Response Models (Handover 0440d)
# ============================================================================


class SeriesCheckResponse(BaseModel):
    """Response for GET /check-series."""

    available: bool


class UsedSubseriesResponse(BaseModel):
    """Response for GET /used-subseries."""

    used_subseries: list[str]


class NextSeriesResponse(BaseModel):
    """Response for GET /next-series."""

    next_series_number: int


class AvailableSeriesResponse(BaseModel):
    """Response for GET /available-series."""

    available_series_numbers: list[int]


# ============================================================================
# Project Review Models (IMP-3: Project detail with agents + memory)
# ============================================================================


class AgentJobDetail(BaseModel):
    """Agent job detail for project review."""

    job_id: str
    job_type: str
    status: str
    display_name: str
    agent_status: str
    mission: str | None = None
    result: dict | None = None
    created_at: str | None = None
    completed_at: str | None = None


class MemoryEntryDetail(BaseModel):
    """360 memory entry detail for project review."""

    id: str
    entry_type: str
    sequence: int
    project_name: str | None = None
    summary: str | None = None
    key_outcomes: list = Field(default_factory=list)
    decisions_made: list = Field(default_factory=list)
    git_commits: list = Field(default_factory=list)
    timestamp: str | None = None


class ProjectReviewResponse(BaseModel):
    """Extended project detail with agent jobs and 360 memory entries.

    Used by the frontend project review modal (Phase 2).
    """

    project: ProjectResponse
    agent_jobs: list[AgentJobDetail] = Field(default_factory=list)
    memory_entries: list[MemoryEntryDetail] = Field(default_factory=list)
