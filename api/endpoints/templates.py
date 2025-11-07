"""
Template management API endpoints

Provides CRUD operations for agent templates with:
- Multi-tenant isolation
- Version history and archiving
- System template protection
- Template size validation (100KB limit)
- Real-time WebSocket updates
"""

import difflib
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.template_renderer import render_template
from src.giljo_mcp.template_validation import (
    get_role_color,
    slugify_name,
    validate_system_prompt,
)


router = APIRouter()

# Maximum template size (100KB as per spec)
MAX_TEMPLATE_SIZE = 100 * 1024  # 100KB in bytes


# Pydantic models for request/response
class TemplateCreate(BaseModel):
    name: str = Field(..., description="Template name")
    role: str = Field(..., description="Agent role")
    cli_tool: str = Field("claude", description="CLI tool: claude, codex, gemini, generic")
    custom_suffix: Optional[str] = Field(None, description="Custom suffix for name generation")
    background_color: Optional[str] = Field(None, description="Background color (hex)")
    description: Optional[str] = Field(None, description="Template description (required for Claude)")
    template_content: str = Field(..., description="System prompt content")
    model: Optional[str] = Field("sonnet", description="Model: sonnet, opus, haiku, inherit")
    tools: Optional[str] = Field(None, description="Tool selection (null = inherit all)")
    behavioral_rules: Optional[list[str]] = Field(default_factory=list, description="Behavioral rules")
    success_criteria: Optional[list[str]] = Field(default_factory=list, description="Success criteria")
    tags: Optional[list[str]] = Field(default_factory=list, description="Tags for categorization")
    is_default: bool = Field(False, description="Set as default for this role")
    is_active: bool = Field(False, description="Set template as active")
    # Legacy fields (kept for compatibility)
    category: Optional[str] = Field(None, description="Template category (deprecated)")
    project_type: Optional[str] = Field(None, description="Project type (deprecated)")
    preferred_tool: Optional[str] = Field(None, description="Preferred AI tool (deprecated)")

    @field_validator("template_content")
    @classmethod
    def validate_template_size(cls, v: str) -> str:
        """Validate template content size (max 100KB)"""
        if len(v.encode("utf-8")) > MAX_TEMPLATE_SIZE:
            raise ValueError(f"Template content exceeds maximum size of {MAX_TEMPLATE_SIZE / 1024}KB")
        return v


class TemplateUpdate(BaseModel):
    """
    Template update request (v3.1+ with dual fields).

    IMPORTANT: system_instructions is read-only and cannot be modified.
    Only user_instructions and other editable fields can be updated.
    """

    # EDITABLE fields
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

    # DEPRECATED: Legacy support (still maps to user_instructions)
    template_content: Optional[str] = Field(None, deprecated=True, description="Legacy field - use user_instructions instead")
    preferred_tool: Optional[str] = None

    # READONLY: system_instructions NOT exposed (protected from modification)

    @field_validator("user_instructions")
    @classmethod
    def validate_user_instructions_size(cls, v: Optional[str]) -> Optional[str]:
        """Validate user instructions size (max 50KB)"""
        if v and len(v.encode("utf-8")) > 50 * 1024:
            raise ValueError("User instructions exceed 50KB limit")
        return v

    @field_validator("template_content")
    @classmethod
    def validate_template_content_size(cls, v: Optional[str]) -> Optional[str]:
        """Validate template content size (max 100KB) - legacy support"""
        if v and len(v.encode("utf-8")) > MAX_TEMPLATE_SIZE:
            raise ValueError(f"Template content exceeds maximum size of {MAX_TEMPLATE_SIZE / 1024}KB")
        return v


class TemplateResponse(BaseModel):
    """Template response with dual fields (v3.1+)."""

    id: str
    tenant_key: str
    product_id: Optional[str]
    name: str
    role: str
    cli_tool: str
    background_color: Optional[str]
    description: Optional[str]

    # NEW: Expose both fields separately (v3.1+)
    system_instructions: str = Field(..., description="Read-only MCP coordination instructions")
    user_instructions: Optional[str] = Field(None, description="User-customizable instructions")

    # DEPRECATED: Merged view for backward compatibility
    template_content: str = Field(..., description="Merged view (system + user)")

    model: Optional[str]
    tools: Optional[str]
    behavioral_rules: list[str]
    success_criteria: list[str]
    tags: list[str]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # Legacy fields (for compatibility)
    category: Optional[str] = None
    project_type: Optional[str] = None
    variables: list[str] = []
    version: str = "1.0.0"
    usage_count: int = 0
    avg_generation_ms: Optional[float] = None
    created_by: Optional[str] = None
    preferred_tool: str = "claude"

    @classmethod
    def from_orm(cls, template):
        """Convert ORM model to response schema with dual fields."""
        # Merge system and user instructions for backward compatibility
        merged_content = template.system_instructions
        if template.user_instructions:
            merged_content = f"{template.system_instructions}\n\n{template.user_instructions}"

        return cls(
            id=template.id,
            tenant_key=template.tenant_key,
            product_id=template.product_id,
            name=template.name,
            role=template.role,
            cli_tool=template.cli_tool,
            background_color=template.background_color,
            description=template.description,
            system_instructions=template.system_instructions,
            user_instructions=template.user_instructions,
            template_content=merged_content,
            model=template.model,
            tools=template.tools,
            behavioral_rules=template.behavioral_rules or [],
            success_criteria=template.success_criteria or [],
            tags=template.tags or [],
            is_default=template.is_default,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at,
            category=template.category,
            project_type=template.project_type,
            variables=template.variables or [],
            version=template.version,
            usage_count=template.usage_count,
            avg_generation_ms=template.avg_generation_ms,
            created_by=template.created_by,
            preferred_tool=getattr(template, "preferred_tool", template.cli_tool or template.tool or "claude")
        )


class TemplateHistoryResponse(BaseModel):
    id: str
    template_id: str
    name: str
    version: str
    template_content: str
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
    preview: str = Field(..., description="Rendered template content (YAML for Claude, plaintext for others)")
    # Legacy fields for backward compatibility
    mission: Optional[str] = Field(None, description="Rendered mission content (deprecated)")
    variables_used: list[str] = Field(default_factory=list, description="Variables found in template")


def get_tenant_and_product_from_user(user: User) -> dict:
    """
    Extract tenant_key and product_id from authenticated user

    Args:
        user: Authenticated user object

    Returns:
        Dictionary with tenant_key and optional product_id
    """
    return {"tenant_key": user.tenant_key, "product_id": None}  # Product-level scoping handled separately


async def validate_active_agent_limit(
    db: AsyncSession,
    tenant_key: str,
    template_id: str,
    new_is_active: bool,
    role: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Validate 8-role active limit before toggling (Handover 0103).

    Claude Code context budget constraint: Maximum 8 distinct active roles
    to ensure optimal performance and sufficient tokens for code analysis.

    Args:
        db: Database session
        tenant_key: Tenant key for isolation
        template_id: Template being toggled
        new_is_active: Desired active state
        role: Role of the template being toggled

    Returns:
        (is_valid, error_message) tuple
        - (True, "") if validation passes
        - (False, error_msg) if validation fails

    Example:
        >>> valid, msg = await validate_active_agent_limit(db, "tenant-1", "tpl-123", True, "orchestrator")
        >>> if not valid:
        ...     raise HTTPException(409, msg)
    """
    from src.giljo_mcp.models import AgentTemplate

    # If deactivating, always allow
    if not new_is_active:
        return True, ""

    # Get current template to fetch its role if not provided
    if role is None:
        stmt = select(AgentTemplate.role).where(AgentTemplate.id == template_id)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()
        if not role:
            return False, "Template not found"

    # Count currently active distinct roles (excluding the one being toggled)
    stmt = select(AgentTemplate.role).where(
        AgentTemplate.tenant_key == tenant_key,
        AgentTemplate.is_active == True,  # noqa: E712
        AgentTemplate.id != template_id,
    ).distinct()

    result = await db.execute(stmt)
    active_roles = {row[0] for row in result.all()}

    # If this role is already active elsewhere, allow toggle
    if role in active_roles:
        return True, ""

    # If we have 8 distinct active roles, block new role activation
    if len(active_roles) >= 8:
        return False, f"Maximum 8 active agent roles allowed (currently {len(active_roles)}). Deactivate another role first."

    return True, ""


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get a single template by ID (v3.1+ with dual fields).

    Returns both system_instructions and user_instructions separately,
    plus merged template_content for backward compatibility.

    Security:
    - Tenant ownership validation (403 if wrong tenant)
    - Authentication required via JWT
    """
    try:
        from src.giljo_mcp.models import AgentTemplate

        context = get_tenant_and_product_from_user(current_user)

        # Get template with tenant isolation
        stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == context["tenant_key"])
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")  # noqa: TRY301

        # Use from_orm helper for consistent dual-field response
        return TemplateResponse.from_orm(template)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[TemplateResponse])
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(
        None, description="Filter by active status (None=all, True=active only, False=inactive only)"
    ),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get all templates with optional filtering.
    Returns templates for the current user's tenant.

    Security:
    - Multi-tenant isolation: Only returns templates for user's tenant_key
    - Authentication required via JWT
    """
    start_time = time.time()

    try:
        from src.giljo_mcp.models import AgentTemplate

        context = get_tenant_and_product_from_user(current_user)

        # Build query with tenant isolation
        filters = [
            AgentTemplate.tenant_key == context["tenant_key"],
        ]

        # Optional is_active filter (None = all templates)
        if is_active is not None:
            filters.append(AgentTemplate.is_active == is_active)

        # Optional product_id filter
        if context.get("product_id"):
            filters.append(AgentTemplate.product_id == context["product_id"])

        stmt = select(AgentTemplate).where(and_(*filters))

        # Apply filters
        if category:
            stmt = stmt.where(AgentTemplate.category == category)
        if role:
            stmt = stmt.where(AgentTemplate.role == role)

        stmt = stmt.order_by(AgentTemplate.name)

        result = await session.execute(stmt)
        templates = result.scalars().all()

        response_time = (time.time() - start_time) * 1000

        # Convert to response models using from_orm helper (includes dual fields)
        responses = [TemplateResponse.from_orm(template) for template in templates]

        # Log performance
        if response_time > 100:
            pass

        return responses  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/active-count", response_model=dict)
async def get_active_count(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get count of active templates for current tenant (Handover 0075).

    Returns active agent count, maximum allowed (8), and remaining slots.
    Used by frontend to display "Active: 6/8" counter and validate limits.

    Security:
    - Multi-tenant isolation: Only counts templates for user's tenant_key
    - Authentication required via JWT

    Returns:
        {
            "active_count": 6,
            "max_allowed": 8,
            "remaining_slots": 2
        }
    """
    try:
        from src.giljo_mcp.models import AgentTemplate

        context = get_tenant_and_product_from_user(current_user)

        # Count active templates for tenant
        stmt = select(func.count(AgentTemplate.id)).where(
            AgentTemplate.tenant_key == context["tenant_key"],
            AgentTemplate.is_active == True,  # noqa: E712
        )

        result = await session.execute(stmt)
        active_count = result.scalar_one()

        return {
            "active_count": active_count,
            "max_allowed": 8,
            "remaining_slots": max(0, 8 - active_count),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TemplateResponse)
async def create_template(
    template: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new template for the current user's tenant.

    Security:
    - Template created under user's tenant_key
    - Size validation (max 100KB)
    - Authentication required
    """
    try:
        import re
        from uuid import uuid4

        from src.giljo_mcp.models import AgentTemplate

        context = get_tenant_and_product_from_user(current_user)

        # Generate name from role + suffix
        if template.custom_suffix:
            generated_name = slugify_name(template.role, template.custom_suffix)
        else:
            generated_name = template.name or template.role

        # Validate name format
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", generated_name):
            raise HTTPException(status_code=400, detail="Name must use lowercase letters, numbers, and hyphens only")
        if len(generated_name) > 100:
            raise HTTPException(status_code=400, detail="Name must be 100 characters or less")

        # Check uniqueness within tenant (async query)
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == context["tenant_key"],
                AgentTemplate.name == generated_name
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Agent name '{generated_name}' already exists")

        # Validate system prompt
        is_valid, error_msg = validate_system_prompt(template.template_content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Auto-assign background color if not provided
        background_color = template.background_color or get_role_color(template.role)

        # Set default description if not provided (Claude only)
        description = template.description
        if not description and template.cli_tool == "claude":
            description = f"Subagent for {template.role}"

        # Extract variables from template content
        variables = re.findall(r"\{(\w+)\}", template.template_content)

        # If setting as default, unset other defaults for this role
        if template.is_default and template.role:
            filters = [
                AgentTemplate.tenant_key == context["tenant_key"],
                AgentTemplate.role == template.role,
                AgentTemplate.is_default == True,
            ]
            if context.get("product_id"):
                filters.append(AgentTemplate.product_id == context["product_id"])

            stmt = select(AgentTemplate).where(and_(*filters))
            result = await session.execute(stmt)
            existing_defaults = result.scalars().all()
            for existing in existing_defaults:
                existing.is_default = False

        # Create new template
        new_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=context["tenant_key"],
            product_id=context["product_id"],
            name=generated_name,
            category=template.category or "role",
            role=template.role,
            cli_tool=template.cli_tool,
            background_color=background_color,
            description=description,
            template_content=template.template_content,
            model=template.model or "sonnet",
            tools=None,  # Always inherit all
            variables=variables,
            behavioral_rules=template.behavioral_rules or [],
            success_criteria=template.success_criteria or [],
            version="1.0.0",
            is_active=template.is_active,
            is_default=template.is_default,
            tags=template.tags or [],
            tool=template.cli_tool,  # Set legacy field too
            created_by=current_user.username,
        )

        session.add(new_template)
        await session.commit()
        await session.refresh(new_template)

        # Optional: materialize Claude files to exports/ for operator visibility (0102a)
        try:
            from src.giljo_mcp.template_materializer import (
                get_materialize_on_save_flag,
                materialize_claude_templates_for_tenant,
            )

            if get_materialize_on_save_flag():
                await materialize_claude_templates_for_tenant(
                    session=session,
                    tenant_key=context["tenant_key"],
                    include_inactive=False,
                )
        except Exception:
            # Do not fail creation if materialization fails
            pass

        # Broadcast template creation via WebSocket
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_template_update(
                template_id=new_template.id,
                template_name=new_template.name,
                operation="create",
                tenant_key=context["tenant_key"],
                product_id=context.get("product_id"),
                user_id=current_user.username,
                change_summary=f"Created new template: {new_template.name}",
            )

        return TemplateResponse(
            id=new_template.id,
            tenant_key=new_template.tenant_key,
            product_id=new_template.product_id,
            name=new_template.name,
            category=new_template.category,
            role=new_template.role,
            cli_tool=new_template.cli_tool or "claude",
            background_color=new_template.background_color,
            project_type=new_template.project_type,
            template_content=new_template.template_content,
            model=new_template.model,
            tools=new_template.tools,
            variables=new_template.variables,
            behavioral_rules=new_template.behavioral_rules,
            success_criteria=new_template.success_criteria,
            description=new_template.description,
            version=new_template.version,
            is_active=new_template.is_active,
            is_default=new_template.is_default,
            tags=new_template.tags,
            usage_count=new_template.usage_count,
            avg_generation_ms=new_template.avg_generation_ms,
            created_at=new_template.created_at,
            updated_at=new_template.updated_at,
            created_by=new_template.created_by,
            preferred_tool=getattr(new_template, "tool", "claude"),
        )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str = Path(..., description="Template ID"),
    update: TemplateUpdate = ...,
    archive_reason: str = Query("User update", description="Reason for archiving"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing template (v3.1+ with system_instructions protection).

    IMPORTANT: system_instructions cannot be modified via this endpoint.
    Only user_instructions and other editable fields can be updated.
    Use POST /templates/{id}/reset-system to restore system defaults.

    Security:
    - Tenant ownership validation (403 if wrong tenant)
    - System template protection (403 if tenant_key="system")
    - system_instructions protection (403 if attempted)
    - Size validation (user_instructions max 50KB)
    - Automatically creates archive of previous version
    """
    try:
        import re

        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = get_tenant_and_product_from_user(current_user)

        # Get existing template
        stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == context["tenant_key"])
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")  # noqa: TRY301

        # Prevent system template editing
        if template.tenant_key == "system":
            raise HTTPException(status_code=403, detail="System templates are read-only")  # noqa: TRY301

        # CRITICAL: Prevent system_instructions modification (Handover 0106)
        # Check if request contains system_instructions field (even if None)
        if hasattr(update, "system_instructions") and "system_instructions" in update.model_dump(exclude_unset=True):
            raise HTTPException(
                status_code=403,
                detail="system_instructions is read-only and cannot be modified. "
                       "Use /templates/{id}/reset-system to restore system defaults."
            )  # noqa: TRY301

        # Validate 8-role active limit if toggling active status (Handover 0103)
        if update.is_active is not None and update.is_active != template.is_active:
            valid, error_msg = await validate_active_agent_limit(
                db=session,
                tenant_key=context["tenant_key"],
                template_id=template_id,
                new_is_active=update.is_active,
                role=template.role,
            )

            if not valid:
                raise HTTPException(status_code=409, detail=error_msg)  # noqa: TRY301

        # Archive current version before updating (include both fields)
        archive = TemplateArchive(
            tenant_key=template.tenant_key,
            template_id=template.id,
            product_id=template.product_id,
            name=template.name,
            category=template.category,
            role=template.role,
            system_instructions=template.system_instructions,  # NEW: Archive system instructions
            user_instructions=template.user_instructions,  # NEW: Archive user instructions
            template_content=template.template_content,  # Legacy
            variables=template.variables,
            behavioral_rules=template.behavioral_rules,
            success_criteria=template.success_criteria,
            version=template.version,
            archive_reason=archive_reason,
            archive_type="auto",
            archived_by=current_user.username,
            usage_count_at_archive=template.usage_count,
            avg_generation_ms_at_archive=template.avg_generation_ms,
        )
        session.add(archive)

        # Update ONLY editable fields
        if update.user_instructions is not None:
            template.user_instructions = update.user_instructions

        if update.name is not None:
            template.name = update.name

        if update.role is not None:
            template.role = update.role
            # Auto-update background_color when role changes
            template.background_color = get_role_color(update.role)

        if update.cli_tool is not None:
            template.cli_tool = update.cli_tool
            template.tool = update.cli_tool  # Update legacy field

        if update.background_color is not None:
            template.background_color = update.background_color

        if update.description is not None:
            template.description = update.description

        # Legacy support: template_content maps to user_instructions
        if update.template_content is not None:
            is_valid, error_msg = validate_system_prompt(update.template_content)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            template.user_instructions = update.template_content  # Map to user_instructions
            # Re-extract variables
            template.variables = re.findall(r"\{(\w+)\}", update.template_content)

        if update.model is not None:
            template.model = update.model

        if update.behavioral_rules is not None:
            template.behavioral_rules = update.behavioral_rules

        if update.success_criteria is not None:
            template.success_criteria = update.success_criteria

        if update.tags is not None:
            template.tags = update.tags

        if update.is_active is not None:
            template.is_active = update.is_active

        if update.preferred_tool is not None:
            template.tool = update.preferred_tool
            template.cli_tool = update.preferred_tool  # Update new field

        # Update merged template_content for backward compatibility
        merged_content = template.system_instructions
        if template.user_instructions:
            merged_content = f"{template.system_instructions}\n\n{template.user_instructions}"
        template.template_content = merged_content

        # Handle default flag
        if update.is_default is not None and update.is_default and template.role:
            # Unset other defaults for this role
            filters = [
                AgentTemplate.tenant_key == context["tenant_key"],
                AgentTemplate.role == template.role,
                AgentTemplate.is_default == True,
                AgentTemplate.id != template_id,
            ]
            if context.get("product_id"):
                filters.append(AgentTemplate.product_id == context["product_id"])

            stmt = select(AgentTemplate).where(and_(*filters))
            result = await session.execute(stmt)
            existing_defaults = result.scalars().all()
            for existing in existing_defaults:
                existing.is_default = False

            template.is_default = update.is_default

        # Increment version
        major, minor, _patch = template.version.split(".")
        template.version = f"{major}.{int(minor) + 1}.0"
        template.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(template)

        # Optional: materialize Claude files to exports/ for operator visibility (0102a)
        try:
            from src.giljo_mcp.template_materializer import (
                get_materialize_on_save_flag,
                materialize_claude_templates_for_tenant,
            )

            if get_materialize_on_save_flag():
                await materialize_claude_templates_for_tenant(
                    session=session,
                    tenant_key=context["tenant_key"],
                    include_inactive=False,
                )
        except Exception:
            # Do not fail update if materialization fails
            pass

        # Broadcast update via WebSocket
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_template_update(
                template_id=template.id,
                template_name=template.name,
                operation="update",
                tenant_key=context["tenant_key"],
                product_id=context.get("product_id"),
                user_id=current_user.username,
                change_summary=f"Updated template to version {template.version}",
                version=template.version,
            )

        # Use from_orm helper for consistent response
        return TemplateResponse.from_orm(template)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(
    template_id: str = Path(..., description="Template ID"),
    archive: bool = Query(True, description="Archive instead of hard delete"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete or archive a template (soft delete by default).

    Security:
    - Tenant ownership validation
    - System template protection (403 if tenant_key="system")
    - Creates archive for restoration
    """
    try:
        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = get_tenant_and_product_from_user(current_user)

        # Get template
        stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == context["tenant_key"])
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")  # noqa: TRY301

        # Prevent system template deletion
        if template.tenant_key == "system":
            raise HTTPException(status_code=403, detail="System templates cannot be deleted")  # noqa: TRY301

        template_name = template.name

        if archive:
            # Soft delete - just mark as inactive and create final archive
            final_archive = TemplateArchive(
                tenant_key=template.tenant_key,
                template_id=template.id,
                product_id=template.product_id,
                name=template.name,
                category=template.category,
                role=template.role,
                template_content=template.template_content,
                variables=template.variables,
                behavioral_rules=template.behavioral_rules,
                success_criteria=template.success_criteria,
                version=template.version,
                archive_reason="Template deleted by user",
                archive_type="manual",
                archived_by=current_user.username,
                usage_count_at_archive=template.usage_count,
                avg_generation_ms_at_archive=template.avg_generation_ms,
                is_restorable=True,
            )
            session.add(final_archive)

            template.is_active = False
            operation = "archive"
        else:
            # Hard delete
            await session.delete(template)
            operation = "delete"

        await session.commit()

        # Broadcast deletion via WebSocket
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_template_update(
                template_id=template_id,
                template_name=template_name,
                operation=operation,
                tenant_key=context["tenant_key"],
                product_id=context.get("product_id"),
                user_id=current_user.username,
                change_summary=f"Template {operation}d: {template_name}",
            )

        return {
            "success": True,
            "message": f"Template {template_name} {operation}d successfully",
            "template_id": template_id,
            "operation": operation,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/reset-system", response_model=TemplateResponse)
async def reset_system_instructions(
    template_id: str = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Reset system_instructions to system defaults (v3.1+ Handover 0106).

    This is the ONLY way to modify system_instructions:
    - Restores default MCP coordination instructions
    - Preserves user_instructions unchanged
    - Creates archive of previous version
    - Admin operation (protects critical MCP tool integration)

    Security:
    - Tenant ownership validation (403 if wrong tenant)
    - System template protection (403 if tenant_key="system")
    - Automatically creates archive of previous version
    """
    try:
        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = get_tenant_and_product_from_user(current_user)

        # Get template
        stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == context["tenant_key"])
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")  # noqa: TRY301

        # Verify tenant isolation
        if template.tenant_key == "system":
            raise HTTPException(status_code=403, detail="Cannot reset system templates")  # noqa: TRY301

        # Archive current version before reset
        archive = TemplateArchive(
            tenant_key=template.tenant_key,
            template_id=template.id,
            product_id=template.product_id,
            name=template.name,
            category=template.category,
            role=template.role,
            system_instructions=template.system_instructions,
            user_instructions=template.user_instructions,
            template_content=template.template_content,
            variables=template.variables,
            behavioral_rules=template.behavioral_rules,
            success_criteria=template.success_criteria,
            version=template.version,
            archive_reason="Pre-reset backup (system instructions reset)",
            archive_type="auto",
            archived_by=current_user.username,
            usage_count_at_archive=template.usage_count,
            avg_generation_ms_at_archive=template.avg_generation_ms,
        )
        session.add(archive)

        # Get system default instructions from template seeder
        from src.giljo_mcp.template_seeder import _get_mcp_coordination_section

        default_system = _get_mcp_coordination_section()

        # Reset system_instructions ONLY (preserve user_instructions)
        template.system_instructions = default_system

        # Update merged content for backward compatibility
        merged_content = template.system_instructions
        if template.user_instructions:
            merged_content = f"{template.system_instructions}\n\n{template.user_instructions}"
        template.template_content = merged_content

        # Update metadata
        major, minor, _patch = template.version.split(".")
        template.version = f"{major}.{int(minor) + 1}.0"
        template.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(template)

        # Broadcast update via WebSocket
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_template_update(
                template_id=template.id,
                template_name=template.name,
                operation="reset-system",
                tenant_key=context["tenant_key"],
                product_id=context.get("product_id"),
                user_id=current_user.username,
                change_summary=f"System instructions reset to defaults (version {template.version})",
                version=template.version,
            )

        # Use from_orm helper for consistent response
        return TemplateResponse.from_orm(template)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}/history", response_model=list[TemplateHistoryResponse])
async def get_template_history(
    template_id: str = Path(..., description="Template ID"),
    limit: int = Query(10, description="Maximum number of history entries"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get version history for a template.

    Security:
    - Tenant ownership validation
    - Returns archived versions in reverse chronological order
    """
    try:
        from src.giljo_mcp.models import TemplateArchive

        context = get_tenant_and_product_from_user(current_user)

        # Query archives for this template
        stmt = (
            select(TemplateArchive)
            .where(
                and_(TemplateArchive.template_id == template_id, TemplateArchive.tenant_key == context["tenant_key"])
            )
            .order_by(TemplateArchive.archived_at.desc())
            .limit(limit)
        )

        result = await session.execute(stmt)
        archives = result.scalars().all()

        # Convert to response models
        history = []
        for archive in archives:
            history.append(
                TemplateHistoryResponse(
                    id=archive.id,
                    template_id=archive.template_id,
                    name=archive.name,
                    version=archive.version,
                    template_content=archive.template_content,
                    archive_reason=archive.archive_reason,
                    archive_type=archive.archive_type,
                    archived_by=archive.archived_by,
                    archived_at=archive.archived_at,
                    is_restorable=archive.is_restorable,
                    usage_count_at_archive=archive.usage_count_at_archive,
                    avg_generation_ms_at_archive=archive.avg_generation_ms_at_archive,
                )
            )

        return history  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/restore/{archive_id}")
async def restore_template_version(
    template_id: str = Path(..., description="Template ID"),
    archive_id: str = Path(..., description="Archive ID to restore"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Restore a template from a specific archived version.

    Security:
    - Tenant ownership validation
    - System template protection
    - Creates archive of current version before restoration
    """
    try:
        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = get_tenant_and_product_from_user(current_user)

        # Get the archive to restore
        archive_stmt = select(TemplateArchive).where(
            and_(
                TemplateArchive.id == archive_id,
                TemplateArchive.template_id == template_id,
                TemplateArchive.tenant_key == context["tenant_key"],
                TemplateArchive.is_restorable,
            )
        )
        archive_result = await session.execute(archive_stmt)
        archive = archive_result.scalar_one_or_none()

        if not archive:
            raise HTTPException(status_code=404, detail="Archive not found or not restorable")  # noqa: TRY301

        # Get current template
        template_stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == context["tenant_key"])
        )
        template_result = await session.execute(template_stmt)
        template = template_result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")  # noqa: TRY301

        # Archive current version before restoring
        current_archive = TemplateArchive(
            tenant_key=template.tenant_key,
            template_id=template.id,
            product_id=template.product_id,
            name=template.name,
            category=template.category,
            role=template.role,
            template_content=template.template_content,
            variables=template.variables,
            behavioral_rules=template.behavioral_rules,
            success_criteria=template.success_criteria,
            version=template.version,
            archive_reason=f"Pre-restoration backup (restoring to v{archive.version})",
            archive_type="auto",
            archived_by=current_user.username,
            usage_count_at_archive=template.usage_count,
            avg_generation_ms_at_archive=template.avg_generation_ms,
        )
        session.add(current_archive)

        # Restore from archive
        template.name = archive.name
        template.category = archive.category
        template.role = archive.role
        template.template_content = archive.template_content
        template.variables = archive.variables
        template.behavioral_rules = archive.behavioral_rules
        template.success_criteria = archive.success_criteria

        # Increment version for restored template
        major, minor, _patch = archive.version.split(".")
        template.version = f"{major}.{int(minor) + 1}.0-restored"
        template.updated_at = datetime.now(timezone.utc)
        template.is_active = True

        # Mark archive as restored
        archive.restored_at = datetime.now(timezone.utc)
        archive.restored_by = current_user.username

        await session.commit()

        # Broadcast restore via WebSocket
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_template_update(
                template_id=template.id,
                template_name=template.name,
                operation="restore",
                tenant_key=context["tenant_key"],
                product_id=context.get("product_id"),
                user_id=current_user.username,
                change_summary=f"Restored template to version {archive.version}",
                version=template.version,
            )

        return {
            "success": True,
            "message": f"Template restored to version {archive.version}",
            "template_id": template_id,
            "new_version": template.version,
            "restored_from_archive": archive_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/reset")
async def reset_template_to_system_default(
    template_id: str = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Reset a tenant template to the system default.

    Copies the system template content to the tenant template and marks
    it as non-customized. This allows tenants to revert to the latest
    system defaults if they've made customizations they want to discard.

    Security:
    - Tenant ownership validation
    - Cannot reset system templates (they are the source)
    - Creates archive of current version before reset

    Returns:
        Success message with reset version information
    """
    try:
        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = get_tenant_and_product_from_user(current_user)

        # Get tenant template
        tenant_stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == template_id,
                AgentTemplate.tenant_key == context["tenant_key"],
            )
        )
        result = await session.execute(tenant_stmt)
        tenant_template = result.scalar_one_or_none()

        if not tenant_template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")

        # Cannot reset system templates
        if tenant_template.tenant_key == "system":
            raise HTTPException(status_code=400, detail="Cannot reset system templates")

        if not tenant_template.role:
            raise HTTPException(status_code=400, detail="Template must have a role to reset to system default")

        # Find system default template for this role
        system_stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == "system",
                AgentTemplate.role == tenant_template.role,
                AgentTemplate.is_active == True,
            )
        )
        system_result = await session.execute(system_stmt)
        system_template = system_result.scalar_one_or_none()

        if not system_template:
            raise HTTPException(status_code=404, detail=f"No system template found for role '{tenant_template.role}'")

        # Archive current version before resetting
        archive = TemplateArchive(
            tenant_key=tenant_template.tenant_key,
            template_id=tenant_template.id,
            product_id=tenant_template.product_id,
            name=tenant_template.name,
            category=tenant_template.category,
            role=tenant_template.role,
            template_content=tenant_template.template_content,
            variables=tenant_template.variables,
            behavioral_rules=tenant_template.behavioral_rules,
            success_criteria=tenant_template.success_criteria,
            version=tenant_template.version,
            archive_reason="Pre-reset backup (resetting to system default)",
            archive_type="auto",
            archived_by=current_user.username,
            usage_count_at_archive=tenant_template.usage_count,
            avg_generation_ms_at_archive=tenant_template.avg_generation_ms,
        )
        session.add(archive)

        # Copy system template content to tenant template
        tenant_template.template_content = system_template.template_content
        tenant_template.variables = system_template.variables
        tenant_template.behavioral_rules = system_template.behavioral_rules
        tenant_template.success_criteria = system_template.success_criteria
        tenant_template.version = system_template.version
        tenant_template.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(tenant_template)

        # Broadcast reset via WebSocket
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_template_update(
                template_id=tenant_template.id,
                template_name=tenant_template.name,
                operation="reset",
                tenant_key=context["tenant_key"],
                product_id=context.get("product_id"),
                user_id=current_user.username,
                change_summary=f"Reset template to system default (v{system_template.version})",
                version=tenant_template.version,
            )

        return {
            "success": True,
            "message": f"Template reset to system default version {system_template.version}",
            "template_id": template_id,
            "reset_to_version": system_template.version,
            "system_template_id": system_template.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}/diff", response_model=TemplateDiffResponse)
async def get_template_diff(
    template_id: str = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Compare tenant template with system template.

    Shows differences between the user's tenant-specific template and
    the system default template for the same role. Useful for understanding
    what customizations have been made.

    Security:
    - Tenant ownership validation
    - Returns unified diff and HTML diff formats

    Returns:
        Diff comparison with change summary
    """
    try:
        from src.giljo_mcp.models import AgentTemplate

        context = get_tenant_and_product_from_user(current_user)

        # Get tenant template
        tenant_stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == template_id,
                AgentTemplate.tenant_key == context["tenant_key"],
            )
        )
        result = await session.execute(tenant_stmt)
        tenant_template = result.scalar_one_or_none()

        if not tenant_template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")

        # Get system template if exists
        system_template = None
        if tenant_template.role:
            system_stmt = select(AgentTemplate).where(
                and_(
                    AgentTemplate.tenant_key == "system",
                    AgentTemplate.role == tenant_template.role,
                    AgentTemplate.is_active == True,
                )
            )
            system_result = await session.execute(system_stmt)
            system_template = system_result.scalar_one_or_none()

        has_system_template = system_template is not None

        # Generate diff if system template exists
        diff_unified = None
        diff_html = None
        changes_summary = {}

        if system_template:
            # Split into lines for difflib
            system_lines = system_template.template_content.splitlines(keepends=True)
            tenant_lines = tenant_template.template_content.splitlines(keepends=True)

            # Generate unified diff
            diff_unified = "".join(
                difflib.unified_diff(
                    system_lines,
                    tenant_lines,
                    fromfile=f"System ({system_template.version})",
                    tofile=f"Tenant ({tenant_template.version})",
                    lineterm="",
                )
            )

            # Generate HTML diff
            diff_html_generator = difflib.HtmlDiff()
            diff_html = diff_html_generator.make_file(
                system_lines,
                tenant_lines,
                fromdesc=f"System Template (v{system_template.version})",
                todesc=f"Tenant Template (v{tenant_template.version})",
            )

            # Calculate change summary
            differ = difflib.Differ()
            diff_lines = list(differ.compare(system_lines, tenant_lines))

            added = sum(1 for line in diff_lines if line.startswith("+ "))
            removed = sum(1 for line in diff_lines if line.startswith("- "))
            changed = added + removed

            changes_summary = {
                "lines_added": added,
                "lines_removed": removed,
                "total_changes": changed,
                "is_identical": changed == 0,
            }
        else:
            changes_summary = {
                "no_system_template": True,
                "message": "No system template available for comparison",
            }

        # Determine if customized (different version or content)
        is_customized = False
        if system_template:
            is_customized = (
                tenant_template.version != system_template.version
                or tenant_template.template_content != system_template.template_content
            )

        return TemplateDiffResponse(
            template_id=template_id,
            template_name=tenant_template.name,
            tenant_version=tenant_template.version,
            system_version=system_template.version if system_template else None,
            has_system_template=has_system_template,
            is_customized=is_customized,
            diff_html=diff_html,
            diff_unified=diff_unified,
            changes_summary=changes_summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: str = Path(..., description="Template ID"),
    preview_request: Optional[TemplatePreviewRequest] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Generate preview of template in CLI tool format (0103).

    Returns rendered YAML (Claude) or plaintext (others).

    Security:
    - Tenant ownership validation
    - Preview only (does not modify template)

    Returns:
        Rendered template content with CLI tool-specific formatting
    """
    try:
        from src.giljo_mcp.models import AgentTemplate

        context = get_tenant_and_product_from_user(current_user)

        # Get template
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == template_id,
                AgentTemplate.tenant_key == context["tenant_key"],
            )
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found or access denied")

        # Render template using CLI tool-specific formatter
        rendered = render_template(template)

        # Extract variables for backward compatibility
        import re
        variables_used = re.findall(r"\{(\w+)\}", template.template_content)

        return TemplatePreviewResponse(
            template_id=template_id,
            cli_tool=template.cli_tool,
            preview=rendered,
            mission=rendered,  # Legacy field
            variables_used=variables_used,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
