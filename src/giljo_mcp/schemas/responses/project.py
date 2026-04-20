# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Project service response models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectTypeInfo(BaseModel):
    """Minimal project type info for embedding in project responses (Handover 0440c)."""

    id: str
    abbreviation: str
    label: str
    color: str

    model_config = ConfigDict(from_attributes=True)


class ProjectDetail(BaseModel):
    """Full project detail with agent information.

    Fields match ProjectService.get_project() output.
    """

    id: str
    alias: Optional[str] = None
    name: str
    mission: Optional[str] = None
    description: Optional[str] = None
    status: str
    staging_status: Optional[str] = None
    product_id: Optional[str] = None
    tenant_key: str
    execution_mode: Optional[str] = None
    auto_checkin_enabled: bool = False
    auto_checkin_interval: int = 10
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancellation_reason: Optional[str] = None
    deactivation_reason: Optional[str] = None
    early_termination: bool = False
    agents: list[dict] = Field(default_factory=list)
    agent_count: int = 0
    message_count: int = 0
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None
    hidden: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProjectListItem(BaseModel):
    """Project item for list operations.

    Fields match ProjectService.list_projects() output per item.
    """

    id: str
    name: str
    mission: Optional[str] = None
    description: Optional[str] = None
    status: str
    staging_status: Optional[str] = None
    tenant_key: str
    product_id: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None
    hidden: bool = False

    model_config = ConfigDict(from_attributes=True)


class ActiveProjectDetail(BaseModel):
    """Active project detail.

    Fields match ProjectService.get_active_project() output.
    """

    id: str
    alias: str = ""
    name: str
    mission: str = ""
    description: Optional[str] = None
    status: str
    product_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    deleted_at: Optional[str] = None
    agent_count: int = 0
    message_count: int = 0
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None
    hidden: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProjectMissionUpdateResult(BaseModel):
    """Project mission update result."""

    message: str
    project_id: str

    model_config = ConfigDict(from_attributes=True)


class ProjectCompleteResult(BaseModel):
    """Project completion result with memory update metadata."""

    message: str
    memory_updated: bool = False
    sequence_number: int = 0
    git_commits_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ProjectCloseOutResult(BaseModel):
    """Project close-out result with decommissioned agent details."""

    message: str
    agents_decommissioned: int = 0
    decommissioned_agent_ids: list[str] = Field(default_factory=list)
    project_status: str = "completed"

    model_config = ConfigDict(from_attributes=True)


class ProjectResumeResult(BaseModel):
    """Project resume (continue_working) result."""

    message: str
    agents_resumed: int = 0
    resumed_agent_ids: list[str] = Field(default_factory=list)
    project_status: str = "inactive"

    model_config = ConfigDict(from_attributes=True)


class ProjectData(BaseModel):
    """Generic project data for cancel_staging and update_project responses."""

    id: str
    name: str
    status: str
    mission: Optional[str] = None
    description: Optional[str] = None
    execution_mode: Optional[str] = None
    auto_checkin_enabled: bool = False
    auto_checkin_interval: int = 10
    cancellation_reason: Optional[str] = None
    deactivation_reason: Optional[str] = None
    early_termination: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    activated_at: Optional[str] = None
    completed_at: Optional[str] = None
    product_id: Optional[str] = None
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None
    hidden: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProjectSummaryResult(BaseModel):
    """Project summary with metrics for dashboard display."""

    id: str
    name: str
    status: str
    mission: Optional[str] = None
    total_jobs: int = 0
    completed_jobs: int = 0
    blocked_jobs: int = 0
    active_jobs: int = 0
    pending_jobs: int = 0
    completion_percentage: float = 0.0
    created_at: Optional[str] = None
    activated_at: Optional[str] = None
    last_activity_at: Optional[str] = None
    product_id: str = ""
    product_name: str = ""

    model_config = ConfigDict(from_attributes=True)


class CloseoutData(BaseModel):
    """Project closeout data with agent status counts."""

    project_id: str
    project_name: str
    agent_count: int = 0
    completed_agents: int = 0
    blocked_agents: int = 0
    silent_agents: int = 0
    all_agents_complete: bool = False
    has_blocked_agents: bool = False

    model_config = ConfigDict(from_attributes=True)


class CanCloseResult(BaseModel):
    """Project can-close readiness assessment."""

    can_close: bool = False
    summary: Optional[str] = None
    all_agents_finished: bool = False
    agent_statuses: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class CloseoutPromptResult(BaseModel):
    """Closeout prompt and checklist for project completion."""

    prompt: str
    checklist: list[str] = Field(default_factory=list)
    project_name: str
    agent_summary: str

    model_config = ConfigDict(from_attributes=True)


class ProjectLaunchResult(BaseModel):
    """Project launch result with orchestrator details."""

    project_id: str
    orchestrator_job_id: str
    launch_prompt: str
    status: str
    staging_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectSwitchResult(BaseModel):
    """Project switch/context change result."""

    project_id: str
    name: str
    mission: Optional[str] = None
    tenant_key: str

    model_config = ConfigDict(from_attributes=True)


class NuclearDeleteResult(BaseModel):
    """Nuclear (permanent) project deletion result."""

    message: str
    deleted_counts: dict[str, int] = Field(default_factory=dict)
    project_name: str

    model_config = ConfigDict(from_attributes=True)


class SoftDeleteResult(BaseModel):
    """Soft delete project result."""

    message: str
    deleted_at: Optional[str] = None
    decommissioned_jobs: int = 0

    model_config = ConfigDict(from_attributes=True)


class ProjectPurgeResult(BaseModel):
    """Purge deleted projects result."""

    purged_count: int = 0
    projects: list[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
