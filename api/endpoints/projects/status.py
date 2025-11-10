"""
Project Status Endpoints - Handover 0125

Handles project status and query operations:
- GET /{project_id}/status - Get project status
- GET /{project_id}/summary - Get project summary

All operations use ProjectService where available.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import ProjectSummaryResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{project_id}/status")
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> dict:
    """
    Get project status with metrics.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        Dict with project status and metrics

    Raises:
        HTTPException 404: Project not found
    """
    logger.debug(f"User {current_user.username} getting status for project {project_id}")

    # Get status via ProjectService
    result = await project_service.get_project_status(project_id=project_id)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Project not found")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    logger.info(f"Retrieved status for project {project_id}")
    return result


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse)
async def get_project_summary(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectSummaryResponse:
    """
    Get comprehensive project summary for after-action review (Handover 0062).

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectSummaryResponse with full project summary

    Raises:
        HTTPException 404: Project not found
        HTTPException 501: Not yet implemented
    """
    logger.debug(f"User {current_user.username} getting summary for project {project_id}")

    # TODO: Add get_project_summary to ProjectService
    # This endpoint requires complex queries across multiple tables (agents, messages)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ProjectService.get_project_summary not yet implemented"
    )
