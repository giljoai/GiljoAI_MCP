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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
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
    return {
        "tenant_key": user.tenant_key,
        "product_id": getattr(user, "active_product_id", None)
    }


def _convert_to_response(template: AgentTemplate) -> TemplateResponse:
    """Convert ORM model to response schema"""
    # Merge system and user instructions for backward compatibility
    merged_content = template.system_instructions or template.template_content or ""
    if template.user_instructions:
        merged_content = f"{merged_content}\n\n{template.user_instructions}"

    return TemplateResponse(
        id=template.id,
        tenant_key=template.tenant_key,
        product_id=template.product_id,
        name=template.name,
        role=template.role,
        cli_tool=template.cli_tool or "claude",
        background_color=template.background_color,
        description=template.description,
        system_instructions=template.system_instructions or template.template_content or "",
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
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Get template by ID.

    Uses TemplateService for data retrieval.
    """
    logger.debug(f"User {current_user.username} getting template {template_id}")

    result = await template_service.get_template(
        template_id=template_id,
        tenant_key=current_user.tenant_key
    )

    if not result.get("success"):
        error_msg = result.get("error", "Template not found")
        raise HTTPException(status_code=404, detail=error_msg)

    template = result.get("template")
    return _convert_to_response(template)


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    template_service: TemplateService = Depends(get_template_service),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> list[TemplateResponse]:
    """
    List all templates for the current tenant.

    Uses TemplateService for data retrieval.
    Note: Filtering logic kept here temporarily until TemplateService supports it.
    """
    logger.debug(f"User {current_user.username} listing templates")

    result = await template_service.list_templates(tenant_key=current_user.tenant_key)

    if not result.get("success"):
        error_msg = result.get("error", "Failed to list templates")
        raise HTTPException(status_code=500, detail=error_msg)

    templates = result.get("templates", [])

    # Apply filters (TODO: Move to TemplateService)
    if role:
        templates = [t for t in templates if t.role == role]
    if is_active is not None:
        templates = [t for t in templates if t.is_active == is_active]

    return [_convert_to_response(t) for t in templates]


@router.post("/", response_model=TemplateResponse)
async def create_template(
    template: TemplateCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """
    Create a new template.

    NOTE: This endpoint currently uses direct DB access for complex validation logic.
    Future work: Extract validation, materialization, and WebSocket logic to TemplateService.
    """
    try:
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

        # Check uniqueness
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == context["tenant_key"],
                AgentTemplate.name == generated_name
            )
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Agent name '{generated_name}' already exists")

        # Validate system prompt
        is_valid, error_msg = validate_system_prompt(template.template_content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Auto-assign background color
        background_color = template.background_color or get_role_color(template.role)

        # Set default description for Claude
        description = template.description
        if not description and template.cli_tool == "claude":
            description = f"Subagent for {template.role}"

        # Extract variables
        variables = re.findall(r"\{(\w+)\}", template.template_content)

        # Handle default template logic
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
            for existing in result.scalars().all():
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
            system_instructions=template.template_content,  # Store in both fields
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    updates: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """
    Update an existing template.

    NOTE: Currently uses direct DB access. Future work: Use TemplateService.update_template().
    """
    try:
        context = get_tenant_and_product_from_user(current_user)

        # Get existing template
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == template_id,
                AgentTemplate.tenant_key == context["tenant_key"]
            )
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Check if system-managed
        if _is_system_managed_role(template.role):
            raise HTTPException(status_code=403, detail="Cannot modify system-managed templates")

        # Apply updates
        update_data = updates.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "template_content" and value:
                # Legacy support: update both fields
                template.template_content = value
                template.system_instructions = value
            elif field == "user_instructions" and value:
                template.user_instructions = value
            elif hasattr(template, field):
                setattr(template, field, value)

        await session.commit()
        await session.refresh(template)

        logger.info(f"Updated template {template_id}")

        return _convert_to_response(template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Soft delete a template.

    NOTE: Currently uses direct DB access. Future work: Add delete_template to TemplateService.
    """
    try:
        context = get_tenant_and_product_from_user(current_user)

        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.id == template_id,
                AgentTemplate.tenant_key == context["tenant_key"]
            )
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        if _is_system_managed_role(template.role):
            raise HTTPException(status_code=403, detail="Cannot delete system-managed templates")

        # Soft delete
        template.is_active = False
        await session.commit()

        logger.info(f"Deleted template {template_id}")

        return {"message": "Template deleted successfully", "template_id": template_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@router.get("/stats/active-count", response_model=dict)
async def get_active_count(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get count of active user-managed templates.
    """
    try:
        context = get_tenant_and_product_from_user(current_user)

        stmt = select(func.count(AgentTemplate.id)).where(
            and_(
                AgentTemplate.tenant_key == context["tenant_key"],
                AgentTemplate.is_active == True,
                AgentTemplate.role.not_in(SYSTEM_MANAGED_ROLES)
            )
        )
        result = await session.execute(stmt)
        count = result.scalar()

        return {
            "active_count": count,
            "limit": USER_MANAGED_AGENT_LIMIT,
            "available": max(0, USER_MANAGED_AGENT_LIMIT - count)
        }

    except Exception as e:
        logger.error(f"Failed to get active count: {e}")
        raise HTTPException(status_code=500, detail=str(e))
