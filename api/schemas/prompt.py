"""
Prompt Generation API Pydantic schemas for Handover 0073: Static Agent Grid.

Provides request/response models for:
- Orchestrator prompt generation (Claude Code, Codex, Gemini)
- Agent prompt generation (universal terminal prompts)
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Prompt Generation Schemas


class OrchestratorPromptResponse(BaseModel):
    """
    Schema for orchestrator prompt generation response.
    GET /api/prompts/orchestrator/{tool}
    """

    prompt: str = Field(..., description="Multi-line bash commands for orchestrator invocation")
    tool: str = Field(..., description="Tool type: claude-code, codex, gemini")
    instructions: str = Field(..., description="User-readable instructions for using the prompt")
    project_name: str = Field(..., description="Project name")
    project_id: str = Field(..., description="Project ID")
    agent_count: int = Field(..., description="Number of agents in project")

    model_config = ConfigDict(from_attributes=True)


class AgentPromptResponse(BaseModel):
    """
    Schema for agent prompt generation response.
    GET /api/prompts/agent/{agent_id}
    """

    prompt: str = Field(..., description="Multi-line bash commands for agent execution")
    agent_id: str = Field(..., description="Agent job ID")
    agent_name: str = Field(..., description="Agent display name")
    agent_display_name: str = Field(..., description="Human-readable display name for UI")
    tool_type: str = Field(..., description="Tool assigned: claude-code, codex, gemini, universal")
    instructions: str = Field(..., description="User-readable instructions for using the prompt")
    mission_preview: str = Field(..., description="First 200 chars of mission")

    model_config = ConfigDict(from_attributes=True)


# Broadcast Messaging Schemas


class BroadcastMessageRequest(BaseModel):
    """
    Schema for broadcasting a message to all agents in a project.
    POST /api/agent-jobs/broadcast
    """

    project_id: str = Field(..., min_length=1, description="Project ID to broadcast to")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content (max 10000 chars)")

    model_config = ConfigDict(from_attributes=True)


class BroadcastMessageResponse(BaseModel):
    """
    Schema for broadcast message response.
    """

    broadcast_id: str = Field(..., description="Unique broadcast identifier (UUID)")
    message_ids: list[str] = Field(..., description="List of created message IDs")
    agent_count: int = Field(..., description="Number of agents messaged")
    timestamp: str = Field(..., description="Broadcast timestamp (ISO format)")

    model_config = ConfigDict(from_attributes=True)


# Project Closeout Schemas


class AgentStatusSummary(BaseModel):
    """
    Schema for agent status counts in closeout check.
    """

    complete: int = Field(..., description="Count of completed agents")
    failed: int = Field(..., description="Count of failed agents")
    active: int = Field(..., description="Count of active agents (working, preparing, review)")
    blocked: int = Field(..., description="Count of blocked agents")

    model_config = ConfigDict(from_attributes=True)


class ProjectCanCloseResponse(BaseModel):
    """
    Schema for project closeout readiness check.
    GET /api/projects/{project_id}/can-close
    """

    can_close: bool = Field(..., description="Whether project can be closed")
    summary: str | None = Field(None, description="AI-generated summary (if can_close=True)")
    agent_statuses: AgentStatusSummary = Field(..., description="Breakdown of agent statuses")
    all_agents_finished: bool = Field(..., description="Whether all agents have finished")

    model_config = ConfigDict(from_attributes=True)


class ProjectCloseoutPromptResponse(BaseModel):
    """
    Schema for project closeout prompt generation.
    POST /api/projects/{project_id}/generate-closeout
    """

    prompt: str = Field(..., description="Multi-line bash script for closeout")
    checklist: list[str] = Field(..., description="Closeout checklist items")
    project_name: str = Field(..., description="Project name")
    agent_summary: str = Field(..., description="Summary of agent work")

    model_config = ConfigDict(from_attributes=True)


class ProjectCompleteRequest(BaseModel):
    """
    Schema for completing a project.
    POST /api/projects/{project_id}/complete
    """

    summary: str = Field(
        ...,
        min_length=50,
        max_length=5000,
        description="Comprehensive project summary (2-3 paragraphs)",
    )
    key_outcomes: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of tangible deliverables/achievements",
    )
    decisions_made: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="List of architectural/technical decisions",
    )
    confirm_closeout: bool = Field(..., description="Must be True to confirm closeout")

    model_config = ConfigDict(from_attributes=True)


class ProjectCompleteResponse(BaseModel):
    """
    Schema for project completion response.
    """

    success: bool = Field(..., description="Whether project was successfully completed")
    completed_at: str = Field(..., description="Completion timestamp (ISO format)")
    memory_updated: bool = Field(..., description="Whether 360 Memory was updated")
    sequence_number: int = Field(..., description="Sequential history entry number")
    git_commits_count: int = Field(..., description="Number of commits captured (if GitHub enabled)")

    model_config = ConfigDict(from_attributes=True)


class ProjectCloseoutDataResponse(BaseModel):
    """
    Schema for project closeout data response.
    GET /api/projects/{project_id}/closeout

    Returns basic project metadata for closeout.
    Frontend fetches 360 memory entries directly from the product.
    """

    project_id: str = Field(..., description="Project UUID")
    project_name: str = Field(..., description="Project name")
    agent_count: int = Field(..., ge=0, description="Number of agents in the project")
    completed_agents: int = Field(..., ge=0, description="Number of completed agents")
    failed_agents: int = Field(..., ge=0, description="Number of failed agents")
    all_agents_complete: bool = Field(..., description="Whether all agents finished work")
    has_failed_agents: bool = Field(..., description="Whether any agents failed")

    model_config = ConfigDict(from_attributes=True)


# Thin Client Prompt Schemas (Handover 0088)


class OrchestratorPromptRequest(BaseModel):
    """
    Schema for thin client orchestrator prompt request.
    POST /api/prompts/orchestrator
    """

    project_id: str = Field(..., min_length=1, description="Project UUID")
    tool: Literal["claude-code", "codex", "gemini"] = Field("claude-code", description="Target AI tool")

    model_config = ConfigDict(from_attributes=True)


class ThinPromptResponse(BaseModel):
    """
    Schema for thin client prompt response (Handover 0088).

    This is the response for the NEW thin client architecture that
    generates ~10 line prompts instead of 2000-3000 line fat prompts.

    Key differences from OrchestratorPromptResponse:
    - estimated_prompt_tokens: ~50 tokens (vs ~30,000)
    - thin_client: Always True (indicates thin client architecture)
    - instructions_stored: Mission stored in database, not embedded
    - mcp_tool_name: The MCP tool orchestrator will call to fetch mission
    """

    prompt: str = Field(..., description="Thin client prompt (~10 lines)")
    orchestrator_id: str = Field(..., description="Created orchestrator job ID")
    project_id: str = Field(..., description="Project UUID")
    project_name: str = Field(..., description="Project name")
    estimated_prompt_tokens: int = Field(..., description="Token estimate for prompt (~50)")
    mcp_tool_name: str = Field(..., description="MCP tool to fetch mission")
    instructions_stored: bool = Field(..., description="Whether instructions are stored in database")
    thin_client: bool = Field(default=True, description="Always True for thin client architecture")

    model_config = ConfigDict(from_attributes=True)
