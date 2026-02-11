"""
Template CRUD Endpoints - Handover 0126

Handles template CRUD operations using TemplateService.

NOTE: This initial implementation uses TemplateService where methods exist.
Complex operations (validation, WebSocket broadcasting, materialization) are
preserved from original implementation. Future work should extract these to
TemplateService methods as the service layer expands.
"""

import logging
import re
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import AgentTemplate, User
from src.giljo_mcp.services.template_service import TemplateService
from src.giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
from src.giljo_mcp.template_validation import get_role_color, slugify_name, validate_system_prompt

from .dependencies import get_template_service
from .models import TemplateCreate, TemplateResponse, TemplateUpdate


logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
USER_MANAGED_AGENT_LIMIT = 7  # Reserve one slot for orchestrator


def _is_system_managed_role(role: Optional[str]) -> bool:
    """Check if role is system-managed"""
    return bool(role and role in SYSTEM_MANAGED_ROLES)


def get_tenant_and_product_from_user(user: User) -> dict:
    """Extract tenant_key and product_id from authenticated user"""
    return {"tenant_key": user.tenant_key, "product_id": getattr(user, "active_product_id", None)}


def _convert_to_response(template: AgentTemplate) -> TemplateResponse:
    """Convert ORM model to response schema"""
    # Merge system and user instructions for backward compatibility
    merged_content = template.system_instructions or ""
    if template.user_instructions:
        merged_content = f"{merged_content}\n\n{template.user_instructions}"

    # Handover 0335: Compute may_be_stale flag
    may_be_stale = (
        template.updated_at is not None
        and template.last_exported_at is not None
        and template.updated_at > template.last_exported_at
    )

    return TemplateResponse(
        id=template.id,
        tenant_key=template.tenant_key,
        product_id=template.product_id,
        name=template.name,
        role=template.role,
        cli_tool=template.cli_tool or "claude",
        background_color=template.background_color,
        description=template.description,
        system_instructions=template.system_instructions or "",
        user_instructions=template.user_instructions,
        model=template.model,
        tools=template.tools,
        behavioral_rules=template.behavioral_rules or [],
        success_criteria=template.success_criteria or [],
        tags=template.tags or [],
        is_default=template.is_default,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
        # Handover 0335: Export tracking fields
        last_exported_at=template.last_exported_at,
        may_be_stale=may_be_stale,
        category=template.category,
        project_type=template.project_type,
        variables=template.variables or [],
        version=template.version or "1.0.0",
        usage_count=template.usage_count or 0,
        avg_generation_ms=template.avg_generation_ms,
        created_by=template.created_by,
        preferred_tool=getattr(template, "preferred_tool", template.cli_tool or "claude"),
        is_system_role=_is_system_managed_role(template.role),
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Get template by ID for the current tenant.

    Migrated to TemplateService - Handover 1011 Phase 2.
    """
    logger.debug(f"User {current_user.username} getting template {template_id}")

    template = await template_service.get_template_by_id(session, template_id, current_user.tenant_key)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    return _convert_to_response(template)


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> list[TemplateResponse]:
    """
    List all templates for the current tenant.

    Migrated to TemplateService - Handover 1011 Phase 2.
    """
    logger.debug(f"User {current_user.username} listing templates")

    templates = await template_service.list_templates_with_filters(
        session, current_user.tenant_key, role=role, is_active=is_active
    )

    return [_convert_to_response(t) for t in templates]


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Create a new template.

    NOTE: This endpoint currently uses direct DB access for complex validation logic.
    Future work: Extract validation, materialization, and WebSocket logic to TemplateService.
    """
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

    if await template_service.check_template_name_exists(session, context["tenant_key"], generated_name):
        raise HTTPException(status_code=400, detail=f"Agent name '{generated_name}' already exists")

    # Validate system prompt
    is_valid, error_msg = validate_system_prompt(template.system_instructions)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Auto-assign background color
    background_color = template.background_color or get_role_color(template.role)

    # Set default description when missing
    description = template.description
    if not description:
        if template.cli_tool == "claude":
            description = f"Subagent for {template.role}"
        else:
            # Generic fallback for non-Claude templates
            description = f"{template.role} agent template" if template.role else "Agent template"

    # Extract variables
    variables = re.findall(r"\{(\w+)\}", template.system_instructions)

    if template.is_default and template.role:
        existing_defaults = await template_service.get_default_templates_by_role(
            session, context["tenant_key"], template.role, context.get("product_id")
        )
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
        system_instructions=template.system_instructions,
        model=template.model or "sonnet",
        tools=None,
        variables=variables,
        behavioral_rules=template.behavioral_rules or [],
        success_criteria=template.success_criteria or [],
        version="1.0.0",
        is_active=template.is_active,
        is_default=template.is_default,
        tags=template.tags or [],
        tool=template.cli_tool,
        created_by=current_user.username,
    )

    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)

    logger.info(f"Created template {new_template.id} for tenant {context['tenant_key']}")

    return _convert_to_response(new_template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    updates: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Update an existing template.

    NOTE: Currently uses direct DB access. Future work: Use TemplateService.update_template().
    """
    context = get_tenant_and_product_from_user(current_user)

    template = await template_service.get_template_by_id(session, template_id, context["tenant_key"])

    if not template:
        if await template_service.check_cross_tenant_template_exists(session, template_id):
            raise HTTPException(status_code=403, detail="Access denied for this template")
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if system-managed
    if _is_system_managed_role(template.role):
        raise HTTPException(status_code=403, detail="Cannot modify system-managed templates")

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)

    # Block attempts to modify system_instructions via API
    if "system_instructions" in update_data:
        raise HTTPException(
            status_code=403,
            detail="system_instructions is read-only; use reset-system to restore defaults",
        )

    if "user_instructions" in update_data:
        await template_service.create_template_archive(
            session,
            template,
            archive_reason="Update user instructions",
            archive_type="auto",
            archived_by=current_user.username,
        )

    # Enforce 8-role active limit when toggling is_active for user-managed roles
    if "is_active" in update_data and update_data["is_active"] is not None:
        new_is_active = bool(update_data["is_active"])
        if new_is_active != bool(template.is_active) and not _is_system_managed_role(template.role):
            is_valid, error_msg = await template_service.validate_active_agent_limit(
                session=session,
                tenant_key=context["tenant_key"],
                template_id=template.id,
                new_is_active=new_is_active,
                role=template.role,
            )
            if not is_valid:
                raise HTTPException(status_code=409, detail=error_msg)

    for field, value in update_data.items():
        if field == "user_instructions" and value:
            template.user_instructions = value
        elif hasattr(template, field):
            setattr(template, field, value)

    # If role changed, auto-update background color to match new role
    if "role" in update_data:
        template.background_color = get_role_color(template.role)

    await session.commit()
    await session.refresh(template)

    logger.info(f"Updated template {template_id}")

    return _convert_to_response(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
) -> dict:
    """
    Hard delete a template and all related records.

    Deletes:
    - TemplateUsageStats records
    - TemplateArchive records (version history)
    - Sets AgentJob.template_id to NULL for historical jobs
    - The template itself

    NOTE: TemplateAugmentation removed (Handover 0423 - dead code cleanup)
    """

    try:
        context = get_tenant_and_product_from_user(current_user)

        template = await template_service.get_template_by_id(session, template_id, context["tenant_key"])

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        if _is_system_managed_role(template.role):
            raise HTTPException(status_code=403, detail="Cannot delete system-managed templates")

        template_name = template.name

        deleted = await template_service.hard_delete_template(session, template_id, context["tenant_key"])

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete template")

        await session.commit()

        logger.info(f"Hard deleted template {template_id} ({template_name})")

        return {"message": f"Template '{template_name}' permanently deleted", "template_id": template_id}

    except HTTPException:
        raise  # Re-raise HTTP exceptions (403, 404, 500, etc.) without modification
    except Exception as e:
        logger.exception("Failed to delete template")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {e!s}") from e


@router.get("/stats/active-count", response_model=dict)
async def get_active_count(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
) -> dict:
    """
    Get count of active user-managed templates.

    Migrated to TemplateService - Handover 1011 Phase 2.
    """
    context = get_tenant_and_product_from_user(current_user)

    count = await template_service.get_active_user_managed_count(session, context["tenant_key"])

    return {
        "active_count": count,
        "limit": USER_MANAGED_AGENT_LIMIT,
        "available": max(0, USER_MANAGED_AGENT_LIMIT - count),
    }
