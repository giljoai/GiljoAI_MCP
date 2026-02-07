"""
Pydantic Models for Product Endpoints - Handover 0126

Request/response models for product operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Request model for creating a product"""

    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    project_path: Optional[str] = Field(
        None, description="File system path to product folder (required for agent export)"
    )
    config_data: Optional[Dict[str, Any]] = Field(None, description="Rich configuration data (JSONB)")
    product_memory: Optional[Dict[str, Any]] = Field(
        None, description="360 Memory storage (GitHub, learnings, context) - Handover 0135"
    )
    target_platforms: Optional[List[str]] = Field(
        default=["all"], description="Target platforms: windows, linux, macos, or all - Handover 0425"
    )


class ProductUpdate(BaseModel):
    """Request model for updating a product"""

    name: Optional[str] = None
    description: Optional[str] = None
    project_path: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = Field(None, description="Rich configuration data (JSONB)")
    product_memory: Optional[Dict[str, Any]] = Field(
        None, description="360 Memory storage (GitHub, learnings, context) - Handover 0135"
    )
    target_platforms: Optional[List[str]] = Field(
        None, description="Target platforms: windows, linux, macos, or all - Handover 0425"
    )


class ProductResponse(BaseModel):
    """Response model for product operations"""

    id: str
    name: str
    description: Optional[str]
    vision_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    project_count: int = 0
    task_count: int = 0
    has_vision: bool = False
    unresolved_tasks: int = 0
    unfinished_projects: int = 0
    vision_documents_count: int = 0
    config_data: Optional[dict] = Field(None, description="Rich configuration data")
    has_config_data: bool = Field(False, description="Whether product has config_data populated")
    is_active: bool = Field(False, description="Whether this product is currently active")
    project_path: Optional[str] = Field(
        None, description="File system path to product folder (required for agent export)"
    )
    product_memory: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {"github": {}, "sequential_history": [], "context": {}},
        description="360 Memory storage (GitHub, sequential_history, context) - Handover 0412",
    )
    target_platforms: Optional[List[str]] = Field(
        default=["all"], description="Target platforms: windows, linux, macos, or all - Handover 0425"
    )


class ActiveProductInfo(BaseModel):
    """Minimal active product info for efficient responses"""

    id: str
    name: str
    description: Optional[str]
    activated_at: datetime = Field(description="When this product was activated")
    active_projects_count: int = Field(default=0, description="Number of active projects")


class ProductActivationResponse(BaseModel):
    """Response for product activation matching frontend expectations (Handover 0503)"""

    product_id: str = Field(..., description="ID of the activated product")
    previous_active_product_id: Optional[str] = Field(
        None, description="ID of previously active product (if any) that was deactivated"
    )
    product: ProductResponse = Field(..., description="Full activated product details")
    message: str = Field(..., description="Success message")
    deactivated_projects: List[str] = Field(default_factory=list, description="IDs of projects that were auto-paused")


class ProductDeleteResponse(BaseModel):
    """Enhanced response for product deletion"""

    message: str
    deleted_product_id: str
    was_active: bool = Field(description="Whether the deleted product was active")
    remaining_products_count: int
    new_active_product: Optional[ActiveProductInfo] = Field(
        None, description="Auto-activated product (if deleted product was active)"
    )


class ActiveProductRefreshResponse(BaseModel):
    """Response for /refresh-active endpoint"""

    has_active_product: bool = Field(False, description="Whether there is an active product")
    product: Optional[ProductResponse] = Field(None, description="Full product details if active")
    total_products_count: Optional[int] = None
    last_refreshed_at: Optional[datetime] = None


class DeletedProductResponse(BaseModel):
    """Response model for deleted products list"""

    id: str
    name: str
    description: Optional[str]
    deleted_at: datetime
    days_until_purge: int = Field(ge=0, description="Days remaining before permanent deletion")
    purge_date: datetime = Field(description="Date when product will be permanently deleted")
    project_count: int = Field(ge=0, description="Total projects under this product")
    vision_documents_count: int = Field(ge=0, description="Total vision documents")


class VisionChunk(BaseModel):
    """Response model for vision document chunks"""

    chunk_number: int
    total_chunks: int
    content: str
    char_start: int
    char_end: int
    boundary_type: str
    keywords: List[str]
    headers: List[str]


class VisionDocumentStatsResponse(BaseModel):
    """Vision document statistics response for active product"""

    product_id: str = Field(..., description="Active product ID")
    product_name: str = Field(..., description="Active product name")
    has_vision_document: bool = Field(..., description="Whether active product has a vision document")
    total_tokens: int = Field(default=0, description="Total tokens in vision document")
    chunk_count: int = Field(default=0, description="Number of chunks in vision document")
    is_summarized: bool = Field(default=False, description="Whether vision document is summarized")
    summary_tokens: int = Field(default=0, description="Token count of summary (if available)")


class CascadeImpact(BaseModel):
    """Cascade impact response for product deletion"""

    product_id: str
    product_name: str = Field(..., description="Product name")
    total_projects: int = Field(..., description="Total number of projects")
    total_tasks: int = Field(..., description="Total number of tasks")
    total_vision_documents: int = Field(..., description="Number of vision documents")
    warning: str = Field(..., description="Warning message about deletion impact")


# ============================================================================
# GitHub Integration Settings (Handover 0137)
# ============================================================================


class GitHubSettingsRequest(BaseModel):
    """Request model for updating GitHub integration settings"""

    enabled: bool = Field(..., description="Whether GitHub integration is enabled")
    repo_url: Optional[str] = Field(
        None,
        description="GitHub repository URL (HTTPS or SSH format). Required when enabled=True",
    )
    auto_commit: bool = Field(False, description="Whether to automatically commit changes to GitHub")


class GitHubSettingsResponse(BaseModel):
    """Response model for GitHub integration settings"""

    enabled: bool = Field(..., description="Whether GitHub integration is enabled")
    repo_url: Optional[str] = Field(None, description="GitHub repository URL (HTTPS or SSH format)")
    auto_commit: bool = Field(..., description="Whether to automatically commit changes to GitHub")
    last_sync: Optional[str] = Field(None, description="ISO timestamp of last sync with GitHub")


# ============================================================================
# Git Integration Settings (Handover 013B - Simplified)
# ============================================================================


class GitIntegrationRequest(BaseModel):
    """Request model for updating Git integration settings (Handover 013B)"""

    enabled: bool = Field(..., description="Whether Git integration is enabled")
    commit_limit: int = Field(20, ge=1, le=100, description="Max commits to include in prompts (1-100)")
    default_branch: str = Field("main", description="Default branch name (e.g., main, master, develop)")


class GitIntegrationResponse(BaseModel):
    """Response model for Git integration settings (Handover 013B)"""

    enabled: bool = Field(..., description="Whether Git integration is enabled")
    commit_limit: int = Field(..., description="Max commits to include in prompts")
    default_branch: str = Field(..., description="Default branch name")


# ============================================================================
# 360 Memory Entries (Handover 0490)
# ============================================================================


class MemoryEntryResponse(BaseModel):
    """Response model for a single 360 memory entry"""

    id: str = Field(..., description="Entry UUID")
    sequence: int = Field(..., description="Sequence number within product")
    entry_type: str = Field(..., description="Entry type (project_closeout, session_handover, etc.)")
    source: str = Field(..., description="Source tool identifier")
    timestamp: str = Field(..., description="ISO timestamp of entry creation")
    project_id: Optional[str] = Field(None, description="Source project UUID (if applicable)")
    project_name: Optional[str] = Field(None, description="Project name at time of entry")
    summary: Optional[str] = Field(None, description="2-3 paragraph summary")
    key_outcomes: list[str] = Field(default_factory=list, description="Key achievements")
    decisions_made: list[str] = Field(default_factory=list, description="Architectural/design decisions")
    git_commits: list[dict[str, Any]] = Field(default_factory=list, description="Git commit objects")
    deliverables: list[Any] = Field(default_factory=list, description="Deliverables/artifacts")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Metrics dictionary")
    priority: int = Field(default=3, description="Priority level 1-5")
    significance_score: float = Field(default=0.5, description="Significance score 0.0-1.0")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    author_job_id: Optional[str] = Field(None, description="Job ID of authoring agent")
    author_name: Optional[str] = Field(None, description="Name of authoring agent")
    author_type: Optional[str] = Field(None, description="Type of authoring agent")
    deleted_by_user: bool = Field(default=False, description="Whether entry was soft-deleted")


class MemoryEntriesResponse(BaseModel):
    """Response model for memory entries list endpoint"""

    success: bool = Field(default=True, description="Operation success status")
    entries: list[MemoryEntryResponse] = Field(default_factory=list, description="Memory entries array")
    total_count: int = Field(..., description="Total entries for product (including deleted)")
    filtered_count: int = Field(..., description="Count of entries returned (after filters)")
