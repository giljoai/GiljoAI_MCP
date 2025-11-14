"""
Template History Endpoints - Handover 0126

Handles template history, restore, and reset operations.

NOTE: This module contains operations not yet in TemplateService.
Future work: Extract history management logic to TemplateService methods.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import AgentTemplate, TemplateArchive, User
from src.giljo_mcp.services.template_service import TemplateService

from .dependencies import get_template_service
from .models import TemplateHistoryResponse, TemplateResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{template_id}/history", response_model=list[TemplateHistoryResponse])
async def get_template_history(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[TemplateHistoryResponse]:
    """
    Get template version history.

    TODO: Add get_template_history to TemplateService.
    """
    logger.info("User %s requesting history for template %s", current_user.username, template_id)

    stmt = (
        select(TemplateArchive)
        .where(
            TemplateArchive.template_id == template_id,
            TemplateArchive.tenant_key == current_user.tenant_key,
        )
        .order_by(TemplateArchive.archived_at.desc())
    )
    result = await session.execute(stmt)
    archives = result.scalars().all()

    return [
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
        for archive in archives
    ]


@router.post("/{template_id}/restore/{archive_id}", response_model=TemplateResponse)
async def restore_template(
    template_id: str,
    archive_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """
    Restore template from archive.

    TODO: Add restore_template to TemplateService.
    """
    logger.info(
        "User %s restoring template %s from archive %s",
        current_user.username,
        template_id,
        archive_id,
    )

    # Fetch archive with tenant isolation
    stmt = select(TemplateArchive).where(
        TemplateArchive.id == archive_id,
        TemplateArchive.template_id == template_id,
        TemplateArchive.tenant_key == current_user.tenant_key,
    )
    result = await session.execute(stmt)
    archive = result.scalar_one_or_none()
    if not archive:
        raise HTTPException(status_code=404, detail="Archive entry not found")

    # Fetch template
    stmt = select(AgentTemplate).where(
        AgentTemplate.id == template_id,
        AgentTemplate.tenant_key == current_user.tenant_key,
    )
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Archive current template version before overwriting
    current_archive = TemplateArchive(
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
        archive_reason="Replaced by restoration",
        archive_type="auto",
        archived_by=current_user.username,
        usage_count_at_archive=template.usage_count,
        avg_generation_ms_at_archive=template.avg_generation_ms,
    )
    session.add(current_archive)

    # Restore from selected archive
    template.template_content = archive.template_content
    template.variables = archive.variables
    template.behavioral_rules = archive.behavioral_rules
    template.success_criteria = archive.success_criteria
    template.version = archive.version

    await session.commit()
    await session.refresh(template)

    from .crud import _convert_to_response  # local import to avoid cycles

    return _convert_to_response(template)


@router.post("/{template_id}/reset", response_model=TemplateResponse)
async def reset_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """
    Reset template to default state.

    TODO: Add reset_template to TemplateService.
    """
    logger.info("User %s resetting template %s", current_user.username, template_id)

    stmt = select(AgentTemplate).where(
        AgentTemplate.id == template_id,
        AgentTemplate.tenant_key == current_user.tenant_key,
    )
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        cross_tenant_result = await session.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
        if cross_tenant_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied for this template")
        raise HTTPException(status_code=404, detail="Template not found")

    # Archive current version
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
        archive_reason="Reset template",
        archive_type="auto",
        archived_by=current_user.username,
        usage_count_at_archive=template.usage_count,
        avg_generation_ms_at_archive=template.avg_generation_ms,
    )
    session.add(archive)

    # Reset editable fields to defaults
    template.user_instructions = None
    template.behavioral_rules = []
    template.success_criteria = []
    template.tags = []

    await session.commit()
    await session.refresh(template)

    from .crud import _convert_to_response  # local import to avoid cycles

    return _convert_to_response(template)


@router.post("/{template_id}/reset-system", response_model=TemplateResponse)
async def reset_system_instructions(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """
    Reset system instructions to default.

    TODO: Add reset_system_instructions to TemplateService.
    """
    logger.info("User %s resetting system instructions for template %s", current_user.username, template_id)

    stmt = select(AgentTemplate).where(
        AgentTemplate.id == template_id,
        AgentTemplate.tenant_key == current_user.tenant_key,
    )
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        cross_tenant_result = await session.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
        if cross_tenant_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied for this template")
        raise HTTPException(status_code=404, detail="Template not found")

    original_system = template.system_instructions

    # Archive previous system instructions (including user_instructions in template_content)
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
        archive_reason="Reset system instructions",
        archive_type="auto",
        archived_by=current_user.username,
        usage_count_at_archive=template.usage_count,
        avg_generation_ms_at_archive=template.avg_generation_ms,
    )
    session.add(archive)

    # Reset system instructions to a canonical default that includes core MCP
    # tools referenced in tests (acknowledge_job, report_progress, complete_job, get_next_instruction).
    # This mirrors the seeded default orchestrator/system role instructions.
    template.system_instructions = (
        "# System Instructions\n\n"
        "Use acknowledge_job() to claim tasks.\n"
        "Use report_progress() to send updates.\n"
        "Use complete_job() when the task is finished.\n"
        "Use get_next_instruction() to request additional guidance.\n"
    )

    await session.commit()
    await session.refresh(template)

    from .crud import _convert_to_response  # local import to avoid cycles

    return _convert_to_response(template)
