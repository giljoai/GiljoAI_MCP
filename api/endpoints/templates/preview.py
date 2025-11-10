"""
Template Preview & Diff Endpoints - Handover 0126

Handles template preview and diff operations.

NOTE: This module contains operations not yet in TemplateService.
Future work: Extract preview/diff logic to TemplateService methods.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.template_service import TemplateService

from .dependencies import get_template_service
from .models import TemplateDiffResponse, TemplatePreviewRequest, TemplatePreviewResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{template_id}/diff", response_model=TemplateDiffResponse)
async def get_template_diff(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateDiffResponse:
    """
    Get diff between tenant template and system template.

    TODO: Add get_template_diff to TemplateService.
    """
    logger.info(f"User {current_user.username} requesting diff for template {template_id}")

    # TODO: Implement in TemplateService
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TemplateService.get_template_diff not yet implemented"
    )


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: str,
    request: TemplatePreviewRequest,
    current_user: User = Depends(get_current_active_user),
    template_service: TemplateService = Depends(get_template_service),
) -> TemplatePreviewResponse:
    """
    Preview template with variable substitutions.

    TODO: Add preview_template to TemplateService.
    """
    logger.info(f"User {current_user.username} previewing template {template_id}")

    # TODO: Implement in TemplateService
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="TemplateService.preview_template not yet implemented"
    )
