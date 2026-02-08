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

from src.giljo_mcp.exceptions import (
    AlreadyExistsError,
    AuthorizationError,
    DatabaseError,
    ResourceNotFoundError,
    ValidationError,
)
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
    ) -> Organization:
        """
        Create organization with owner.

        Args:
            name: Organization display name
            owner_id: User ID who will be owner
            tenant_key: Tenant isolation key
            slug: URL-friendly identifier (auto-generated if not provided)
            settings: Optional org-level settings

        Returns:
            Organization: Created organization with owner membership

        Raises:
            AlreadyExistsError: Organization with slug already exists
            DatabaseError: Database operation failed
        """
        try:
            # Generate slug from name if not provided
            if not slug:
                slug = self._generate_slug(name)

            # Check slug uniqueness
            try:
                existing = await self.get_organization_by_slug(slug)
                if existing:
                    raise AlreadyExistsError(
                        message=f"Organization with slug '{slug}' already exists", context={"slug": slug}
                    )
            except ResourceNotFoundError:
                # Slug is available
                pass

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

            return org

        except AlreadyExistsError:
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to create organization")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to create organization", context={"name": name, "slug": slug, "error": str(e)}
            ) from e

    async def get_organization(self, org_id: str) -> Organization:
        """
        Get organization by ID (only active orgs).

        Args:
            org_id: Organization ID

        Returns:
            Organization: Found organization with members

        Raises:
            ResourceNotFoundError: Organization not found or inactive
            DatabaseError: Database operation failed
        """
        try:
            stmt = (
                select(Organization)
                .where(
                    Organization.id == org_id,
                    Organization.is_active,
                )
                .options(selectinload(Organization.members))
            )

            result = await self.session.execute(stmt)
            org = result.scalar_one_or_none()

            if not org:
                raise ResourceNotFoundError(message="Organization not found", context={"org_id": org_id})

            return org

        except ResourceNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to get organization")
            raise DatabaseError(
                message="Failed to get organization", context={"org_id": org_id, "error": str(e)}
            ) from e

    async def get_organization_by_slug(self, slug: str) -> Organization:
        """
        Get organization by slug.

        Args:
            slug: Organization slug

        Returns:
            Organization: Found organization with members

        Raises:
            ResourceNotFoundError: Organization with slug not found
            DatabaseError: Database operation failed
        """
        try:
            stmt = select(Organization).where(Organization.slug == slug).options(selectinload(Organization.members))

            result = await self.session.execute(stmt)
            org = result.scalar_one_or_none()

            if not org:
                raise ResourceNotFoundError(message="Organization not found", context={"slug": slug})

            return org

        except ResourceNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to get organization by slug")
            raise DatabaseError(
                message="Failed to get organization by slug", context={"slug": slug, "error": str(e)}
            ) from e

    async def update_organization(
        self, org_id: str, name: Optional[str] = None, settings: Optional[dict] = None
    ) -> Organization:
        """
        Update organization details.

        Args:
            org_id: Organization ID
            name: New organization name
            settings: New organization settings

        Returns:
            Organization: Updated organization

        Raises:
            ResourceNotFoundError: Organization not found
            DatabaseError: Database operation failed
        """
        try:
            org = await self.get_organization(org_id)

            if name:
                org.name = name
            if settings is not None:
                org.settings = settings

            await self.session.commit()

            logger.info("Organization updated", extra={"org_id": org_id})

            # Re-query with members to ensure relationships are loaded
            return await self.get_organization(org_id)

        except ResourceNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to update organization")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to update organization", context={"org_id": org_id, "error": str(e)}
            ) from e

    async def delete_organization(self, org_id: str) -> None:
        """
        Delete organization (soft delete by setting is_active=False).

        Args:
            org_id: Organization ID

        Raises:
            ResourceNotFoundError: Organization not found
            DatabaseError: Database operation failed
        """
        try:
            org = await self.get_organization(org_id)
            org.is_active = False

            await self.session.commit()

            logger.info("Organization deleted (soft)", extra={"org_id": org_id})

        except ResourceNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to delete organization")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to delete organization", context={"org_id": org_id, "error": str(e)}
            ) from e

    # =========================================================================
    # Membership Management
    # =========================================================================

    async def invite_member(
        self, org_id: str, user_id: str, role: str, invited_by: str, tenant_key: str
    ) -> OrgMembership:
        """
        Invite user to organization.

        Args:
            org_id: Organization ID
            user_id: User ID to invite
            role: Role to assign (admin, member, viewer)
            invited_by: User ID of inviter
            tenant_key: Tenant isolation key

        Returns:
            OrgMembership: Created membership

        Raises:
            AlreadyExistsError: User is already a member
            ValidationError: Invalid role specified
            DatabaseError: Database operation failed
        """
        try:
            # Check if already a member
            existing = await self._get_membership(org_id, user_id)
            if existing:
                raise AlreadyExistsError(
                    message="User is already a member of this organization",
                    context={"org_id": org_id, "user_id": user_id},
                )

            # Validate role
            if role not in ("admin", "member", "viewer"):
                raise ValidationError(
                    message=f"Invalid role: {role}. Must be admin, member, or viewer",
                    context={"role": role, "valid_roles": ["admin", "member", "viewer"]},
                )

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

            return membership

        except (AlreadyExistsError, ValidationError):
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to invite member")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to invite member", context={"org_id": org_id, "user_id": user_id, "error": str(e)}
            ) from e

    async def remove_member(self, org_id: str, user_id: str) -> None:
        """
        Remove member from organization.

        Args:
            org_id: Organization ID
            user_id: User ID to remove

        Raises:
            ResourceNotFoundError: User is not a member
            AuthorizationError: Cannot remove owner (must transfer first)
            DatabaseError: Database operation failed
        """
        try:
            membership = await self._get_membership(org_id, user_id)

            if not membership:
                raise ResourceNotFoundError(
                    message="User is not a member", context={"org_id": org_id, "user_id": user_id}
                )

            if membership.role == "owner":
                raise AuthorizationError(
                    message="Cannot remove owner. Transfer ownership first.",
                    context={"org_id": org_id, "user_id": user_id, "role": "owner"},
                )

            await self.session.delete(membership)
            await self.session.commit()

            logger.info("Member removed from organization", extra={"org_id": org_id, "user_id": user_id})

        except (ResourceNotFoundError, AuthorizationError):
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to remove member")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to remove member", context={"org_id": org_id, "user_id": user_id, "error": str(e)}
            ) from e

    async def change_member_role(self, org_id: str, user_id: str, new_role: str) -> OrgMembership:
        """
        Change member's role in organization.

        Args:
            org_id: Organization ID
            user_id: User ID whose role to change
            new_role: New role to assign

        Returns:
            OrgMembership: Updated membership

        Raises:
            ResourceNotFoundError: User is not a member
            AuthorizationError: Cannot change owner role (must use transfer_ownership)
            ValidationError: Invalid role specified
            DatabaseError: Database operation failed
        """
        try:
            membership = await self._get_membership(org_id, user_id)

            if not membership:
                raise ResourceNotFoundError(
                    message="User is not a member", context={"org_id": org_id, "user_id": user_id}
                )

            if membership.role == "owner":
                raise AuthorizationError(
                    message="Cannot change owner role. Use transfer_ownership instead.",
                    context={"org_id": org_id, "user_id": user_id, "role": "owner"},
                )

            if new_role not in ("admin", "member", "viewer"):
                raise ValidationError(
                    message=f"Invalid role: {new_role}",
                    context={"new_role": new_role, "valid_roles": ["admin", "member", "viewer"]},
                )

            membership.role = new_role
            await self.session.commit()

            logger.info("Member role changed", extra={"org_id": org_id, "user_id": user_id, "new_role": new_role})

            return membership

        except (ResourceNotFoundError, AuthorizationError, ValidationError):
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to change member role")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to change member role", context={"org_id": org_id, "user_id": user_id, "error": str(e)}
            ) from e

    async def transfer_ownership(self, org_id: str, current_owner_id: str, new_owner_id: str) -> None:
        """
        Transfer organization ownership to another member.

        Args:
            org_id: Organization ID
            current_owner_id: Current owner's user ID
            new_owner_id: New owner's user ID

        Raises:
            AuthorizationError: Current user is not owner
            ResourceNotFoundError: New owner is not a member
            DatabaseError: Database operation failed
        """
        try:
            # Verify current owner
            current = await self._get_membership(org_id, current_owner_id)
            if not current or current.role != "owner":
                raise AuthorizationError(
                    message="Only owner can transfer ownership", context={"org_id": org_id, "user_id": current_owner_id}
                )

            # Verify new owner is a member
            new_owner = await self._get_membership(org_id, new_owner_id)
            if not new_owner:
                raise ResourceNotFoundError(
                    message="New owner must be a member", context={"org_id": org_id, "user_id": new_owner_id}
                )

            # Transfer
            current.role = "admin"  # Demote to admin
            new_owner.role = "owner"

            await self.session.commit()

            logger.info("Ownership transferred", extra={"org_id": org_id, "from": current_owner_id, "to": new_owner_id})

        except (AuthorizationError, ResourceNotFoundError):
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.exception("Failed to transfer ownership")
            await self.session.rollback()
            raise DatabaseError(
                message="Failed to transfer ownership",
                context={"org_id": org_id, "from": current_owner_id, "to": new_owner_id, "error": str(e)},
            ) from e

    async def list_members(self, org_id: str) -> list[OrgMembership]:
        """
        List all members of organization.

        Args:
            org_id: Organization ID

        Returns:
            list[OrgMembership]: List of active memberships

        Raises:
            DatabaseError: Database operation failed
        """
        try:
            stmt = (
                select(OrgMembership)
                .where(OrgMembership.org_id == org_id, OrgMembership.is_active)
                .order_by(OrgMembership.joined_at)
            )

            result = await self.session.execute(stmt)
            members = result.scalars().all()

            return list(members)

        except SQLAlchemyError as e:
            logger.exception("Failed to list members")
            raise DatabaseError(message="Failed to list members", context={"org_id": org_id, "error": str(e)}) from e

    # =========================================================================
    # User Queries
    # =========================================================================

    async def get_user_organizations(self, user_id: str) -> list[Organization]:
        """
        Get all organizations for a user.

        Args:
            user_id: User ID

        Returns:
            list[Organization]: List of organizations user is a member of

        Raises:
            DatabaseError: Database operation failed
        """
        try:
            stmt = (
                select(Organization)
                .join(OrgMembership, Organization.id == OrgMembership.org_id)
                .where(OrgMembership.user_id == user_id, OrgMembership.is_active, Organization.is_active)
                .options(selectinload(Organization.members))
            )

            result = await self.session.execute(stmt)
            orgs = result.scalars().all()

            return list(orgs)

        except SQLAlchemyError as e:
            logger.exception("Failed to get user organizations")
            raise DatabaseError(
                message="Failed to get user organizations", context={"user_id": user_id, "error": str(e)}
            ) from e

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
