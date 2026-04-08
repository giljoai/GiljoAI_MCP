# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for OrgService - organization management business logic.

Handover 0424b: TDD implementation of organization service layer.

This test suite follows TDD discipline (Red → Green → Refactor):
1. Tests written FIRST (this file)
2. All tests must FAIL initially (RED phase)
3. Implementation makes tests pass (GREEN phase)
4. Refactor for quality (REFACTOR phase)

Test Coverage:
- Organization creation with owner
- Slug generation and uniqueness validation
- Membership management (invite, remove, change role)
- Owner protection (cannot remove, cannot change role)
- Permission checks (can_manage_members, can_edit_org, etc.)
- User organization queries
- Organization lookup by slug
- Role queries
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.exceptions import AlreadyExistsError, AuthorizationError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.services.org_service import OrgService


# Fixtures


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user for organization testing"""

    # Create org first (0424m: tenant_key required)
    tenant_key = f"tenant_{uuid4().hex[:8]}"
    org = Organization(
        name=f"Test Org {uuid4().hex[:8]}", slug=f"test-org-{uuid4().hex[:8]}", tenant_key=tenant_key, is_active=True
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=tenant_key,
        role="developer",
        password_hash="hashed_password",
        is_active=True,
        org_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_2(db_session):
    """Create second test user for membership testing"""

    # Create org first (0424m: tenant_key required)
    tenant_key = f"tenant2_{uuid4().hex[:8]}"
    org = Organization(
        name=f"Test Org 2 {uuid4().hex[:8]}",
        slug=f"test-org-2-{uuid4().hex[:8]}",
        tenant_key=tenant_key,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        username=f"testuser2_{uuid4().hex[:8]}",
        email=f"test2_{uuid4().hex[:8]}@example.com",
        tenant_key=tenant_key,
        role="developer",
        password_hash="hashed_password",
        is_active=True,
        org_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestOrgServiceCreation:
    """Tests for organization creation."""

    @pytest.mark.asyncio
    async def test_create_org_with_owner(self, db_session, test_user):
        """Test creating org automatically creates owner membership."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Company", slug="test-company", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        assert org.name == "Test Company"
        assert org.slug == "test-company"
        assert len(org.members) == 1
        assert org.members[0].user_id == test_user.id
        assert org.members[0].role == "owner"

    @pytest.mark.asyncio
    async def test_create_org_generates_slug(self, db_session, test_user):
        """Test slug is auto-generated from name if not provided."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="My Awesome Company!", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        assert org.slug == "my-awesome-company"

    @pytest.mark.asyncio
    async def test_create_org_duplicate_slug_fails(self, db_session, test_user):
        """Test duplicate slug raises AlreadyExistsError."""
        service = OrgService(db_session)

        await service.create_organization(
            name="First Org", slug="same-slug", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        with pytest.raises(AlreadyExistsError) as exc_info:
            await service.create_organization(
                name="Second Org", slug="same-slug", owner_id=test_user.id, tenant_key=test_user.tenant_key
            )

        assert "slug" in str(exc_info.value).lower()


class TestOrgServiceMembership:
    """Tests for membership management."""

    @pytest.mark.asyncio
    async def test_invite_member_to_org(self, db_session, test_user, test_user_2):
        """Test inviting a member to organization."""
        service = OrgService(db_session)

        # Create org with test_user as owner
        org = await service.create_organization(
            name="Test Org", slug="test-invite", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        # Invite test_user_2 as member
        membership = await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id,
            tenant_key=test_user.tenant_key,
        )

        assert membership.org_id == org.id
        assert membership.user_id == test_user_2.id
        assert membership.role == "member"
        assert membership.invited_by == test_user.id

    @pytest.mark.asyncio
    async def test_invite_duplicate_member_fails(self, db_session, test_user, test_user_2):
        """Test inviting same user twice raises AlreadyExistsError."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-dup", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        # First invite
        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id,
            tenant_key=test_user.tenant_key,
        )

        # Second invite (same user)
        with pytest.raises(AlreadyExistsError) as exc_info:
            await service.invite_member(
                org_id=org.id,
                user_id=test_user_2.id,
                role="admin",
                invited_by=test_user.id,
                tenant_key=test_user.tenant_key,
            )

        assert "already" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_change_member_role(self, db_session, test_user, test_user_2):
        """Test changing a member's role."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-role-change", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id,
            tenant_key=test_user.tenant_key,
        )

        membership = await service.change_member_role(org_id=org.id, user_id=test_user_2.id, new_role="admin")

        assert membership.role == "admin"

    @pytest.mark.asyncio
    async def test_cannot_change_owner_role(self, db_session, test_user):
        """Test owner role cannot be changed (raises AuthorizationError)."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-owner-role", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        with pytest.raises(AuthorizationError) as exc_info:
            await service.change_member_role(org_id=org.id, user_id=test_user.id, new_role="admin")

        assert "owner" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_remove_member_from_org(self, db_session, test_user, test_user_2):
        """Test removing a member from organization."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-remove", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id,
            tenant_key=test_user.tenant_key,
        )

        await service.remove_member(org_id=org.id, user_id=test_user_2.id)

        # Verify member removed
        members = await service.list_members(org.id)
        assert len(members) == 1  # Only owner remains

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(self, db_session, test_user):
        """Test owner cannot be removed (raises AuthorizationError)."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-remove-owner", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        with pytest.raises(AuthorizationError) as exc_info:
            await service.remove_member(org_id=org.id, user_id=test_user.id)

        assert "owner" in str(exc_info.value).lower()


class TestOrgServiceQuery:
    """Tests for organization queries."""

    @pytest.mark.asyncio
    async def test_get_user_organizations(self, db_session, test_user):
        """Test getting all orgs for a user."""
        service = OrgService(db_session)

        await service.create_organization(
            name="Org 1", slug="user-org-1", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )
        await service.create_organization(
            name="Org 2", slug="user-org-2", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        orgs = await service.get_user_organizations(test_user.id)

        assert len(orgs) == 2

    @pytest.mark.asyncio
    async def test_get_org_by_slug(self, db_session, test_user):
        """Test getting org by slug."""
        service = OrgService(db_session)

        await service.create_organization(
            name="Test Org", slug="find-by-slug", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        org = await service.get_organization_by_slug("find-by-slug")

        assert org.name == "Test Org"

    @pytest.mark.asyncio
    async def test_get_user_role_in_org(self, db_session, test_user, test_user_2):
        """Test getting user's role in org."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-role-query", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="admin",
            invited_by=test_user.id,
            tenant_key=test_user.tenant_key,
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

        org = await service.create_organization(
            name="Test Org", slug="test-perm-owner", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        can_manage = await service.can_manage_members(org.id, test_user.id)
        assert can_manage is True

    @pytest.mark.asyncio
    async def test_user_can_manage_members_as_admin(self, db_session, test_user, test_user_2):
        """Test admin can manage members."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-perm-admin", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="admin",
            invited_by=test_user.id,
            tenant_key=test_user.tenant_key,
        )

        can_manage = await service.can_manage_members(org.id, test_user_2.id)
        assert can_manage is True

    @pytest.mark.asyncio
    async def test_member_cannot_manage_members(self, db_session, test_user, test_user_2):
        """Test member cannot manage other members."""
        service = OrgService(db_session)

        org = await service.create_organization(
            name="Test Org", slug="test-perm-member", owner_id=test_user.id, tenant_key=test_user.tenant_key
        )

        await service.invite_member(
            org_id=org.id,
            user_id=test_user_2.id,
            role="member",
            invited_by=test_user.id,
            tenant_key=test_user.tenant_key,
        )

        can_manage = await service.can_manage_members(org.id, test_user_2.id)
        assert can_manage is False
