"""
Pydantic Models for Template Endpoints - Handover 0126

Request/response models for template operations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Maximum template sizes
MAX_TEMPLATE_SIZE = 100 * 1024  # 100KB
MAX_USER_INSTRUCTIONS_SIZE = 50 * 1024  # 50KB


class TemplateCreate(BaseModel):
    """Request model for creating a template"""

    # Name is optional; when omitted, the backend generates it from role/suffix.
    name: Optional[str] = Field(None, description="Template name (optional, generated from role when omitted)")
    role: str = Field(..., description="Agent role")
    cli_tool: str = Field("claude", description="CLI tool: claude, codex, gemini, generic")
    custom_suffix: Optional[str] = Field(None, description="Custom suffix for name generation")
    background_color: Optional[str] = Field(None, description="Background color (hex)")
    description: Optional[str] = Field(None, description="Template description")
    system_instructions: str = Field(..., description="System prompt content")
    model: Optional[str] = Field("sonnet", description="Model: sonnet, opus, haiku, inherit")
    tools: Optional[str] = Field(None, description="Tool selection (null = inherit all)")
    behavioral_rules: Optional[list[str]] = Field(default_factory=list)
    success_criteria: Optional[list[str]] = Field(default_factory=list)
    tags: Optional[list[str]] = Field(default_factory=list)
    is_default: bool = Field(default=False, description="Set as default for this role")
    is_active: bool = Field(default=False, description="Set template as active")
    # Legacy fields
    category: Optional[str] = Field(None, description="Template category (deprecated)")
    project_type: Optional[str] = Field(None, description="Project type (deprecated)")
    preferred_tool: Optional[str] = Field(None, description="Preferred AI tool (deprecated)")

    @field_validator("system_instructions")
    @classmethod
    def validate_template_size(cls, v: str) -> str:
        """Validate template content size (max 100KB)"""
        if len(v.encode("utf-8")) > MAX_TEMPLATE_SIZE:
            raise ValueError(f"Template content exceeds maximum size of {MAX_TEMPLATE_SIZE / 1024}KB")
        return v


class TemplateUpdate(BaseModel):
    """Request model for updating a template"""

    # Editable fields
    system_instructions: Optional[str] = Field(
        None, description="System instructions are read-only via API; presence triggers a 403"
    )
    user_instructions: Optional[str] = Field(None, description="User-customizable instructions (max 50KB)")
    name: Optional[str] = None
    role: Optional[str] = None
    cli_tool: Optional[str] = None
    background_color: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    behavioral_rules: Optional[list[str]] = None
    success_criteria: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    # Legacy support
    preferred_tool: Optional[str] = None

    @field_validator("user_instructions")
    @classmethod
    def validate_user_instructions_size(cls, v: Optional[str]) -> Optional[str]:
        """Validate user instructions size (max 50KB)"""
        if v and len(v.encode("utf-8")) > MAX_USER_INSTRUCTIONS_SIZE:
            raise ValueError("User instructions exceed 50KB limit")
        return v


class TemplateResponse(BaseModel):
    """Response model for template operations"""

    id: str
    tenant_key: str
    product_id: Optional[str]
    name: str
    role: str
    cli_tool: str
    background_color: Optional[str]
    description: Optional[str]
    # Dual fields (v3.1+)
    system_instructions: str = Field(..., description="Read-only MCP coordination instructions")
    user_instructions: Optional[str] = Field(None, description="User-customizable instructions")
    model: Optional[str]
    tools: Optional[str]
    behavioral_rules: list[str]
    success_criteria: list[str]
    tags: list[str]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    # Export tracking (Handover 0335)
    last_exported_at: Optional[datetime] = Field(default=None, description="Timestamp of last export to CLI")
    may_be_stale: bool = Field(default=False, description="True if template modified after last export")
    # Legacy fields
    category: Optional[str] = None
    project_type: Optional[str] = None
    variables: list[str] = []
    version: str = "1.0.0"
    usage_count: int = 0
    avg_generation_ms: Optional[float] = None
    created_by: Optional[str] = None
    preferred_tool: str = "claude"
    is_system_role: bool = Field(default=False, description="True when template is system managed")


class TemplateHistoryResponse(BaseModel):
    """Response model for template history"""

    id: str
    template_id: str
    name: str
    version: str
    system_instructions: Optional[str] = None
    user_instructions: Optional[str] = None
    archive_reason: Optional[str]
    archive_type: str
    archived_by: Optional[str]
    archived_at: datetime
    is_restorable: bool
    usage_count_at_archive: Optional[int]
    avg_generation_ms_at_archive: Optional[float]


class TemplateDiffResponse(BaseModel):
    """Response model for template diff comparison"""

    template_id: str
    template_name: str
    tenant_version: str
    system_version: Optional[str]
    has_system_template: bool
    is_customized: bool
    diff_html: Optional[str] = Field(None, description="HTML diff output")
    diff_unified: Optional[str] = Field(None, description="Unified diff format")
    changes_summary: dict = Field(default_factory=dict, description="Summary of changes")


class TemplatePreviewRequest(BaseModel):
    """Request model for template preview"""

    variables: dict[str, str] = Field(default_factory=dict, description="Variable substitutions")
    augmentations: Optional[str] = Field(None, description="Additional augmentation content")


class TemplatePreviewResponse(BaseModel):
    """Response model for template preview"""

    template_id: str
    cli_tool: str = Field(..., description="CLI tool type")
    preview: str = Field(..., description="Rendered template content")
    variables_used: list[str] = Field(default_factory=list, description="Variables found in template")
