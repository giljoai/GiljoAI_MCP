"""
Organization CRUD Endpoints - Handover 0424c.

Handles organization CRUD operations using OrgService.

All database access goes through OrgService following the established
service layer pattern (similar to ProductService, ProjectService).
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.org_service import OrgService

from .models import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _serialize_organization(org) -> dict:
    """Convert Organization model to dict for JSON response.

    Must be called while still in session context to access attributes.
    """
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "is_active": org.is_active,
        "created_at": org.created_at,
        "updated_at": org.updated_at,
        "settings": org.settings or {},
        "members": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role,
                "joined_at": m.joined_at,
                "invited_by": m.invited_by
            }
            for m in (org.members or [])
        ]
    }


def get_org_service(
    db: AsyncSession = Depends(get_db_session)
) -> OrgService:
    """Dependency for OrgService injection."""
    return OrgService(db)


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """
    Create new organization with current user as owner.

    Args:
        org_data: Organization creation data
        current_user: Current authenticated user (becomes owner)
        org_service: Organization service instance

    Returns:
        Created organization with owner membership

    Raises:
        409: Organization with slug already exists
        400: Validation error or creation failed
    """
    try:
        result = await org_service.create_organization(
            name=org_data.name,
            slug=org_data.slug,
            owner_id=current_user.id,
            tenant_key=current_user.tenant_key,
            settings=org_data.settings
        )

        if not result["success"]:
            if "already exists" in result["error"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result["error"]
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        org = result["data"]
        logger.info(
            "Organization created via API",
            extra={
                "org_id": org.id,
                "slug": org.slug,
                "owner_id": current_user.id
            }
        )

        return _serialize_organization(org)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """
    List all organizations for current user.

    Returns organizations where current user is a member (any role).

    Args:
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        List of organizations user belongs to

    Raises:
        500: Internal server error
    """
    try:
        result = await org_service.get_user_organizations(current_user.id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )

        return [_serialize_organization(org) for org in result["data"]]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing organizations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """
    Get organization by ID.

    Requires user to be a member of the organization.

    Args:
        org_id: Organization ID
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        Organization details with members

    Raises:
        403: User is not a member of organization
        404: Organization not found
    """
    try:
        # Check membership
        if not await org_service.can_view_org(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization"
            )

        result = await org_service.get_organization(org_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        return _serialize_organization(result["data"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """
    Update organization (owner or admin only).

    Allows updating organization name and settings.
    Requires owner or admin role.

    Args:
        org_id: Organization ID
        org_data: Update data
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        Updated organization

    Raises:
        403: User is not owner or admin
        400: Update failed
    """
    try:
        if not await org_service.can_edit_org(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can update organization"
            )

        result = await org_service.update_organization(
            org_id=org_id,
            name=org_data.name,
            settings=org_data.settings
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        logger.info(
            "Organization updated via API",
            extra={
                "org_id": org_id,
                "updated_by": current_user.id
            }
        )

        return _serialize_organization(result["data"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service)
):
    """
    Delete organization (owner only).

    Soft deletes organization by setting is_active=False.
    Only organization owner can delete.

    Args:
        org_id: Organization ID
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        Success message

    Raises:
        403: User is not owner
        400: Delete failed
    """
    try:
        if not await org_service.can_delete_org(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner can delete organization"
            )

        result = await org_service.delete_organization(org_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        logger.info(
            "Organization deleted via API",
            extra={
                "org_id": org_id,
                "deleted_by": current_user.id
            }
        )

        return {"message": "Organization deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
