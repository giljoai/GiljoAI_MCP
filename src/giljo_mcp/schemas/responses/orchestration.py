# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Orchestration service response models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentTodoCounts(BaseModel):
    """Per-agent todo item counts by status."""

    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    skipped: int = 0


class AgentWorkflowDetail(BaseModel):
    """Per-agent detail within workflow status."""

    job_id: str
    agent_id: str
    agent_name: str = ""
    display_name: str = ""
    status: str = ""
    job_type: str = ""
    unread_messages: int = 0
    todos: AgentTodoCounts = AgentTodoCounts()


class WorkflowStatus(BaseModel):
    """Workflow status for a project.

    Fields match OrchestrationService.get_workflow_status() output.
    Tracks agent execution counts and overall progress.
    """

    active_agents: int = 0
    completed_agents: int = 0
    pending_agents: int = 0
    blocked_agents: int = 0
    silent_agents: int = 0
    decommissioned_agents: int = 0
    current_stage: str = "Not started"
    progress_percent: float = 0.0
    total_agents: int = 0
    caller_note: str = ""
    agents: list[AgentWorkflowDetail] = []

    model_config = ConfigDict(from_attributes=True)


class SpawnResult(BaseModel):
    """Agent spawn result.

    Fields match OrchestrationService.spawn_job() output.
    Contains both work order (job_id) and executor (agent_id) UUIDs
    plus the thin client prompt for agent startup.
    """

    job_id: str
    agent_id: str
    execution_id: Optional[str] = None
    agent_display_name: Optional[str] = None
    agent_prompt: str
    mission_stored: bool = True
    thin_client: bool = True
    thin_client_note: list[str] = Field(default_factory=list)
    predecessor_job_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MissionResponse(BaseModel):
    """Agent mission response.

    Fields match OrchestrationService.get_agent_mission() output.
    Contains the full team-aware mission with lifecycle protocol.
    """

    job_id: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    agent_display_name: Optional[str] = None
    agent_identity: Optional[str] = None
    mission: Optional[str] = None
    project_id: Optional[str] = None
    parent_job_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    thin_client: bool = True
    full_protocol: Optional[str] = None
    current_team_state: Optional[list[dict]] = Field(
        default=None,
        description="Orchestrator-only. Live team state with agent statuses. Null for non-orchestrator agents.",
    )
    blocked: bool = False
    error: Optional[str] = None
    user_instruction: Optional[str] = Field(
        default=None,
        description="Present only when blocked=True. Contains guidance for the blocked state. Null in normal responses.",
    )

    model_config = ConfigDict(from_attributes=True)


class PendingJobsResult(BaseModel):
    """Pending jobs list result.

    Fields match OrchestrationService.get_pending_jobs() output.
    """

    jobs: list[dict] = Field(default_factory=list)
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ProgressResult(BaseModel):
    """Progress report result.

    Fields match OrchestrationService.report_progress() output.
    """

    status: str = "success"
    message: str = "Progress reported successfully"
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CompleteJobResult(BaseModel):
    """Job completion result.

    Fields match OrchestrationService.complete_job() output.
    """

    status: str = "success"
    job_id: str
    message: str = "Job completed successfully"
    warnings: list[str] = Field(default_factory=list)
    result_stored: bool = False
    closeout_checklist: dict | None = Field(
        default=None,
        description="HITL closeout checklist (orchestrator jobs only)",
    )

    model_config = ConfigDict(from_attributes=True)


class ReactivationResult(BaseModel):
    """Reactivation result (Handover 0827c).

    Returned by OrchestrationService.reactivate_job().
    """

    status: str = "reactivated"
    job_id: str
    reactivation_count: int = 1
    instruction: str = ""

    model_config = ConfigDict(from_attributes=True)


class DismissResult(BaseModel):
    """Dismiss reactivation result (Handover 0827c).

    Returned by OrchestrationService.dismiss_reactivation().
    """

    status: str = "dismissed"
    job_id: str
    instruction: str = "Message acknowledged. No action needed. You remain in complete status."

    model_config = ConfigDict(from_attributes=True)


class ErrorReportResult(BaseModel):
    """Agent status change result (Handover 0880: expanded from report_error).

    Returned by OrchestrationService.set_agent_status() for blocked/idle/sleeping states.
    """

    job_id: str
    message: str = "Status updated"
    status: str = "blocked"
    block_reason: Optional[str] = None
    guidance: str = "To resume, call report_progress() with updated todo_items."

    model_config = ConfigDict(from_attributes=True)


class JobListResult(BaseModel):
    """Paginated job list result.

    Fields match OrchestrationService.list_jobs() output.
    """

    jobs: list[dict] = Field(default_factory=list)
    total: int = 0
    limit: int = 100
    offset: int = 0

    model_config = ConfigDict(from_attributes=True)


class MissionUpdateResult(BaseModel):
    """Mission update result.

    Fields match OrchestrationService.update_agent_mission() output.
    """

    job_id: str
    mission_updated: bool = True
    mission_length: int = 0

    model_config = ConfigDict(from_attributes=True)


class SuccessionContextResult(BaseModel):
    """Successor orchestrator context result (Handover 0461f).

    Fields match OrchestrationService.create_successor_orchestrator() output.
    Same agent_id is preserved (no ID swap); context is reset and written to 360 Memory.
    """

    job_id: str
    agent_id: str
    context_reset: bool = True
    memory_entry_created: bool = True
    reason: str = "manual"
    message: str = ""

    model_config = ConfigDict(from_attributes=True)


class SuccessionStatus(BaseModel):
    """Orchestrator succession status check result.

    Fields match OrchestrationService.check_succession_status() output.
    """

    should_trigger: bool = False
    usage_percentage: float = 0.0
    threshold_reached: bool = False
    recommendation: str = ""

    model_config = ConfigDict(from_attributes=True)


# Legacy aliases for backward compatibility with existing imports.
InstructionsResponse = SuccessionContextResult
SuccessionResult = SuccessionContextResult
