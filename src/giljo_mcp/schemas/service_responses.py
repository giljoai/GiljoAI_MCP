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


class SendMessageResult(BaseModel):
    """Message send result."""

    message_id: str
    delivered_to: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class BroadcastResult(BaseModel):
    """Broadcast message result."""

    broadcast_id: str
    recipients_count: int = 0
    message_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MessageListResult(BaseModel):
    """Message list result."""

    messages: list[dict] = Field(default_factory=list)
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Orchestration Service Models
# ---------------------------------------------------------------------------


class SpawnResult(BaseModel):
    """Agent spawn result."""

    job_id: str
    agent_role: str
    project_id: str
    status: str = "pending"

    model_config = ConfigDict(from_attributes=True)


class MissionResponse(BaseModel):
    """Agent mission response."""

    job_id: str
    mission: str
    full_protocol: Optional[str] = None
    agent_role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MissionUpdateResult(BaseModel):
    """Mission update result."""

    job_id: str
    mission_updated: bool = True

    model_config = ConfigDict(from_attributes=True)


class InstructionsResponse(BaseModel):
    """Orchestrator instructions response."""

    orchestrator_id: str
    instructions: str
    priority_categories: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SuccessionResult(BaseModel):
    """Orchestrator succession result."""

    predecessor_id: str
    successor_id: str
    handover_summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SuccessionStatus(BaseModel):
    """Orchestrator succession status."""

    orchestrator_id: str
    context_used: int = 0
    context_budget: int = 0
    succession_recommended: bool = False
    active_agents: int = 0

    model_config = ConfigDict(from_attributes=True)


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


class ConsolidationResult(BaseModel):
    """Vision document consolidation result."""

    product_id: str
    documents_consolidated: int = 0
    aggregate: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Auth Service Models
# ---------------------------------------------------------------------------


class AuthResult(BaseModel):
    """Authentication result."""

    user_id: str
    username: str
    token: str
    tenant_key: str
    role: str = "user"

    model_config = ConfigDict(from_attributes=True)


class SetupState(BaseModel):
    """System setup state."""

    is_configured: bool = False
    has_admin: bool = False
    has_database: bool = False

    model_config = ConfigDict(from_attributes=True)
