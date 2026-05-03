# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from giljo_mcp.models import AgentTemplate, User
from giljo_mcp.services.template_service import TemplateService
from giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES
from giljo_mcp.template_seeder import _get_mcp_bootstrap_section
from giljo_mcp.template_validation import get_role_color, slugify_name
from giljo_mcp.utils.log_sanitizer import sanitize

from .dependencies import get_template_service
from .models import TemplateCreate, TemplateResponse, TemplateUpdate


logger = logging.getLogger(__name__)

# Field allowlist for template updates — only these fields may be set via the
# update endpoint.  Replaces the previous hasattr() gate which allowed setting
# any model attribute including id, tenant_key, created_at, etc.
_ALLOWED_TEMPLATE_UPDATE_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "category",
        "role",
        "user_instructions",
        "variables",
        "behavioral_rules",
        "success_criteria",
        "tool",
        "cli_tool",
        "background_color",
        "model",
        "tools",
        "description",
        "version",
        "is_active",
        "is_default",
        "tags",
        "meta_data",
        "user_managed_export",
    }
)
router = APIRouter()

# Constants
USER_MANAGED_AGENT_LIMIT = 7  # Reserve one slot for orchestrator


def _is_system_managed_role(role: str | None) -> bool:
    """Check if role is system-managed"""
    return bool(role and role in SYSTEM_MANAGED_ROLES)


def _convert_to_response(template: AgentTemplate) -> TemplateResponse:
    """Convert ORM model to response schema"""
    # Merge system and user instructions for backward compatibility
    merged_content = template.system_instructions or ""
    if template.user_instructions:
        merged_content = f"{merged_content}\n\n{template.user_instructions}"

    may_be_stale = template.may_be_stale

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
        user_managed_export=template.user_managed_export or False,
        category=template.category,
        variables=template.variables or [],
        version=template.version or "1.0.0",
        usage_count=template.usage_count or 0,
        avg_generation_ms=template.avg_generation_ms,
        created_by=template.created_by,
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
    logger.debug("User %s getting template %s", sanitize(current_user.username), sanitize(template_id))

    template = await template_service.get_template_by_id(session, template_id, current_user.tenant_key)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    return _convert_to_response(template)


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
    role: str | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
) -> list[TemplateResponse]:
    """
    List templates for the current tenant with optional filters.
    """
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
    tenant_key = current_user.tenant_key

    # Generate name from role + suffix (always slugify for safety)
    raw_name = template.name or template.role or ""
    generated_name = slugify_name(template.role or raw_name, template.custom_suffix)

    if not generated_name or not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", generated_name):
        raise HTTPException(status_code=400, detail="Name must use lowercase letters, numbers, and hyphens only")
    if len(generated_name) > 100:
        raise HTTPException(status_code=400, detail="Name must be 100 characters or less")

    # Auto-suffix if name already taken for this tenant
    base_name = generated_name
    counter = 2
    while await template_service.check_template_name_exists(session, tenant_key, generated_name):
        generated_name = f"{base_name}-{counter}"
        counter += 1
        if counter > 20:
            raise HTTPException(status_code=400, detail=f"Too many agents named '{base_name}' — use a custom suffix")

    # Inject canonical MCP bootstrap — ignore whatever the frontend sends
    canonical_bootstrap = _get_mcp_bootstrap_section()

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

    # Extract variables from user_instructions (if any)
    variables = re.findall(r"\{(\w+)\}", template.user_instructions or "")

    if template.is_default and template.role:
        existing_defaults = await template_service.get_default_templates_by_role(session, tenant_key, template.role)
        for existing in existing_defaults:
            existing.is_default = False

    # Create new template
    new_template = AgentTemplate(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name=generated_name,
        category=template.category or "role",
        role=template.role,
        cli_tool=template.cli_tool,
        background_color=background_color,
        description=description,
        system_instructions=canonical_bootstrap,
        user_instructions=template.user_instructions or "",
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

    await template_service.add_and_commit_template(session, new_template)

    logger.info("Created template %s for tenant %s", new_template.id, sanitize(tenant_key))

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
    tenant_key = current_user.tenant_key

    template = await template_service.get_template_by_id(session, template_id, tenant_key)

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
                tenant_key=tenant_key,
                template_id=template.id,
                new_is_active=new_is_active,
                role=template.role,
            )
            if not is_valid:
                raise HTTPException(status_code=409, detail=error_msg)

    # Metadata-only updates (e.g. is_active toggle) should not bump updated_at,
    # otherwise the staleness check falsely triggers after enable/disable.
    metadata_only_fields = {"is_active"}
    is_metadata_only = set(update_data.keys()).issubset(metadata_only_fields)
    previous_updated_at = template.updated_at

    # Clear user_managed_export when content fields change (re-triggers staleness)
    content_fields = {"user_instructions", "role", "model", "tools", "description", "cli_tool"}
    if update_data.keys() & content_fields and "user_managed_export" not in update_data:
        template.user_managed_export = False

    for field, value in update_data.items():
        if field == "user_instructions" and value:
            template.user_instructions = value
        elif field in _ALLOWED_TEMPLATE_UPDATE_FIELDS:
            setattr(template, field, value)

    # If role changed, auto-update background color to match new role
    if "role" in update_data:
        template.background_color = get_role_color(template.role)

    await template_service.commit_and_refresh_template(session, template)

    # Restore updated_at when only metadata changed — use raw SQL to bypass onupdate
    if is_metadata_only and previous_updated_at is not None:
        from sqlalchemy import update

        await session.execute(
            update(AgentTemplate).where(AgentTemplate.id == template.id).values(updated_at=previous_updated_at)
        )
        await session.commit()
        await session.refresh(template)

    logger.info("Updated template %s", sanitize(template_id))

    response = _convert_to_response(template)

    # Broadcast template update via EventBus for real-time UI refresh
    try:
        from api.app_state import state

        if getattr(state, "event_bus", None):
            await state.event_bus.publish(
                "template:updated",
                {
                    "tenant_key": tenant_key,
                    "template_id": template.id,
                    "is_active": template.is_active,
                    "may_be_stale": template.may_be_stale,
                    "updated_fields": list(update_data.keys()),
                },
            )
    except Exception as pub_err:  # noqa: BLE001 - fire-and-forget WS event
        logger.warning("Failed to publish template update event: %s", sanitize(str(pub_err)))

    return response


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
        tenant_key = current_user.tenant_key

        template = await template_service.get_template_by_id(session, template_id, tenant_key)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        if _is_system_managed_role(template.role):
            raise HTTPException(status_code=403, detail="Cannot delete system-managed templates")

        template_name = template.name

        deleted = await template_service.hard_delete_template(session, template_id, tenant_key)

        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete template")

        logger.info("Hard deleted template %s (%s)", sanitize(template_id), sanitize(template_name))

        return {"message": f"Template '{template_name}' permanently deleted", "template_id": template_id}

    except HTTPException:
        raise  # Re-raise HTTP exceptions (403, 404, 500, etc.) without modification
    except Exception as e:  # Broad catch: API boundary, converts to HTTP error
        logger.exception("Failed to delete template")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete template. Check server logs.") from e


@router.get("/stats/active-count", response_model=dict)
async def get_active_count(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    template_service: TemplateService = Depends(get_template_service),
) -> dict:
    """
    Get count of active user-managed templates for the current tenant.
    """
    count = await template_service.get_active_user_managed_count(session, current_user.tenant_key)

    return {
        "active_count": count,
        "limit": USER_MANAGED_AGENT_LIMIT,
        "available": max(0, USER_MANAGED_AGENT_LIMIT - count),
    }
