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
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User


router = APIRouter()

# Maximum template size (100KB as per spec)
MAX_TEMPLATE_SIZE = 100 * 1024  # 100KB in bytes


# Pydantic models for request/response
class TemplateCreate(BaseModel):
    name: str = Field(..., description="Template name")
    category: str = Field(..., description="Template category (role, project_type, custom)")
    template_content: str = Field(..., description="Template content with {variable} placeholders")
    role: Optional[str] = Field(None, description="Agent role if category is 'role'")
    project_type: Optional[str] = Field(None, description="Project type if category is 'project_type'")
    description: Optional[str] = Field(None, description="Template description")
    behavioral_rules: Optional[list[str]] = Field(default_factory=list, description="Behavioral rules")
    success_criteria: Optional[list[str]] = Field(default_factory=list, description="Success criteria")
    tags: Optional[list[str]] = Field(default_factory=list, description="Tags for categorization")
    is_default: bool = Field(False, description="Set as default for this role")
    preferred_tool: str = Field("claude", description="Preferred AI tool (claude, codex, gemini)")

    @field_validator("template_content")
    @classmethod
    def validate_template_size(cls, v: str) -> str:
        """Validate template content size (max 100KB)"""
        if len(v.encode("utf-8")) > MAX_TEMPLATE_SIZE:
            raise ValueError(f"Template content exceeds maximum size of {MAX_TEMPLATE_SIZE / 1024}KB")
        return v


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_content: Optional[str] = None
    description: Optional[str] = None
    behavioral_rules: Optional[list[str]] = None
    success_criteria: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    preferred_tool: Optional[str] = None

    @field_validator("template_content")
    @classmethod
    def validate_template_size(cls, v: Optional[str]) -> Optional[str]:
        """Validate template content size (max 100KB)"""
        if v and len(v.encode("utf-8")) > MAX_TEMPLATE_SIZE:
            raise ValueError(f"Template content exceeds maximum size of {MAX_TEMPLATE_SIZE / 1024}KB")
        return v


class TemplateResponse(BaseModel):
    id: str
    tenant_key: str
    product_id: Optional[str]
    name: str
    category: str
    role: Optional[str]
    project_type: Optional[str]
    template_content: str
    variables: list[str]
    behavioral_rules: list[str]
    success_criteria: list[str]
    description: Optional[str]
    version: str
    is_active: bool
    is_default: bool
    tags: list[str]
    usage_count: int
    avg_generation_ms: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[str]
    preferred_tool: str = "claude"


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
    mission: str = Field(..., description="Rendered mission content")
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


@router.get("/", response_model=list[TemplateResponse])
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: bool = Query(True, description="Filter by active status"),
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
            AgentTemplate.is_active == is_active,
        ]

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

        # Convert to response models
        responses = []
        for template in templates:
            responses.append(
                TemplateResponse(
                    id=template.id,
                    tenant_key=template.tenant_key,
                    product_id=template.product_id,
                    name=template.name,
                    category=template.category,
                    role=template.role,
                    project_type=template.project_type,
                    template_content=template.template_content,
                    variables=template.variables or [],
                    behavioral_rules=template.behavioral_rules or [],
                    success_criteria=template.success_criteria or [],
                    description=template.description,
                    version=template.version,
                    is_active=template.is_active,
                    is_default=template.is_default,
                    tags=template.tags or [],
                    usage_count=template.usage_count,
                    avg_generation_ms=template.avg_generation_ms,
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                    created_by=template.created_by,
                    preferred_tool=template.preferred_tool or "claude",
                )
            )

        # Log performance
        if response_time > 100:
            pass

        return responses  # noqa: TRY300

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

        from src.giljo_mcp.models import AgentTemplate

        context = get_tenant_and_product_from_user(current_user)

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
            tenant_key=context["tenant_key"],
            product_id=context["product_id"],
            name=template.name,
            category=template.category,
            role=template.role,
            project_type=template.project_type,
            template_content=template.template_content,
            variables=variables,
            behavioral_rules=template.behavioral_rules or [],
            success_criteria=template.success_criteria or [],
            description=template.description,
            version="1.0.0",
            is_active=True,
            is_default=template.is_default,
            tags=template.tags or [],
            preferred_tool=template.preferred_tool,
            created_by=current_user.username,
        )

        session.add(new_template)
        await session.commit()
        await session.refresh(new_template)

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
            project_type=new_template.project_type,
            template_content=new_template.template_content,
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
            preferred_tool=getattr(new_template, 'preferred_tool', 'claude'),
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
    Update an existing template.

    Security:
    - Tenant ownership validation (403 if wrong tenant)
    - System template protection (403 if tenant_key="system")
    - Size validation (max 100KB)
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

        # Archive current version before updating
        archive = TemplateArchive(
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
            archive_reason=archive_reason,
            archive_type="auto",
            archived_by=current_user.username,
            usage_count_at_archive=template.usage_count,
            avg_generation_ms_at_archive=template.avg_generation_ms,
        )
        session.add(archive)

        # Update template fields
        if update.name is not None:
            template.name = update.name
        if update.template_content is not None:
            template.template_content = update.template_content
            # Re-extract variables
            template.variables = re.findall(r"\{(\w+)\}", update.template_content)
        if update.description is not None:
            template.description = update.description
        if update.behavioral_rules is not None:
            template.behavioral_rules = update.behavioral_rules
        if update.success_criteria is not None:
            template.success_criteria = update.success_criteria
        if update.tags is not None:
            template.tags = update.tags
        if update.is_active is not None:
            template.is_active = update.is_active
        if update.preferred_tool is not None:
            template.preferred_tool = update.preferred_tool

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
        template.version = f"{major}.{int(minor)+1}.0"
        template.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(template)

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

        return TemplateResponse(
            id=template.id,
            tenant_key=template.tenant_key,
            product_id=template.product_id,
            name=template.name,
            category=template.category,
            role=template.role,
            project_type=template.project_type,
            template_content=template.template_content,
            variables=template.variables,
            behavioral_rules=template.behavioral_rules,
            success_criteria=template.success_criteria,
            description=template.description,
            version=template.version,
            is_active=template.is_active,
            is_default=template.is_default,
            tags=template.tags,
            usage_count=template.usage_count,
            avg_generation_ms=template.avg_generation_ms,
            created_at=template.created_at,
            updated_at=template.updated_at,
            created_by=template.created_by,
            preferred_tool=template.preferred_tool or "claude",
        )

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
        template.version = f"{major}.{int(minor)+1}.0-restored"
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
            raise HTTPException(
                status_code=404, detail=f"No system template found for role '{tenant_template.role}'"
            )

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
    preview_request: TemplatePreviewRequest = ...,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Generate a preview of the template with variable substitution.

    Useful for testing template content before deploying it to agents.
    Supports variable substitution and optional augmentation content.

    Security:
    - Tenant ownership validation
    - Preview only (does not modify template)

    Returns:
        Rendered mission content with variables substituted
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

        # Start with template content
        mission = template.template_content

        # Substitute variables
        for var_name, var_value in preview_request.variables.items():
            placeholder = "{" + var_name + "}"
            mission = mission.replace(placeholder, var_value)

        # Append augmentation if provided
        if preview_request.augmentations:
            mission += "\n\n## Additional Context\n\n" + preview_request.augmentations

        # Extract variables that were used
        import re

        variables_used = re.findall(r"\{(\w+)\}", template.template_content)

        return TemplatePreviewResponse(
            template_id=template_id,
            mission=mission,
            variables_used=variables_used,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
