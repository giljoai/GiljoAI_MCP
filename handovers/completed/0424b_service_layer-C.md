# Handover 0424b: Organization Service Layer

**Date:** 2026-01-19
**From Agent:** Planning Session
**To Agent:** tdd-implementor / database-expert
**Priority:** HIGH
**Estimated Complexity:** 6-8 hours
**Status:** Ready for Implementation
**Parent:** 0424_org_hierarchy_overview.md
**Depends On:** 0424a (Database Schema)

---

## Summary

Create service layer for Organization management:
- `OrgService` - Business logic for org CRUD and membership management
- `OrgRepository` - Data access layer for organizations
- Update `AuthService` to create default org on registration

---

## TDD Discipline

Follow RED -> GREEN -> REFACTOR for all implementation.

```bash
# Create test files FIRST
touch tests/services/test_org_service.py
touch tests/repositories/test_org_repository.py

# Write failing tests
pytest tests/services/test_org_service.py -v
# MUST SEE: FAILED (RED)

# Implement service
pytest tests/services/test_org_service.py -v
# MUST SEE: PASSED (GREEN)
```

---

## Implementation Plan

### Step 1: Create Test File (tests/services/test_org_service.py)

```python
"""Tests for OrgService - organization management business logic."""
import pytest
from src.giljo_mcp.services.org_service import OrgService
from src.giljo_mcp.models.organizations import Organization, OrgMembership


class TestOrgServiceCreation:
    """Tests for organization creation."""

    @pytest.mark.asyncio
    async def test_create_org_with_owner(self, db_session, test_user):
        """Test creating org automatically creates owner membership."""
        service = OrgService(db_session)

        result = await service.create_organization(
            name="Test Company",
            slug="test-company",
            owner_id=test_user.id
        )

        assert result["success"] is True
        org = result["data"]
        assert org.name == "Test Company"
        assert org.slug == "test-company"
        assert len(org.members) == 1
        assert org.members[0].user_id == test_user.id
        assert org.members[0].role == "owner"

    @pytest.mark.asyncio
    async def test_create_org_generates_slug(self, db_session, test_user):
        """Test slug is auto-generated from name if not provided."""
        service = OrgService(db_session)

        result = await service.create_organization(
            name="My Awesome Company!",
            owner_id=test_user.id
        )

        assert result["success"] is True
        assert result["data"].slug == "my-awesome-company"

    @pytest.mark.asyncio
    async def test_create_org_duplicate_slug_fails(self, db_session, test_user):
        """Test duplicate slug returns error."""
        service = OrgService(db_session)

        await service.create_organization(
            name="First Org",
            slug="same-slug",
            owner_id=test_user.id
        )

        result = await service.create_organization(
            name="Second Org",
            slug="same-slug",
            owner_id=test_user.id
        )

        assert result["success"] is False
        assert "slug" in result["error"].lower()


class TestOrgServiceMembership:
    """Tests for membership management."""

    @pytest.mark.asyncio
    async def test_invite_member_to_org(self, db_session, test_user, test_user_2):
        """Test inviting a member to organization."""
        service = OrgService(db_session)

        # Create org with test_user as owner
        org_result = await service.create_organization(
            name="Test Org",
            slug="test-invite",
            owner_id=test_user.id
        )
        org = org_result["data"]

        # Invite test_user_2 as member
        result = await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id
        )

        assert result["success"] is True
        membership = result["data"]
        assert membership.org_id == org.id
        assert membership.user_id == test_user_2.id
        assert membership.role == "member"
        assert membership.invited_by == test_user.id

    @pytest.mark.asyncio
    async def test_invite_duplicate_member_fails(self, db_session, test_user, test_user_2):
        """Test inviting same user twice returns error."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-dup",
            owner_id=test_user.id
        )
        org = org_result["data"]

        # First invite
        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id
        )

        # Second invite (same user)
        result = await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="admin",
            invited_by=test_user.id
        )

        assert result["success"] is False
        assert "already" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_change_member_role(self, db_session, test_user, test_user_2):
        """Test changing a member's role."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-role-change",
            owner_id=test_user.id
        )
        org = org_result["data"]

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id
        )

        result = await service.change_member_role(
            org_id=org.id,
            user_id=test_user_2.id,
            new_role="admin"
        )

        assert result["success"] is True
        assert result["data"].role == "admin"

    @pytest.mark.asyncio
    async def test_cannot_change_owner_role(self, db_session, test_user):
        """Test owner role cannot be changed (must transfer instead)."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-owner-role",
            owner_id=test_user.id
        )
        org = org_result["data"]

        result = await service.change_member_role(
            org_id=org.id,
            user_id=test_user.id,
            new_role="admin"
        )

        assert result["success"] is False
        assert "owner" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_remove_member_from_org(self, db_session, test_user, test_user_2):
        """Test removing a member from organization."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-remove",
            owner_id=test_user.id
        )
        org = org_result["data"]

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id
        )

        result = await service.remove_member(
            org_id=org.id,
            user_id=test_user_2.id
        )

        assert result["success"] is True

        # Verify member removed
        members = await service.list_members(org.id)
        assert len(members["data"]) == 1  # Only owner remains

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(self, db_session, test_user):
        """Test owner cannot be removed (must transfer first)."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-remove-owner",
            owner_id=test_user.id
        )
        org = org_result["data"]

        result = await service.remove_member(
            org_id=org.id,
            user_id=test_user.id
        )

        assert result["success"] is False
        assert "owner" in result["error"].lower()


class TestOrgServiceQuery:
    """Tests for organization queries."""

    @pytest.mark.asyncio
    async def test_get_user_organizations(self, db_session, test_user):
        """Test getting all orgs for a user."""
        service = OrgService(db_session)

        await service.create_organization(
            name="Org 1",
            slug="user-org-1",
            owner_id=test_user.id
        )
        await service.create_organization(
            name="Org 2",
            slug="user-org-2",
            owner_id=test_user.id
        )

        result = await service.get_user_organizations(test_user.id)

        assert result["success"] is True
        assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_org_by_slug(self, db_session, test_user):
        """Test getting org by slug."""
        service = OrgService(db_session)

        await service.create_organization(
            name="Test Org",
            slug="find-by-slug",
            owner_id=test_user.id
        )

        result = await service.get_organization_by_slug("find-by-slug")

        assert result["success"] is True
        assert result["data"].name == "Test Org"

    @pytest.mark.asyncio
    async def test_get_user_role_in_org(self, db_session, test_user, test_user_2):
        """Test getting user's role in org."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-role-query",
            owner_id=test_user.id
        )
        org = org_result["data"]

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="admin",
            invited_by=test_user.id
        )

        owner_role = await service.get_user_role(org.id, test_user.id)
        admin_role = await service.get_user_role(org.id, test_user_2.id)

        assert owner_role == "owner"
        assert admin_role == "admin"


class TestOrgServicePermissions:
    """Tests for permission checks."""

    @pytest.mark.asyncio
    async def test_user_can_manage_members_as_owner(self, db_session, test_user):
        """Test owner can manage members."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-perm-owner",
            owner_id=test_user.id
        )
        org = org_result["data"]

        can_manage = await service.can_manage_members(org.id, test_user.id)
        assert can_manage is True

    @pytest.mark.asyncio
    async def test_user_can_manage_members_as_admin(self, db_session, test_user, test_user_2):
        """Test admin can manage members."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-perm-admin",
            owner_id=test_user.id
        )
        org = org_result["data"]

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="admin",
            invited_by=test_user.id
        )

        can_manage = await service.can_manage_members(org.id, test_user_2.id)
        assert can_manage is True

    @pytest.mark.asyncio
    async def test_member_cannot_manage_members(self, db_session, test_user, test_user_2):
        """Test member cannot manage other members."""
        service = OrgService(db_session)

        org_result = await service.create_organization(
            name="Test Org",
            slug="test-perm-member",
            owner_id=test_user.id
        )
        org = org_result["data"]

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id
        )

        can_manage = await service.can_manage_members(org.id, test_user_2.id)
        assert can_manage is False
```

### Step 2: Create OrgService (src/giljo_mcp/services/org_service.py)

```python
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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.models.organizations import Organization, OrgMembership
from src.giljo_mcp.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class OrgService:
    """Service for organization management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Organization CRUD
    # =========================================================================

    async def create_organization(
        self,
        name: str,
        owner_id: str,
        slug: Optional[str] = None,
        settings: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Create organization with owner.

        Args:
            name: Organization display name
            owner_id: User ID who will be owner
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
                return {
                    "success": False,
                    "error": f"Organization with slug '{slug}' already exists"
                }

            # Create organization
            org = Organization(
                name=name,
                slug=slug,
                settings=settings or {}
            )
            self.session.add(org)
            await self.session.flush()  # Get org.id

            # Create owner membership
            owner_membership = OrgMembership(
                org_id=org.id,
                user_id=owner_id,
                role="owner"
            )
            self.session.add(owner_membership)

            await self.session.commit()
            await self.session.refresh(org, ["members"])

            logger.info(
                "Organization created",
                extra={
                    "org_id": org.id,
                    "slug": slug,
                    "owner_id": owner_id
                }
            )

            # Emit WebSocket event
            await websocket_manager.broadcast_to_user(
                user_id=owner_id,
                event="org:created",
                data={"org_id": org.id, "name": name, "slug": slug}
            )

            return {"success": True, "data": org}

        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def get_organization(self, org_id: str) -> dict[str, Any]:
        """Get organization by ID."""
        try:
            stmt = select(Organization).where(
                Organization.id == org_id
            ).options(selectinload(Organization.members))

            result = await self.session.execute(stmt)
            org = result.scalar_one_or_none()

            if not org:
                return {"success": False, "error": "Organization not found"}

            return {"success": True, "data": org}

        except Exception as e:
            logger.error(f"Failed to get organization: {e}")
            return {"success": False, "error": str(e)}

    async def get_organization_by_slug(self, slug: str) -> dict[str, Any]:
        """Get organization by slug."""
        try:
            stmt = select(Organization).where(
                Organization.slug == slug
            ).options(selectinload(Organization.members))

            result = await self.session.execute(stmt)
            org = result.scalar_one_or_none()

            if not org:
                return {"success": False, "error": "Organization not found"}

            return {"success": True, "data": org}

        except Exception as e:
            logger.error(f"Failed to get organization by slug: {e}")
            return {"success": False, "error": str(e)}

    async def update_organization(
        self,
        org_id: str,
        name: Optional[str] = None,
        settings: Optional[dict] = None
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

            logger.info(
                "Organization updated",
                extra={"org_id": org_id}
            )

            return {"success": True, "data": org}

        except Exception as e:
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

            logger.info(
                "Organization deleted (soft)",
                extra={"org_id": org_id}
            )

            return {"success": True, "data": {"deleted": True}}

        except Exception as e:
            logger.error(f"Failed to delete organization: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Membership Management
    # =========================================================================

    async def invite_member(
        self,
        org_id: str,
        user_id: str,
        role: str,
        invited_by: str
    ) -> dict[str, Any]:
        """
        Invite user to organization.

        Args:
            org_id: Organization ID
            user_id: User ID to invite
            role: Role to assign (admin, member, viewer)
            invited_by: User ID of inviter

        Returns:
            dict with 'success' bool and 'data' or 'error'
        """
        try:
            # Check if already a member
            existing = await self._get_membership(org_id, user_id)
            if existing:
                return {
                    "success": False,
                    "error": "User is already a member of this organization"
                }

            # Validate role
            if role not in ("admin", "member", "viewer"):
                return {
                    "success": False,
                    "error": f"Invalid role: {role}. Must be admin, member, or viewer"
                }

            membership = OrgMembership(
                org_id=org_id,
                user_id=user_id,
                role=role,
                invited_by=invited_by
            )
            self.session.add(membership)
            await self.session.commit()

            logger.info(
                "Member invited to organization",
                extra={
                    "org_id": org_id,
                    "user_id": user_id,
                    "role": role,
                    "invited_by": invited_by
                }
            )

            # Emit WebSocket event
            await websocket_manager.broadcast_to_user(
                user_id=user_id,
                event="org:invited",
                data={"org_id": org_id, "role": role}
            )

            return {"success": True, "data": membership}

        except Exception as e:
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
                return {
                    "success": False,
                    "error": "Cannot remove owner. Transfer ownership first."
                }

            await self.session.delete(membership)
            await self.session.commit()

            logger.info(
                "Member removed from organization",
                extra={"org_id": org_id, "user_id": user_id}
            )

            return {"success": True, "data": {"removed": True}}

        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def change_member_role(
        self,
        org_id: str,
        user_id: str,
        new_role: str
    ) -> dict[str, Any]:
        """Change member's role in organization."""
        try:
            membership = await self._get_membership(org_id, user_id)

            if not membership:
                return {"success": False, "error": "User is not a member"}

            if membership.role == "owner":
                return {
                    "success": False,
                    "error": "Cannot change owner role. Use transfer_ownership instead."
                }

            if new_role not in ("admin", "member", "viewer"):
                return {
                    "success": False,
                    "error": f"Invalid role: {new_role}"
                }

            membership.role = new_role
            await self.session.commit()

            logger.info(
                "Member role changed",
                extra={
                    "org_id": org_id,
                    "user_id": user_id,
                    "new_role": new_role
                }
            )

            return {"success": True, "data": membership}

        except Exception as e:
            logger.error(f"Failed to change member role: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def transfer_ownership(
        self,
        org_id: str,
        current_owner_id: str,
        new_owner_id: str
    ) -> dict[str, Any]:
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

            logger.info(
                "Ownership transferred",
                extra={
                    "org_id": org_id,
                    "from": current_owner_id,
                    "to": new_owner_id
                }
            )

            return {"success": True, "data": {"transferred": True}}

        except Exception as e:
            logger.error(f"Failed to transfer ownership: {e}")
            await self.session.rollback()
            return {"success": False, "error": str(e)}

    async def list_members(self, org_id: str) -> dict[str, Any]:
        """List all members of organization."""
        try:
            stmt = select(OrgMembership).where(
                OrgMembership.org_id == org_id,
                OrgMembership.is_active == True
            ).order_by(OrgMembership.joined_at)

            result = await self.session.execute(stmt)
            members = result.scalars().all()

            return {"success": True, "data": list(members)}

        except Exception as e:
            logger.error(f"Failed to list members: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # User Queries
    # =========================================================================

    async def get_user_organizations(self, user_id: str) -> dict[str, Any]:
        """Get all organizations for a user."""
        try:
            stmt = select(Organization).join(
                OrgMembership,
                Organization.id == OrgMembership.org_id
            ).where(
                OrgMembership.user_id == user_id,
                OrgMembership.is_active == True,
                Organization.is_active == True
            ).options(selectinload(Organization.members))

            result = await self.session.execute(stmt)
            orgs = result.scalars().all()

            return {"success": True, "data": list(orgs)}

        except Exception as e:
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

    async def _get_membership(
        self,
        org_id: str,
        user_id: str
    ) -> Optional[OrgMembership]:
        """Get membership for user in org."""
        stmt = select(OrgMembership).where(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user_id,
            OrgMembership.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name."""
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'[\s_-]+', '-', slug)  # Replace spaces with hyphens
        slug = slug.strip('-')
        return slug
```

### Step 3: Update AuthService for Default Org (src/giljo_mcp/services/auth_service.py)

Add this method and call it during registration:

```python
async def _create_default_organization(
    self,
    user_id: str,
    username: str
) -> dict[str, Any]:
    """Create default personal organization for new user."""
    from src.giljo_mcp.services.org_service import OrgService

    org_service = OrgService(self.session)

    return await org_service.create_organization(
        name=f"{username}'s Workspace",
        slug=f"{username}-workspace",
        owner_id=user_id
    )
```

Then call it in `register_user()` after creating the user:

```python
async def register_user(self, user_data: dict) -> dict[str, Any]:
    # ... existing user creation code ...

    # Create default organization (Handover 0424b)
    org_result = await self._create_default_organization(
        user_id=user.id,
        username=user.username
    )

    if not org_result["success"]:
        logger.warning(
            f"Failed to create default org for user {user.id}: {org_result['error']}"
        )

    return {"success": True, "data": user}
```

---

## Files to Create/Modify

### NEW Files:
```
□ src/giljo_mcp/services/org_service.py (~350 lines)
□ tests/services/test_org_service.py (~300 lines)
```

### MODIFIED Files:
```
□ src/giljo_mcp/services/__init__.py (1 line - export)
□ src/giljo_mcp/services/auth_service.py (~20 lines - default org)
```

---

## Expected Test Results

```bash
# Service tests
pytest tests/services/test_org_service.py -v
# Expected: 15+ tests passed (GREEN)

# Full suite (no regressions)
pytest tests/ -v
# Expected: All existing tests pass
```

---

## Verification Checklist

- [ ] OrgService implements all CRUD operations
- [ ] Membership management works (invite, remove, change role)
- [ ] Owner protection enforced (cannot remove, cannot change role)
- [ ] Permission checks work for all role levels
- [ ] Default org created on user registration
- [ ] WebSocket events emitted for org changes
- [ ] Structured logging for all operations
- [ ] All tests pass (>80% coverage)

---

## Dependencies

- **Depends on:** 0424a (Database Schema - models must exist)
- **Blocks:** 0424c (API Endpoints need service)

---

## Notes for Implementing Agent

1. **Test first** - Write test_org_service.py before service
2. **Follow service pattern** - Match existing services (ProductService, etc.)
3. **Multi-tenant aware** - Users only see their orgs
4. **WebSocket events** - Emit for real-time UI updates
5. **Structured logging** - All operations logged with metadata

---

## Success Criteria

- [ ] All 15+ service tests pass
- [ ] OrgService follows existing service patterns
- [ ] Permission checks work correctly
- [ ] Default org created on registration
- [ ] No regressions in auth flow
- [ ] Coverage >80% for new code

---

## Chain Execution Instructions

**This handover is part of a multi-terminal chain. Follow these instructions EXACTLY.**

### Step 1: Read Chain Log

Read `prompts/0424_chain/chain_log.json`:
- Review `0424a` session's `notes_for_next` for critical context
- Verify `0424a` status is `complete`
- If `0424a` is `blocked` or `failed`, STOP and report to user

### Step 2: Mark Session Started

Update chain_log.json session `0424b`:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover Tasks

**CRITICAL: Use Task tool subagents for ALL implementation work. Do NOT do work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Read handover 0424b at F:\GiljoAI_MCP\handovers\0424b_service_layer.md. Implement OrgService with TDD - write tests first, then service code.")
```

**Required subagents:**
- `tdd-implementor` - For test-first service implementation
- `database-expert` - For repository pattern and query optimization

### Step 4: Update Chain Log Before Spawning Next

Update chain_log.json session `0424b`:
```json
{
  "status": "complete",
  "completed_at": "<current ISO timestamp>",
  "tasks_completed": ["<list what you actually did>"],
  "deviations": ["<any changes from plan, or empty>"],
  "blockers_encountered": ["<any issues, or empty>"],
  "notes_for_next": "<critical info for 0424c API endpoints>",
  "summary": "<2-3 sentence summary>"
}
```

### Step 5: Commit Your Work

**Before spawning next terminal, commit all changes:**
```bash
git add .
git commit -m "feat(0424b): Add OrgService and OrgRepository

- Create OrgService with CRUD and membership management
- Create OrgRepository for data access
- Update AuthService for default org on registration
- Add 15+ service tests (all passing)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 6: Spawn Next Terminal

**Use Bash tool to EXECUTE this command (don't just print it!):**

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0424c - API Endpoints\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0424c. READ: F:\GiljoAI_MCP\handovers\0424c_api_endpoints.md\"' -Verb RunAs"
```
