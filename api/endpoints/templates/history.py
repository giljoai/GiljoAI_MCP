"""
Template History Endpoints - Handover 0126

Handles template history, restore, and reset operations.

NOTE: This module contains operations not yet in TemplateService.
Future work: Extract history management logic to TemplateService methods.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.template_service import TemplateService

from .dependencies import get_template_service
from .models import TemplateHistoryResponse, TemplateResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{template_id}/history", response_model=list[TemplateHistoryResponse])
async def get_template_history(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    template_service: TemplateService = Depends(get_template_service),
) -> list[TemplateHistoryResponse]:
    """
    Get template version history.

    TODO: Add get_template_history to TemplateService.
    """
    logger.info(f"User {current_user.username} requesting history for template {template_id}")

    # TODO: Implement in TemplateService
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TemplateService.get_template_history not yet implemented"
    )


@router.post("/{template_id}/restore/{archive_id}", response_model=TemplateResponse)
async def restore_template(
    template_id: str,
    archive_id: str,
    current_user: User = Depends(get_current_active_user),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Restore template from archive.

    TODO: Add restore_template to TemplateService.
    """
    logger.info(f"User {current_user.username} restoring template {template_id} from archive {archive_id}")

    # TODO: Implement in TemplateService
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TemplateService.restore_template not yet implemented"
    )


@router.post("/{template_id}/reset", response_model=TemplateResponse)
async def reset_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Reset template to default state.

    TODO: Add reset_template to TemplateService.
    """
    logger.info(f"User {current_user.username} resetting template {template_id}")

    # TODO: Implement in TemplateService
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TemplateService.reset_template not yet implemented"
    )


@router.post("/{template_id}/reset-system", response_model=TemplateResponse)
async def reset_system_instructions(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Reset system instructions to default.

    TODO: Add reset_system_instructions to TemplateService.
    """
    logger.info(f"User {current_user.username} resetting system instructions for template {template_id}")

    # TODO: Implement in TemplateService
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TemplateService.reset_system_instructions not yet implemented"
    )
