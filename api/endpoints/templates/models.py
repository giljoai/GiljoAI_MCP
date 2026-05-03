# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Pydantic Models for Template Endpoints - Handover 0126

Request/response models for template operations.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# Maximum template sizes
MAX_TEMPLATE_SIZE = 100 * 1024  # 100KB
MAX_USER_INSTRUCTIONS_SIZE = 50 * 1024  # 50KB


class TemplateCreate(BaseModel):
    """Request model for creating a template"""

    # Name is optional; when omitted, the backend generates it from role/suffix.
    name: str | None = Field(None, description="Template name (optional, generated from role when omitted)")
    role: str = Field(..., description="Agent role")
    cli_tool: str = Field("claude", description="CLI tool: claude, codex, gemini, generic")
    custom_suffix: str | None = Field(None, description="Custom suffix for name generation")
    background_color: str | None = Field(None, description="Background color (hex)")
    description: str | None = Field(None, description="Template description")
    system_instructions: str | None = Field(
        None, description="Ignored on create; backend always injects canonical MCP bootstrap"
    )
    user_instructions: str | None = Field(None, description="User-customizable role identity prose (max 50KB)")
    model: str | None = Field("sonnet", description="Model: sonnet, opus, haiku, inherit")
    tools: str | None = Field(None, description="Tool selection (null = inherit all)")
    behavioral_rules: list[str] | None = Field(default_factory=list)
    success_criteria: list[str] | None = Field(default_factory=list)
    tags: list[str] | None = Field(default_factory=list)
    is_default: bool = Field(default=False, description="Set as default for this role")
    is_active: bool = Field(default=False, description="Set template as active")
    # Legacy fields
    category: str | None = Field(None, description="Template category (deprecated)")

    @field_validator("user_instructions")
    @classmethod
    def validate_user_instructions_size(cls, v: str | None) -> str | None:
        """Validate user instructions size (max 50KB)"""
        if v and len(v.encode("utf-8")) > MAX_USER_INSTRUCTIONS_SIZE:
            raise ValueError("User instructions exceed 50KB limit")
        return v


class TemplateUpdate(BaseModel):
    """Request model for updating a template"""

    # Editable fields
    system_instructions: str | None = Field(
        None, description="System instructions are read-only via API; presence triggers a 403"
    )
    user_instructions: str | None = Field(None, description="User-customizable instructions (max 50KB)")
    name: str | None = None
    role: str | None = None
    cli_tool: str | None = None
    background_color: str | None = None
    description: str | None = None
    model: str | None = None
    behavioral_rules: list[str] | None = None
    success_criteria: list[str] | None = None
    tags: list[str] | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    user_managed_export: bool | None = None

    @field_validator("user_instructions")
    @classmethod
    def validate_user_instructions_size(cls, v: str | None) -> str | None:
        """Validate user instructions size (max 50KB)"""
        if v and len(v.encode("utf-8")) > MAX_USER_INSTRUCTIONS_SIZE:
            raise ValueError("User instructions exceed 50KB limit")
        return v


class TemplateResponse(BaseModel):
    """Response model for template operations"""

    id: str
    tenant_key: str
    product_id: str | None
    name: str
    role: str
    cli_tool: str
    background_color: str | None
    description: str | None
    # Dual fields (v3.1+)
    system_instructions: str = Field(..., description="Read-only MCP coordination instructions")
    user_instructions: str | None = Field(None, description="User-customizable instructions")
    model: str | None
    tools: str | None
    behavioral_rules: list[str]
    success_criteria: list[str]
    tags: list[str]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    # Export tracking (Handover 0335)
    last_exported_at: datetime | None = Field(default=None, description="Timestamp of last export to CLI")
    may_be_stale: bool = Field(default=False, description="True if template modified after last export")
    user_managed_export: bool = Field(default=False, description="User dismissed staleness manually")
    # Legacy fields
    category: str | None = None
    variables: list[str] = []
    version: str = "1.0.0"
    usage_count: int = 0
    avg_generation_ms: float | None = None
    created_by: str | None = None
    is_system_role: bool = Field(default=False, description="True when template is system managed")


class TemplateHistoryResponse(BaseModel):
    """Response model for template history"""

    id: str
    template_id: str
    name: str
    version: str
    system_instructions: str | None = None
    user_instructions: str | None = None
    archive_reason: str | None
    archive_type: str
    archived_by: str | None
    archived_at: datetime
    is_restorable: bool
    usage_count_at_archive: int | None
    avg_generation_ms_at_archive: float | None


class TemplatePreviewRequest(BaseModel):
    """Request model for template preview"""

    variables: dict[str, str] = Field(default_factory=dict, description="Variable substitutions")
    augmentations: str | None = Field(None, description="Additional augmentation content")


class TemplatePreviewResponse(BaseModel):
    """Response model for template preview"""

    template_id: str
    cli_tool: str = Field(..., description="CLI tool type")
    preview: str = Field(..., description="Rendered template content")
    variables_used: list[str] = Field(default_factory=list, description="Variables found in template")
