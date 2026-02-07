"""
Organization Service - Business logic for organization management.

Handover 0424b: Implements CRUD and membership management.

Features:
- Create organization with owner
- Invite/remove members
- Role management (owner, admin, member, viewer)
- Permission checks
"""

import logging
import re
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.models.organizations import Organization, OrgMembership


logger = logging.getLogger(__name__)


class OrgService:
    """Service for organization management."""

    def __init__(self, session: AsyncSession, websocket_manager: Optional[Any] = None):
        self.session = session
        self._websocket_manager = websocket_manager

    # =========================================================================
    # Organization CRUD
    # =========================================================================

    async def create_organization(
        self, name: str, owner_id: str, tenant_key: str, slug: Optional[str] = None, settings: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Create organization with owner.

        Args:
            name: Organization display name
            owner_id: User ID who will be owner
            tenant_key: Tenant isolation key
            slug: URL-friendly identifier (auto-generated if not provided)
            settings: Optional org-level settings

        Returns:
            dict with 'success' bool and 'data' or 'error'
        """
        try:
            # Generate slug from name if not provided
            if not slug:
                slug = self._generate_slug(name)

            # Check slug uniqueness
            existing = await self.get_organization_by_slug(slug)
            if existing["success"]:
                return {"success": False, "error": f"Organization with slug '{slug}' already exists"}

            # Create organization
            org = Organization(name=name, tenant_key=tenant_key, slug=slug, settings=settings or {})
            self.session.add(org)
            await self.session.flush()  # Get org.id

            # Create owner membership
            owner_membership = OrgMembership(org_id=org.id, user_id=owner_id, tenant_key=tenant_key, role="owner")
            self.session.add(owner_membership)

            await self.session.commit()
            await self.session.refresh(org, ["members"])

            logger.info("Organization created", extra={"org_id": org.id, "slug": slug, "owner_id": owner_id})

            # Emit WebSocket event (if available)
            if self._websocket_manager:
                await self._websocket_manager.broadcast_to_user(
                    user_id=owner_id, event="org:created", data={"org_id": org.id, "name": name, "slug": slug}
                )

            return {"success": True, "data": org}

        except SQLAlchemyError as e:
            logger.error(f"Failed to create organization: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def get_organization(self, org_id: str) -> dict[str, Any]:
        """Get organization by ID (only active orgs)."""
        try:
            stmt = (
                select(Organization)
                .where(
                    Organization.id == org_id,
                    Organization.is_active == True,  # noqa: E712
                )
                .options(selectinload(Organization.members))
            )

            result = await self.session.execute(stmt)
            org = result.scalar_one_or_none()

            if not org:
                return {"success": False, "error": "Organization not found"}

            return {"success": True, "data": org}

        except SQLAlchemyError as e:
            logger.error(f"Failed to get organization: {e}")
            return {"success": False, "error": str(e)}

    async def get_organization_by_slug(self, slug: str) -> dict[str, Any]:
        """Get organization by slug."""
        try:
            stmt = select(Organization).where(Organization.slug == slug).options(selectinload(Organization.members))

            result = await self.session.execute(stmt)
            org = result.scalar_one_or_none()

            if not org:
                return {"success": False, "error": "Organization not found"}

            return {"success": True, "data": org}

        except SQLAlchemyError as e:
            logger.error(f"Failed to get organization by slug: {e}")
            return {"success": False, "error": str(e)}

    async def update_organization(
        self, org_id: str, name: Optional[str] = None, settings: Optional[dict] = None
    ) -> dict[str, Any]:
        """Update organization details."""
        try:
            org_result = await self.get_organization(org_id)
            if not org_result["success"]:
                return org_result

            org = org_result["data"]

            if name:
                org.name = name
            if settings is not None:
                org.settings = settings

            await self.session.commit()

            logger.info("Organization updated", extra={"org_id": org_id})

            # Re-query with members to ensure relationships are loaded
            return await self.get_organization(org_id)

        except SQLAlchemyError as e:
            logger.error(f"Failed to update organization: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def delete_organization(self, org_id: str) -> dict[str, Any]:
        """Delete organization (soft delete by setting is_active=False)."""
        try:
            org_result = await self.get_organization(org_id)
            if not org_result["success"]:
                return org_result

            org = org_result["data"]
            org.is_active = False

            await self.session.commit()

            logger.info("Organization deleted (soft)", extra={"org_id": org_id})

            return {"success": True, "data": {"deleted": True}}

        except SQLAlchemyError as e:
            logger.error(f"Failed to delete organization: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Membership Management
    # =========================================================================

    async def invite_member(
        self, org_id: str, user_id: str, role: str, invited_by: str, tenant_key: str
    ) -> dict[str, Any]:
        """
        Invite user to organization.

        Args:
            org_id: Organization ID
            user_id: User ID to invite
            role: Role to assign (admin, member, viewer)
            invited_by: User ID of inviter
            tenant_key: Tenant isolation key

        Returns:
            dict with 'success' bool and 'data' or 'error'
        """
        try:
            # Check if already a member
            existing = await self._get_membership(org_id, user_id)
            if existing:
                return {"success": False, "error": "User is already a member of this organization"}

            # Validate role
            if role not in ("admin", "member", "viewer"):
                return {"success": False, "error": f"Invalid role: {role}. Must be admin, member, or viewer"}

            membership = OrgMembership(
                org_id=org_id, user_id=user_id, role=role, invited_by=invited_by, tenant_key=tenant_key
            )
            self.session.add(membership)
            await self.session.commit()

            logger.info(
                "Member invited to organization",
                extra={"org_id": org_id, "user_id": user_id, "role": role, "invited_by": invited_by},
            )

            # Emit WebSocket event (if available)
            if self._websocket_manager:
                await self._websocket_manager.broadcast_to_user(
                    user_id=user_id, event="org:invited", data={"org_id": org_id, "role": role}
                )

            return {"success": True, "data": membership}

        except SQLAlchemyError as e:
            logger.error(f"Failed to invite member: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def remove_member(self, org_id: str, user_id: str) -> dict[str, Any]:
        """Remove member from organization."""
        try:
            membership = await self._get_membership(org_id, user_id)

            if not membership:
                return {"success": False, "error": "User is not a member"}

            if membership.role == "owner":
                return {"success": False, "error": "Cannot remove owner. Transfer ownership first."}

            await self.session.delete(membership)
            await self.session.commit()

            logger.info("Member removed from organization", extra={"org_id": org_id, "user_id": user_id})

            return {"success": True, "data": {"removed": True}}

        except SQLAlchemyError as e:
            logger.error(f"Failed to remove member: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def change_member_role(self, org_id: str, user_id: str, new_role: str) -> dict[str, Any]:
        """Change member's role in organization."""
        try:
            membership = await self._get_membership(org_id, user_id)

            if not membership:
                return {"success": False, "error": "User is not a member"}

            if membership.role == "owner":
                return {"success": False, "error": "Cannot change owner role. Use transfer_ownership instead."}

            if new_role not in ("admin", "member", "viewer"):
                return {"success": False, "error": f"Invalid role: {new_role}"}

            membership.role = new_role
            await self.session.commit()

            logger.info("Member role changed", extra={"org_id": org_id, "user_id": user_id, "new_role": new_role})

            return {"success": True, "data": membership}

        except SQLAlchemyError as e:
            logger.error(f"Failed to change member role: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def transfer_ownership(self, org_id: str, current_owner_id: str, new_owner_id: str) -> dict[str, Any]:
        """Transfer organization ownership to another member."""
        try:
            # Verify current owner
            current = await self._get_membership(org_id, current_owner_id)
            if not current or current.role != "owner":
                return {"success": False, "error": "Only owner can transfer ownership"}

            # Verify new owner is a member
            new_owner = await self._get_membership(org_id, new_owner_id)
            if not new_owner:
                return {"success": False, "error": "New owner must be a member"}

            # Transfer
            current.role = "admin"  # Demote to admin
            new_owner.role = "owner"

            await self.session.commit()

            logger.info("Ownership transferred", extra={"org_id": org_id, "from": current_owner_id, "to": new_owner_id})

            return {"success": True, "data": {"transferred": True}}

        except SQLAlchemyError as e:
            logger.error(f"Failed to transfer ownership: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def list_members(self, org_id: str) -> dict[str, Any]:
        """List all members of organization."""
        try:
            stmt = (
                select(OrgMembership)
                .where(OrgMembership.org_id == org_id, OrgMembership.is_active)
                .order_by(OrgMembership.joined_at)
            )

            result = await self.session.execute(stmt)
            members = result.scalars().all()

            return {"success": True, "data": list(members)}

        except SQLAlchemyError as e:
            logger.error(f"Failed to list members: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # User Queries
    # =========================================================================

    async def get_user_organizations(self, user_id: str) -> dict[str, Any]:
        """Get all organizations for a user."""
        try:
            stmt = (
                select(Organization)
                .join(OrgMembership, Organization.id == OrgMembership.org_id)
                .where(
                    OrgMembership.user_id == user_id, OrgMembership.is_active, Organization.is_active
                )
                .options(selectinload(Organization.members))
            )

            result = await self.session.execute(stmt)
            orgs = result.scalars().all()

            return {"success": True, "data": list(orgs)}

        except SQLAlchemyError as e:
            logger.error(f"Failed to get user organizations: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_role(self, org_id: str, user_id: str) -> Optional[str]:
        """Get user's role in organization."""
        membership = await self._get_membership(org_id, user_id)
        return membership.role if membership else None

    # =========================================================================
    # Permission Checks
    # =========================================================================

    async def can_manage_members(self, org_id: str, user_id: str) -> bool:
        """Check if user can manage members (owner or admin)."""
        role = await self.get_user_role(org_id, user_id)
        return role in ("owner", "admin")

    async def can_edit_org(self, org_id: str, user_id: str) -> bool:
        """Check if user can edit organization (owner or admin)."""
        role = await self.get_user_role(org_id, user_id)
        return role in ("owner", "admin")

    async def can_delete_org(self, org_id: str, user_id: str) -> bool:
        """Check if user can delete organization (owner only)."""
        role = await self.get_user_role(org_id, user_id)
        return role == "owner"

    async def can_view_org(self, org_id: str, user_id: str) -> bool:
        """Check if user can view organization (any member)."""
        role = await self.get_user_role(org_id, user_id)
        return role is not None

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _get_membership(self, org_id: str, user_id: str) -> Optional[OrgMembership]:
        """Get membership for user in org."""
        stmt = select(OrgMembership).where(
            OrgMembership.org_id == org_id, OrgMembership.user_id == user_id, OrgMembership.is_active
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)  # Remove special chars
        slug = re.sub(r"[\s_-]+", "-", slug)  # Replace spaces with hyphens
        slug = slug.strip("-")
        return slug
