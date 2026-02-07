"""
Organization Membership Endpoints - Handover 0424c.

Handles organization membership management using OrgService.

Features:
- List organization members
- Invite new members
- Change member roles
- Remove members
- Transfer ownership
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.org_service import OrgService

from .models import MemberInvite, MemberResponse, MemberRoleUpdate, OwnershipTransfer


logger = logging.getLogger(__name__)

# Router for member operations
router = APIRouter()


def get_org_service(db: AsyncSession = Depends(get_db_session)) -> OrgService:
    """Dependency for OrgService injection."""
    return OrgService(db)


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
):
    """
    List all members of organization.

    Requires user to be a member of the organization.

    Args:
        org_id: Organization ID
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        List of organization members with roles

    Raises:
        403: User is not a member
        500: Internal server error
    """
    try:
        if not await org_service.can_view_org(org_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")

        result = await org_service.list_members(org_id)

        if not result["success"]:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["error"])

        return result["data"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing members: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: str,
    invite_data: MemberInvite,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
):
    """
    Invite user to organization (owner or admin only).

    Creates membership record for invited user.
    Requires owner or admin role.

    Args:
        org_id: Organization ID
        invite_data: Invitation data (user_id, role)
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        Created membership record

    Raises:
        403: User is not owner or admin
        409: User is already a member
        400: Invitation failed
    """
    try:
        if not await org_service.can_manage_members(org_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner or admin can invite members")

        result = await org_service.invite_member(
            org_id=org_id,
            user_id=invite_data.user_id,
            role=invite_data.role,
            invited_by=current_user.id,
            tenant_key=current_user.tenant_key,
        )

        if not result["success"]:
            if "already" in result["error"].lower():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result["error"])
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        logger.info(
            "Member invited via API",
            extra={
                "org_id": org_id,
                "invited_user_id": invite_data.user_id,
                "role": invite_data.role,
                "invited_by": current_user.id,
            },
        )

        return result["data"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting member: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.put("/{org_id}/members/{user_id}", response_model=MemberResponse)
async def change_member_role(
    org_id: str,
    user_id: str,
    role_data: MemberRoleUpdate,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
):
    """
    Change member's role (owner or admin only).

    Updates member's role within organization.
    Requires owner or admin role.
    Cannot change owner's role.

    Args:
        org_id: Organization ID
        user_id: User ID whose role to change
        role_data: New role data
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        Updated membership record

    Raises:
        403: User is not owner or admin
        400: Cannot change owner's role
    """
    try:
        if not await org_service.can_manage_members(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only owner or admin can change member roles"
            )

        result = await org_service.change_member_role(org_id=org_id, user_id=user_id, new_role=role_data.role)

        if not result["success"]:
            if "owner" in result["error"].lower():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        logger.info(
            "Member role changed via API",
            extra={"org_id": org_id, "user_id": user_id, "new_role": role_data.role, "changed_by": current_user.id},
        )

        return result["data"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing member role: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.delete("/{org_id}/members/{user_id}")
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
):
    """
    Remove member from organization (owner or admin only).

    Deletes membership record.
    Requires owner or admin role.
    Cannot remove organization owner.

    Args:
        org_id: Organization ID
        user_id: User ID to remove
        current_user: Current authenticated user
        org_service: Organization service instance

    Returns:
        Success message

    Raises:
        403: User is not owner or admin
        400: Cannot remove owner
    """
    try:
        if not await org_service.can_manage_members(org_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner or admin can remove members")

        result = await org_service.remove_member(org_id=org_id, user_id=user_id)

        if not result["success"]:
            if "owner" in result["error"].lower():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        logger.info(
            "Member removed via API",
            extra={"org_id": org_id, "removed_user_id": user_id, "removed_by": current_user.id},
        )

        return {"message": "Member removed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


# Separate router for transfer endpoint (different path pattern)
transfer_router = APIRouter()


@transfer_router.post("/{org_id}/transfer")
async def transfer_ownership(
    org_id: str,
    transfer_data: OwnershipTransfer,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
):
    """
    Transfer organization ownership (owner only).

    Changes organization owner to another member.
    Previous owner becomes admin.
    Only current owner can transfer ownership.

    Args:
        org_id: Organization ID
        transfer_data: Transfer data (new_owner_id)
        current_user: Current authenticated user (must be owner)
        org_service: Organization service instance

    Returns:
        Success message

    Raises:
        403: User is not owner
        400: Transfer failed (e.g., new owner not a member)
    """
    try:
        if not await org_service.can_delete_org(org_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can transfer ownership")

        result = await org_service.transfer_ownership(
            org_id=org_id, current_owner_id=current_user.id, new_owner_id=transfer_data.new_owner_id
        )

        if not result["success"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        logger.info(
            "Ownership transferred via API",
            extra={"org_id": org_id, "previous_owner_id": current_user.id, "new_owner_id": transfer_data.new_owner_id},
        )

        return {"message": "Ownership transferred"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transferring ownership: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
