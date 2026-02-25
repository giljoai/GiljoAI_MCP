"""
Service-layer Pydantic response models for GiljoAI MCP.

These models replace dict[str, Any] returns in service methods, providing
type safety, validation, and self-documenting API contracts at the service
layer. They live under src/giljo_mcp/schemas/ (separate from api/schemas/
which houses request/response models for HTTP endpoints).

Each model uses ConfigDict(from_attributes=True) to support construction
from SQLAlchemy ORM instances via model_validate(orm_obj).

Created: Handover 0731
"""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Shared Result Types
# ---------------------------------------------------------------------------


class DeleteResult(BaseModel):
    """Standard delete operation result."""

    deleted: bool = True
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OperationResult(BaseModel):
    """Generic operation success result with a message."""

    message: str

    model_config = ConfigDict(from_attributes=True)


class TransferResult(BaseModel):
    """Ownership transfer result."""

    transferred: bool = True
    from_user_id: str
    to_user_id: str

    model_config = ConfigDict(from_attributes=True)


class PaginatedResult(BaseModel, Generic[T]):
    """Paginated list result."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Product Service Models
# ---------------------------------------------------------------------------


class ProductStatistics(BaseModel):
    """Product statistics response.

    Fields match ProductService._get_product_metrics() output plus product metadata.
    """

    product_id: str
    name: str
    is_active: bool
    project_count: int = 0
    unfinished_projects: int = 0
    task_count: int = 0
    unresolved_tasks: int = 0
    vision_documents_count: int = 0
    has_vision: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CascadeImpact(BaseModel):
    """Cascade delete impact analysis.

    Fields match ProductService.get_cascade_impact() output.
    """

    product_id: str
    product_name: str
    total_projects: int = 0
    total_tasks: int = 0
    total_vision_documents: int = 0
    warning: str = ""

    model_config = ConfigDict(from_attributes=True)


class VisionUploadResult(BaseModel):
    """Vision document upload result.

    Fields match ProductService.upload_vision_document() output.
    """

    document_id: str
    document_name: str
    chunks_created: int = 0
    total_tokens: int = 0

    model_config = ConfigDict(from_attributes=True)


class PurgeResult(BaseModel):
    """Purge expired deleted products result."""

    purged_count: int = 0
    purged_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PathValidationResult(BaseModel):
    """Project path validation result."""

    valid: bool
    path: str
    message: str = ""

    model_config = ConfigDict(from_attributes=True)


class GitIntegrationSettings(BaseModel):
    """Git integration settings."""

    enabled: bool = False
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    auto_commit: bool = False

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Task Service Models
# ---------------------------------------------------------------------------


class TaskListResponse(BaseModel):
    """Task list with count."""

    tasks: list[dict] = Field(default_factory=list)
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TaskUpdateResult(BaseModel):
    """Task update result."""

    task_id: str
    updated_fields: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TaskSummary(BaseModel):
    """Task summary statistics."""

    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class ConversionResult(BaseModel):
    """Task-to-project conversion result."""

    task_id: str
    project_id: str
    project_name: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Message Service Models
# ---------------------------------------------------------------------------


class StagingDirective(BaseModel):
    """Staging session completion directive for orchestrator stop signal.

    Defense-in-depth Layer 5.5: Reinforced advisory STOP signal for staging
    completion (Handover 0709b).
    """

    status: str
    action: str
    message: str
    implementation_gate: str
    next_step: str

    model_config = ConfigDict(from_attributes=True)


class SendMessageResult(BaseModel):
    """Message send result.

    Returned by send_message() and broadcast().
    message_id is Optional because broadcasting to an empty project yields None.
    staging_directive is present only when a staging-phase orchestrator broadcasts.
    """

    message_id: Optional[str] = None
    to_agents: list[str] = Field(default_factory=list)
    message_type: str = "direct"
    staging_directive: Optional[StagingDirective] = None

    model_config = ConfigDict(from_attributes=True)


class BroadcastResult(BaseModel):
    """Broadcast-to-project result.

    Extends SendMessageResult semantics with a recipient count.
    Returned by broadcast_to_project().
    """

    message_id: Optional[str] = None
    to_agents: list[str] = Field(default_factory=list)
    message_type: str = "broadcast"
    recipients_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MessageListResult(BaseModel):
    """Message list result.

    Returned by get_messages(), receive_messages(), and list_messages().
    The optional agent field is populated by get_messages() only.
    """

    messages: list[dict] = Field(default_factory=list)
    count: int = 0
    agent: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompleteMessageResult(BaseModel):
    """Message completion result."""

    message_id: str
    completed_by: str

    model_config = ConfigDict(from_attributes=True)


class AcknowledgeMessageResult(BaseModel):
    """Message acknowledgment result."""

    acknowledged: bool = True
    message_id: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Orchestration Service Models
# ---------------------------------------------------------------------------


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

    model_config = ConfigDict(from_attributes=True)


class SpawnResult(BaseModel):
    """Agent spawn result.

    Fields match OrchestrationService.spawn_agent_job() output.
    Contains both work order (job_id) and executor (agent_id) UUIDs
    plus the thin client prompt for agent startup.
    """

    job_id: str
    agent_id: str
    execution_id: Optional[str] = None
    agent_prompt: str
    prompt_tokens: int = 0
    mission_stored: bool = True
    mission_tokens: int = 0
    total_tokens: int = 0
    thin_client: bool = True
    thin_client_note: list[str] = Field(default_factory=list)

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
    mission: Optional[str] = None
    project_id: Optional[str] = None
    parent_job_id: Optional[str] = None
    estimated_tokens: int = 0
    status: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    thin_client: bool = True
    full_protocol: Optional[str] = None
    blocked: bool = False
    error: Optional[str] = None
    user_instruction: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PendingJobsResult(BaseModel):
    """Pending jobs list result.

    Fields match OrchestrationService.get_pending_jobs() output.
    """

    jobs: list[dict] = Field(default_factory=list)
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AcknowledgeJobResult(BaseModel):
    """Job acknowledgment result.

    Fields match OrchestrationService.acknowledge_job() output.
    """

    job: dict = Field(default_factory=dict)
    next_instructions: str = "Begin executing your mission"

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

    model_config = ConfigDict(from_attributes=True)


class ErrorReportResult(BaseModel):
    """Error report result.

    Fields match OrchestrationService.report_error() output.
    """

    job_id: str
    message: str = "Error reported"

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
# These models were replaced by more specific types but are kept as aliases
# so that existing test files and __init__.py exports continue to work.
InstructionsResponse = SuccessionContextResult  # Legacy alias; orchestrator instructions returns dict
SuccessionResult = SuccessionContextResult  # Legacy alias; renamed to SuccessionContextResult in 0731c


# ---------------------------------------------------------------------------
# Template Service Models
# ---------------------------------------------------------------------------


class TemplateListResult(BaseModel):
    """Template list result."""

    templates: list[dict] = Field(default_factory=list)
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Consolidation Service Models
# ---------------------------------------------------------------------------


class SummaryLevel(BaseModel):
    """Single summary level (light or medium) within a consolidation result."""

    summary: str = ""
    tokens: int = 0

    model_config = ConfigDict(from_attributes=True)


class ConsolidationResult(BaseModel):
    """Vision document consolidation result.

    Fields match ConsolidatedVisionService.consolidate_vision_documents() output.
    """

    light: SummaryLevel = Field(default_factory=SummaryLevel)
    medium: SummaryLevel = Field(default_factory=SummaryLevel)
    hash: str = ""
    source_docs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SummarizeSingleResult(BaseModel):
    """Single-document summarization result.

    Fields match VisionDocumentSummarizer.summarize() output.
    """

    summary: str = ""
    original_tokens: int = 0
    summary_tokens: int = 0
    compression_ratio: float = 0.0
    processing_time_ms: int = 0

    model_config = ConfigDict(from_attributes=True)


class MultiLevelSummaryLevel(BaseModel):
    """Single level within a multi-level summarization result."""

    summary: str = ""
    tokens: int = 0
    sentences: int = 0

    model_config = ConfigDict(from_attributes=True)


class SummarizeMultiLevelResult(BaseModel):
    """Multi-level summarization result.

    Fields match VisionDocumentSummarizer.summarize_multi_level() output.
    """

    light: MultiLevelSummaryLevel = Field(default_factory=MultiLevelSummaryLevel)
    medium: MultiLevelSummaryLevel = Field(default_factory=MultiLevelSummaryLevel)
    original_tokens: int = 0
    processing_time_ms: int = 0

    model_config = ConfigDict(from_attributes=True)


class TemplateDetail(BaseModel):
    """Single template detail for get_template response."""

    id: str
    name: str
    role: Optional[str] = None
    content: Optional[str] = None
    cli_tool: Optional[str] = None
    background_color: Optional[str] = None
    category: Optional[str] = None
    tenant_key: Optional[str] = None
    product_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TemplateGetResult(BaseModel):
    """Single template retrieval result."""

    template: TemplateDetail

    model_config = ConfigDict(from_attributes=True)


class TemplateCreateResult(BaseModel):
    """Template creation result."""

    template_id: str
    name: str
    tenant_key: str

    model_config = ConfigDict(from_attributes=True)


class TemplateUpdateResult(BaseModel):
    """Template update result."""

    template_id: str
    updated: bool = True

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Project Service Models
# ---------------------------------------------------------------------------


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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    agents: list[dict] = Field(default_factory=list)
    agent_count: int = 0
    message_count: int = 0
    # Handover 0440a: Project taxonomy fields
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None  # Handover 0440c: Nested type info
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None

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
    # Handover 0440a: Project taxonomy fields
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None  # Handover 0440c: Nested type info
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None

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
    # Handover 0440a: Project taxonomy fields
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None  # Handover 0440c: Nested type info
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None

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
    meta_data: dict = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    activated_at: Optional[str] = None
    completed_at: Optional[str] = None
    product_id: Optional[str] = None
    # Handover 0440a: Project taxonomy fields
    project_type_id: Optional[str] = None
    project_type: Optional[ProjectTypeInfo] = None  # Handover 0440c: Nested type info
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None

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


# ---------------------------------------------------------------------------
# Auth Service Models
# ---------------------------------------------------------------------------


class AuthResult(BaseModel):
    """Authentication result returned by authenticate_user and create_first_admin.

    Contains the authenticated user's profile data and a JWT token for
    session establishment.  Optional fields (email, full_name, is_active,
    created_at, last_login) are populated when the full user profile is
    available (e.g. authenticate_user), but may be omitted in lightweight
    flows.
    """

    user_id: str
    username: str
    token: str
    tenant_key: str
    role: str = "user"
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    last_login: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SetupStateInfo(BaseModel):
    """Setup state information for a tenant.

    Maps directly to the SetupState ORM model fields returned by
    AuthService.check_setup_state().
    """

    first_admin_created: bool = False
    database_initialized: bool = False
    tenant_key: str

    model_config = ConfigDict(from_attributes=True)


class ApiKeyInfo(BaseModel):
    """API key summary information (no sensitive data).

    Returned by AuthService.list_api_keys(). Contains only the key
    prefix (never the full key or hash) for display purposes.
    """

    id: str
    name: str
    key_prefix: str
    permissions: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: Optional[str] = None
    last_used: Optional[str] = None
    revoked_at: Optional[str] = None
    expires_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResult(BaseModel):
    """Result of creating a new API key.

    Contains the raw API key (shown only once), the key prefix for future
    identification, and the hashed version stored in the database.

    SECURITY: The ``api_key`` field contains the plaintext key and must
    only be returned to the user once at creation time.
    """

    id: str
    name: str
    api_key: str
    key_prefix: str
    key_hash: str
    permissions: list[str] = Field(default_factory=list)
    expires_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserInfo(BaseModel):
    """Basic user profile information returned by registration methods.

    Returned by AuthService.register_user(), create_user_in_org(),
    and _register_user_impl(). Does not include sensitive fields
    like password hashes.
    """

    id: str
    username: str
    email: Optional[str] = None
    role: str
    tenant_key: str

    model_config = ConfigDict(from_attributes=True)


# Keep legacy SetupState alias for backward compatibility with existing imports
SetupState = SetupStateInfo
