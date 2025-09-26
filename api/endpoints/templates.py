"""
Template management API endpoints
"""

import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()


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


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_content: Optional[str] = None
    description: Optional[str] = None
    behavioral_rules: Optional[list[str]] = None
    success_criteria: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


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


async def get_db_session():
    """Get database session dependency"""
    from api.app import state

    if not state.db_manager:
        from src.giljo_mcp.database import DatabaseManager

        state.db_manager = DatabaseManager(is_async=True)
        await state.db_manager.create_tables_async()

    async with state.db_manager.get_session_async() as session:
        yield session


async def get_tenant_and_product():
    """Get tenant_key and product_id from context"""
    # In production, this would come from authentication/context
    # For now, using defaults
    return {"tenant_key": "default-tenant", "product_id": "giljo-mcp"}


@router.get("/", response_model=list[TemplateResponse])
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: bool = Query(True, description="Filter by active status"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get all templates with optional filtering.
    Returns templates for the current tenant/product context.
    """
    start_time = time.time()

    try:
        from src.giljo_mcp.models import AgentTemplate

        context = await get_tenant_and_product()

        # Build query
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == context["tenant_key"],
                AgentTemplate.product_id == context["product_id"],
                AgentTemplate.is_active == is_active,
            )
        )

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
                )
            )

        # Log performance
        if response_time > 100:
            pass

        return responses  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TemplateResponse)
async def create_template(template: TemplateCreate, session: AsyncSession = Depends(get_db_session)):
    """
    Create a new template.
    Automatically archives previous version if updating existing template.
    """
    try:
        import re

        from src.giljo_mcp.models import AgentTemplate

        context = await get_tenant_and_product()

        # Extract variables from template content
        variables = re.findall(r"\{(\w+)\}", template.template_content)

        # If setting as default, unset other defaults for this role
        if template.is_default and template.role:
            stmt = select(AgentTemplate).where(
                and_(
                    AgentTemplate.tenant_key == context["tenant_key"],
                    AgentTemplate.product_id == context["product_id"],
                    AgentTemplate.role == template.role,
                    AgentTemplate.is_default,
                )
            )
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
            created_by="api",
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
                product_id=context["product_id"],
                user_id="api",
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
        )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str = Path(..., description="Template ID"),
    update: TemplateUpdate = ...,
    archive_reason: str = Query("API update", description="Reason for archiving"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing template.
    Automatically creates an archive of the previous version.
    """
    try:
        import re

        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = await get_tenant_and_product()

        # Get existing template
        stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == context["tenant_key"])
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")  # noqa: TRY301

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
            archived_by="api",
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

        # Handle default flag
        if update.is_default is not None and update.is_default and template.role:
            # Unset other defaults for this role
            stmt = select(AgentTemplate).where(
                and_(
                    AgentTemplate.tenant_key == context["tenant_key"],
                    AgentTemplate.product_id == context["product_id"],
                    AgentTemplate.role == template.role,
                    AgentTemplate.is_default,
                    AgentTemplate.id != template_id,
                )
            )
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
                product_id=context["product_id"],
                user_id="api",
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
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete or archive a template.
    By default, templates are archived (soft delete) rather than permanently deleted.
    """
    try:
        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = await get_tenant_and_product()

        # Get template
        stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == context["tenant_key"])
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")  # noqa: TRY301

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
                archive_reason="Template deleted via API",
                archive_type="manual",
                archived_by="api",
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
                product_id=context["product_id"],
                user_id="api",
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
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get version history for a template.
    Returns archived versions in reverse chronological order.
    """
    try:
        from src.giljo_mcp.models import TemplateArchive

        context = await get_tenant_and_product()

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
    session: AsyncSession = Depends(get_db_session),
):
    """
    Restore a template from a specific archived version.
    Creates a new archive of current version before restoration.
    """
    try:
        from src.giljo_mcp.models import AgentTemplate, TemplateArchive

        context = await get_tenant_and_product()

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
            archived_by="api",
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
        archive.restored_by = "api"

        await session.commit()

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
